#!/usr/bin/env python3
"""Database test: a human review of a self-model observation or decision trace survives a later
unreviewed re-submission of the same record (MED-254, review finding S1).

The record ids are content hashes, so an agent re-submitting the same observation or trace (over MCP,
where it cannot set user_state or a non-proposed status) hits ON CONFLICT. The upsert must keep the
reviewed state, confidence, evidence and metadata; an explicit review write must still update the row.

Runs only when MEMIBRIUM_TEST_DSN names a disposable Postgres with pgvector whose user may create
databases. Each run creates its own memibrium_review_<random> database, builds the real schema with
ColdStore.initialize and drops the database at the end. Without the variable every test is skipped.
"""

import asyncio
import os
import unittest
import uuid
from unittest.mock import patch
from urllib.parse import unquote, urlparse

import asyncpg

import server

DSN = os.environ.get("MEMIBRIUM_TEST_DSN")

OBSERVATION = {"engine": "manual", "observation_type": "preference", "claim_text": "Prefers evidence first.",
               "evidence_memory_ids": ["mem_1"], "confidence": 0.4}
TRACE = {"query": "Ship the parser now?", "answer": "Not yet; tests first.", "evidence_memory_ids": ["mem_1"]}


@unittest.skipUnless(DSN, "needs MEMIBRIUM_TEST_DSN: a disposable Postgres with pgvector whose user may "
                           "CREATE DATABASE; MEMIBRIUM_TEST_DSN is not set")
class ReviewPreservationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dbname = f"memibrium_review_{uuid.uuid4().hex[:12]}"
        asyncio.run(cls._admin(f'CREATE DATABASE "{cls.dbname}"'))

    @classmethod
    def tearDownClass(cls):
        asyncio.run(cls._admin(f'DROP DATABASE IF EXISTS "{cls.dbname}" WITH (FORCE)'))

    @staticmethod
    async def _admin(statement):
        conn = await asyncpg.connect(DSN)
        try:
            await conn.execute(statement)
        finally:
            await conn.close()

    def run_with_store(self, scenario):
        url = urlparse(DSN)
        settings = {"DB_HOST": url.hostname or "localhost", "DB_PORT": url.port or 5432, "DB_NAME": self.dbname,
                    "DB_USER": unquote(url.username or ""), "DB_PASS": unquote(url.password or "")}

        async def main():
            with patch.multiple(server, **settings):
                store = server.ColdStore()
                await store.initialize()  # the real DDL, so the test cannot drift from the schema
            try:
                async with store.pool.acquire() as conn:
                    await conn.execute("TRUNCATE self_model_observations, decision_traces")
                return await scenario(store)
            finally:
                await store.pool.close()

        return asyncio.run(main())

    def test_unreviewed_resubmission_keeps_a_human_review(self):
        async def scenario(store):
            results = {}
            for review in ("confirmed", "rejected"):
                obs = dict(OBSERVATION, claim_text=f"{OBSERVATION['claim_text']} ({review})")
                created = await store.create_self_model_observation(dict(obs))
                oid = created["observation_id"]
                # A human review (the REST path, with user_state set explicitly).
                await store.create_self_model_observation(
                    dict(obs, user_state=review, lifecycle_state="accepted", confidence=0.6))
                # The agent re-submits the same observation (same id-seed fields): unreviewed, confidence 1.0,
                # different metadata. Before the fix this reset the review and raised confidence.
                again = await store.create_self_model_observation(
                    dict(obs, confidence=1.0, metadata={"agent": True}))
                self.assertEqual(again["observation_id"], oid)
                async with store.pool.acquire() as conn:
                    results[review] = dict(await conn.fetchrow(
                        "SELECT user_state, lifecycle_state, confidence, evidence_memory_ids::text AS ev, "
                        "metadata::text AS md, surfaced_count FROM self_model_observations "
                        "WHERE observation_id = $1", oid))
            return results

        for review, row in self.run_with_store(scenario).items():
            self.assertEqual(row["user_state"], review, review)
            self.assertEqual(row["lifecycle_state"], "accepted", review)
            self.assertAlmostEqual(row["confidence"], 0.6, msg=review)
            self.assertEqual(row["ev"], '["mem_1"]', review)
            self.assertEqual(row["md"], "{}", review)

    def test_unreviewed_rows_still_update_and_explicit_reviews_still_apply(self):
        async def scenario(store):
            created = await store.create_self_model_observation(dict(OBSERVATION))
            oid = created["observation_id"]
            await store.create_self_model_observation(dict(OBSERVATION, confidence=0.7))  # unreviewed: updates
            async with store.pool.acquire() as conn:
                first = await conn.fetchval("SELECT confidence FROM self_model_observations WHERE observation_id=$1", oid)
            await store.create_self_model_observation(dict(OBSERVATION, user_state="confirmed"))
            await store.create_self_model_observation(dict(OBSERVATION, user_state="rejected"))  # a human changes it
            async with store.pool.acquire() as conn:
                state = await conn.fetchval("SELECT user_state FROM self_model_observations WHERE observation_id=$1", oid)
            return first, state

        confidence, state = self.run_with_store(scenario)
        self.assertAlmostEqual(confidence, 0.7)
        self.assertEqual(state, "rejected")

    def test_proposed_resubmission_keeps_a_reviewed_trace(self):
        async def scenario(store):
            created = await store.create_decision_trace(dict(TRACE))
            tid = created["trace_id"]
            await store.create_decision_trace(dict(TRACE, status="rejected", outcome_signal={"by": "human"}))
            again = await store.create_decision_trace(dict(TRACE, outcome_signal={"by": "agent"}))
            self.assertEqual(again["trace_id"], tid)
            async with store.pool.acquire() as conn:
                kept = dict(await conn.fetchrow(
                    "SELECT status, outcome_signal::text AS sig FROM decision_traces WHERE trace_id=$1", tid))
            await store.create_decision_trace(dict(TRACE, status="corrected"))  # a human re-review still applies
            async with store.pool.acquire() as conn:
                rereviewed = await conn.fetchval("SELECT status FROM decision_traces WHERE trace_id=$1", tid)
            return kept, rereviewed

        kept, rereviewed = self.run_with_store(scenario)
        self.assertEqual(kept["status"], "rejected")
        self.assertEqual(kept["sig"], '{"by": "human"}')
        self.assertEqual(rereviewed, "corrected")


if __name__ == "__main__":
    unittest.main()
