#!/usr/bin/env python3
"""Regression tests for opt-in recall telemetry response behavior."""

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


class FakeEmbedder:
    def __init__(self):
        self._executor = ThreadPoolExecutor(max_workers=1)

    def embed(self, query):
        return [0.1, 0.2, 0.3]


class FakeHybridRetriever:
    def __init__(self):
        self.calls = []
        self.results = [
            {"id": "m1", "content": "first memory"},
            {"id": "m2", "content": "second memory"},
        ]

    async def search(self, **kwargs):
        self.calls.append(kwargs)
        if kwargs.get("include_telemetry"):
            return list(self.results), {
                "schema": "memibrium.hybrid_retrieval.telemetry.v1",
                "query": kwargs["query"],
                "final": {
                    "returned_count": len(self.results),
                    "items": [{"id": item["id"]} for item in self.results],
                },
            }
        return list(self.results)


class RecallTelemetryResponseTests(unittest.TestCase):
    def run_async(self, coro):
        return asyncio.run(coro)

    def decode_response(self, response):
        return json.loads(response.body.decode("utf-8"))

    def test_handle_recall_omits_telemetry_unless_requested(self):
        fake_retriever = FakeHybridRetriever()
        with patch.object(server, "hybrid_retriever", fake_retriever), patch.object(
            server, "embedder", FakeEmbedder()
        ):
            response = self.run_async(server.handle_recall(FakeRequest({"query": "q", "top_k": 2})))

        payload = self.decode_response(response)
        self.assertIsInstance(payload, list)
        self.assertEqual([item["id"] for item in payload], ["m1", "m2"])
        self.assertEqual(fake_retriever.calls[0]["include_telemetry"], False)

    def test_handle_recall_include_telemetry_preserves_results_and_adds_telemetry_object(self):
        fake_retriever = FakeHybridRetriever()
        with patch.object(server, "hybrid_retriever", fake_retriever), patch.object(
            server, "embedder", FakeEmbedder()
        ):
            plain = self.run_async(server.handle_recall(FakeRequest({"query": "q", "top_k": 2})))
            instrumented = self.run_async(
                server.handle_recall(FakeRequest({"query": "q", "top_k": 2, "include_telemetry": True}))
            )

        plain_payload = self.decode_response(plain)
        telemetry_payload = self.decode_response(instrumented)
        self.assertEqual([item["id"] for item in telemetry_payload["results"]], [item["id"] for item in plain_payload])
        self.assertEqual(len(telemetry_payload["results"]), len(plain_payload))
        self.assertEqual(telemetry_payload["telemetry"]["final"]["returned_count"], len(plain_payload))
        self.assertFalse(telemetry_payload["telemetry"]["server"]["legacy_fallback_executed"])
        self.assertTrue(telemetry_payload["telemetry"]["server"]["hybrid_retriever_present"])
        self.assertTrue(telemetry_payload["telemetry"]["server"]["embedding_success"])


if __name__ == "__main__":
    unittest.main()
