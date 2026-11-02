#!/usr/bin/env python3
"""Idempotent retain: re-sending an observation that carries the same
refs.idempotency_key (or refs.event_id) in the same domain returns the existing
memory and performs no embedding, insert or background scoring.

Runs without Postgres: the store and embedder are fakes that record calls."""

import asyncio
import json
import unittest

import asyncpg
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from unittest.mock import patch

import server
from server import (
    IDEMPOTENCY_KEY_MAX_CHARS,
    ColdStore,
    IdempotencyKeyError,
    IngestAgent,
    _idempotency_key_from_refs,
    _normalize_refs,
)


class FakeStore:
    def __init__(self):
        self.rows: list[dict] = []
        self.lookups: list[tuple[str, str]] = []

    async def find_by_idempotency_key(self, domain, key):
        self.lookups.append((domain, key))
        # Mirrors ColdStore.IDEMPOTENCY_LOOKUP_SQL: only the materialized idempotency_key field.
        for r in self.rows:
            refs = r["refs"] or {}
            if r["domain"] == domain and "idempotency_key" in refs and refs["idempotency_key"] == key:
                return {"id": r["id"], "state": r["state"], "source": r["source"], "domain": r["domain"],
                        "created_at": datetime.now(timezone.utc)}
        return None

    async def insert_memory(self, mid, content, embedding, state, source, domain, importance, entities, topics,
                            witness_chain, memory_type="semantic", event_at=None, refs=None):
        refs = refs or {}
        # Mirrors memories_domain_idempotency_uidx.
        if "idempotency_key" in refs:
            for r in self.rows:
                if r["domain"] == domain and (r["refs"] or {}).get("idempotency_key") == refs["idempotency_key"]:
                    raise asyncpg.UniqueViolationError("duplicate key value violates unique constraint")
        self.rows.append({"id": mid, "content": content, "state": state, "source": source, "domain": domain,
                          "refs": refs})


class FakeEmbedder:
    _executor = ThreadPoolExecutor(max_workers=1)

    def __init__(self):
        self.calls = 0

    def embed(self, text):
        self.calls += 1
        return [0.0] * 8


def make_agent(store, embedder):
    with patch.object(server, "LocalSLMClient", lambda: object()):
        return IngestAgent(store, embedder, chat=None)


def run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


class IdempotencyKeyTests(unittest.TestCase):
    def test_key_precedence_and_coercion(self):
        self.assertEqual(_idempotency_key_from_refs({"idempotency_key": "k1", "event_id": "e1"}), "k1")
        self.assertEqual(_idempotency_key_from_refs({"event_id": "e1"}), "e1")
        self.assertEqual(_idempotency_key_from_refs({"event_id": 42}), "42")
        self.assertIsNone(_idempotency_key_from_refs({"event_id": "  "}))
        self.assertIsNone(_idempotency_key_from_refs({}))
        self.assertIsNone(_idempotency_key_from_refs(None))
        self.assertEqual(_idempotency_key_from_refs('{"idempotency_key": "from-json"}'), "from-json")
        with self.assertRaises(IdempotencyKeyError):
            _idempotency_key_from_refs({"event_id": "x" * (IDEMPOTENCY_KEY_MAX_CHARS + 1)})
        self.assertEqual(len(_idempotency_key_from_refs({"event_id": "y" * IDEMPOTENCY_KEY_MAX_CHARS})), IDEMPOTENCY_KEY_MAX_CHARS)

    def test_normalize_refs_materializes_trimmed_key_for_persistence(self):
        refs, key = _normalize_refs('{"event_id": "  v-9  ", "scan_id": "s"}')
        self.assertEqual(key, "v-9")
        self.assertEqual(refs, {"event_id": "  v-9  ", "scan_id": "s", "idempotency_key": "v-9"})
        refs, key = _normalize_refs({"idempotency_key": " explicit ", "event_id": "ignored"})
        self.assertEqual((key, refs["idempotency_key"]), ("explicit", "explicit"))
        self.assertEqual(_normalize_refs(None), ({}, None))
        self.assertEqual(_normalize_refs({"scan_id": "s"}), ({"scan_id": "s"}, None))


