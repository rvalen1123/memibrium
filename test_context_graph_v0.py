#!/usr/bin/env python3
"""Regression tests for Memibrium context graph / self-model v0 primitives."""

import asyncio
import json
import unittest
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

        with patch.object(server, "store", fake_store):
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

        obs_payload = self.decode_response(obs_response)
        trace_payload = self.decode_response(trace_response)
        packet_payload = self.decode_response(packet_response)

        self.assertEqual(obs_payload["engine"], "disposition")
        self.assertEqual(trace_payload["schema"], "memibrium.decision_trace.v1")
        self.assertEqual(packet_payload["schema"], "memibrium.context_packet.v1")
        self.assertGreaterEqual(len(packet_payload["self_model_observations"]), 2)
        self.assertEqual(packet_payload["decision_traces"][0]["query"], "Build context graph?")
        self.assertEqual(packet_payload["provenance_summary"]["memory_ids"], ["mem_1", "mem_2"])


if __name__ == "__main__":
    unittest.main()
