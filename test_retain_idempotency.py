#!/usr/bin/env python3
"""Idempotent retain: re-sending an observation that carries the same
refs.idempotency_key (or refs.event_id) in the same domain returns the existing
memory and performs no embedding, insert or background scoring.

Runs without Postgres: the store and embedder are fakes that record calls."""

import asyncio
import os
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

    def test_normalize_refs_never_persists_a_blank_key(self):
        # The partial unique index keys on the field's presence, so a stored "" would make
        # every keyless retain in a domain collide with the next one.
        for blank in ("", "   ", None):
            refs, key = _normalize_refs({"idempotency_key": blank, "scan_id": "s"})
            self.assertIsNone(key)
            self.assertEqual(refs, {"scan_id": "s"})
        refs, key = _normalize_refs({"idempotency_key": "", "event_id": "e-1"})
        self.assertEqual((key, refs["idempotency_key"]), ("e-1", "e-1"))


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

    def test_two_retains_with_a_blank_key_both_succeed(self):
        a = run(self.agent.ingest("first", domain="d", refs={"idempotency_key": ""}))
        b = run(self.agent.ingest("second", domain="d", refs={"idempotency_key": "  "}))
        self.assertNotEqual(a["id"], b["id"])
        self.assertFalse(a.get("duplicate") or b.get("duplicate"))
        self.assertEqual(self.store.lookups, [])
        self.assertEqual([r["refs"] for r in self.store.rows], [{}, {}])

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


class _MigrationConn:
    """Records the migration's statements; `has_index` drives the existence probe."""

    def __init__(self, has_index):
        self.has_index = has_index
        self.calls: list[tuple[str, tuple]] = []
        self.in_tx = False
        self.tx_calls = 0

    async def fetchval(self, sql, *args):
        self.calls.append(("fetchval", sql, args))
        return 1 if self.has_index else None

    async def execute(self, sql, *args):
        assert self.in_tx, "migration statements must run inside the transaction"
        self.calls.append(("execute", sql, args))
        return "UPDATE 2"

    def transaction(self):
        conn = self

        class _Tx:
            async def __aenter__(self_inner):
                conn.in_tx = True
                conn.tx_calls += 1

            async def __aexit__(self_inner, *exc):
                conn.in_tx = False
                return False

        return _Tx()


class IdempotencyMigrationTests(unittest.TestCase):
    """Startup must make a pre-#12 database indexable: normalize, backfill, dedupe, then
    build the unique index, all in one transaction, and only when the index is absent."""

    def test_skips_entirely_when_the_index_exists(self):
        conn = _MigrationConn(has_index=True)
        self.assertIsNone(run(server.migrate_idempotency_keys(conn)))
        self.assertEqual([c[0] for c in conn.calls], ["fetchval"])
        self.assertEqual(conn.calls[0][2], (server.IDEMPOTENCY_INDEX_NAME,))

    def test_runs_steps_in_order_inside_one_transaction(self):
        conn = _MigrationConn(has_index=False)
        counts = run(server.migrate_idempotency_keys(conn))
        self.assertEqual(counts, {"normalized": 2, "backfilled": 2, "deduped": 2})
        self.assertEqual(conn.tx_calls, 1)
        executed = [sql for kind, sql, _ in conn.calls if kind == "execute"]
        self.assertEqual(executed[:3], [
            server.IDEMPOTENCY_MIGRATION_SQL["normalize"],
            server.IDEMPOTENCY_MIGRATION_SQL["backfill"],
            server.IDEMPOTENCY_MIGRATION_SQL["dedupe"],
        ])
        # backfill is bounded by the same limit the request path enforces
        backfill_args = [a for kind, sql, a in conn.calls if sql == server.IDEMPOTENCY_MIGRATION_SQL["backfill"]]
        self.assertEqual(backfill_args, [(IDEMPOTENCY_KEY_MAX_CHARS,)])
        self.assertIn("DROP INDEX IF EXISTS memories_domain_event_id_idx", executed[3])
        self.assertIn("DROP INDEX IF EXISTS memories_domain_idempotency_idx", executed[4])
        self.assertIn(f"CREATE UNIQUE INDEX {server.IDEMPOTENCY_INDEX_NAME}", executed[5])
        self.assertIn("WHERE refs ? 'idempotency_key'", executed[5])
        self.assertEqual(len(executed), 6)

    def test_migration_sql_guards_non_object_refs_and_dedupes_without_deleting(self):
        for sql in server.IDEMPOTENCY_MIGRATION_SQL.values():
            self.assertIn("jsonb_typeof(refs) = 'object'", sql)
            self.assertNotIn("DELETE", sql.upper())
        self.assertIn("ORDER BY created_at, id", server.IDEMPOTENCY_MIGRATION_SQL["dedupe"])
        self.assertIn("idempotency_duplicate_of", server.IDEMPOTENCY_MIGRATION_SQL["dedupe"])


