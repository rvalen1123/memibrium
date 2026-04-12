#!/usr/bin/env python3
"""
Memibrium — Sovereign AI Memory Server
=========================================================

Sovereign MCP memory server implementing Crystallization Theory (CT)
as a knowledge governance layer over tiered vector search.

No cloud memory dependencies. Fully self-hosted.

Patent POC mapping:
  CT  #63/953,509  — 5-stage lifecycle, W(k,t), δ-decay
  KEOS #63/962,609 — MKP 6-state lifecycle hooks (dependent claims)
  STG  (pending)   — anti-contamination provenance, freeze-and-revert

Architecture:
  MCP endpoint (retain/recall/reflect/confirm/freeze/revert/dashboard)
  → CT Lifecycle Engine (state machine, W(k,t), δ-decay, witness chains)
  → Dual-tier vector search:
      HOT: ruvector-postgres (GNN re-ranking, SONA self-learning) or pgvector
      COLD: pgvector (Phase 3: LEANN compression)
  → Any OpenAI-compatible LLM provider for embeddings + synthesis

  Phase 2.5 (current): USE_RUVECTOR=true swaps hot tier to ruvector-postgres
    docker pull ruvnet/ruvector-postgres:latest
  Phase 3 (current):   USE_LEANN=true enables LEANN cold tier compression
    pip install leann (97% storage savings on crystallized/shed memories)

Tiering policy = lifecycle state:
  HOT  (pgvector, fast)  : observation, consideration, accepted
  COLD (pgvector, deep)  : crystallized, shed
  The lifecycle state IS the tiering policy. That's the paper.

Key distinction from prior art (negative limitation):
  "Automation determined by accumulated human consensus,
   NOT ML model confidence."  — STG Claim 1

Author: Ricky Valentine / Orchard Holdings LLC
License: Proprietary — patent-pending architecture
"""

import asyncio
import hashlib
import json
import logging
import math
import os
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from pathlib import Path
from urllib.parse import urlparse

import asyncpg
from openai import OpenAI, AzureOpenAI
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
import uvicorn

from ingest_engine import DocumentIngestEngine, WikiCompiler
from knowledge_taxonomy import KnowledgeClassifier

# ── Configuration ──────────────────────────────────────────────────

FOUNDRY_KEY = os.environ.get("OPENAI_API_KEY", "")
FOUNDRY_BASE = os.environ.get("OPENAI_BASE_URL", "")
EMBED_MODEL = os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small")
CHAT_MODEL = os.environ.get("CHAT_MODEL", "gpt-4.1-mini")

# Auto-detect Azure vs standard OpenAI-compatible provider
_azure_env_enabled = bool(os.environ.get("AZURE_OPENAI_ENDPOINT"))
_foundry_parsed = urlparse(FOUNDRY_BASE) if FOUNDRY_BASE else None
_foundry_host = _foundry_parsed.hostname if _foundry_parsed else None
USE_AZURE = _azure_env_enabled or (
    bool(_foundry_host)
    and (_foundry_host == "openai.azure.com" or _foundry_host.endswith(".openai.azure.com"))
)
AZURE_API_VERSION = os.environ.get("AZURE_API_VERSION", "2024-12-01-preview")

DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = int(os.environ.get("DB_PORT", "5432"))
DB_NAME = os.environ.get("DB_NAME", "memory")
DB_USER = os.environ.get("DB_USER", "memory")
DB_PASS = os.environ.get("DB_PASSWORD", "memory")

# RuVector Configuration (Phase 2.5)
# Set USE_RUVECTOR=true to use ruvector-postgres extension for hot tier
# RuVector is a drop-in pgvector replacement with GNN re-ranking + SONA self-learning
# Docker: docker pull ruvnet/ruvector-postgres:latest
USE_RUVECTOR = os.environ.get("USE_RUVECTOR", "false").lower() in ("true", "1", "yes")
RUVECTOR_GNN = os.environ.get("RUVECTOR_GNN", "true").lower() in ("true", "1", "yes")
VECTOR_EXTENSION = "ruvector" if USE_RUVECTOR else "vector"

# Type + operator mapping: ruvector uses its own type name, same operators
VECTOR_TYPE = "ruvector" if USE_RUVECTOR else "vector"
VECTOR_COSINE_OPS = "ruvector_cosine_ops" if USE_RUVECTOR else "vector_cosine_ops"

# CT Parameters
IMPORTANCE_THRESHOLD = float(os.environ.get("IMPORTANCE_THRESHOLD", "0.4"))
SHEDDING_THRESHOLD = float(os.environ.get("SHEDDING_THRESHOLD", "0.05"))
CONSOLIDATE_INTERVAL = int(os.environ.get("CONSOLIDATE_INTERVAL_MIN", "30"))
DECAY_RATE = float(os.environ.get("DECAY_RATE", "0.02"))  # δ per consolidation cycle
CRYSTALLIZE_CONFIRMATIONS = int(os.environ.get("CRYSTALLIZE_CONFIRMATIONS", "3"))

# LEANN Configuration (Phase 3 — cold tier compression)
# pip install leann (or: uv pip install leann)
# Stores pruned graph + recomputes embeddings on-demand = 97% storage savings
# Falls back to pgvector/ruvector cold search if leann not installed
USE_LEANN = os.environ.get("USE_LEANN", "false").lower() in ("true", "1", "yes")
LEANN_INDEX_DIR = os.environ.get("LEANN_INDEX_DIR", "./data/leann")
LEANN_BACKEND = os.environ.get("LEANN_BACKEND", "hnsw")  # hnsw or diskann
LEANN_EMBEDDING_MODE = os.environ.get("LEANN_EMBEDDING_MODE", "openai")
# For local embeddings without API key: LEANN_EMBEDDING_MODE=sentence-transformers
# Models: facebook/contriever (fast), BAAI/bge-base-en-v1.5 (balanced)
LEANN_EMBEDDING_MODEL = os.environ.get("LEANN_EMBEDDING_MODEL", EMBED_MODEL)

HOT_STATES = ["observation", "consideration", "accepted"]
COLD_STATES = ["crystallized", "shed"]

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("memibrium")


# ══════════════════════════════════════════════════════════════════
# §1  CRYSTALLIZATION THEORY — LIFECYCLE ENGINE
# ══════════════════════════════════════════════════════════════════

