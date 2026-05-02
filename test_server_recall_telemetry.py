#!/usr/bin/env python3
"""Regression tests for opt-in recall telemetry response behavior."""

import asyncio
import json
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from decimal import Decimal
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
            result = [dict(item) for item in self.results]
            for idx, item in enumerate(result, start=1):
                item.setdefault("cosine_score", Decimal(f"0.{idx}25"))
                item.setdefault("similarity", Decimal(f"0.{idx}75"))
            return result, {
                "schema": "memibrium.hybrid_retrieval.telemetry.v1",
                "query": kwargs["query"],
                "streams": {
                    "semantic": {
                        "returned_count": len(result),
                        "items": [
                            {"id": result[0]["id"], "cosine_score": Decimal("0.9123"), "similarity": Decimal("0.8123")},
                            {"id": result[1]["id"], "cosine_score": Decimal("0.8345"), "similarity": Decimal("0.7345")},
                        ],
                        "score_summary": {"min": Decimal("0.8345"), "max": Decimal("0.9123"), "mean": Decimal("0.8734")},
                    },
                    "lexical": {
                        "returned_count": 1,
                        "items": [{"id": result[0]["id"], "bm25_score": Decimal("0.5000")}],
                        "score_summary": {"min": Decimal("0.5"), "max": Decimal("0.5"), "mean": Decimal("0.5")},
                    },
                },
                "fusion": {
                    "fused_count_before_cap": Decimal("2"),
                    "cutoff_items": [{"id": "m3", "rrf_score": Decimal("0.03125"), "combined_score": Decimal("1.125")}],
                },
                "final": {
                    "returned_count": len(result),
                    "items": [
                        {"id": item["id"], "rrf_score": Decimal("0.016393"), "combined_score": Decimal("1.25")}
                        for item in result
                    ],
                    "score_summary": {"min": Decimal("0.016393"), "max": Decimal("0.032786"), "mean": Decimal("0.0245895")},
                },
            }
        return list(self.results)


class RecallTelemetryResponseTests(unittest.TestCase):
    def run_async(self, coro):
        return asyncio.run(coro)

    def decode_response(self, response):
        return json.loads(response.body.decode("utf-8"))

    def test_serialize_result_normalizes_nested_decimal_and_preserves_existing_json_types(self):
        payload = {
            "top_level_score": Decimal("0.9876"),
            "results": [
                {
                    "id": "m1",
                    "cosine_score": Decimal("0.9123"),
                    "similarity": Decimal("0.8123"),
                    "created_at": datetime(2026, 5, 2, 1, 2, 3, tzinfo=timezone.utc),
                    "event_date": date(2026, 5, 2),
                    "flag": True,
                    "none_value": None,
                    "int_value": 2,
                    "float_value": 1.25,
                    "text": "first",
                },
                {"id": "m2", "combined_score": Decimal("1.125")},
            ],
            "telemetry": {
                "streams": {
                    "semantic": {
                        "items": [{"id": "m1", "cosine_score": Decimal("0.9123")}],
                        "score_summary": {"min": Decimal("0.8123"), "max": Decimal("0.9123"), "mean": Decimal("0.8623")},
                    },
                    "lexical": {
                        "items": [{"id": "m2", "bm25_score": Decimal("0.5")}],
                        "score_summary": {"min": Decimal("0.5"), "max": Decimal("0.5"), "mean": Decimal("0.5")},
                    },
                },
                "fusion": {
                    "cutoff_items": [{"id": "m3", "rrf_score": Decimal("0.03125"), "combined_score": Decimal("1.125")}]
                },
                "final": {
                    "items": [{"id": "m1", "rrf_score": Decimal("0.016393")}],
                    "score_summary": {"min": Decimal("0.016393"), "max": Decimal("0.032786"), "mean": Decimal("0.0245895")},
                },
            },
        }

        serialized = server._serialize_result(payload)
        encoded = json.dumps(serialized)
        decoded = json.loads(encoded)

        self.assertIsInstance(decoded["top_level_score"], float)
        self.assertEqual(decoded["results"][0]["created_at"], "2026-05-02T01:02:03+00:00")
        self.assertEqual(decoded["results"][0]["event_date"], "2026-05-02")
        self.assertEqual(decoded["results"][0]["flag"], True)
        self.assertIsNone(decoded["results"][0]["none_value"])
        self.assertEqual(decoded["results"][0]["int_value"], 2)
        self.assertEqual(decoded["results"][0]["float_value"], 1.25)
        self.assertEqual(decoded["results"][0]["text"], "first")
        self.assertIsInstance(decoded["results"][0]["cosine_score"], float)
        self.assertIsInstance(decoded["results"][0]["similarity"], float)
        self.assertIsInstance(decoded["telemetry"]["streams"]["semantic"]["items"][0]["cosine_score"], float)
        self.assertIsInstance(decoded["telemetry"]["streams"]["semantic"]["score_summary"]["mean"], float)
        self.assertIsInstance(decoded["telemetry"]["fusion"]["cutoff_items"][0]["rrf_score"], float)
        self.assertIsInstance(decoded["telemetry"]["final"]["score_summary"]["mean"], float)

    def test_handle_recall_include_telemetry_serializes_production_like_decimal_payload(self):
        fake_retriever = FakeHybridRetriever()
        with patch.object(server, "hybrid_retriever", fake_retriever), patch.object(
            server, "embedder", FakeEmbedder()
        ):
            response = self.run_async(
                server.handle_recall(FakeRequest({"query": "q", "top_k": 2, "include_telemetry": True}))
            )

        payload = self.decode_response(response)
        self.assertEqual([item["id"] for item in payload["results"]], ["m1", "m2"])
        self.assertIsInstance(payload["results"][0]["cosine_score"], float)
        self.assertIsInstance(payload["results"][0]["similarity"], float)
        self.assertIsInstance(payload["telemetry"]["streams"]["semantic"]["items"][0]["cosine_score"], float)
        self.assertIsInstance(payload["telemetry"]["streams"]["semantic"]["score_summary"]["mean"], float)
        self.assertIsInstance(payload["telemetry"]["fusion"]["cutoff_items"][0]["rrf_score"], float)
        self.assertIsInstance(payload["telemetry"]["final"]["items"][0]["combined_score"], float)

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
