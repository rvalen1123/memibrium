#!/usr/bin/env python3
"""Regression tests for Memibrium context graph / self-model v0 primitives."""

import asyncio
import json
import unittest
from datetime import datetime
from unittest.mock import patch

import server


class FakeRequest:
    def __init__(self, payload):
        self.payload = payload

    async def json(self):
        return dict(self.payload)


class FakeContextStore:
    def __init__(self):
        self.observations = []
        self.decision_traces = []
        self.entities = [
            {"entity_id": "ent_ricky", "name": "Ricky", "entity_type": "person", "attributes": {"role": "builder"}},
        ]
        self.graph_facts = [
            {"edge_id": "cg_edge_1", "source_kind": "entity", "source_id": "ent_ricky", "target_kind": "observation", "target_id": "obs_existing", "edge_type": "expresses", "weight": 0.8, "evidence_memory_ids": ["mem_1"]},
        ]

    async def create_self_model_observation(self, payload):
        record = server.make_self_model_observation_record(**payload)
        self.observations.append(record)
        return record

    async def list_self_model_observations(self, **kwargs):
        return list(self.observations)

    async def create_decision_trace(self, payload):
        trace = server.make_decision_trace_record(**payload)
        self.decision_traces.append(trace)
        return trace

    async def list_decision_traces(self, **kwargs):
        return list(self.decision_traces)

    async def get_context_graph_entities(self, query, limit=10):
        return self.entities[:limit]

    async def list_context_graph_facts(self, **kwargs):
        return list(self.graph_facts)


class CaptureConnection:
    def __init__(self):
        self.execute_calls = []

    async def execute(self, sql, *args):
        self.execute_calls.append((sql, args))


class FakeAcquire:
    def __init__(self, conn):
        self.conn = conn

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, exc_type, exc, tb):
        return False


class CapturePool:
    def __init__(self, conn):
        self.conn = conn

    def acquire(self):
        return FakeAcquire(self.conn)


class FakeQueryAgent:
    async def recall(self, query, top_k=5, domain=None, expand=True):
        return {
            "results": [
                {"id": "mem_recalled", "content": "Recalled episodic evidence from the active domain.", "domain": domain},
            ],
            "tier": "fake",
        }


