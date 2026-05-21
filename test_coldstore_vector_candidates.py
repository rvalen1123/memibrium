#!/usr/bin/env python3
"""Regression tests for ColdStore vector candidates vs CT-ranked search."""

import asyncio
import json
import unittest
from datetime import datetime, timezone

import server


class FakeAcquire:
    def __init__(self, conn):
        self.conn = conn

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakePool:
    def __init__(self, conn):
        self.conn = conn

    def acquire(self):
        return FakeAcquire(self.conn)


class FakeConn:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.fetch_calls = []

    async def fetch(self, sql, *params):
        self.fetch_calls.append((sql, params))
        return self.rows


class FeedbackStore(server.ColdStore):
    async def get_memory_feedback_score(self, mid):
        return 0.0


class ColdStoreVectorCandidateTests(unittest.TestCase):
    def run_async(self, coro):
        return asyncio.run(coro)

    def test_vector_memory_store_alias_preserves_compatibility(self):
        self.assertIs(server.VectorMemoryStore, server.ColdStore)

    def test_vector_candidates_returns_raw_vector_scores_without_ct_ranking_fields(self):
        conn = FakeConn(rows=[{
            "id": "m1",
            "content": "raw vector candidate",
            "source": "test",
            "domain": "default",
            "state": "accepted",
            "memory_type": "semantic",
            "confirmation_count": 3,
            "recency_score": 0.8,
            "validation_score": 0.7,
            "importance_score": 0.6,
            "frozen": False,
            "frozen_at": None,
            "created_at": datetime(2026, 5, 1, tzinfo=timezone.utc),
            "updated_at": datetime(2026, 5, 1, tzinfo=timezone.utc),
            "entities": json.dumps([]),
            "topics": json.dumps([]),
            "refs": json.dumps({}),
            "witness_chain": json.dumps([]),
            "cosine_score": 0.81234,
        }])
        store = server.ColdStore()
        store.pool = FakePool(conn)

        result = self.run_async(store.vector_candidates([0.1, 0.2], top_k=3, domain="default"))

        self.assertEqual(result[0]["id"], "m1")
        self.assertEqual(result[0]["cosine_score"], 0.8123)
        self.assertEqual(result[0]["retrieval_source"], "vector")
        self.assertNotIn("w_kt", result[0])
        self.assertNotIn("ct_score", result[0])
        self.assertNotIn("final_score", result[0])
        sql, params = conn.fetch_calls[0]
        self.assertIn("state != 'shed'", sql)
        self.assertIn("domain = $3", sql)
        self.assertEqual(params[1], 3)

    def test_legacy_search_wraps_vector_candidates_with_ct_ranker(self):
        conn = FakeConn(rows=[
            {
                "id": "raw_high",
                "content": "high vector weak CT",
                "source": "test",
                "domain": "default",
                "state": "observation",
                "memory_type": "episodic",
                "confirmation_count": 0,
                "recency_score": 0.1,
                "validation_score": 0.0,
                "importance_score": 0.1,
                "frozen": False,
                "frozen_at": None,
                "created_at": datetime(2026, 5, 1, tzinfo=timezone.utc),
                "updated_at": datetime(2026, 5, 1, tzinfo=timezone.utc),
                "entities": [],
                "topics": [],
                "refs": {},
                "witness_chain": [],
                "cosine_score": 0.99,
            },
            {
                "id": "ct_high",
                "content": "moderate vector strong CT",
                "source": "test",
                "domain": "default",
                "state": "crystallized",
                "memory_type": "procedural",
                "confirmation_count": 8,
                "recency_score": 1.0,
                "validation_score": 0.95,
                "importance_score": 0.9,
                "frozen": False,
                "frozen_at": None,
                "created_at": datetime(2026, 5, 1, tzinfo=timezone.utc),
                "updated_at": datetime(2026, 5, 1, tzinfo=timezone.utc),
                "entities": [],
                "topics": [],
                "refs": {},
                "witness_chain": [{"kind": "confirm"}],
                "cosine_score": 0.6,
            },
        ])
        store = FeedbackStore()
        store.pool = FakePool(conn)

        result = self.run_async(store.search([0.1, 0.2], top_k=2, apply_personalization=True))

        self.assertEqual(result[0]["id"], "ct_high")
        self.assertIn("ct_score", result[0])
        self.assertIn("final_score", result[0])
        self.assertIn("ct_ranker", result[0]["ranking_path"])
        _sql, params = conn.fetch_calls[0]
        self.assertEqual(params[1], 6)  # legacy wrapper fetches extra candidates before final CT cap


if __name__ == "__main__":
    unittest.main()
