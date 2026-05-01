#!/usr/bin/env python3
"""Regression tests for hybrid retrieval SQL in ruvector mode."""

import asyncio
import unittest

from hybrid_retrieval import HybridRetriever


class FakeConn:
    def __init__(self, fail_first_fetch=False):
        self.calls = []
        self.fail_first_fetch = fail_first_fetch

    async def fetch(self, query, *params):
        self.calls.append((query, params))
        if self.fail_first_fetch and len(self.calls) == 1:
            raise RuntimeError("force tsvector fallback")
        return []


class FakeAcquire:
    def __init__(self, conn):
        self.conn = conn

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakePool:
    def __init__(self, fail_first_fetch=False):
        self.conn = FakeConn(fail_first_fetch=fail_first_fetch)

    def acquire(self):
        return FakeAcquire(self.conn)




class FakeHybridRetriever(HybridRetriever):
    def __init__(self):
        super().__init__(pool=None, vtype="ruvector")
        self.semantic = [
            {"id": "s1", "content": "semantic one", "refs": {"session_index": 1}, "created_at": "2026-05-01T00:00:00Z", "cosine_score": 0.9},
            {"id": "shared", "content": "shared memory", "refs": {"session_index": 1}, "created_at": "2026-05-01T00:01:00Z", "cosine_score": 0.8},
        ]
        self.lexical = [
            {"id": "l1", "content": "lexical one", "refs": {"session_index": 2}, "created_at": "2026-05-01T00:02:00Z", "bm25_score": 0.7},
            {"id": "shared", "content": "shared memory", "refs": {"session_index": 1}, "created_at": "2026-05-01T00:01:00Z", "bm25_score": 0.6},
        ]
        self.temporal = [
            {"id": "t1", "content": "temporal one", "refs": {"session_index": 3}, "created_at": "2026-05-01T00:03:00Z", "temporal_score": 1.0},
        ]

    async def _semantic_search(self, embedding, top_k, state_filter=None, domain=None, telemetry=None):
        result = [dict(item) for item in self.semantic[:top_k]]
        if telemetry is not None:
            telemetry["streams"]["semantic"] = self._stream_telemetry(result, "cosine_score", top_k)
        return result

    async def _lexical_search(self, query, top_k, state_filter=None, domain=None, telemetry=None):
        result = [dict(item) for item in self.lexical[:top_k]]
        if telemetry is not None:
            telemetry["streams"]["lexical"] = self._stream_telemetry(result, "bm25_score", top_k, path="fake")
        return result

    async def _temporal_search(self, start, end, top_k, state_filter=None, domain=None, telemetry=None):
        result = [dict(item) for item in self.temporal[:top_k]]
        if telemetry is not None:
            telemetry["streams"]["temporal"] = self._stream_telemetry(result, "temporal_score", top_k)
        return result