class IdempotentRetainTests(unittest.TestCase):
    def setUp(self):
        self._bg = server.ENABLE_BACKGROUND_SCORING
        self._cd = server.ENABLE_CONTRADICTION_DETECTION
        self._hp = server.ENABLE_HIERARCHY_PROCESSING
        server.ENABLE_BACKGROUND_SCORING = False
        server.ENABLE_CONTRADICTION_DETECTION = False
        server.ENABLE_HIERARCHY_PROCESSING = False
        self.store = FakeStore()
        self.embedder = FakeEmbedder()
        self.agent = make_agent(self.store, self.embedder)

    def tearDown(self):
        server.ENABLE_BACKGROUND_SCORING = self._bg
        server.ENABLE_CONTRADICTION_DETECTION = self._cd
        server.ENABLE_HIERARCHY_PROCESSING = self._hp

    def test_second_retain_with_same_event_id_is_a_duplicate(self):
        # Background scoring stays enabled here so the queue itself proves the duplicate path
        # never enqueues; the first retain adds exactly one entry, the second adds none.
        server.ENABLE_BACKGROUND_SCORING = True
        first = run(self.agent.ingest("Verdict CONTRADICTS on leverage claim.", source="listnr:x",
                                      domain="listnr:tenant-a:example.com", refs={"event_id": "v-a-003"}))
        self.assertNotIn("duplicate", first)
        self.assertEqual(len(self.store.rows), 1)
        self.assertEqual(self.embedder.calls, 1)

        second = run(self.agent.ingest("Verdict CONTRADICTS on leverage claim (resynced).", source="listnr:x",
                                       domain="listnr:tenant-a:example.com", refs={"event_id": "v-a-003"}))
        self.assertTrue(second["duplicate"])
        self.assertEqual(second["id"], first["id"])
        self.assertEqual(second["memory_id"], first["id"])
        self.assertEqual(second["idempotency_key"], "v-a-003")
        self.assertFalse(second["background_scoring_queued"])
        self.assertEqual(len(self.store.rows), 1, "no second insert")
        self.assertEqual(self.embedder.calls, 1, "no second embedding")
        self.assertEqual(len(self.agent._score_queue), 1, "duplicate path must not enqueue scoring")
        self.assertEqual(self.store.rows[0]["refs"]["idempotency_key"], "v-a-003", "key materialized on the stored row")

    def test_same_key_in_another_domain_is_a_new_memory(self):
        run(self.agent.ingest("x", domain="listnr:tenant-a:example.com", refs={"event_id": "v-1"}))
        other = run(self.agent.ingest("x", domain="listnr:tenant-b:example.com", refs={"event_id": "v-1"}))
        self.assertNotIn("duplicate", other)
        self.assertEqual(len(self.store.rows), 2)

    def test_explicit_idempotency_key_is_honoured(self):
        a = run(self.agent.ingest("x", domain="d", refs={"idempotency_key": "abc"}))
        b = run(self.agent.ingest("x", domain="d", refs={"idempotency_key": "abc", "event_id": "different"}))
        self.assertTrue(b["duplicate"])
        self.assertEqual(a["id"], b["id"])

    def test_event_id_alias_does_not_override_an_explicit_key(self):
        old = run(self.agent.ingest("old", domain="d", refs={"event_id": "e-1"}))
        new = run(self.agent.ingest("new", domain="d", refs={"idempotency_key": "k-new", "event_id": "e-1"}))
        self.assertNotIn("duplicate", new)
        self.assertNotEqual(old["id"], new["id"])
        self.assertEqual(len(self.store.rows), 2)

    def test_json_text_and_padded_refs_dedupe_on_retry(self):
        first = run(self.agent.ingest("x", domain="d", refs='{"event_id": " v-7 "}'))
        retry = run(self.agent.ingest("x", domain="d", refs={"event_id": "v-7"}))
        self.assertTrue(retry["duplicate"])
        self.assertEqual(retry["id"], first["id"])

    def test_concurrent_identical_retains_resolve_to_one_memory(self):
        """Both lookups miss, both insert; the unique index admits one and the other returns it."""
        async def race():
            return await asyncio.gather(
                self.agent.ingest("x", domain="d", refs={"event_id": "race"}),
                self.agent.ingest("x", domain="d", refs={"event_id": "race"}),
            )
        a, b = run(race())
        self.assertEqual(len(self.store.rows), 1)
        self.assertEqual({a["id"], b["id"]}, {self.store.rows[0]["id"]})
        self.assertEqual(sorted([a.get("duplicate", False), b.get("duplicate", False)]), [False, True])

    def test_no_key_means_no_lookup_and_no_dedupe(self):
        run(self.agent.ingest("same text", domain="d"))
        run(self.agent.ingest("same text", domain="d"))
        self.assertEqual(self.store.lookups, [])
        self.assertEqual(len(self.store.rows), 2)

    def test_diagnostics_record_the_lookup_stage(self):
        run(self.agent.ingest("x", domain="d", refs={"event_id": "e"}))
        diag: dict = {}
        res = run(self.agent.ingest("x", domain="d", refs={"event_id": "e"}, diagnostics=diag))
        self.assertTrue(res["duplicate"])
        self.assertEqual(diag["stage_order"], ["ingest.start", "idempotency.lookup"])
        self.assertIn("total_ms", diag["timings_ms"])


class _RecordingConn:
    def __init__(self, row):
        self.row = row
        self.calls = []

    async def fetchrow(self, sql, *args):
        self.calls.append((sql, args))
        return self.row


class _RecordingPool:
    def __init__(self, conn):
        self.conn = conn

    def acquire(self):
        pool = self

        class _Ctx:
            async def __aenter__(self_inner):
                return pool.conn

            async def __aexit__(self_inner, *exc):
                return False

        return _Ctx()


class ColdStoreLookupSQLTests(unittest.TestCase):
    """The production lookup, exercised through a recording connection: the SQL must consult
    only the materialized key, carry the partial-index predicate, and bind (domain, key)."""

    def _store(self, row):
        store = ColdStore.__new__(ColdStore)
        conn = _RecordingConn(row)
        store.pool = _RecordingPool(conn)
        return store, conn

    def test_sql_shape_and_bindings(self):
        store, conn = self._store({"id": "mem_1", "state": "observation", "source": "s", "domain": "d", "created_at": None})
        found = run(store.find_by_idempotency_key("d", "k"))
        self.assertEqual(found["id"], "mem_1")
        (sql, args), = conn.calls
        self.assertEqual(args, ("d", "k"))
        self.assertIn("refs ? 'idempotency_key'", sql)
        self.assertIn("refs->>'idempotency_key' = $2", sql)
        self.assertNotIn("event_id", sql)
        self.assertIn("domain = $1", sql)

    def test_miss_returns_none_and_empty_key_skips_the_query(self):
        store, conn = self._store(None)
        self.assertIsNone(run(store.find_by_idempotency_key("d", "k")))
        self.assertEqual(len(conn.calls), 1)
        self.assertIsNone(run(store.find_by_idempotency_key("d", "")))
        self.assertEqual(len(conn.calls), 1)


if __name__ == "__main__":
    unittest.main()
