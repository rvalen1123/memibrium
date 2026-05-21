#!/usr/bin/env python3
"""Tests for CT final ranking over retrieval candidates."""

import asyncio
import unittest
from datetime import datetime, timedelta, timezone

from ct_ranker import CTRanker


class FakeStore:
    def __init__(self, feedback=None):
        self.feedback = feedback or {}

    async def get_memory_feedback_score(self, memory_id):
        return self.feedback.get(memory_id, 0.0)


class CTRankerTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 5, 20, tzinfo=timezone.utc)

    def run_async(self, coro):
        return asyncio.run(coro)

    def test_crystallized_confirmed_memory_ranks_appropriately(self):
        ranker = CTRanker(now=self.now)
        candidates = [
            {
                "id": "obs",
                "content": "raw observation",
                "state": "observation",
                "created_at": self.now - timedelta(hours=2),
                "confirmation_count": 0,
                "validation_score": 0.1,
                "recency_score": 0.7,
                "cosine_score": 0.70,
            },
            {
                "id": "crys",
                "content": "confirmed fact",
                "state": "crystallized",
                "created_at": self.now - timedelta(hours=2),
                "confirmation_count": 4,
                "validation_score": 0.95,
                "recency_score": 0.9,
                "cosine_score": 0.69,
                "witness_chain": [{"entry_hash": "abc"}],
            },
        ]

        ranked = self.run_async(ranker.rank(candidates))

        self.assertEqual(ranked[0]["id"], "crys")
        self.assertGreater(ranked[0]["ct_score"], ranked[1]["ct_score"])
        self.assertIn("witness_chain_present", ranked[0]["rank_explanation"])

    def test_stale_low_validation_memory_is_penalized(self):
        ranker = CTRanker(now=self.now)
        candidates = [
            {
                "id": "stale",
                "state": "accepted",
                "created_at": self.now - timedelta(days=90),
                "confirmation_count": 1,
                "validation_score": 0.05,
                "recency_score": 0.05,
                "cosine_score": 0.90,
            },
            {
                "id": "fresh",
                "state": "accepted",
                "created_at": self.now - timedelta(hours=2),
                "confirmation_count": 2,
                "validation_score": 0.8,
                "recency_score": 0.9,
                "cosine_score": 0.85,
            },
        ]

        ranked = self.run_async(ranker.rank(candidates))

        self.assertEqual(ranked[0]["id"], "fresh")
        self.assertLess(ranked[1]["ct_score"], ranked[0]["ct_score"])

    def test_missing_fields_do_not_crash_and_ranking_fields_exist(self):
        ranker = CTRanker(now=self.now)

        ranked = self.run_async(ranker.rank([{"id": "minimal", "content": "hello"}]))

        self.assertEqual(ranked[0]["id"], "minimal")
        self.assertIn("final_score", ranked[0])
        self.assertIn("ct_score", ranked[0])
        self.assertIn("retrieval_score", ranked[0])
        self.assertIn("rank_explanation", ranked[0])
        self.assertIn("ranking_path", ranked[0])
        self.assertIn("retrieval_sources", ranked[0])

    def test_incoming_retrieval_scores_are_preserved(self):
        ranker = CTRanker(now=self.now)
        candidate = {
            "id": "scores",
            "cosine_score": 0.7,
            "bm25_score": 0.4,
            "temporal_score": 0.3,
            "rrf_score": 0.02,
            "graph_score": 0.5,
            "leann_score": 0.6,
            "combined_score": 1.2,
        }

        ranked = self.run_async(ranker.rank([candidate]))
        item = ranked[0]

        for field in ("cosine_score", "bm25_score", "temporal_score", "rrf_score", "graph_score", "leann_score", "combined_score"):
            self.assertEqual(item[field], candidate[field])
        self.assertEqual(item["source_combined_score"], candidate["combined_score"])

    def test_shed_memories_are_penalized_unless_allowed(self):
        ranker = CTRanker(now=self.now)
        candidates = [
            {
                "id": "shed",
                "state": "shed",
                "created_at": self.now - timedelta(hours=1),
                "confirmation_count": 5,
                "validation_score": 1.0,
                "recency_score": 1.0,
                "cosine_score": 0.99,
            },
            {
                "id": "accepted",
                "state": "accepted",
                "created_at": self.now - timedelta(hours=1),
                "confirmation_count": 1,
                "validation_score": 0.5,
                "recency_score": 0.8,
                "cosine_score": 0.80,
            },
        ]

        default_ranked = self.run_async(ranker.rank(candidates))
        allowed_ranked = self.run_async(ranker.rank(candidates, allow_shed=True))

        self.assertEqual(default_ranked[0]["id"], "accepted")
        self.assertIn("shed_penalty_applied", default_ranked[1]["rank_explanation"])
        self.assertGreater(allowed_ranked[0]["ct_score"], default_ranked[1]["ct_score"])

    def test_feedback_can_influence_ranking(self):
        ranker = CTRanker(store=FakeStore({"fav": 4.0}), now=self.now)
        candidates = [
            {
                "id": "plain",
                "state": "accepted",
                "created_at": self.now - timedelta(hours=1),
                "confirmation_count": 1,
                "validation_score": 0.5,
                "recency_score": 0.8,
                "cosine_score": 0.75,
            },
            {
                "id": "fav",
                "state": "accepted",
                "created_at": self.now - timedelta(hours=1),
                "confirmation_count": 1,
                "validation_score": 0.5,
                "recency_score": 0.8,
                "cosine_score": 0.75,
            },
        ]

        ranked = self.run_async(ranker.rank(candidates))

        self.assertEqual(ranked[0]["id"], "fav")
        self.assertEqual(ranked[0]["feedback_score"], 4.0)
        self.assertIn("feedback=4.000", ranked[0]["rank_explanation"])

    def test_rank_telemetry_shape(self):
        ranker = CTRanker(now=self.now)

        ranked, telemetry = self.run_async(
            ranker.rank([{"id": "m1", "cosine_score": 0.5}], include_telemetry=True)
        )

        self.assertEqual(telemetry["schema"], "memibrium.ct_ranking.telemetry.v1")
        self.assertEqual(telemetry["candidate_count_before_ct"], 1)
        self.assertEqual(telemetry["returned_count_after_ct"], len(ranked))
        self.assertEqual(telemetry["top_ranked_ids"], ["m1"])
        self.assertEqual(telemetry["score_components"][0]["id"], "m1")


if __name__ == "__main__":
    unittest.main()