class HybridRetrievalRuvectorTests(unittest.TestCase):
    def run_async(self, coro):
        return asyncio.run(coro)

    def test_ruvector_semantic_search_casts_to_ruvector_type(self):
        pool = FakePool()
        retriever = HybridRetriever(pool=pool, vtype="ruvector")

        self.run_async(retriever._semantic_search([0.1, 0.2], top_k=3, domain="locomo-test"))

        sql, params = pool.conn.calls[0]
        self.assertIn("::ruvector", sql)
        self.assertNotIn("::vector", sql)

    def test_ruvector_semantic_search_applies_domain_and_state_filters(self):
        pool = FakePool()
        retriever = HybridRetriever(pool=pool, vtype="ruvector")

        self.run_async(
            retriever._semantic_search(
                [0.1, 0.2],
                top_k=3,
                state_filter=["accepted", "crystallized"],
                domain="locomo-test",
            )
        )

        sql, params = pool.conn.calls[0]
        self.assertIn("domain =", sql)
        self.assertIn("state IN", sql)
        self.assertIn("locomo-test", params)
        self.assertIn("accepted", params)
        self.assertIn("crystallized", params)

    def test_ruvector_lexical_search_applies_domain_and_state_filters_to_tsvector_path(self):
        pool = FakePool()
        retriever = HybridRetriever(pool=pool, vtype="ruvector")

        self.run_async(
            retriever._lexical_search(
                "alice cobalt",
                top_k=3,
                state_filter=["accepted"],
                domain="locomo-test",
            )
        )

        sql, params = pool.conn.calls[0]
        self.assertIn("domain =", sql)
        self.assertIn("state IN", sql)
        self.assertIn("locomo-test", params)
        self.assertIn("accepted", params)
    def test_default_pgvector_alias_casts_to_vector_type(self):
        pool = FakePool()
        retriever = HybridRetriever(pool=pool)

        self.run_async(retriever._semantic_search([0.1, 0.2], top_k=3))

        sql, _params = pool.conn.calls[0]
        self.assertIn("::vector", sql)
        self.assertNotIn("::pgvector", sql)

    def test_invalid_vtype_is_rejected_before_sql_construction(self):
        with self.assertRaises(ValueError):
            HybridRetriever(pool=FakePool(), vtype="vector); DROP TABLE memories; --")

    def test_ruvector_lexical_search_applies_domain_and_state_filters_to_ilike_fallback(self):
        pool = FakePool(fail_first_fetch=True)
        retriever = HybridRetriever(pool=pool, vtype="ruvector")

        self.run_async(
            retriever._lexical_search(
                "alice cobalt",
                top_k=3,
                state_filter=["accepted"],
                domain="locomo-test",
            )
        )

        self.assertEqual(len(pool.conn.calls), 2)
        sql, params = pool.conn.calls[1]
        self.assertIn("domain =", sql)
        self.assertIn("state IN", sql)
        self.assertIn("ILIKE", sql)
        self.assertIn("locomo-test", params)
        self.assertIn("accepted", params)


    def test_telemetry_disabled_preserves_search_return_ids_order_and_count(self):
        retriever = FakeHybridRetriever()

        baseline = self.run_async(
            retriever.search(
                "regular query",
                embedding=[0.1, 0.2],
                top_k=3,
                include_telemetry=False,
            )
        )
        control = self.run_async(
            retriever.search(
                "regular query",
                embedding=[0.1, 0.2],
                top_k=3,
            )
        )

        self.assertIsInstance(baseline, list)
        self.assertEqual([m["id"] for m in baseline], [m["id"] for m in control])
        self.assertFalse(hasattr(retriever, "last_telemetry"))

    def test_telemetry_enabled_preserves_search_return_ids_order_and_count(self):
        retriever = FakeHybridRetriever()

        without_telemetry = self.run_async(
            retriever.search("regular query", embedding=[0.1, 0.2], top_k=3)
        )
        with_telemetry, telemetry = self.run_async(
            retriever.search("regular query", embedding=[0.1, 0.2], top_k=3, include_telemetry=True)
        )

        self.assertEqual([m["id"] for m in with_telemetry], [m["id"] for m in without_telemetry])
        self.assertEqual(len(with_telemetry), len(without_telemetry))
        self.assertEqual(telemetry["schema"], "memibrium.hybrid_retrieval.telemetry.v1")
        self.assertEqual(telemetry["final"]["returned_count"], len(with_telemetry))

    def test_telemetry_captures_stream_fusion_cutoff_and_final_counts(self):
        retriever = FakeHybridRetriever()

        result, telemetry = self.run_async(
            retriever.search(
                "after 2026-05-01",
                embedding=[0.1, 0.2],
                top_k=2,
                include_telemetry=True,
            )
        )

        self.assertEqual([m["id"] for m in result], [item["id"] for item in telemetry["final"]["items"]])
        self.assertEqual(telemetry["streams"]["semantic"]["returned_count"], 2)
        self.assertEqual(telemetry["streams"]["lexical"]["returned_count"], 2)
        self.assertEqual(telemetry["streams"]["temporal"]["returned_count"], 1)
        self.assertTrue(telemetry["temporal"]["executed"])
        self.assertEqual(telemetry["fusion"]["fused_count_before_cap"], 4)
        self.assertEqual(telemetry["final"]["returned_count"], 2)
        self.assertEqual(len(telemetry["final"]["cutoff_items"]), 2)

    def test_telemetry_captures_lexical_tsvector_fallback_without_changing_results(self):
        plain_pool = FakePool(fail_first_fetch=True)
        plain_retriever = HybridRetriever(pool=plain_pool, vtype="ruvector")
        instrumented_pool = FakePool(fail_first_fetch=True)
        retriever = HybridRetriever(pool=instrumented_pool, vtype="ruvector")

        plain = self.run_async(
            plain_retriever._lexical_search("alice cobalt", top_k=3, domain="locomo-test")
        )
        telemetry = retriever._new_telemetry(
            query="alice cobalt",
            top_k=3,
            fetch_k=3,
            state_filter=None,
            domain="locomo-test",
            use_rrf=True,
            rerank=False,
        )
        instrumented = self.run_async(
            retriever._lexical_search(
                "alice cobalt",
                top_k=3,
                domain="locomo-test",
                telemetry=telemetry,
            )
        )

        self.assertEqual(instrumented, plain)
        self.assertEqual(telemetry["streams"]["lexical"]["path"], "ilike_fallback")
        self.assertEqual(telemetry["streams"]["lexical"]["tsvector_error"]["class"], "RuntimeError")
        self.assertEqual(telemetry["streams"]["lexical"]["returned_count"], len(instrumented))


if __name__ == "__main__":
    unittest.main()
