#!/usr/bin/env python3
"""Database test: tied lexical, ILIKE and temporal results do not depend on insertion order.

Runs only when MEMIBRIUM_TEST_DSN names a disposable Postgres server whose user may create databases,
for example postgresql://postgres:postgres@127.0.0.1:5432/postgres. Each run creates its own
memibrium_tiebreak_<random> database, loads the same rows in several insertion orders and drops the
database at the end. Without the variable every test is skipped. pgvector is not needed: the semantic
stream is not exercised here.
"""

import asyncio
import os
import random
import unittest
import uuid
from datetime import datetime, timedelta, timezone

import asyncpg

from hybrid_retrieval import HybridRetriever

DSN = os.environ.get("MEMIBRIUM_TEST_DSN")

# The columns HybridRetriever reads, with the types MemoryStore creates in server.py (embedding omitted).
SCHEMA = """
    CREATE TABLE memories (
        id                  TEXT PRIMARY KEY,
        content             TEXT NOT NULL,
        source              TEXT NOT NULL DEFAULT 'unknown',
        state               TEXT NOT NULL DEFAULT 'observation',
        domain              TEXT NOT NULL DEFAULT 'default',
        memory_type         TEXT NOT NULL DEFAULT 'semantic',
        confirmation_count  INTEGER NOT NULL DEFAULT 0,
        recency_score       FLOAT NOT NULL DEFAULT 1.0,
        validation_score    FLOAT NOT NULL DEFAULT 0.0,
        importance_score    FLOAT NOT NULL DEFAULT 0.0,
        entities            JSONB NOT NULL DEFAULT '[]',
        topics              JSONB NOT NULL DEFAULT '[]',
        refs                JSONB NOT NULL DEFAULT '{}',
        frozen              BOOLEAN NOT NULL DEFAULT FALSE,
        frozen_at           TIMESTAMPTZ,
        witness_chain       JSONB NOT NULL DEFAULT '[]',
        created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
"""

AT = datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc)
TWINS = [f"twin-{n:02d}" for n in range(8)]
LOWEST_THREE = TWINS[:3]


def insertion_orders(rows):
    """The same rows in ascending, descending and a fixed shuffled id order."""
    ascending = sorted(rows, key=lambda r: r["id"])
    shuffled = list(ascending)
    random.Random(7).shuffle(shuffled)
    return {"ascending": ascending, "descending": ascending[::-1], "shuffled": shuffled}


def twins(content, extra=()):
    """Eight rows with identical content and created_at, so every stream scores them equally."""
    return [{"id": i, "content": content, "created_at": AT} for i in TWINS] + list(extra)


@unittest.skipUnless(DSN, "MEMIBRIUM_TEST_DSN is not set")
class TieBreakDatabaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dbname = f"memibrium_tiebreak_{uuid.uuid4().hex[:12]}"
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

    def results_by_order(self, rows, run):
        """Load `rows` into a fresh table once per insertion order, one INSERT per row, and call `run`."""
        async def main():
            pool = await asyncpg.create_pool(DSN, database=self.dbname, min_size=1, max_size=1)
            try:
                async with pool.acquire() as conn:
                    await conn.execute("DROP TABLE IF EXISTS memories")
                    await conn.execute(SCHEMA)
                out = {}
                for name, ordered in insertion_orders(rows).items():
                    async with pool.acquire() as conn:
                        await conn.execute("TRUNCATE memories")
                        for row in ordered:
                            await conn.execute(
                                "INSERT INTO memories (id, content, created_at) VALUES ($1, $2, $3)",
                                row["id"], row["content"], row["created_at"],
                            )
                    out[name] = await run(HybridRetriever(pool=pool, vtype="pgvector"))
                return out
            finally:
                await pool.close()

        return asyncio.run(main())

    def assertSameInEveryOrder(self, out, expected=None):
        first = next(iter(out.values()))
        for name, got in out.items():
            self.assertEqual(got, first, name)
            if expected is not None:
                self.assertEqual(got, expected, name)

    def test_lexical_ties_are_cut_by_id_in_every_insertion_order(self):
        rows = twins("Rotate the signing keys every quarter.",
                     extra=[{"id": "other", "content": "Use pnpm for installs.", "created_at": AT}])

        async def run(retriever):
            telemetry = retriever._new_telemetry(query="rotate signing keys", top_k=3, fetch_k=3, state_filter=None,
                                                 domain=None, use_rrf=True, rerank=False)
            result = await retriever._lexical_search("rotate signing keys", top_k=3, telemetry=telemetry)
            self.assertEqual(telemetry["streams"]["lexical"]["path"], "tsvector")
            return [m["id"] for m in result]

        self.assertSameInEveryOrder(self.results_by_order(rows, run), expected=LOWEST_THREE)

    def test_ilike_fallback_ties_are_cut_by_id_in_every_insertion_order(self):
        # "which" is an English stop word, so the tsvector query matches nothing and the ILIKE fallback runs.
        rows = twins("Which twin is this?",
                     extra=[{"id": "other", "content": "Use pnpm for installs.", "created_at": AT}])

        async def run(retriever):
            telemetry = retriever._new_telemetry(query="which", top_k=3, fetch_k=3, state_filter=None,
                                                 domain=None, use_rrf=True, rerank=False)
            result = await retriever._lexical_search("which", top_k=3, telemetry=telemetry)
            self.assertEqual(telemetry["streams"]["lexical"]["path"], "ilike_fallback")
            return [m["id"] for m in result]

        self.assertSameInEveryOrder(self.results_by_order(rows, run), expected=LOWEST_THREE)

    def test_temporal_ties_are_cut_by_id_in_every_insertion_order(self):
        rows = twins("Deployed the release.",
                     extra=[{"id": "later", "content": "Outside the window.", "created_at": AT + timedelta(days=2)}])

        async def run(retriever):
            result = await retriever._temporal_search(AT - timedelta(hours=1), AT + timedelta(hours=1), top_k=3)
            return [m["id"] for m in result]

        self.assertSameInEveryOrder(self.results_by_order(rows, run), expected=LOWEST_THREE)

    def test_full_search_without_embedding_is_identical_in_every_insertion_order(self):
        rows = twins("Rotate the signing keys every quarter.",
                     extra=[{"id": "other", "content": "Rotate nothing, use pnpm.", "created_at": AT}])

        async def run(retriever):
            result = await retriever.search("rotate signing keys", embedding=None, top_k=3)
            return [m["id"] for m in result]

        self.assertSameInEveryOrder(self.results_by_order(rows, run))


if __name__ == "__main__":
    unittest.main()