class ContextGraphV0Tests(unittest.TestCase):
    def run_async(self, coro):
        return asyncio.run(coro)

    def decode_response(self, response):
        return json.loads(response.body.decode("utf-8"))

    def test_self_model_observation_requires_source_backed_evidence(self):
        with self.assertRaises(ValueError):
            server.make_self_model_observation_record(
                engine="ethos",
                observation_type="value",
                claim_text="User values quality over speed.",
                evidence_memory_ids=[],
                evidence_artifact_ids=[],
            )

        record = server.make_self_model_observation_record(
            engine="ethos",
            observation_type="value",
            claim_text="User values quality over speed.",
            evidence_memory_ids=["mem_quality"],
            entity_ids=["ent_user"],
            confidence=0.82,
            sensitivity="medium",
        )

        self.assertEqual(record["schema"], "memibrium.self_model_observation.v1")
        self.assertTrue(record["observation_id"].startswith("obs_"))
        self.assertEqual(record["engine"], "ethos")
        self.assertEqual(record["lifecycle_state"], "observation")
        self.assertEqual(record["user_state"], "unreviewed")
        self.assertEqual(record["evidence_memory_ids"], ["mem_quality"])
        self.assertEqual(record["entity_ids"], ["ent_user"])
        self.assertAlmostEqual(record["confidence"], 0.82)

    def test_self_model_observation_timestamps_are_db_ready_and_json_serializable(self):
        record = server.make_self_model_observation_record(
            engine="manual",
            observation_type="smoke_test",
            claim_text="Context Graph persistence timestamps must be DB-ready.",
            evidence_artifact_ids=["smoke://context-graph/timestamp"],
        )

        self.assertIsInstance(record["first_seen"], datetime)
        self.assertIsInstance(record["last_seen"], datetime)
        serialized = server._serialize_result(record)
        self.assertIsInstance(serialized["first_seen"], str)
        self.assertIsInstance(serialized["last_seen"], str)

        explicit = server.make_self_model_observation_record(
            engine="manual",
            observation_type="smoke_test",
            claim_text="Explicit ISO timestamps should also be DB-ready.",
            evidence_artifact_ids=["smoke://context-graph/timestamp"],
            first_seen="2026-05-03T18:00:00+00:00",
            last_seen="2026-05-03T18:01:00Z",
        )
        self.assertIsInstance(explicit["first_seen"], datetime)
        self.assertIsInstance(explicit["last_seen"], datetime)

    def test_decision_trace_timestamps_are_db_ready_and_json_serializable(self):
        trace = server.make_decision_trace_record(
            query="Should Context Graph timestamps be DB-ready?",
            answer="Yes, asyncpg timestamptz inserts require datetime objects.",
            evidence_memory_ids=["mem_timestamp"],
        )

        self.assertIsInstance(trace["created_at"], datetime)
        self.assertIsInstance(trace["updated_at"], datetime)
        serialized = server._serialize_result(trace)
        self.assertIsInstance(serialized["created_at"], str)
        self.assertIsInstance(serialized["updated_at"], str)

        explicit = server.make_decision_trace_record(
            query="Should explicit ISO timestamps be DB-ready?",
            answer="Yes, parse them before asyncpg persistence.",
            evidence_memory_ids=["mem_timestamp"],
            created_at="2026-05-03T18:00:00Z",
        )
        self.assertIsInstance(explicit["created_at"], datetime)
        self.assertIsInstance(explicit["updated_at"], datetime)

    def test_context_graph_persistence_passes_datetime_objects_to_asyncpg(self):
        conn = CaptureConnection()
        store = server.ColdStore()
        store.pool = CapturePool(conn)

        self.run_async(store.create_self_model_observation({
            "engine": "manual",
            "observation_type": "smoke_test",
            "claim_text": "Context Graph observation persistence must pass datetime objects.",
            "evidence_artifact_ids": ["smoke://context-graph/db-ready"],
        }))
        self.run_async(store.create_decision_trace({
            "query": "Should Context Graph persistence pass datetime objects?",
            "answer": "Yes, asyncpg timestamptz parameters must be datetime objects.",
            "evidence_memory_ids": ["mem_timestamp"],
        }))

        observation_args = conn.execute_calls[0][1]
        decision_args = conn.execute_calls[1][1]
        self.assertIsInstance(observation_args[13], datetime)
        self.assertIsInstance(observation_args[14], datetime)
        self.assertIsInstance(decision_args[10], datetime)
        self.assertIsInstance(decision_args[11], datetime)

    def test_decision_trace_preserves_evidence_observations_and_feedback_surface(self):
        trace = server.make_decision_trace_record(
            query="Should we build the context graph first?",
            answer="Build self-model observations and context packets first.",
            evidence_memory_ids=["mem_locomo_full_domain"],
            self_model_observation_ids=["obs_quality"],
            entity_ids=["ent_memibrium"],
            values_invoked=["quality over speed"],
            status="proposed",
            outcome_signal={"user": "approved"},
        )

        self.assertEqual(trace["schema"], "memibrium.decision_trace.v1")
        self.assertTrue(trace["trace_id"].startswith("trace_"))
        self.assertEqual(trace["evidence_memory_ids"], ["mem_locomo_full_domain"])
        self.assertEqual(trace["self_model_observation_ids"], ["obs_quality"])
        self.assertEqual(trace["status"], "proposed")
        self.assertEqual(trace["outcome_signal"], {"user": "approved"})

    def test_context_packet_composes_episodic_evidence_self_model_graph_and_guidance(self):
        packet = server.build_context_packet(
            query="What should Memibrium build next?",
            episodic_evidence=[
                {"id": "mem_1", "content": "Full-domain context improved LoCoMo but multi-hop stayed weak.", "source": "eval", "state": "accepted", "combined_score": 1.2},
            ],
            self_model_observations=[
                {"observation_id": "obs_quality", "engine": "ethos", "claim_text": "User prefers evidence before feature work.", "evidence_memory_ids": ["mem_1"], "confidence": 0.9, "user_state": "confirmed"},
            ],
            entities=[{"entity_id": "ent_memibrium", "name": "Memibrium", "entity_type": "project"}],
            graph_facts=[{"edge_id": "edge_1", "edge_type": "supports", "evidence_memory_ids": ["mem_1"]}],
        )

        self.assertEqual(packet["schema"], "memibrium.context_packet.v1")
        self.assertEqual(packet["query_type"], "strategic_decision")
        self.assertEqual(packet["episodic_evidence"][0]["memory_id"], "mem_1")
        self.assertEqual(packet["self_model_observations"][0]["observation_id"], "obs_quality")
        self.assertEqual(packet["relevant_entities"][0]["entity_id"], "ent_memibrium")
        self.assertEqual(packet["graph_facts"][0]["edge_type"], "supports")
        self.assertIn("source-backed", " ".join(packet["answer_guidance"]).lower())
        self.assertEqual(packet["provenance_summary"]["memory_ids"], ["mem_1"])

    def test_handlers_create_observations_decision_traces_and_context_packets(self):
        fake_store = FakeContextStore()
        fake_store.observations.append(server.make_self_model_observation_record(
            engine="ethos",
            observation_type="value",
            claim_text="User rewards rigorous preregistered evidence.",
            evidence_memory_ids=["mem_1"],
            entity_ids=["ent_ricky"],
            confidence=0.88,
        ))

        with patch.object(server, "store", fake_store), patch.object(server, "query_agent", FakeQueryAgent()):
            obs_response = self.run_async(server.handle_self_model_observe(FakeRequest({
                "engine": "disposition",
                "observation_type": "flow_signal",
                "claim_text": "User enters flow when architecture and evidence line up.",
                "evidence_memory_ids": ["mem_2"],
                "entity_ids": ["ent_ricky"],
                "confidence": 0.7,
            })))
            trace_response = self.run_async(server.handle_decision_trace(FakeRequest({
                "query": "Build context graph?",
                "answer": "Yes: begin with source-backed observations.",
                "evidence_memory_ids": ["mem_1", "mem_2"],
                "self_model_observation_ids": [fake_store.observations[0]["observation_id"]],
                "entity_ids": ["ent_ricky"],
                "values_invoked": ["quality over speed"],
            })))
            packet_response = self.run_async(server.handle_context_packet(FakeRequest({
                "query": "Should Memibrium build the context graph first?",
                "episodic_evidence": [
                    {"id": "mem_1", "content": "Context stuffing helped but did not solve reasoning.", "source": "eval"}
                ],
                "include_decision_traces": True,
            })))
            recalled_packet_response = self.run_async(server.handle_context_packet(FakeRequest({
                "query": "What did active recall return?",
                "domain": "locomo-test",
            })))

        obs_payload = self.decode_response(obs_response)
        trace_payload = self.decode_response(trace_response)
        packet_payload = self.decode_response(packet_response)
        recalled_packet_payload = self.decode_response(recalled_packet_response)

        self.assertEqual(obs_payload["engine"], "disposition")
        self.assertEqual(trace_payload["schema"], "memibrium.decision_trace.v1")
        self.assertEqual(packet_payload["schema"], "memibrium.context_packet.v1")
        self.assertGreaterEqual(len(packet_payload["self_model_observations"]), 2)
        self.assertEqual(packet_payload["decision_traces"][0]["query"], "Build context graph?")
        self.assertEqual(packet_payload["provenance_summary"]["memory_ids"], ["mem_1", "mem_2"])
        self.assertEqual(recalled_packet_payload["episodic_evidence"][0]["memory_id"], "mem_recalled")
        self.assertEqual(recalled_packet_payload["episodic_evidence"][0]["content"], "Recalled episodic evidence from the active domain.")
        self.assertIn("mem_recalled", recalled_packet_payload["provenance_summary"]["memory_ids"])

    def test_context_packet_source_attribution_is_opt_in_and_records_internal_recall_source(self):
        fake_store = FakeContextStore()
        fake_agent = FakeQueryAgent()

        with patch.object(server, "store", fake_store), patch.object(server, "query_agent", fake_agent):
            plain_response = self.run_async(server.handle_context_packet(FakeRequest({
                "query": "What did active recall return?",
                "domain": "locomo-test",
                "top_k": 3,
            })))
            attributed_response = self.run_async(server.handle_context_packet(FakeRequest({
                "query": "What did active recall return?",
                "domain": "locomo-test",
                "top_k": 3,
                "include_source_attribution": True,
            })))

        plain_payload = self.decode_response(plain_response)
        attributed_payload = self.decode_response(attributed_response)

        self.assertNotIn("source_attribution", plain_payload)
        source = attributed_payload["source_attribution"]
        self.assertEqual(source["schema"], "memibrium.context_packet.source_attribution.v1")
        self.assertEqual(source["request"]["query"], "What did active recall return?")
        self.assertEqual(source["request"]["domain"], "locomo-test")
        self.assertEqual(source["request"]["top_k"], 3)
        self.assertEqual(source["retrieval_path"], "query_agent.recall")
        self.assertEqual(source["recall_tier"], "fake")
        self.assertEqual(source["evidence"][0]["id"], "mem_recalled")
        self.assertIn("content_sha256", source["evidence"][0])


if __name__ == "__main__":
    unittest.main()