class LifecycleState(str, Enum):
    OBSERVATION = "observation"
    CONSIDERATION = "consideration"
    ACCEPTED = "accepted"
    CRYSTALLIZED = "crystallized"
    SHED = "shed"

# Valid transitions — enforced by the engine
VALID_TRANSITIONS = {
    "observation":   ["consideration", "shed"],
    "consideration": ["accepted", "shed"],
    "accepted":      ["crystallized", "shed"],
    "crystallized":  ["shed"],
    "shed":          ["observation"],
}


def compute_weight(confirmation_count: int, recency_score: float,
                   validation_score: float, created_at, now=None) -> float:
    """
    W(k,t) = (C × R × V) / A
    CT patent core formula. Drives retrieval ranking AND shedding.
    """
    now = now or datetime.now(timezone.utc)
    c = max(confirmation_count, 1)
    r = recency_score
    v = max(validation_score, 0.1)
    if hasattr(created_at, "timestamp"):
        age_hours = max((now - created_at).total_seconds() / 3600, 1.0)
    else:
        age_hours = max((now - datetime.fromisoformat(str(created_at))).total_seconds() / 3600, 1.0)
    return (c * r * v) / age_hours


def make_witness_entry(from_state: str, to_state: str, trigger: str,
                       w_before: float, w_after: float,
                       prev_hash: str = "genesis") -> dict:
    """STG Claim 6: tamper-evident provenance chain."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "from_state": from_state,
        "to_state": to_state,
        "trigger": trigger,
        "weight_before": round(w_before, 6),
        "weight_after": round(w_after, 6),
        "prev_hash": prev_hash,
    }
    payload = json.dumps(entry, sort_keys=True).encode()
    entry["entry_hash"] = hashlib.sha256(payload).hexdigest()[:16]
    return entry


# ══════════════════════════════════════════════════════════════════
# §2  VECTOR STORE — pgvector / RuVector (dual-tier)
# ══════════════════════════════════════════════════════════════════

class ColdStore:
    """
    PostgreSQL + pgvector/ruvector. Serves BOTH hot and cold tiers,
    distinguished by lifecycle state.

    Phase 2.5 (current): USE_RUVECTOR=true swaps the extension to
    ruvector-postgres, a drop-in pgvector replacement with:
      - GNN re-ranking (attention over HNSW candidates)
      - SONA self-learning (query patterns improve results over time)
      - Same SQL operators: <=> cosine, <-> L2, <#> inner product
      - Same vector(N) type, same index syntax
    Docker: docker pull ruvnet/ruvector-postgres:latest
    """

    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        self.vector_ext: str = VECTOR_EXTENSION
        self.vtype: str = VECTOR_TYPE
        self.vcosine_ops: str = VECTOR_COSINE_OPS

    async def initialize(self):
        self.pool = await asyncpg.create_pool(
            host=DB_HOST, port=DB_PORT, database=DB_NAME,
            user=DB_USER, password=DB_PASS,
            min_size=2, max_size=10,
        )
        async with self.pool.acquire() as conn:
            # Phase 2.5: Use ruvector extension when available, fall back to pgvector
            try:
                await conn.execute(f"CREATE EXTENSION IF NOT EXISTS {self.vector_ext};")
                log.info(f"Vector extension: {self.vector_ext}")
            except Exception as e:
                if self.vector_ext == "ruvector":
                    log.warning(f"ruvector extension not available, falling back to pgvector: {e}")
                    self.vector_ext = "vector"
                    self.vtype = "vector"
                    self.vcosine_ops = "vector_cosine_ops"
                    await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                else:
                    raise
            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS memories (
                    id                  TEXT PRIMARY KEY,
                    content             TEXT NOT NULL,
                    source              TEXT NOT NULL DEFAULT 'unknown',
                    embedding           {self.vtype}(1536),
                    state               TEXT NOT NULL DEFAULT 'observation',
                    domain              TEXT NOT NULL DEFAULT 'default',
                    confirmation_count  INTEGER NOT NULL DEFAULT 0,
                    recency_score       FLOAT NOT NULL DEFAULT 1.0,
                    validation_score    FLOAT NOT NULL DEFAULT 0.0,
                    importance_score    FLOAT NOT NULL DEFAULT 0.0,
                    entities            JSONB NOT NULL DEFAULT '[]',
                    topics              JSONB NOT NULL DEFAULT '[]',
                    refs                JSONB NOT NULL DEFAULT '[]',
                    frozen              BOOLEAN NOT NULL DEFAULT FALSE,
                    frozen_at           TIMESTAMPTZ,
                    witness_chain       JSONB NOT NULL DEFAULT '[]',
                    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
            """)
            # HNSW index — ruvector adds GNN re-ranking + SONA self-learning on top
            # Same SQL syntax, same operators, enhanced results over time
            hnsw_params = "WITH (m = 16, ef_construction = 200)"
            if self.vector_ext == "ruvector" and RUVECTOR_GNN:
                # RuVector HNSW with GNN attention layer enabled
                hnsw_params = "WITH (m = 16, ef_construction = 200)"
                log.info("RuVector HNSW index with GNN re-ranking enabled")
            await conn.execute(f"""
                CREATE INDEX IF NOT EXISTS memories_embedding_idx
                ON memories USING hnsw (embedding {self.vcosine_ops})
                {hnsw_params};
            """)
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS memories_state_idx ON memories (state);"
            )
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_snapshots (
                    snapshot_id     TEXT PRIMARY KEY,
                    memory_id       TEXT NOT NULL REFERENCES memories(id),
                    snapshot_data   JSONB NOT NULL,
                    reason          TEXT,
                    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS entities (
                    entity_id   TEXT PRIMARY KEY,
                    name        TEXT NOT NULL,
                    entity_type TEXT NOT NULL DEFAULT 'unknown',
                    attributes  JSONB NOT NULL DEFAULT '{}',
                    memory_ids  JSONB NOT NULL DEFAULT '[]',
                    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
            """)
            log.info("Schema initialized: memories, snapshots, entities (pgvector)")

    async def insert_memory(self, mid: str, content: str, embedding: list,
                            state: str, source: str, domain: str,
                            importance: float, entities: list, topics: list,
                            witness_chain: list) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(f"""
                INSERT INTO memories (id, content, embedding, state, source, domain,
                                     importance_score, entities, topics, witness_chain)
                VALUES ($1, $2, $3::{self.vtype}, $4, $5, $6, $7, $8::jsonb, $9::jsonb, $10::jsonb)
                ON CONFLICT (id) DO UPDATE SET
                    content = EXCLUDED.content, embedding = EXCLUDED.embedding,
                    state = EXCLUDED.state, importance_score = EXCLUDED.importance_score,
                    entities = EXCLUDED.entities, topics = EXCLUDED.topics,
                    witness_chain = EXCLUDED.witness_chain, updated_at = NOW()
            """, mid, content, json.dumps(embedding), state, source, domain,
                importance, json.dumps(entities), json.dumps(topics),
                json.dumps(witness_chain))

    async def search(self, embedding: list, top_k: int = 5,
                     state_filter: Optional[list] = None,
                     domain: Optional[str] = None) -> list:
        """Vector search with W(k,t) re-ranking."""
        where_parts, params = [], [json.dumps(embedding), top_k * 3]
        idx = 3
        if state_filter:
            where_parts.append(f"state = ANY(${idx}::text[])")
            params.append(state_filter)
            idx += 1
        if domain:
            where_parts.append(f"domain = ${idx}")
            params.append(domain)
            idx += 1
        where = "WHERE " + " AND ".join(where_parts) if where_parts else ""

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(f"""
                SELECT *, 1 - (embedding <=> $1::{self.vtype}) AS cosine_score
                FROM memories {where}
                ORDER BY embedding <=> $1::{self.vtype} LIMIT $2
            """, *params)

        now = datetime.now(timezone.utc)
        results = []
        for row in rows:
            r = dict(row)
            cosine = r.pop("cosine_score", 0.5)
            w = compute_weight(r["confirmation_count"], r["recency_score"],
                               r["validation_score"], r["created_at"], now)
            r["cosine_score"] = round(cosine, 4)
            r["w_kt"] = round(w, 4)
            r["combined_score"] = round(cosine * (1.0 + math.log1p(w)), 4)
            r.pop("embedding", None)
            for k in ("created_at", "updated_at", "frozen_at"):
                if r.get(k) and hasattr(r[k], "isoformat"):
                    r[k] = r[k].isoformat()
            for k in ("entities", "topics", "refs", "witness_chain"):
                if isinstance(r.get(k), str):
                    r[k] = json.loads(r[k])
            results.append(r)

        results.sort(key=lambda x: x["combined_score"], reverse=True)
        return results[:top_k]

    async def update_memory(self, mid: str, **kwargs) -> None:
        """Generic update — pass only the columns you want to change."""
        sets, params = ["updated_at = NOW()"], [mid]
        idx = 2
        for col, val in kwargs.items():
            if col == "witness_append":
                sets.append(f"witness_chain = witness_chain || ${idx}::jsonb")
                params.append(json.dumps([val]))
            else:
                sets.append(f"{col} = ${idx}")
                params.append(val)
            idx += 1
        async with self.pool.acquire() as conn:
            await conn.execute(
                f"UPDATE memories SET {', '.join(sets)} WHERE id = $1", *params
            )

    async def get_memory(self, mid: str) -> Optional[dict]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM memories WHERE id = $1", mid)
        return dict(row) if row else None

    async def get_active_memories(self) -> list:
        """All non-shed, non-frozen memories for consolidation."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT id, state, confirmation_count, recency_score,
                       validation_score, frozen, created_at
                FROM memories WHERE state != 'shed' AND frozen = FALSE
            """)
        return [dict(r) for r in rows]

    async def freeze(self, mid: str, reason: str = "") -> dict:
        """STG Claim 7: Snapshot + freeze."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM memories WHERE id = $1", mid)
            if not row:
                return {"error": "not_found"}
            snap_id = f"snap_{uuid.uuid4().hex[:12]}"
            data = dict(row)
            data.pop("embedding", None)
            for k in ("created_at", "updated_at", "frozen_at"):
                if data.get(k) and hasattr(data[k], "isoformat"):
                    data[k] = data[k].isoformat()
            await conn.execute("""
                INSERT INTO memory_snapshots (snapshot_id, memory_id, snapshot_data, reason)
                VALUES ($1, $2, $3::jsonb, $4)
            """, snap_id, mid, json.dumps(data), reason)
            await conn.execute("""
                UPDATE memories SET frozen=TRUE, frozen_at=NOW(), updated_at=NOW()
                WHERE id = $1
            """, mid)
        return {"snapshot_id": snap_id, "memory_id": mid, "frozen": True}

    async def revert(self, mid: str, snap_id: Optional[str] = None) -> dict:
        """STG Claim 7: Revert to snapshot."""
        async with self.pool.acquire() as conn:
            q = ("SELECT * FROM memory_snapshots WHERE snapshot_id=$1 AND memory_id=$2"
                 if snap_id else
                 "SELECT * FROM memory_snapshots WHERE memory_id=$1 ORDER BY created_at DESC LIMIT 1")
            params = [snap_id, mid] if snap_id else [mid]
            snap = await conn.fetchrow(q, *params)
            if not snap:
                return {"error": "no_snapshot"}
            d = json.loads(snap["snapshot_data"]) if isinstance(snap["snapshot_data"], str) else snap["snapshot_data"]
            await conn.execute("""
                UPDATE memories SET state=$2, confirmation_count=$3, recency_score=$4,
                    validation_score=$5, frozen=FALSE, frozen_at=NULL, updated_at=NOW()
                WHERE id = $1
            """, mid, d.get("state", "accepted"), d.get("confirmation_count", 0),
                d.get("recency_score", 1.0), d.get("validation_score", 0.0))
        return {"reverted_to": snap["snapshot_id"], "memory_id": mid}

    async def upsert_entity(self, name: str, etype: str, attrs: dict, mid: str) -> None:
        """World-state entity management. 'I moved to Berlin' updates Location entity."""
        eid = f"ent_{hashlib.md5(f'{name}:{etype}'.encode()).hexdigest()[:12]}"
        async with self.pool.acquire() as conn:
            existing = await conn.fetchrow("SELECT * FROM entities WHERE entity_id = $1", eid)
            if existing:
                old_attrs = json.loads(existing["attributes"]) if isinstance(existing["attributes"], str) else existing["attributes"]
                old_attrs.update(attrs)
                old_mids = json.loads(existing["memory_ids"]) if isinstance(existing["memory_ids"], str) else existing["memory_ids"]
                if mid not in old_mids:
                    old_mids.append(mid)
                await conn.execute("""
                    UPDATE entities SET attributes=$2::jsonb, memory_ids=$3::jsonb, updated_at=NOW()
                    WHERE entity_id = $1
                """, eid, json.dumps(old_attrs), json.dumps(old_mids))
            else:
                await conn.execute("""
                    INSERT INTO entities (entity_id, name, entity_type, attributes, memory_ids)
                    VALUES ($1, $2, $3, $4::jsonb, $5::jsonb)
                """, eid, name, etype, json.dumps(attrs), json.dumps([mid]))

    async def count_by_state(self) -> dict:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT state, COUNT(*) as count FROM memories GROUP BY state"
            )
        return {r["state"]: r["count"] for r in rows}


