#!/usr/bin/env python3
"""Regression tests for CT-governed recall integration."""

import asyncio
import json
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import server


class FakeRequest:
    def __init__(self, payload):
        self.payload = payload

    async def json(self):
        return dict(self.payload)

    async def body(self):
        return json.dumps(self.payload).encode("utf-8")


class FakeEmbedder:
    _executor = ThreadPoolExecutor(max_workers=1)

    def embed(self, _text):
        return [0.1, 0.2, 0.3]


class FakeChat:
    def expand_query(self, _query):
        return []

    def synthesize(self, memories, topic):
        return f"synthesis for {topic}: {len(memories)}"


class FakeHybridRetriever:
    def __init__(self, fail=False):
        self.fail = fail
        self.calls = []

    async def search(self, **kwargs):
        self.calls.append(kwargs)
        if self.fail:
            raise RuntimeError("hybrid unavailable")
        results = [
            {
                "id": "raw_high",
                "content": "raw high retrieval but weak CT",
                "state": "observation",
                "confirmation_count": 0,
                "validation_score": 0.0,
                "recency_score": 0.1,
                "importance_score": 0.1,
                "memory_type": "episodic",
                "rrf_score": 0.09,
            },
            {
                "id": "ct_high",
                "content": "lower retrieval but confirmed CT",
                "state": "crystallized",
                "confirmation_count": 8,
                "validation_score": 0.95,
                "recency_score": 1.0,
                "importance_score": 0.9,
                "memory_type": "procedural",
                "rrf_score": 0.03,
                "witness_chain": [{"kind": "confirm"}],
            },
        ]
        telemetry = {
            "schema": "memibrium.hybrid_retrieval.telemetry.v1",
            "query": kwargs["query"],
            "streams": {},
            "fusion": {},
            "final": {"returned_count": len(results), "items": [{"id": r["id"]} for r in results]},
        }
        return (results, telemetry) if kwargs.get("include_telemetry") else results


class FakeStore:
    def __init__(self):
        self.feedback = {}
        self.vector_calls = []

    async def get_memory_feedback_score(self, mid):
        return self.feedback.get(mid, 0.0)

    async def get_memory(self, _mid):
        return None

    async def vector_candidates(self, embedding, top_k=5, state_filter=None, domain=None, include_shed=False):
        self.vector_calls.append({"embedding": embedding, "state_filter": state_filter, "domain": domain, "include_shed": include_shed})
        return [
            {
                "id": "fallback_ct",
                "content": "fallback vector candidate",
                "state": "crystallized",
                "confirmation_count": 6,
                "validation_score": 0.9,
                "recency_score": 0.9,
                "importance_score": 0.8,
                "memory_type": "semantic",
                "cosine_score": 0.5,
            }
        ]

    async def get_context_graph_entities(self, *args, **kwargs):
        return []

    async def list_self_model_observations(self, *args, **kwargs):
        return []

    async def list_context_graph_facts(self, *args, **kwargs):
        return []

    async def get_related_memories(self, _mid, limit=3):
        return []



class FakeLeann:
    available = False
    searcher = None