@unittest.skipUnless(os.environ.get("MEMIBRIUM_TEST_DSN"), "set MEMIBRIUM_TEST_DSN to a disposable Postgres")
class IdempotencyMigrationPostgresTests(unittest.TestCase):
    """The migration against a real Postgres (needs only the refs/domain/created_at columns),
    seeded with every shape a PR #11 database can hold."""

    ROWS = [
        ("a1", "d1", {"idempotency_key": "k1", "event_id": "e1"}, "2026-01-01"),
        ("a2", "d1", {"idempotency_key": "k1 ", "event_id": "e1"}, "2026-01-02"),  # padded dup of a1
        ("a3", "d1", {"event_id": "e1"}, "2026-01-03"),                               # event_id only
        ("a4", "d2", {"event_id": "e1"}, "2026-01-01"),                               # other domain
        ("a5", "d1", {"idempotency_key": ""}, "2026-01-01"),                          # blank
        ("a6", "d1", {"idempotency_key": "  ", "event_id": "e6"}, "2026-01-01"),      # blank + event_id
        ("a7", "d1", {"idempotency_key": None, "event_id": "e7"}, "2026-01-01"),      # json null
        ("a8", "d1", {"idempotency_key": 123}, "2026-01-01"),                         # number
        ("a9", "d1", {"event_id": "x" * 300}, "2026-01-01"),                          # too long
        ("b1", "d1", [], "2026-01-01"),                                               # array refs
        ("b2", "d1", {"other": 1}, "2026-01-01"),
    ]

    def test_against_postgres(self):
        from datetime import date

        async def go():
            conn = await asyncpg.connect(os.environ["MEMIBRIUM_TEST_DSN"])
            try:
                await conn.execute("DROP TABLE IF EXISTS memories")
                await conn.execute("""CREATE TABLE memories (id TEXT PRIMARY KEY,
                    domain TEXT NOT NULL DEFAULT 'default', refs JSONB NOT NULL DEFAULT '{}',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())""")
                for id_, dom, refs, ts in self.ROWS:
                    await conn.execute(
                        "INSERT INTO memories (id, domain, refs, created_at) VALUES ($1,$2,$3::jsonb,$4::date)",
                        id_, dom, json.dumps(refs), date.fromisoformat(ts))
                await conn.execute("CREATE INDEX memories_domain_event_id_idx ON memories (domain, (refs->>'event_id'))")
                counts = await server.migrate_idempotency_keys(conn)
                rows = {r["id"]: json.loads(r["refs"]) for r in await conn.fetch("SELECT id, refs FROM memories")}
                idx = {r["indexname"] for r in await conn.fetch("SELECT indexname FROM pg_indexes WHERE tablename='memories'")}
                again = await server.migrate_idempotency_keys(conn)
                try:
                    await conn.execute("""INSERT INTO memories (id, domain, refs) VALUES ('zz','d1','{"idempotency_key":"k1"}')""")
                    rejected = False
                except asyncpg.UniqueViolationError:
                    rejected = True
                return counts, rows, idx, again, rejected
            finally:
                await conn.close()

        counts, rows, idx, again, rejected = run(go())
        self.assertEqual(counts, {"normalized": 5, "backfilled": 4, "deduped": 1})
        self.assertEqual(rows["a1"]["idempotency_key"], "k1")
        self.assertEqual(rows["a2"], {"event_id": "e1", "idempotency_key_retired": "k1", "idempotency_duplicate_of": "a1"})
        self.assertEqual(rows["a3"]["idempotency_key"], "e1")
        self.assertEqual(rows["a4"]["idempotency_key"], "e1")
        self.assertEqual(rows["a5"], {})
        self.assertEqual(rows["a6"]["idempotency_key"], "e6")
        self.assertEqual(rows["a7"]["idempotency_key"], "e7")
        self.assertEqual(rows["a8"], {"idempotency_key": "123"})
        self.assertNotIn("idempotency_key", rows["a9"])
        self.assertEqual(rows["b1"], [])
        self.assertEqual(rows["b2"], {"other": 1})
        self.assertIn(server.IDEMPOTENCY_INDEX_NAME, idx)
        self.assertNotIn("memories_domain_event_id_idx", idx)
        self.assertIsNone(again)
        self.assertTrue(rejected)


if __name__ == "__main__":
    unittest.main()