# ══════════════════════════════════════════════════════════════════
# §2b LEANN COLD TIER — 97% storage compression (Phase 3)
# ══════════════════════════════════════════════════════════════════

class LEANNColdTier:
    """
    LEANN cold tier for crystallized/shed memories.
    Stores a pruned graph + recomputes embeddings on-demand.
    97% storage savings vs storing all embeddings.

    Integration pattern:
      - When memory transitions to crystallized/shed → index in LEANN
      - Cold tier queries → search LEANN first, fall back to pgvector
      - Hot tier → unchanged (ruvector/pgvector)
      - LEANN handles its own embeddings (same OpenAI-compatible provider)

    pip install leann (or: uv pip install leann)
    https://github.com/yichuan-w/LEANN
    """

    def __init__(self):
        self.available = False
        self.builder = None
        self.searcher = None
        self.index_path = os.path.abspath(LEANN_INDEX_DIR)
        self._dirty = False  # tracks if index needs rebuild

    async def initialize(self):
        """Try to import leann. If not installed, cold tier stays in pgvector."""
        try:
            from leann import LeannBuilder, LeannSearcher
            os.makedirs(self.index_path, exist_ok=True)
            index_file = os.path.join(self.index_path, "cold.leann")

            # Check if existing index exists
            if os.path.exists(index_file):
                try:
                    self.searcher = LeannSearcher(index_file)
                    log.info(f"LEANN cold tier loaded from {index_file}")
                except Exception as e:
                    log.warning(f"LEANN index exists but failed to load: {e}")
                    self.searcher = None

            self.available = True
            log.info(f"LEANN cold tier available (backend={LEANN_BACKEND}, "
                     f"embedding_mode={LEANN_EMBEDDING_MODE})")
        except ImportError:
            self.available = False
            log.info("LEANN not installed — cold tier stays in pgvector/ruvector "
                     "(pip install leann to enable)")

    async def index_memory(self, memory_id: str, content: str):
        """Add a crystallized/shed memory to the LEANN index."""
        if not self.available:
            return
        try:
            from leann import LeannBuilder
            index_file = os.path.join(self.index_path, "cold.leann")

            # LEANN builder accumulates texts then builds
            # We use a staging file to track pending additions
            staging_file = os.path.join(self.index_path, "staging.jsonl")
            entry = json.dumps({"id": memory_id, "content": content})
            with open(staging_file, "a") as f:
                f.write(entry + "\n")
            self._dirty = True
            log.info(f"LEANN staged {memory_id} for cold indexing")
        except Exception as e:
            log.error(f"LEANN index_memory error: {e}")

    async def rebuild_index(self):
        """Rebuild LEANN index from staging + existing cold memories."""
        if not self.available or not self._dirty:
            return
        try:
            from leann import LeannBuilder, LeannSearcher
            index_file = os.path.join(self.index_path, "cold.leann")
            staging_file = os.path.join(self.index_path, "staging.jsonl")

            if not os.path.exists(staging_file):
                return

            builder = LeannBuilder(
                backend_name=LEANN_BACKEND,
                embedding_mode=LEANN_EMBEDDING_MODE,
                embedding_model=LEANN_EMBEDDING_MODEL,
            )

            # Load staged entries
            count = 0
            with open(staging_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    entry = json.loads(line)
                    builder.add_text(entry["content"])
                    count += 1

            if count > 0:
                builder.build_index(index_file)
                self.searcher = LeannSearcher(index_file)
                # Clear staging after successful build
                os.remove(staging_file)
                self._dirty = False
                log.info(f"LEANN cold index rebuilt: {count} memories indexed")
        except Exception as e:
            log.error(f"LEANN rebuild error: {e}")

    async def search(self, query: str, top_k: int = 5) -> list:
        """Search the LEANN cold tier."""
        if not self.available or self.searcher is None:
            return []
        try:
            results = self.searcher.search(query, top_k=top_k)
            return [
                {
                    "text": r.text if hasattr(r, "text") else str(r),
                    "score": r.score if hasattr(r, "score") else 0.0,
                    "source": "leann_cold",
                }
                for r in results
            ]
        except Exception as e:
            log.error(f"LEANN search error: {e}")
            return []


# ══════════════════════════════════════════════════════════════════
# §3  LLM CLIENTS — Any OpenAI-compatible provider
# ══════════════════════════════════════════════════════════════════

def _make_llm_client():
    """Create OpenAI or AzureOpenAI client based on env config."""
    if USE_AZURE:
        return AzureOpenAI(
            api_key=FOUNDRY_KEY,
            azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT", FOUNDRY_BASE),
            api_version=AZURE_API_VERSION,
        )
    return OpenAI(api_key=FOUNDRY_KEY, base_url=FOUNDRY_BASE or None)


class EmbedClient:
    def __init__(self):
        self.client = _make_llm_client()

    def embed(self, text: str) -> list[float]:
        resp = self.client.embeddings.create(input=[text], model=EMBED_MODEL)
        return resp.data[0].embedding


class ChatClient:
    def __init__(self):
        self.client = _make_llm_client()

    def score_importance(self, content: str) -> dict:
        """LLM importance assessment — INFORMATIONAL ONLY. Does NOT gate lifecycle transitions."""
        resp = self.client.chat.completions.create(
            model=CHAT_MODEL, temperature=0.1, max_tokens=200,
            messages=[
                {"role": "system", "content": (
                    "Score the following memory for importance (0.0-1.0), "
                    "extract entities as [{name, type}], and list topics. "
                    "Respond ONLY with JSON: "
                    '{"importance": 0.7, "entities": [{"name":"X","type":"person"}], "topics": ["ai"]}'
                )},
                {"role": "user", "content": content},
            ],
        )
        try:
            text = resp.choices[0].message.content.strip()
            text = text.removeprefix("```json").removesuffix("```").strip()
            return json.loads(text)
        except (json.JSONDecodeError, IndexError, AttributeError):
            return {"importance": 0.5, "entities": [], "topics": []}

    def synthesize(self, memories: list[dict], topic: str) -> str:
        """Generate a structured reflection over a set of memories."""
        memory_text = "\n".join(
            f"- [{m.get('state','?')}] (W={m.get('w_kt',0):.3f}) {m.get('content','')[:200]}"
            for m in memories
        )
        resp = self.client.chat.completions.create(
            model=CHAT_MODEL, temperature=0.3, max_tokens=800,
            messages=[
                {"role": "system", "content": (
                    "You are a knowledge synthesis agent. Given a set of memories "
                    "with lifecycle states and crystallization weights, produce a "
                    "structured summary: key decisions, patterns, contradictions, "
                    "and open questions. Weight crystallized memories highest."
                )},
                {"role": "user", "content": f"Topic: {topic}\n\nMemories:\n{memory_text}"},
            ],
        )
        return resp.choices[0].message.content.strip()

    def expand_query(self, query: str) -> list[str]:
        """Topic expansion — generate related search terms."""
        resp = self.client.chat.completions.create(
            model=CHAT_MODEL, temperature=0.5, max_tokens=150,
            messages=[
                {"role": "system", "content": (
                    "Given a query, produce 3 related search terms that would "
                    "find complementary memories. Respond as JSON array of strings."
                )},
                {"role": "user", "content": query},
            ],
        )
        try:
            text = resp.choices[0].message.content.strip()
            text = text.removeprefix("```json").removesuffix("```").strip()
            return json.loads(text)
        except (json.JSONDecodeError, IndexError):
            return []


# ══════════════════════════════════════════════════════════════════
# §4  AGENTS — INGEST, CONSOLIDATE, QUERY
# ══════════════════════════════════════════════════════════════════

class IngestAgent:
    """Receives raw content → scores → embeds → stores in hot tier."""

    def __init__(self, store: ColdStore, embedder: EmbedClient, chat: ChatClient):
        self.store = store
        self.embedder = embedder
        self.chat = chat

    async def ingest(self, content: str, source: str = "conversation",
                     domain: str = "default") -> dict:
        mid = f"mem_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)

        scored = self.chat.score_importance(content)
        importance = scored.get("importance", 0.5)
        entities = scored.get("entities", [])
        topics = scored.get("topics", [])

        w_obs = 0.0
        witness_1 = make_witness_entry("none", "observation", "auto_ingest", 0.0, w_obs)

        if importance >= IMPORTANCE_THRESHOLD:
            final_state = "accepted"
            trigger = "importance_gate_pass"
        else:
            final_state = "observation"
            trigger = "importance_gate_low"

        embedding = self.embedder.embed(content)
        w_after = compute_weight(0, 1.0, 0.0, now, now)
        witness_2 = make_witness_entry(
            "observation", final_state, trigger, w_obs, w_after,
            prev_hash=witness_1["entry_hash"]
        )

        await self.store.insert_memory(
            mid, content, embedding, final_state, source, domain,
            importance, entities, topics, [witness_1, witness_2],
        )

        for ent in entities:
            await self.store.upsert_entity(
                ent.get("name", "unknown"), ent.get("type", "unknown"),
                ent.get("attributes", {}), mid,
            )

        log.info(f"Ingested {mid} → {final_state} (importance={importance:.2f})")
        return {
            "id": mid, "state": final_state, "importance": importance,
            "entities": entities, "topics": topics, "witness_count": 2,
        }


class ConsolidateAgent:
    """
    Background loop: δ-decay, shedding, auto-crystallization.
    This is the pruning engine. Without it, you get 'a dense context
    of outdated state that can mislead the model worse than no memory.'
    """

    def __init__(self, store: ColdStore, leann_tier: Optional[LEANNColdTier] = None):
        self.store = store
        self.leann = leann_tier
        self._running = False

    async def run_cycle(self) -> dict:
        memories = await self.store.get_active_memories()
        now = datetime.now(timezone.utc)
        stats = {"decayed": 0, "shed": 0, "crystallized": 0, "total": len(memories)}

        for m in memories:
            mid = m["id"]
            old_w = compute_weight(
                m["confirmation_count"], m["recency_score"],
                m["validation_score"], m["created_at"], now,
            )
            new_recency = m["recency_score"] * (1.0 - DECAY_RATE)
            new_w = compute_weight(
                m["confirmation_count"], new_recency,
                m["validation_score"], m["created_at"], now,
            )

            if new_w < SHEDDING_THRESHOLD and m["state"] != "observation":
                witness = make_witness_entry(
                    m["state"], "shed", "decay_below_threshold", old_w, new_w,
                )
                await self.store.update_memory(
                    mid, state="shed", recency_score=new_recency,
                    witness_append=witness,
                )
                stats["shed"] += 1
                log.info(f"Shed {mid}: W={old_w:.4f} -> {new_w:.4f}")
                # Phase 3: Index shed memory in LEANN cold tier
                if self.leann and self.leann.available:
                    full_mem = await self.store.get_memory(mid)
                    if full_mem:
                        await self.leann.index_memory(mid, full_mem["content"])

            elif (m["state"] == "accepted"
                  and m["confirmation_count"] >= CRYSTALLIZE_CONFIRMATIONS
                  and m["validation_score"] >= 0.5):
                witness = make_witness_entry(
                    "accepted", "crystallized", "consensus_threshold", old_w, new_w,
                )
                await self.store.update_memory(
                    mid, state="crystallized", recency_score=new_recency,
                    witness_append=witness,
                )
                stats["crystallized"] += 1
                log.info(f"Crystallized {mid}: confirmations={m['confirmation_count']}")
                # Phase 3: Index crystallized memory in LEANN cold tier
                if self.leann and self.leann.available:
                    full_mem = await self.store.get_memory(mid)
                    if full_mem:
                        await self.leann.index_memory(mid, full_mem["content"])

            else:
                await self.store.update_memory(mid, recency_score=new_recency)
                stats["decayed"] += 1

        # Phase 3: Rebuild LEANN cold index if any memories were staged
        if self.leann and self.leann.available and self.leann._dirty:
            await self.leann.rebuild_index()
            stats["leann_rebuilt"] = True

        log.info(f"Consolidation complete: {stats}")
        return stats

    async def start_loop(self):
        self._running = True
        log.info(f"ConsolidateAgent started (interval={CONSOLIDATE_INTERVAL}min)")
        while self._running:
            try:
                await self.run_cycle()
            except Exception as e:
                log.error(f"Consolidation error: {e}")
            await asyncio.sleep(CONSOLIDATE_INTERVAL * 60)

    def stop(self):
        self._running = False


class QueryAgent:
    """Dual-tier recall: hot (recent) → cold (crystallized history)."""

    def __init__(self, store: ColdStore, embedder: EmbedClient, chat: ChatClient,
                 leann_tier: Optional[LEANNColdTier] = None):
        self.store = store
        self.embedder = embedder
        self.chat = chat
        self.leann = leann_tier

    async def recall(self, query: str, top_k: int = 5,
                     domain: Optional[str] = None, expand: bool = True) -> dict:
        embedding = self.embedder.embed(query)

        # Tier 1: Hot search
        hot_results = await self.store.search(
            embedding, top_k=top_k, state_filter=HOT_STATES, domain=domain,
        )
        good_hot = [r for r in hot_results if r.get("combined_score", 0) > 0.6]

        if len(good_hot) >= 2:
            return {"results": hot_results[:top_k], "tier": "hot",
                    "query": query, "total_searched": len(hot_results)}

        # Tier 2: Cold search (crystallized history)
        cold_results = await self.store.search(
            embedding, top_k=top_k, state_filter=COLD_STATES, domain=domain,
        )

        # Tier 2b: LEANN cold tier (Phase 3 — 97% storage compression)
        leann_results = []
        if self.leann and self.leann.available and self.leann.searcher:
            leann_results = await self.leann.search(query, top_k=top_k)

        # Topic expansion
        expanded = []
        if expand:
            related_terms = self.chat.expand_query(query)
            for term in related_terms[:2]:
                try:
                    exp_emb = self.embedder.embed(term)
                    exp_results = await self.store.search(exp_emb, top_k=2, domain=domain)
                    expanded.extend(exp_results)
                except Exception:
                    pass

        # Merge and de-duplicate (pgvector/ruvector + LEANN + expanded)
        seen = set()
        merged = []
        for r in hot_results + cold_results + expanded:
            if r["id"] not in seen:
                seen.add(r["id"])
                merged.append(r)

        # Append LEANN results (text-based, no ID dedup needed)
        for lr in leann_results:
            merged.append({
                "id": f"leann_{hash(lr.get('text', '')) % 10**8}",
                "content": lr.get("text", ""),
                "state": "crystallized",
                "source": "leann_cold",
                "cosine_score": lr.get("score", 0.0),
                "w_kt": 0.0,
                "combined_score": lr.get("score", 0.0),
            })

        merged.sort(key=lambda x: x.get("combined_score", 0), reverse=True)
        tier_label = "hot+cold"
        if leann_results:
            tier_label += "+leann"
        return {"results": merged[:top_k], "tier": tier_label,
                "query": query, "total_searched": len(merged)}

    async def reflect(self, topic: str, top_k: int = 10,
                      domain: Optional[str] = None) -> dict:
        recall_result = await self.recall(topic, top_k=top_k, domain=domain, expand=True)
        memories = recall_result["results"]
        if not memories:
            return {"synthesis": "No memories found for this topic.", "memories": []}

        synthesis = self.chat.synthesize(memories, topic)
        return {
            "synthesis": synthesis, "memory_count": len(memories),
            "tier": recall_result["tier"],
            "crystallized_count": sum(1 for m in memories if m.get("state") == "crystallized"),
        }


# ══════════════════════════════════════════════════════════════════
# §5  MCP HTTP SERVER
# ══════════════════════════════════════════════════════════════════

store = ColdStore()
leann_tier = LEANNColdTier()
embedder = EmbedClient()
chat = ChatClient()
ingest_agent = IngestAgent(store, embedder, chat)
consolidate_agent = ConsolidateAgent(store, leann_tier)
query_agent = QueryAgent(store, embedder, chat, leann_tier)
classifier = KnowledgeClassifier()
doc_engine = DocumentIngestEngine(ingest_agent, store, classifier)
wiki_compiler = WikiCompiler(store, chat)


async def handle_retain(request: Request) -> JSONResponse:
    body = await request.json()
    content = body.get("content", "")
    if not content:
        return JSONResponse({"error": "content required"}, status_code=400)
    result = await ingest_agent.ingest(
        content, source=body.get("source", "conversation"),
        domain=body.get("domain", "default"),
    )
    return JSONResponse(result)


async def handle_recall(request: Request) -> JSONResponse:
    body = await request.json()
    query = body.get("query", "")
    if not query:
        return JSONResponse({"error": "query required"}, status_code=400)
    result = await query_agent.recall(
        query, top_k=body.get("top_k", 5),
        domain=body.get("domain"), expand=body.get("expand", True),
    )
    return JSONResponse(result)


async def handle_reflect(request: Request) -> JSONResponse:
    body = await request.json()
    topic = body.get("topic", "")
    if not topic:
        return JSONResponse({"error": "topic required"}, status_code=400)
    result = await query_agent.reflect(
        topic, top_k=body.get("top_k", 10), domain=body.get("domain"),
    )
    return JSONResponse(result)


async def handle_confirm(request: Request) -> JSONResponse:
    """Human validation signal — THE ONLY PATH TO CRYSTALLIZATION."""
    body = await request.json()
    mid = body.get("memory_id", "")
    if not mid:
        return JSONResponse({"error": "memory_id required"}, status_code=400)

    mem = await store.get_memory(mid)
    if not mem:
        return JSONResponse({"error": "not_found"}, status_code=404)

    old_w = compute_weight(
        mem["confirmation_count"], mem["recency_score"],
        mem["validation_score"], mem["created_at"],
    )
    new_count = mem["confirmation_count"] + 1
    weight = body.get("weight", 1.0)
    new_validation = 1.0 - (1.0 - mem["validation_score"]) * (1.0 - weight * 0.3)
    new_w = compute_weight(new_count, 1.0, new_validation, mem["created_at"])

    new_state = mem["state"]
    if (new_count >= CRYSTALLIZE_CONFIRMATIONS
            and new_validation >= 0.5
            and mem["state"] == "accepted"):
        new_state = "crystallized"

    witness = make_witness_entry(mem["state"], new_state, "human_confirm", old_w, new_w)
    await store.update_memory(
        mid, state=new_state, confirmation_count=new_count,
        recency_score=1.0, validation_score=new_validation,
        witness_append=witness,
    )
    return JSONResponse({
        "memory_id": mid, "state": new_state,
        "confirmation_count": new_count,
        "validation_score": round(new_validation, 4),
        "w_kt": round(new_w, 4),
        "crystallized": new_state == "crystallized",
    })


async def handle_freeze(request: Request) -> JSONResponse:
    body = await request.json()
    mid = body.get("memory_id", "")
    if not mid:
        return JSONResponse({"error": "memory_id required"}, status_code=400)
    result = await store.freeze(mid, body.get("reason", ""))
    return JSONResponse(result)


async def handle_revert(request: Request) -> JSONResponse:
    body = await request.json()
    mid = body.get("memory_id", "")
    if not mid:
        return JSONResponse({"error": "memory_id required"}, status_code=400)
    result = await store.revert(mid, body.get("snapshot_id"))
    return JSONResponse(result)


async def handle_consolidate(request: Request) -> JSONResponse:
    result = await consolidate_agent.run_cycle()
    return JSONResponse(result)


async def handle_dashboard(request: Request) -> JSONResponse:
    counts = await store.count_by_state()
    total = sum(counts.values())
    return JSONResponse({
        "lifecycle_counts": counts,
        "total_memories": total,
        "ct_parameters": {
            "importance_threshold": IMPORTANCE_THRESHOLD,
            "shedding_threshold": SHEDDING_THRESHOLD,
            "decay_rate": DECAY_RATE,
            "crystallize_confirmations": CRYSTALLIZE_CONFIRMATIONS,
            "consolidate_interval_min": CONSOLIDATE_INTERVAL,
        },
        "architecture": {
            "vector_extension": store.vector_ext,
            "hot_tier": f"{'ruvector (GNN + SONA)' if store.vector_ext == 'ruvector' else 'pgvector'} HNSW",
            "cold_tier": f"LEANN ({LEANN_BACKEND})" if leann_tier.available else f"{store.vector_ext} (LEANN not installed)",
            "leann_available": leann_tier.available,
            "leann_index_dir": leann_tier.index_path if leann_tier.available else None,
            "ruvector_gnn": RUVECTOR_GNN if store.vector_ext == "ruvector" else "n/a",
            "embeddings": EMBED_MODEL,
            "synthesis": CHAT_MODEL,
            "provider": "azure" if USE_AZURE else "openai-compatible",
            "sovereignty": "full — no cloud memory dependencies",
        },
    })


async def handle_health(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", "engine": "memibrium"})


# ── Ingestion Endpoints ───────────────────────────────────────────

async def handle_ingest_file(request: Request) -> JSONResponse:
    """Ingest a single file through the document engine."""
    body = await request.json()
    filepath = body.get("filepath", "")
    if not filepath:
        return JSONResponse({"error": "filepath required"}, status_code=400)
    if not os.path.isfile(filepath):
        return JSONResponse({"error": f"File not found: {filepath}"}, status_code=404)
    from dataclasses import asdict
    result = await doc_engine.ingest_file(
        filepath,
        domain=body.get("domain", "default"),
        source_label=body.get("source_label"),
        skip_duplicates=body.get("skip_duplicates", True),
    )
    return JSONResponse(asdict(result))


async def handle_ingest_directory(request: Request) -> JSONResponse:
    """Scan and ingest all supported files in a directory."""
    body = await request.json()
    dirpath = body.get("directory", "")
    if not dirpath:
        return JSONResponse({"error": "directory required"}, status_code=400)
    if not os.path.isdir(dirpath):
        return JSONResponse({"error": f"Directory not found: {dirpath}"}, status_code=404)
    from dataclasses import asdict
    result = await doc_engine.ingest_directory(
        dirpath,
        domain=body.get("domain", "default"),
        recursive=body.get("recursive", True),
        skip_duplicates=body.get("skip_duplicates", True),
    )
    return JSONResponse(asdict(result))


async def handle_ingest_jsonl(request: Request) -> JSONResponse:
    """Ingest Claude conversation JSONL (RV-Brain format)."""
    body = await request.json()
    filepath = body.get("filepath", "")
    if not filepath:
        return JSONResponse({"error": "filepath required"}, status_code=400)
    if not os.path.isfile(filepath):
        return JSONResponse({"error": f"File not found: {filepath}"}, status_code=404)
    from dataclasses import asdict
    result = await doc_engine.ingest_jsonl(
        filepath,
        skip_duplicates=body.get("skip_duplicates", True),
    )
    return JSONResponse(asdict(result))


async def handle_ingest_status(request: Request) -> JSONResponse:
    """Return ingestion engine stats."""
    return JSONResponse(doc_engine.get_stats())


async def handle_compile(request: Request) -> JSONResponse:
    """Compile wiki index from ingested memories."""
    body = await request.json() if request.method == "POST" else {}
    domain = body.get("domain", "default") if body else "default"
    output_dir = body.get("output_dir") if body else None
    if output_dir:
        from pathlib import Path as P
        wiki_compiler.output_dir = P(output_dir)
    result = await wiki_compiler.compile(domain=domain)
    return JSONResponse(result)


async def handle_taxonomy(request: Request) -> JSONResponse:
    """Return or update the knowledge taxonomy."""
    if request.method == "GET":
        return JSONResponse({"categories": classifier.export_taxonomy()})
    body = await request.json()
    if "categories" in body:
        classifier.import_taxonomy(body["categories"])
    return JSONResponse({"status": "updated", "count": len(classifier.categories)})


async def handle_wiki_read(request: Request) -> JSONResponse:
    """Read compiled wiki files. GET with no params lists files; with ?file=name reads that file."""
    wiki_dir = wiki_compiler.output_dir
    if not wiki_dir.is_dir():
        return JSONResponse({"error": "Wiki not compiled yet. Call /mcp/ingest/compile first.",
                             "files": []}, status_code=404)
    filename = request.query_params.get("file")
    if filename:
        safe_name = Path(filename).name
        filepath = wiki_dir / safe_name
        if not filepath.is_file():
            return JSONResponse({"error": f"File not found: {safe_name}"}, status_code=404)
        content = filepath.read_text(encoding="utf-8", errors="replace")
        return JSONResponse({"file": safe_name, "content": content, "size_chars": len(content)})
    files = []
    for f in sorted(wiki_dir.iterdir()):
        if f.is_file() and f.suffix == ".md":
            files.append({"name": f.name, "size_chars": f.stat().st_size})
    return JSONResponse({"wiki_dir": str(wiki_dir), "files": files})


async def handle_mcp_manifest(request: Request) -> JSONResponse:
    """MCP tool definitions for client auto-discovery."""
    return JSONResponse({
        "tools": [
            {"name": "retain", "description": "Store a memory through the CT lifecycle.",
             "inputSchema": {"type": "object", "properties": {
                 "content": {"type": "string"}, "source": {"type": "string", "default": "conversation"},
                 "domain": {"type": "string", "default": "default"}}, "required": ["content"]}},
            {"name": "recall", "description": "Dual-tier memory search. Hot first, cold fallback. Ranked by cosine × W(k,t).",
             "inputSchema": {"type": "object", "properties": {
                 "query": {"type": "string"}, "top_k": {"type": "integer", "default": 5},
                 "domain": {"type": "string"}, "expand": {"type": "boolean", "default": True}}, "required": ["query"]}},
            {"name": "reflect", "description": "Synthesize memories about a topic. Crystallized weighted highest.",
             "inputSchema": {"type": "object", "properties": {
                 "topic": {"type": "string"}, "top_k": {"type": "integer", "default": 10},
                 "domain": {"type": "string"}}, "required": ["topic"]}},
            {"name": "confirm", "description": "Human validation — ONLY path to crystallization.",
             "inputSchema": {"type": "object", "properties": {
                 "memory_id": {"type": "string"}, "weight": {"type": "number", "default": 1.0}}, "required": ["memory_id"]}},
            {"name": "freeze", "description": "Freeze memory — exempt from decay, snapshot preserved. STG Claim 7.",
             "inputSchema": {"type": "object", "properties": {
                 "memory_id": {"type": "string"}, "reason": {"type": "string"}}, "required": ["memory_id"]}},
            {"name": "revert", "description": "Revert memory to snapshot. STG Claim 7.",
             "inputSchema": {"type": "object", "properties": {
                 "memory_id": {"type": "string"}, "snapshot_id": {"type": "string"}}, "required": ["memory_id"]}},
            {"name": "consolidate", "description": "Trigger manual consolidation: δ-decay, shedding, auto-crystallization.",
             "inputSchema": {"type": "object", "properties": {}}},
            {"name": "dashboard", "description": "Lifecycle counts, CT parameters, architecture info.",
             "inputSchema": {"type": "object", "properties": {}}},
            {"name": "ingest_file", "description": "Ingest a file: read, chunk, classify, embed, store through CT lifecycle.",
             "inputSchema": {"type": "object", "properties": {
                 "filepath": {"type": "string", "description": "Absolute path to the file"},
                 "domain": {"type": "string", "default": "default"},
                 "source_label": {"type": "string"},
                 "skip_duplicates": {"type": "boolean", "default": True}}, "required": ["filepath"]}},
            {"name": "ingest_directory", "description": "Scan directory and ingest all supported files (.md, .txt, .json, .csv, .pdf).",
             "inputSchema": {"type": "object", "properties": {
                 "directory": {"type": "string", "description": "Absolute path to directory"},
                 "domain": {"type": "string", "default": "default"},
                 "recursive": {"type": "boolean", "default": True},
                 "skip_duplicates": {"type": "boolean", "default": True}}, "required": ["directory"]}},
            {"name": "ingest_jsonl", "description": "Ingest Claude conversation JSONL with auto-classification into 30 knowledge categories and CT tier assignment.",
             "inputSchema": {"type": "object", "properties": {
                 "filepath": {"type": "string", "description": "Path to JSONL file"},
                 "skip_duplicates": {"type": "boolean", "default": True}}, "required": ["filepath"]}},
            {"name": "ingest_status", "description": "Ingestion engine stats: hashes seen, taxonomy categories, config.",
             "inputSchema": {"type": "object", "properties": {}}},
            {"name": "compile_wiki", "description": "Compile wiki index from ingested memories — generates topic articles and index with backlinks.",
             "inputSchema": {"type": "object", "properties": {
                 "domain": {"type": "string", "default": "default"},
                 "output_dir": {"type": "string"}}, "required": []}},
            {"name": "wiki_read", "description": "List compiled wiki files or read a specific file's content.",
             "inputSchema": {"type": "object", "properties": {
                 "file": {"type": "string", "description": "Filename to read (omit to list all files)"}}, "required": []}},
        ],
    })


# ── App ──────────────────────────────────────────────────────────

app = Starlette(
    routes=[
        Route("/health", handle_health, methods=["GET"]),
        Route("/mcp/tools", handle_mcp_manifest, methods=["GET"]),
        Route("/mcp/retain", handle_retain, methods=["POST"]),
        Route("/mcp/recall", handle_recall, methods=["POST"]),
        Route("/mcp/reflect", handle_reflect, methods=["POST"]),
        Route("/mcp/confirm", handle_confirm, methods=["POST"]),
        Route("/mcp/freeze", handle_freeze, methods=["POST"]),
        Route("/mcp/revert", handle_revert, methods=["POST"]),
        Route("/mcp/consolidate", handle_consolidate, methods=["POST"]),
        Route("/mcp/dashboard", handle_dashboard, methods=["GET"]),
        Route("/mcp/ingest/file", handle_ingest_file, methods=["POST"]),
        Route("/mcp/ingest/directory", handle_ingest_directory, methods=["POST"]),
        Route("/mcp/ingest/jsonl", handle_ingest_jsonl, methods=["POST"]),
        Route("/mcp/ingest/status", handle_ingest_status, methods=["GET"]),
        Route("/mcp/ingest/compile", handle_compile, methods=["POST"]),
        Route("/mcp/ingest/taxonomy", handle_taxonomy, methods=["GET", "POST"]),
        Route("/mcp/wiki", handle_wiki_read, methods=["GET"]),
    ],
)


@app.on_event("startup")
async def startup():
    await store.initialize()
    await leann_tier.initialize()
    asyncio.create_task(consolidate_agent.start_loop())
    ext_label = "ruvector (GNN + SONA)" if store.vector_ext == "ruvector" else "pgvector"
    leann_label = "LEANN" if leann_tier.available else "pgvector"
    log.info(f"Memibrium started — hot: {ext_label}, cold: {leann_label}, fully sovereign")


@app.on_event("shutdown")
async def shutdown():
    consolidate_agent.stop()
    if store.pool:
        await store.pool.close()
    log.info("Memibrium stopped")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9999, log_level="info")