class RecallHybridCTTests(unittest.TestCase):
    def run_async(self, coro):
        return asyncio.run(coro)

    def decode_response(self, response):
        return json.loads(response.body.decode("utf-8"))

    def test_handle_recall_passes_hybrid_candidates_through_ct_ranker(self):
        fake_store = FakeStore()
        with patch.object(server, "store", fake_store), patch.object(server, "embedder", FakeEmbedder()), patch.object(
            server, "chat", FakeChat()
        ), patch.object(server, "leann_tier", FakeLeann()), patch.object(
            server, "hybrid_retriever", FakeHybridRetriever()
        ), patch.object(server, "hierarchy_manager", None):
            response = self.run_async(server.handle_recall(FakeRequest({"query": "q", "top_k": 2, "expand": False, "graph_walk": False})))

        payload = self.decode_response(response)
        self.assertEqual(payload[0]["id"], "ct_high")
        self.assertIn("final_score", payload[0])
        self.assertIn("ct_score", payload[0])
        self.assertIn("candidate_retrieval->ct_ranker", payload[0]["ranking_path"])

    def test_handle_recall_telemetry_includes_hybrid_and_ct_ranking(self):
        fake_store = FakeStore()
        with patch.object(server, "store", fake_store), patch.object(server, "embedder", FakeEmbedder()), patch.object(
            server, "chat", FakeChat()
        ), patch.object(server, "leann_tier", FakeLeann()), patch.object(
            server, "hybrid_retriever", FakeHybridRetriever()
        ), patch.object(server, "hierarchy_manager", None):
            response = self.run_async(server.handle_recall(FakeRequest({"query": "q", "top_k": 2, "include_telemetry": True, "expand": False, "graph_walk": False})))

        payload = self.decode_response(response)
        self.assertEqual(payload["telemetry"]["schema"], "memibrium.hybrid_retrieval.telemetry.v1")
        ranking = payload["telemetry"]["ranking"]
        self.assertEqual(ranking["schema"], "memibrium.ct_ranking.telemetry.v1")
        self.assertEqual(ranking["top_ranked_ids"][0], "ct_high")
        self.assertIn("score_components", ranking)
        self.assertFalse(payload["telemetry"]["server"]["legacy_fallback_executed"])

    def test_hybrid_failure_fallback_still_returns_ct_ranked_results(self):
        fake_store = FakeStore()
        with patch.object(server, "store", fake_store), patch.object(server, "embedder", FakeEmbedder()), patch.object(
            server, "chat", FakeChat()
        ), patch.object(server, "leann_tier", FakeLeann()), patch.object(
            server, "hybrid_retriever", FakeHybridRetriever(fail=True)
        ), patch.object(server, "hierarchy_manager", None):
            response = self.run_async(server.handle_recall(FakeRequest({"query": "q", "top_k": 1, "include_telemetry": True, "expand": False, "graph_walk": False})))

        payload = self.decode_response(response)
        self.assertEqual(payload["results"][0]["id"], "fallback_ct")
        self.assertIn("final_score", payload["results"][0])
        self.assertTrue(payload["telemetry"]["server"]["legacy_fallback_executed"])
        self.assertEqual(payload["telemetry"]["ranking"]["schema"], "memibrium.ct_ranking.telemetry.v1")

    def test_query_agent_recall_uses_shared_recall_service(self):
        fake_store = FakeStore()
        with patch.object(server, "store", fake_store), patch.object(server, "embedder", FakeEmbedder()), patch.object(
            server, "chat", FakeChat()
        ), patch.object(server, "leann_tier", FakeLeann()), patch.object(
            server, "hybrid_retriever", FakeHybridRetriever()
        ), patch.object(server, "hierarchy_manager", None):
            result = self.run_async(server.query_agent.recall("q", top_k=2, expand=False, graph_walk=False))

        self.assertEqual(result["results"][0]["id"], "ct_high")
        self.assertIn("ct_ranker", result["results"][0]["ranking_path"])

    def test_handle_reflect_uses_shared_ct_ranked_recall_for_synthesis(self):
        fake_store = FakeStore()
        with patch.object(server, "store", fake_store), patch.object(server, "embedder", FakeEmbedder()), patch.object(
            server, "chat", FakeChat()
        ), patch.object(server, "leann_tier", FakeLeann()), patch.object(
            server, "hybrid_retriever", FakeHybridRetriever()
        ), patch.object(server, "hierarchy_manager", None):
            response = self.run_async(server.handle_reflect(FakeRequest({"topic": "q", "top_k": 2, "expand": False, "graph_walk": False})))

        payload = self.decode_response(response)
        self.assertEqual(payload["memory_count"], 2)
        self.assertEqual(payload["ranking_path"], "recall_memories->ct_ranker")
        self.assertIn("synthesis for q", payload["synthesis"])

    def test_handle_context_packet_uses_shared_ct_ranked_recall(self):
        fake_store = FakeStore()
        with patch.object(server, "store", fake_store), patch.object(server, "embedder", FakeEmbedder()), patch.object(
            server, "chat", FakeChat()
        ), patch.object(server, "leann_tier", FakeLeann()), patch.object(
            server, "hybrid_retriever", FakeHybridRetriever()
        ), patch.object(server, "hierarchy_manager", None):
            response = self.run_async(server.handle_context_packet(FakeRequest({
                "query": "q", "top_k": 2, "expand": False, "graph_walk": False, "include_source_attribution": True
            })))

        payload = self.decode_response(response)
        self.assertEqual(payload["episodic_evidence"][0]["memory_id"], "ct_high")
        self.assertEqual(payload["source_attribution"]["retrieval_path"], "recall_memories.ct_ranked")
        self.assertEqual(payload["source_attribution"]["evidence"][0]["id"], "ct_high")



if __name__ == "__main__":
    unittest.main()
