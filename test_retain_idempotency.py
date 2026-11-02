#!/usr/bin/env python3
"""Idempotent retain: re-sending an observation that carries the same
refs.idempotency_key (or refs.event_id) in the same domain returns the existing
memory and performs no embedding, insert or background scoring.

Runs without Postgres: the store and embedder are fakes that record calls."""

import asyncio
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from unittest.mock import patch

import server
from server import IngestAgent, _idempotency_key_from_refs


class FakeStore:
    def __init__(self):
        self.rows: list[dict] = []
        self.lookups: list[tuple[str, str]] = []

    async def find_by_idempotency_key(self, domain, key):
        self.lookups.append((domain, key))
        for r in self.rows:
            refs = r["refs"] or {}
            if r["domain"] == domain and key in (refs.get("idempotency_key"), refs.get("event_id")):
                return {"id": r["id"], "state": r["state"], "source": r["source"], "domain": r["domain"],
                        "created_at": datetime.now(timezone.utc)}
        return None

    async def insert_memory(self, mid, content, embedding, state, source, domain, importance, entities, topics,
                            witness_chain, memory_type="semantic", event_at=None, refs=None):
        self.rows.append({"id": mid, "content": content, "state": state, "source": source, "domain": domain,
                          "refs": refs or {}})


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


if __name__ == "__main__":
    unittest.main()
