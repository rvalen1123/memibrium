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


if __name__ == "__main__":
    unittest.main()
