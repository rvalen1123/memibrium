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
from concurrent.futures import ThreadPoolExecutor
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


def _serialize_result(obj):
    """Recursively convert datetime / date objects to ISO strings for JSON."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _serialize_result(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize_result(v) for v in obj]
    return obj


from ingest_engine import DocumentIngestEngine, WikiCompiler
from knowledge_taxonomy import KnowledgeClassifier
from hybrid_retrieval import HybridRetriever, approximate_tokens
from memory_hierarchy import MemoryHierarchyManager, HierarchyLevel

# ── Configuration ──────────────────────────────────────────────────

FOUNDRY_KEY = os.environ.get("OPENAI_API_KEY", "")
FOUNDRY_BASE = os.environ.get("OPENAI_BASE_URL", "")
EMBED_BASE = os.environ.get("EMBEDDING_BASE_URL", FOUNDRY_BASE or "http://localhost:11434/v1")  # separate endpoint for embeddings (default: ollama)
EMBED_MODEL = os.environ.get("EMBEDDING_MODEL", "nomic-embed-text")
# Ollama chat endpoint (sovereign — no cloud API key needed)
OLLAMA_CHAT_BASE = os.environ.get("OLLAMA_CHAT_BASE", "http://ollama:11434/v1")
CHAT_MODEL = os.environ.get("CHAT_MODEL", "gemma4:e4b")

# Azure embedding endpoint (optional — separate from chat endpoint)
AZURE_EMBEDDING_ENDPOINT = os.environ.get("AZURE_EMBEDDING_ENDPOINT", "")
AZURE_EMBEDDING_DEPLOYMENT = os.environ.get("AZURE_EMBEDDING_DEPLOYMENT", "")
AZURE_EMBEDDING_API_KEY = os.environ.get("AZURE_EMBEDDING_API_KEY", os.environ.get("AZURE_OPENAI_API_KEY", ""))
AZURE_CHAT_ENDPOINT = os.environ.get("AZURE_CHAT_ENDPOINT", "")
AZURE_CHAT_DEPLOYMENT = os.environ.get("AZURE_CHAT_DEPLOYMENT", "")
AZURE_CHAT_API_KEY = os.environ.get("AZURE_CHAT_API_KEY", os.environ.get("AZURE_OPENAI_API_KEY", ""))
AZURE_OPENAI_DEPLOYMENT = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "")

# Auto-detect Azure vs standard OpenAI-compatible provider
# Only enable Azure if endpoint is set AND API key is valid (not empty, not placeholder)
_azure_api_key = os.environ.get("AZURE_OPENAI_API_KEY", "")
_azure_env_enabled = bool(os.environ.get("AZURE_OPENAI_ENDPOINT")) and bool(_azure_api_key) and _azure_api_key != "***"
_foundry_parsed = urlparse(FOUNDRY_BASE) if FOUNDRY_BASE else None
_foundry_host = _foundry_parsed.hostname if _foundry_parsed else None
USE_AZURE = _azure_env_enabled or (
    bool(_foundry_host)
    and (_foundry_host == "openai.azure.com" or _foundry_host.endswith(".openai.azure.com"))
)
AZURE_API_VERSION = os.environ.get("AZURE_API_VERSION", "2024-12-01-preview")

# Azure uses deployment names as model identifiers in API calls
# DISABLED: hardcoded to local Ollama for sovereign operation
# if USE_AZURE and AZURE_OPENAI_DEPLOYMENT:
#     CHAT_MODEL = AZURE_OPENAI_DEPLOYMENT

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
ENABLE_BACKGROUND_SCORING = os.environ.get("ENABLE_BACKGROUND_SCORING", "true").lower() in ("true", "1", "yes")
ENABLE_CONTRADICTION_DETECTION = os.environ.get("ENABLE_CONTRADICTION_DETECTION", "true").lower() in ("true", "1", "yes")
ENABLE_HIERARCHY_PROCESSING = os.environ.get("ENABLE_HIERARCHY_PROCESSING", "true").lower() in ("true", "1", "yes")

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
                    memory_type         TEXT NOT NULL DEFAULT 'semantic',
                    confirmation_count  INTEGER NOT NULL DEFAULT 0,
                    recency_score       FLOAT NOT NULL DEFAULT 1.0,
                    validation_score    FLOAT NOT NULL DEFAULT 0.0,
                    importance_score    FLOAT NOT NULL DEFAULT 0.0,
                    entities            JSONB NOT NULL DEFAULT '[]',
                    topics              JSONB NOT NULL DEFAULT '[]',
                    refs                JSONB NOT NULL DEFAULT '{{}}',
                    frozen              BOOLEAN NOT NULL DEFAULT FALSE,
                    frozen_at           TIMESTAMPTZ,
                    witness_chain       JSONB NOT NULL DEFAULT '[]',
                    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
            """)
            # Schema migrations for existing deployments (must run before indexes)
            await conn.execute("ALTER TABLE memories ADD COLUMN IF NOT EXISTS memory_type TEXT NOT NULL DEFAULT 'semantic'")
            await conn.execute("ALTER TABLE memories ADD COLUMN IF NOT EXISTS frozen BOOLEAN NOT NULL DEFAULT FALSE")
            await conn.execute("ALTER TABLE memories ADD COLUMN IF NOT EXISTS frozen_at TIMESTAMPTZ")
            await conn.execute("ALTER TABLE memories ADD COLUMN IF NOT EXISTS validation_score FLOAT NOT NULL DEFAULT 0.0")
            await conn.execute("ALTER TABLE memories ADD COLUMN IF NOT EXISTS witness_chain JSONB NOT NULL DEFAULT '[]'")
            await conn.execute("ALTER TABLE memories ADD COLUMN IF NOT EXISTS refs JSONB NOT NULL DEFAULT '[]'")
            # HNSW index
            hnsw_params = "WITH (m = 16, ef_construction = 200)"
            if self.vector_ext == "ruvector" and RUVECTOR_GNN:
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
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS memories_type_idx ON memories (memory_type);"
            )
            # BM25 full-text search support (hybrid retrieval)
            await conn.execute("""
                ALTER TABLE memories
                ADD COLUMN IF NOT EXISTS content_tsv tsvector
                GENERATED ALWAYS AS (to_tsvector('english', COALESCE(content, ''))) STORED;
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS memories_content_tsv_idx
                ON memories USING GIN (content_tsv);
            """)
            # Temporal indexing
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS memories_created_at_idx
                ON memories (created_at);
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS temporal_expressions (
                    expr_id      TEXT PRIMARY KEY,
                    memory_id    TEXT NOT NULL REFERENCES memories(id),
                    expression   TEXT NOT NULL,
                    kind         TEXT NOT NULL DEFAULT 'relative',
                    start_time   TIMESTAMPTZ,
                    end_time     TIMESTAMPTZ,
                    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
            """)
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS temporal_expr_memory_idx ON temporal_expressions (memory_id);"
            )
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS temporal_expr_time_idx ON temporal_expressions (start_time, end_time);"
            )
            # Entity relationships table (must come AFTER entities table)
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
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS entity_relationships (
                    rel_id      TEXT PRIMARY KEY,
                    entity_a    TEXT NOT NULL REFERENCES entities(entity_id),
                    entity_b    TEXT NOT NULL REFERENCES entities(entity_id),
                    rel_type    TEXT NOT NULL DEFAULT 'cooccurs',
                    weight      FLOAT NOT NULL DEFAULT 1.0,
                    evidence    JSONB NOT NULL DEFAULT '[]',
                    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
            """)
            # User feedback signals for personalized ranking
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS user_feedback (
                    feedback_id     TEXT PRIMARY KEY,
                    memory_id       TEXT NOT NULL REFERENCES memories(id),
                    action          TEXT NOT NULL,  -- confirm, freeze, revert
                    weight          FLOAT NOT NULL DEFAULT 1.0,
                    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
            """)
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS feedback_memory_idx ON user_feedback (memory_id);"
            )
            # Contradiction tracking
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS contradictions (
                    contradiction_id TEXT PRIMARY KEY,
                    memory_a_id      TEXT NOT NULL REFERENCES memories(id),
                    memory_b_id      TEXT NOT NULL REFERENCES memories(id),
                    reason           TEXT,
                    resolved         BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
            """)
            # Graph edges between memories sharing entities
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_edges (
                    edge_id     TEXT PRIMARY KEY,
                    source_id   TEXT NOT NULL REFERENCES memories(id),
                    target_id   TEXT NOT NULL REFERENCES memories(id),
                    edge_type   TEXT NOT NULL DEFAULT 'related',
                    weight      FLOAT NOT NULL DEFAULT 1.0,
                    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
            """)
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS memory_edges_source_idx ON memory_edges (source_id);"
            )
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS memory_edges_target_idx ON memory_edges (target_id);"
            )
            log.info("Schema initialized: memories, snapshots, entities, feedback, contradictions, edges")

    async def insert_memory(self, mid: str, content: str, embedding: list,
                            state: str, source: str, domain: str,
                            importance: float, entities: list, topics: list,
                            witness_chain: list, memory_type: str = "semantic",
                            event_at: Optional[str] = None,
                            refs: Optional[dict] = None) -> None:
        created_at = None
        if event_at:
            created_at = datetime.fromisoformat(event_at.replace("Z", "+00:00"))
        refs = refs or {}
        async with self.pool.acquire() as conn:
            await conn.execute(f"""
                INSERT INTO memories (id, content, embedding, state, source, domain,
                                     memory_type, importance_score, entities, topics, refs, witness_chain, created_at)
                VALUES ($1, $2, $3::{self.vtype}, $4, $5, $6, $7, $8, $9::jsonb, $10::jsonb, $11::jsonb, $12::jsonb,
                        COALESCE($13, NOW()))
                ON CONFLICT (id) DO UPDATE SET
                    content = EXCLUDED.content, embedding = EXCLUDED.embedding,
                    state = EXCLUDED.state, importance_score = EXCLUDED.importance_score,
                    memory_type = EXCLUDED.memory_type,
                    entities = EXCLUDED.entities, topics = EXCLUDED.topics,
                    refs = EXCLUDED.refs,
                    witness_chain = EXCLUDED.witness_chain,
                    created_at = EXCLUDED.created_at,
                    updated_at = NOW()
            """, mid, content, json.dumps(embedding), state, source, domain,
                memory_type, importance, json.dumps(entities), json.dumps(topics), json.dumps(refs),
                json.dumps(witness_chain), created_at)

    async def add_feedback(self, memory_id: str, action: str, weight: float = 1.0) -> None:
        fid = f"fb_{uuid.uuid4().hex[:12]}"
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO user_feedback (feedback_id, memory_id, action, weight)
                VALUES ($1, $2, $3, $4)
            """, fid, memory_id, action, weight)

    async def get_memory_feedback_score(self, memory_id: str) -> float:
        """Compute personalized boost from confirm/freeze/revert signals."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT
                    COALESCE(SUM(CASE WHEN action = 'confirm' THEN weight ELSE 0 END), 0) as confirms,
                    COALESCE(SUM(CASE WHEN action = 'freeze' THEN weight * 2 ELSE 0 END), 0) as freezes,
                    COALESCE(SUM(CASE WHEN action = 'revert' THEN -weight ELSE 0 END), 0) as reverts
                FROM user_feedback
                WHERE memory_id = $1
            """, memory_id)
        if not row:
            return 0.0
        return float(row["confirms"]) + float(row["freezes"]) + float(row["reverts"])

    async def find_similar_semantic_memories(self, embedding: list, exclude_id: str,
                                              threshold: float = 0.85, limit: int = 5) -> list:
        """Find semantic memories with high cosine similarity — candidates for contradiction."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(f"""
                SELECT id, content, 1 - (embedding <=> $1::{self.vtype}) AS cosine_score
                FROM memories
                WHERE memory_type = 'semantic'
                  AND id != $2
                  AND state != 'shed'
                ORDER BY embedding <=> $1::{self.vtype}
                LIMIT $3
            """, json.dumps(embedding), exclude_id, limit)
        return [dict(r) for r in rows if r["cosine_score"] >= threshold]

    async def record_contradiction(self, mid_a: str, mid_b: str, reason: str = "") -> None:
        cid = f"cntr_{uuid.uuid4().hex[:12]}"
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO contradictions (contradiction_id, memory_a_id, memory_b_id, reason)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT DO NOTHING
            """, cid, mid_a, mid_b, reason)

    async def get_unresolved_contradictions(self, limit: int = 10) -> list:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT c.contradiction_id, c.memory_a_id, c.memory_b_id, c.reason,
                       ma.content as content_a, mb.content as content_b
                FROM contradictions c
                JOIN memories ma ON ma.id = c.memory_a_id
                JOIN memories mb ON mb.id = c.memory_b_id
                WHERE c.resolved = FALSE
                LIMIT $1
            """, limit)
        return [dict(r) for r in rows]

    async def resolve_contradiction(self, cid: str, resolution: str) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE contradictions SET resolved = TRUE WHERE contradiction_id = $1
            """, cid)

    async def create_memory_edge(self, source_id: str, target_id: str,
                                  edge_type: str = "related", weight: float = 1.0) -> None:
        eid = f"edge_{uuid.uuid4().hex[:12]}"
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO memory_edges (edge_id, source_id, target_id, edge_type, weight)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT DO NOTHING
            """, eid, source_id, target_id, edge_type, weight)

    async def get_related_memories(self, memory_id: str, limit: int = 5) -> list:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT m.*, e.edge_type, e.weight
                FROM memory_edges e
                JOIN memories m ON m.id = e.target_id
                WHERE e.source_id = $1 AND m.state != 'shed'
                UNION ALL
                SELECT m.*, e.edge_type, e.weight
                FROM memory_edges e
                JOIN memories m ON m.id = e.source_id
                WHERE e.target_id = $1 AND m.state != 'shed'
                LIMIT $2
            """, memory_id, limit)
        return [dict(r) for r in rows]

    async def get_prefetch_candidates(self, topic: str, embedding: list,
                                       top_k: int = 5) -> list:
        """Retrieve hot memories likely to be needed next for a given topic."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(f"""
                SELECT *, 1 - (embedding <=> $1::{self.vtype}) AS cosine_score
                FROM memories
                WHERE state = ANY($2::text[])
                  AND (topics @> $3::jsonb OR entities @> $4::jsonb)
                ORDER BY embedding <=> $1::{self.vtype}
                LIMIT $5
            """, json.dumps(embedding), HOT_STATES,
                json.dumps([topic]), json.dumps([{"name": topic}]), top_k)
        results = []
        for row in rows:
            r = dict(row)
            r.pop("embedding", None)
            for k in ("created_at", "updated_at", "frozen_at"):
                if r.get(k) and hasattr(r[k], "isoformat"):
                    r[k] = r[k].isoformat()
            for k in ("entities", "topics", "refs", "witness_chain"):
                if isinstance(r.get(k), str):
                    r[k] = json.loads(r[k])
            results.append(r)
        return results

    async def search(self, embedding: list, top_k: int = 5,
                     state_filter: Optional[list] = None,
                     domain: Optional[str] = None,
                     apply_personalization: bool = True) -> list:
        """Vector search with W(k,t) re-ranking + optional personalization."""
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
            if cosine is None:
                cosine = 0.5
            w = compute_weight(r["confirmation_count"], r["recency_score"],
                               r["validation_score"], r["created_at"], now)
            r["cosine_score"] = round(cosine, 4)
            r["w_kt"] = round(w, 4)
            # Base combined score
            base_score = cosine * (1.0 + math.log1p(w))
            # Personalization boost from user feedback (confirm/freeze/revert)
            if apply_personalization:
                feedback_boost = 0.0
                try:
                    feedback_boost = await self.get_memory_feedback_score(r["id"])
                except Exception:
                    pass
                # Normalize: each confirm adds ~0.05, freeze adds ~0.10, revert subtracts
                base_score += min(feedback_boost * 0.05, 0.3)
            # Memory type decay adjustment in scoring
            mem_type = r.get("memory_type", "semantic")
            if mem_type == "episodic":
                base_score *= 0.9  # episodic memories are less stable
            elif mem_type == "procedural":
                base_score *= 1.05  # procedures are reliably useful
            r["combined_score"] = round(base_score, 4)
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
                SELECT id, state, memory_type, confirmation_count, recency_score,
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
    if USE_AZURE and AZURE_EMBEDDING_ENDPOINT:
        return AzureOpenAI(
            api_key=AZURE_EMBEDDING_API_KEY or FOUNDRY_KEY,
            azure_endpoint=AZURE_EMBEDDING_ENDPOINT,
            api_version=AZURE_API_VERSION,
        )
    return OpenAI(api_key=FOUNDRY_KEY, base_url=FOUNDRY_BASE or None)


class EmbedClient:
    """Embedding client with content-hash dedup cache."""

    # Dedicated thread pool so embedding calls never compete with hierarchy LLM tasks
    _executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="embed")

    def __init__(self):
        _embed_host = urlparse(EMBED_BASE).hostname if EMBED_BASE else None
        # Auto-detect Azure embeddings endpoint (separate from chat endpoint)
        _use_azure_embed = bool(AZURE_EMBEDDING_ENDPOINT) and bool(AZURE_EMBEDDING_API_KEY)
        if _use_azure_embed:
            self.client = AzureOpenAI(
                api_key=AZURE_EMBEDDING_API_KEY,
                azure_endpoint=AZURE_EMBEDDING_ENDPOINT,
                api_version=AZURE_API_VERSION,
            )
        else:
            self.client = OpenAI(api_key="ollama", base_url=EMBED_BASE)
        self._model = AZURE_EMBEDDING_DEPLOYMENT if _use_azure_embed else EMBED_MODEL
        self._dimensions = 1536 if _use_azure_embed else None
        # LRU cache with bounded size (max 2000 entries)
        self._cache: dict[str, list[float]] = {}
        self._cache_order: list[str] = []  # LRU tracking
        self._cache_max = 2000
        self._cache_hits = 0
        self._cache_misses = 0

    def _cache_put(self, key: str, value: list[float]):
        if key in self._cache:
            self._cache_order.remove(key)
        elif len(self._cache) >= self._cache_max:
            evict = self._cache_order.pop(0)
            del self._cache[evict]
        self._cache[key] = value
        self._cache_order.append(key)

    def embed(self, text: str) -> list[float]:
        h = hashlib.sha256(text.encode()).hexdigest()
        if h in self._cache:
            self._cache_hits += 1
            return self._cache[h]
        self._cache_misses += 1
        for attempt in range(3):
            try:
                kwargs = {'input': [text], 'model': self._model}
                if self._dimensions:
                    kwargs['dimensions'] = self._dimensions
                resp = self.client.embeddings.create(**kwargs)
                emb = resp.data[0].embedding
                self._cache_put(h, emb)
                return emb
            except Exception as e:
                if attempt < 2 and ("500" in str(e) or "429" in str(e) or "timeout" in str(e).lower()):
                    import time; time.sleep(0.5 * (attempt + 1))
                    continue
                raise

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Batch embed multiple texts in one API call. Returns embeddings in same order."""
        if not texts:
            return []
        # Check cache first, track which need embedding
        hashes = [hashlib.sha256(t.encode()).hexdigest() for t in texts]
        results: list[list[float] | None] = [None] * len(texts)
        uncached_indices = []
        uncached_texts = []
        for i, h in enumerate(hashes):
            if h in self._cache:
                results[i] = self._cache[h]
                self._cache_hits += 1
            else:
                uncached_indices.append(i)
                uncached_texts.append(texts[i])
                self._cache_misses += 1
        if uncached_texts:
            # Azure supports up to 16 inputs per call; batch in chunks
            BATCH_SIZE = 16
            for chunk_start in range(0, len(uncached_texts), BATCH_SIZE):
                chunk = uncached_texts[chunk_start:chunk_start + BATCH_SIZE]
                chunk_idx = uncached_indices[chunk_start:chunk_start + BATCH_SIZE]
                for attempt in range(3):
                    try:
                        kwargs = {'input': chunk, 'model': self._model}
                        if self._dimensions:
                            kwargs['dimensions'] = self._dimensions
                        resp = self.client.embeddings.create(**kwargs)
                        for j, data in enumerate(resp.data):
                            idx = chunk_idx[j]
                            results[idx] = data.embedding
                            self._cache_put(hashes[idx], data.embedding)
                        break
                    except Exception as e:
                        if attempt < 2 and ("500" in str(e) or "429" in str(e)):
                            import time; time.sleep(0.5 * (attempt + 1))
                            continue
                        raise
        return results

    def cache_stats(self) -> dict:
        total = self._cache_hits + self._cache_misses
        return {
            "cached": len(self._cache),
            "hits": self._cache_hits,
            "misses": self._cache_misses,
            "hit_rate": f"{self._cache_hits/total*100:.1f}%" if total else "N/A",
        }

    def test_azure_endpoint(self, test_text: str = "Hello world") -> dict:
        """Test Azure OpenAI embeddings endpoint and return timing + dimension info."""
        if not (AZURE_EMBEDDING_ENDPOINT and AZURE_EMBEDDING_DEPLOYMENT):
            return {"error": "AZURE_EMBEDDING_ENDPOINT and AZURE_EMBEDDING_DEPLOYMENT not configured"}
        import time
        try:
            client = AzureOpenAI(
                api_key=AZURE_EMBEDDING_API_KEY or FOUNDRY_KEY,
                azure_endpoint=AZURE_EMBEDDING_ENDPOINT,
                api_version=AZURE_API_VERSION,
            )
            t0 = time.perf_counter()
            resp = client.embeddings.create(input=[test_text], model=AZURE_EMBEDDING_DEPLOYMENT)
            latency_ms = round((time.perf_counter() - t0) * 1000, 2)
            emb = resp.data[0].embedding
            return {
                "success": True,
                "latency_ms": latency_ms,
                "dimensions": len(emb),
                "endpoint": AZURE_EMBEDDING_ENDPOINT,
                "deployment": AZURE_EMBEDDING_DEPLOYMENT,
                "sample_embedding_prefix": emb[:3],
            }
        except Exception as e:
            return {"success": False, "error": str(e), "endpoint": AZURE_EMBEDDING_ENDPOINT}


class LocalSLMClient:
    """Fast local SLM for importance scoring via Ollama."""

    SLM_MODEL = os.environ.get("SLM_MODEL", "qwen2.5:0.5b")
    SLM_BASE = os.environ.get("SLM_BASE_URL", "http://ollama:11434/v1")

    def __init__(self):
        self.client = OpenAI(api_key="ollama", base_url=self.SLM_BASE)

    def score_importance(self, content: str) -> dict:
        """Lightweight importance scoring using local SLM."""
        try:
            resp = self.client.chat.completions.create(
                model=self.SLM_MODEL, temperature=0.1, max_tokens=200,
                messages=[
                    {"role": "system", "content": (
                        "Score memory importance 0.0-1.0. Extract entities as JSON array "
                        "with name and type. List topics. Respond ONLY with JSON: "
                        '{"importance":0.7,"entities":[{"name":"X","type":"person"}],"topics":["ai"]}'
                    )},
                    {"role": "user", "content": content},
                ],
            )
            text = resp.choices[0].message.content.strip()
            text = text.removeprefix("```json").removesuffix("```").strip()
            return json.loads(text)
        except Exception:
            return {"importance": 0.5, "entities": [], "topics": []}

    def score_batch(self, items: list[tuple[str, str]]) -> list[dict]:
        """Batch score multiple memories in one LLM call."""
        if not items:
            return []
        numbered = "\n".join(f"{i+1}. [{mid}] {content}" for i, (mid, content) in enumerate(items))
        try:
            resp = self.client.chat.completions.create(
                model=self.SLM_MODEL, temperature=0.1, max_tokens=400 + len(items) * 100,
                messages=[
                    {"role": "system", "content": (
                        "For each numbered memory, score importance 0.0-1.0, extract entities, "
                        "and list topics. Respond ONLY with JSON array in same order: "
                        '[{"importance":0.7,"entities":[{"name":"X","type":"person"}],"topics":["ai"]}, ...]'
                    )},
                    {"role": "user", "content": numbered},
                ],
            )
            text = resp.choices[0].message.content.strip()
            text = text.removeprefix("```json").removesuffix("```").strip()
            results = json.loads(text)
            if isinstance(results, list) and len(results) == len(items):
                return results
            # Fallback: try to parse from a dict keyed by numbers
            if isinstance(results, dict):
                return [results.get(str(i+1), {"importance":0.5,"entities":[],"topics":[]}) for i in range(len(items))]
        except Exception:
            pass
        return [{"importance": 0.5, "entities": [], "topics": []} for _ in items]


class ChatClient:
    def __init__(self):
        _use_azure_chat = bool(AZURE_CHAT_ENDPOINT) and bool(AZURE_CHAT_API_KEY)
        if _use_azure_chat:
            # Azure AI Foundry uses OpenAI-compatible /models/ endpoint
            self.client = OpenAI(
                api_key=AZURE_CHAT_API_KEY,
                base_url=AZURE_CHAT_ENDPOINT.rstrip("/") + "/models",
            )
            self.model = AZURE_CHAT_DEPLOYMENT or "gpt-4.1-mini"
            log.info(f"ChatClient: Azure Foundry ({AZURE_CHAT_ENDPOINT}, model={self.model})")
        else:
            # Fallback: Ollama for sovereign local chat
            self.client = OpenAI(api_key="ollama", base_url=OLLAMA_CHAT_BASE)
            self.model = CHAT_MODEL
            log.info(f"ChatClient: Ollama ({OLLAMA_CHAT_BASE}, model={self.model})")

    def score_importance(self, content: str) -> dict:
        """LLM importance assessment — INFORMATIONAL ONLY. Does NOT gate lifecycle transitions."""
        resp = self.client.chat.completions.create(
            model=self.model, temperature=0.1, max_tokens=200,
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
        try:
            resp = self.client.chat.completions.create(
                model=self.model, temperature=0.3, max_tokens=800,
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
        except Exception:
            log.debug("Synthesis failed (LLM unavailable), using fallback summary")
            lines = [
                f"Topic: {topic}",
                f"Memory count: {len(memories)}",
                "Top memories:",
            ]
            lines.extend(
                f"- [{m.get('state','?')}] {m.get('content','')[:200]}"
                for m in memories[:5]
            )
            return "\n".join(lines)

    def expand_query(self, query: str) -> list[str]:
        """Topic expansion — generate related search terms."""
        try:
            resp = self.client.chat.completions.create(
                model=self.model, temperature=0.5, max_tokens=150,
                messages=[
                    {"role": "system", "content": (
                        "Given a query, produce 3 related search terms that would "
                        "find complementary memories. Respond as JSON array of strings."
                    )},
                    {"role": "user", "content": query},
                ],
            )
            text = resp.choices[0].message.content.strip()
            text = text.removeprefix("```json").removesuffix("```").strip()
            return json.loads(text)
        except Exception:
            log.debug("Query expansion failed (LLM unavailable), continuing without expansion")
            return []


# ══════════════════════════════════════════════════════════════════
# §4  AGENTS — INGEST, CONSOLIDATE, QUERY
# ══════════════════════════════════════════════════════════════════

class IngestAgent:
    """
    Receives raw content → fast-path embeds+stores → batches background scoring via local SLM.
    """

    BATCH_SIZE = int(os.environ.get("SCORE_BATCH_SIZE", "5"))
    BATCH_TIMEOUT = float(os.environ.get("SCORE_BATCH_TIMEOUT", "1.0"))

    def __init__(self, store: ColdStore, embedder: EmbedClient, chat: ChatClient):
        self.store = store
        self.embedder = embedder
        self.chat = chat
        self.slm = LocalSLMClient()
        self._background_tasks = set()
        self._hierarchy_sem = asyncio.Semaphore(3)  # Max 3 concurrent hierarchy LLM tasks
        self._score_queue: list[tuple] = []
        self._queue_lock = asyncio.Lock()
        self._flush_task = None
        self._flush_event = asyncio.Event()
        self._running = True

    def start(self):
        """Start background batch flush loop. Call once event loop is running."""
        if not ENABLE_BACKGROUND_SCORING:
            log.info("Background scoring disabled; score batch loop not started")
            return
        if self._flush_task is None:
            self._flush_task = asyncio.create_task(self._batch_flush_loop())

    def _auto_classify_memory_type(self, content: str) -> str:
        """Episodic / Semantic / Procedural auto-classification (heuristic, no LLM)."""
        c = content.lower()
        procedural_markers = ["step", "how to", "first", "then", "next", "finally",
                              "run ", "execute", "deploy", "install", "configure"]
        proc_score = sum(1 for m in procedural_markers if m in c)
        episodic_markers = ["yesterday", "last week", "today", "this morning",
                            "we discussed", "i tried", "we decided", "meeting"]
        ep_score = sum(1 for m in episodic_markers if m in c)
        semantic_markers = ["is a", "are a", "means", "defined as", "equals",
                            "standard", "port", "protocol", "maximum", "minimum"]
        sem_score = sum(1 for m in semantic_markers if m in c)
        scores = [("procedural", proc_score), ("episodic", ep_score), ("semantic", sem_score)]
        best = max(scores, key=lambda x: x[1])
        return best[0] if best[1] > 0 else "semantic"

    async def _batch_flush_loop(self):
        """Background loop: flush scoring batch every BATCH_TIMEOUT seconds."""
        while self._running:
            try:
                await asyncio.wait_for(self._flush_event.wait(), timeout=self.BATCH_TIMEOUT)
            except asyncio.TimeoutError:
                pass
            self._flush_event.clear()
            await self._flush_batch()

    async def _flush_batch(self):
        """Flush the scoring queue via single batched LLM call (OpenRouter)."""
        async with self._queue_lock:
            batch = self._score_queue[:]
            self._score_queue = []
        if not batch:
            return
        try:
            numbered = "\n".join(
                f"{i+1}. [{mid}] {content[:200]}"
                for i, (mid, content, *_rest) in enumerate(batch)
            )
            resp = await asyncio.to_thread(
                self.chat.client.chat.completions.create,
                model=self.chat.model, temperature=0.1,
                max_tokens=200 + len(batch) * 120,
                messages=[
                    {"role": "system", "content": (
                        "For each numbered memory, score importance 0.0-1.0, extract entities, "
                        "and list topics. Respond ONLY with JSON array in same order: "
                        '[{"importance":0.7,"entities":[{"name":"X","type":"person"}],"topics":["ai"]}, ...]'
                    )},
                    {"role": "user", "content": numbered},
                ],
            )
            text = resp.choices[0].message.content.strip()
            text = text.removeprefix("```json").removesuffix("```").strip()
            results = json.loads(text)
            if not isinstance(results, list):
                results = [results.get(str(i+1), {"importance":0.5,"entities":[],"topics":[]}) for i in range(len(batch))]
            for i, result in enumerate(results[:len(batch)]):
                mid, content, source, domain, embedding, now = batch[i]
                importance = result.get("importance", 0.5)
                entities = result.get("entities", [])
                topics = result.get("topics", [])
                new_state = "accepted" if importance >= IMPORTANCE_THRESHOLD else "observation"
                trigger = "importance_gate_pass" if new_state == "accepted" else "importance_gate_low"
                w_before = 0.0
                w_after = compute_weight(0, 1.0, 0.0, now, now)
                witness = make_witness_entry("observation", new_state, trigger, w_before, w_after)
                await self.store.update_memory(
                    mid, state=new_state, importance_score=importance,
                    entities=json.dumps(entities), topics=json.dumps(topics),
                    witness_append=witness,
                )
                for ent in entities:
                    await self.store.upsert_entity(
                        ent.get("name", "unknown"), ent.get("type", "unknown"),
                        ent.get("attributes", {}), mid,
                    )
                # · Graph edges: link to existing memories sharing entities ·
                for ent in entities:
                    ent_name = ent.get("name", "").lower()
                    if not ent_name:
                        continue
                    # Find other memories mentioning this entity
                    related = await self.store.get_related_memories(mid, limit=20)
                    if related:
                        continue  # already has edges, skip bulk scan
                    rows = await self.store.pool.fetch("""
                        SELECT id FROM memories
                        WHERE id != $1
                          AND state != 'shed'
                          AND EXISTS (
                              SELECT 1 FROM jsonb_array_elements(entities) AS e
                              WHERE e->>'name' = $2
                          )
                        LIMIT 10
                    """, mid, ent.get("name"))
                    for row in rows:
                        tid = row["id"]
                        if tid != mid:
                            await self.store.create_memory_edge(
                                mid, tid, edge_type="shared_entity", weight=0.7,
                            )
            log.info(f"Batch scored {len(batch)} memories via batched LLM")
        except Exception as e:
            log.error(f"Batch scoring failed: {e}")

    async def _async_detect_contradictions(self, mid: str, content: str, embedding: list):
        """Background task: find similar semantic memories and flag contradictions."""
        try:
            candidates = await self.store.find_similar_semantic_memories(
                embedding, exclude_id=mid, threshold=0.82, limit=3
            )
            if not candidates:
                return
            for cand in candidates:
                cand_id = cand["id"]
                cand_content = cand["content"]
                try:
                    resp = await asyncio.to_thread(
                        self.chat.client.chat.completions.create,
                        model=self.chat.model, temperature=0.1, max_tokens=50,
                        messages=[
                            {"role": "system", "content": (
                                "You detect contradictions. Respond ONLY with JSON: "
                                '{"contradiction": true/false, "reason": "brief explanation"}'
                            )},
                            {"role": "user", "content": (
                                f"Memory A: {content}\nMemory B: {cand_content}\n"
                                "Do these directly contradict each other?"
                            )},
                        ],
                    )
                    text = resp.choices[0].message.content.strip()
                    text = text.removeprefix("```json").removesuffix("```").strip()
                    result = json.loads(text)
                    if result.get("contradiction"):
                        reason = result.get("reason", "")
                        await self.store.record_contradiction(mid, cand_id, reason)
                        log.info(f"Contradiction detected: {mid} vs {cand_id} — {reason}")
                except Exception:
                    pass
        except Exception as e:
            log.debug(f"Contradiction detection failed for {mid}: {e}")

    async def ingest(self, content: str, source: str = "conversation",
                     domain: str = "default", event_at: Optional[str] = None,
                     refs: Optional[dict] = None) -> dict:
        mid = f"mem_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)
        memory_type = self._auto_classify_memory_type(content)
        refs = refs or {}

        # FAST PATH: embed + store immediately with defaults (no blocking LLM call)
        importance = 0.5
        entities = []
        topics = []
        final_state = "observation"

        w_obs = 0.0
        witness_1 = make_witness_entry("none", "observation", "auto_ingest", 0.0, w_obs)
        w_after = compute_weight(0, 1.0, 0.0, now, now)
        witness_2 = make_witness_entry(
            "observation", final_state, "importance_gate_low", w_obs, w_after,
            prev_hash=witness_1["entry_hash"]
        )

        embedding = await asyncio.get_event_loop().run_in_executor(
            self.embedder._executor, self.embedder.embed, content
        )
        await self.store.insert_memory(
            mid, content, embedding, final_state, source, domain,
            importance, entities, topics, [witness_1, witness_2],
            memory_type=memory_type, event_at=event_at, refs=refs,
        )

        # BACKGROUND: add to batch scoring queue
        if ENABLE_BACKGROUND_SCORING:
            async with self._queue_lock:
                self._score_queue.append((mid, content, source, domain, embedding, now))
                if len(self._score_queue) >= self.BATCH_SIZE:
                    self._flush_event.set()

        # ADAPTIVE BACKPRESSURE: if too many background tasks, wait before spawning more
        if len(self._background_tasks) > 20:
            log.warning(f"Backpressure: {len(self._background_tasks)} background tasks, waiting...")
            while len(self._background_tasks) > 10:
                await asyncio.sleep(0.1)

        # BACKGROUND: contradiction detection for semantic memories
        if ENABLE_CONTRADICTION_DETECTION and memory_type == "semantic":
            task = asyncio.create_task(
                self._async_detect_contradictions(mid, content, embedding)
            )
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)

        # HIERARCHY: async entity extraction + graph building (non-blocking)
        if ENABLE_HIERARCHY_PROCESSING and hierarchy_manager:
            async def _hierarchy_background(mid, content, event_at):
                async with self._hierarchy_sem:
                    try:
                        reference_time = None
                        if event_at:
                            reference_time = datetime.fromisoformat(event_at.replace("Z", "+00:00"))
                        result = await hierarchy_manager.process_new_memory(mid, content, reference_time=reference_time)
                        log.info(f"Hierarchy processed {mid}: {result['entities_extracted']} entities, {result['temporal_expressions']} temporal")
                    except Exception as e:
                        log.warning(f"Hierarchy processing failed for {mid}: {e}")
            task = asyncio.create_task(_hierarchy_background(mid, content, event_at))
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)

        log.info(f"Ingested {mid} → {final_state} (type={memory_type}) [batch queued]")
        return {
            "id": mid, "state": final_state, "importance": importance,
            "entities": entities, "topics": topics, "witness_count": 2,
            "memory_type": memory_type,
            "event_at": event_at,
            "refs": refs,
        }


class ConsolidateAgent:
    """
    Background loop: δ-decay, shedding, auto-crystallization.
    Memory-type aware: episodic decays faster, semantic slower, procedural moderate.
    """

    def __init__(self, store: ColdStore, leann_tier: Optional[LEANNColdTier] = None,
                 resolver: Optional["ContradictionResolver"] = None):
        self.store = store
        self.leann = leann_tier
        self.resolver = resolver
        self._running = False

    def _decay_rate_for_type(self, memory_type: str) -> float:
        """Type-specific decay multipliers."""
        multipliers = {
            "episodic": 2.0,    # fast decay for transient events
            "semantic": 0.5,    # slow decay for facts
            "procedural": 1.0,  # normal decay for workflows
        }
        return DECAY_RATE * multipliers.get(memory_type, 1.0)

    async def run_cycle(self) -> dict:
        memories = await self.store.get_active_memories()
        now = datetime.now(timezone.utc)
        stats = {"decayed": 0, "shed": 0, "crystallized": 0, "total": len(memories)}

        for m in memories:
            mid = m["id"]
            mem_type = m.get("memory_type", "semantic")
            type_decay = self._decay_rate_for_type(mem_type)

            old_w = compute_weight(
                m["confirmation_count"], m["recency_score"],
                m["validation_score"], m["created_at"], now,
            )
            new_recency = m["recency_score"] * (1.0 - type_decay)
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
                log.info(f"Shed {mid}: W={old_w:.4f} -> {new_w:.4f} (type={mem_type})")
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

        # Auto-resolve contradictions
        if self.resolver:
            try:
                res_stats = await self.resolver.resolve_batch(limit=5)
                stats["contradictions_resolved"] = res_stats.get("resolved", 0)
            except Exception as e:
                log.warning(f"Contradiction resolution error: {e}")

        # HIERARCHY CONSOLIDATION: run mental model synthesis periodically
        if hierarchy_manager:
            try:
                cons_result = await hierarchy_manager.run_consolidation()
                if cons_result.get("consolidated", 0) > 0:
                    stats["mental_models_created"] = cons_result["consolidated"]
                    log.info(f"Hierarchy consolidation: created {cons_result['consolidated']} mental models")
            except Exception as e:
                log.warning(f"Hierarchy consolidation error: {e}")

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
                 leann_tier: Optional[LEANNColdTier] = None,
                 tier0: Optional["Tier0Cache"] = None):
        self.store = store
        self.embedder = embedder
        self.chat = chat
        self.leann = leann_tier
        self.tier0 = tier0 or Tier0Cache()

    async def recall(self, query: str, top_k: int = 5,
                     domain: Optional[str] = None, expand: bool = True,
                     graph_walk: bool = True) -> dict:
        # Tier 0: predictive prefetch cache (instant)
        cached_ids = self.tier0.get(query, domain)
        if cached_ids:
            results = []
            for mid in cached_ids[:top_k]:
                mem = await self.store.get_memory(mid)
                if mem and mem.get("state") != "shed":
                    results.append(mem)
            if results:
                return {"results": results, "tier": "tier0",
                        "query": query, "total_searched": len(results)}

        embedding = await asyncio.get_event_loop().run_in_executor(
            self.embedder._executor, self.embedder.embed, query
        )

        # Tier 1: Hot search
        hot_results = await self.store.search(
            embedding, top_k=top_k, state_filter=HOT_STATES, domain=domain,
        )
        good_hot = [r for r in hot_results if r.get("combined_score", 0) > 0.6]

        if len(good_hot) >= 2:
            # Cache direct search results for subsequent identical queries
            self.tier0.set(query, [r["id"] for r in hot_results[:top_k]], domain)
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
            related_terms = await asyncio.to_thread(self.chat.expand_query, query)
            for term in related_terms[:2]:
                try:
                    exp_emb = await asyncio.get_event_loop().run_in_executor(
                        self.embedder._executor, self.embedder.embed, term
                    )
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

        # ── Graph-walking recall: fetch neighbors of top results ──
        if graph_walk and merged:
            neighbor_ids = set()
            for r in merged[:top_k]:
                try:
                    neighbors = await self.store.get_related_memories(r["id"], limit=3)
                    for n in neighbors:
                        nid = n["id"]
                        if nid not in seen and nid not in neighbor_ids:
                            neighbor_ids.add(nid)
                            n["combined_score"] = r.get("combined_score", 0.5) * 0.85
                            n["graph_walk_source"] = r["id"]
                            merged.append(n)
                except Exception:
                    pass

        merged.sort(key=lambda x: x.get("combined_score", 0), reverse=True)
        tier_label = "hot+cold"
        if leann_results:
            tier_label += "+leann"
        if graph_walk:
            tier_label += "+graph"

        # Cache direct search results in Tier-0 so next identical query is instant
        self.tier0.set(query, [r["id"] for r in merged[:top_k]], domain)

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


class PrefetchAgent:
    """
    Predictive memory pre-fetching.
    Analyzes recent conversation context to predict likely next topics
    and pre-warms the working memory cache.
    """

    def __init__(self, store: ColdStore, embedder: EmbedClient, chat: ChatClient,
                 tier0: Optional["Tier0Cache"] = None):
        self.store = store
        self.embedder = embedder
        self.chat = chat
        self.tier0 = tier0 or Tier0Cache()
        self._working_set: list[dict] = []
        self._recent_topics: list[str] = []

    def _extract_topics_from_memories(self, memories: list[dict]) -> list[str]:
        """Extract recurring topics from recent memories (no LLM — fast)."""
        topic_counts = {}
        for m in memories:
            for t in m.get("topics", []):
                topic_counts[t] = topic_counts.get(t, 0) + 1
        # Return topics that appear more than once
        return [t for t, c in topic_counts.items() if c >= 1]

    async def predict_and_prefetch(self, recent_memories: list[dict],
                                    top_k: int = 5) -> dict:
        """
        Given recent memories, predict what topics will come up next
        and pre-fetch relevant memories.
        """
        if not recent_memories:
            return {"prefetched": [], "predicted_topics": []}

        # Extract topics from recent context
        topics = self._extract_topics_from_memories(recent_memories)
        self._recent_topics = topics[-5:]  # keep last 5

        # For each topic, find candidate memories that might be needed next
        prefetched = []
        seen_ids = set()
        for topic in topics[:3]:  # limit to top 3 topics
            try:
                emb = await asyncio.get_event_loop().run_in_executor(
                    self.embedder._executor, self.embedder.embed, topic
                )
                candidates = await self.store.get_prefetch_candidates(
                    topic, emb, top_k=top_k
                )
                for c in candidates:
                    if c["id"] not in seen_ids:
                        seen_ids.add(c["id"])
                        prefetched.append(c)
            except Exception as e:
                log.debug(f"Prefetch failed for topic '{topic}': {e}")

        self._working_set = prefetched[:top_k]
        # Warm Tier-0 cache with each predicted topic as a cache key
        pf_ids = [m["id"] for m in self._working_set]
        for topic in topics[:3]:
            self.tier0.set(topic, pf_ids)
        return {
            "predicted_topics": topics,
            "prefetched_count": len(self._working_set),
            "prefetched_ids": pf_ids,
        }

    def get_working_set(self) -> list[dict]:
        """Return the current pre-fetched working set."""
        return self._working_set


class Tier0Cache:
    """
    In-memory Tier-0 cache for predictive prefetch hits.
    Maps query fingerprints → pre-fetched memory IDs with TTL.
    """
    def __init__(self, ttl_seconds: float = 300.0):
        self._cache: dict[str, tuple[list[str], float]] = {}
        self._ttl = ttl_seconds

    def _key(self, query: str, domain: Optional[str] = None) -> str:
        h = hashlib.sha256(f"{domain or ''}:{query.lower().strip()}".encode()).hexdigest()[:16]
        return h

    def get(self, query: str, domain: Optional[str] = None) -> Optional[list[str]]:
        key = self._key(query, domain)
        if key in self._cache:
            ids, expiry = self._cache[key]
            if datetime.now(timezone.utc).timestamp() < expiry:
                return ids
            del self._cache[key]
        return None

    def set(self, query: str, memory_ids: list[str], domain: Optional[str] = None) -> None:
        key = self._key(query, domain)
        expiry = datetime.now(timezone.utc).timestamp() + self._ttl
        self._cache[key] = (memory_ids, expiry)

    def invalidate(self, query: str, domain: Optional[str] = None) -> None:
        key = self._key(query, domain)
        self._cache.pop(key, None)

    def stats(self) -> dict:
        now = datetime.now(timezone.utc).timestamp()
        active = sum(1 for _, expiry in self._cache.values() if expiry > now)
        return {"entries": len(self._cache), "active": active, "ttl_seconds": self._ttl}


class ContradictionResolver:
    """
    Background agent that uses the LLM to reconcile unresolved contradictions.
    """
    def __init__(self, store: ColdStore, chat: ChatClient, embedder: EmbedClient):
        self.store = store
        self.chat = chat
        self.embedder = embedder

    async def resolve_batch(self, limit: int = 5) -> dict:
        contradictions = await self.store.get_unresolved_contradictions(limit)
        if not contradictions:
            return {"resolved": 0, "attempted": 0}
        resolved_count = 0
        for c in contradictions:
            try:
                await self._resolve_one(c)
                resolved_count += 1
            except Exception as e:
                log.warning(f"Contradiction resolution failed for {c['contradiction_id']}: {e}")
        return {"resolved": resolved_count, "attempted": len(contradictions)}

    async def _resolve_one(self, c: dict) -> None:
        """Ask the LLM to reconcile two conflicting memories."""
        prompt = f"""Memory A: {c['content_a']}
Memory B: {c['content_b']}

These memories contradict each other. Produce a single reconciled statement that preserves the truth from both (or chooses the more specific/authoritative one). Respond ONLY with the reconciled text."""
        resp = await asyncio.to_thread(
            self.chat.client.chat.completions.create,
            model=self.chat.model, temperature=0.2, max_tokens=300,
            messages=[
                {"role": "system", "content": "You are a contradiction resolution agent. Be concise."},
                {"role": "user", "content": prompt},
            ],
        )
        reconciled = resp.choices[0].message.content.strip()
        # Create a new reconciled memory
        rec_id = f"rec_{uuid.uuid4().hex[:12]}"
        emb = await asyncio.get_event_loop().run_in_executor(
            self.embedder._executor, self.embedder.embed, reconciled
        )
        now = datetime.now(timezone.utc)
        witness = make_witness_entry("observation", "accepted", "auto_reconciled", 0.0, 1.0)
        await self.store.insert_memory(
            rec_id, reconciled, emb, "accepted", "contradiction_resolver", "default",
            importance=0.9, entities=[], topics=["reconciled"],
            witness_chain=[witness], memory_type="semantic",
        )
        # Mark original contradiction as resolved
        await self.store.resolve_contradiction(c["contradiction_id"], reconciled)
        # Link the new memory to both originals via edges
        await self.store.create_memory_edge(c["memory_a_id"], rec_id, "reconciled", 1.0)
        await self.store.create_memory_edge(c["memory_b_id"], rec_id, "reconciled", 1.0)
        log.info(f"Resolved contradiction {c['contradiction_id']} → {rec_id}")


# ══════════════════════════════════════════════════════════════════
# §5  MCP HTTP SERVER
# ══════════════════════════════════════════════════════════════════

store = ColdStore()
leann_tier = LEANNColdTier()
embedder = EmbedClient()
chat = ChatClient()
tier0_cache = Tier0Cache(ttl_seconds=300.0)
ingest_agent = IngestAgent(store, embedder, chat)
resolver = ContradictionResolver(store, chat, embedder)
consolidate_agent = ConsolidateAgent(store, leann_tier, resolver=resolver)
query_agent = QueryAgent(store, embedder, chat, leann_tier, tier0=tier0_cache)
prefetch_agent = PrefetchAgent(store, embedder, chat, tier0=tier0_cache)
classifier = KnowledgeClassifier()
doc_engine = DocumentIngestEngine(ingest_agent, store, classifier)
wiki_compiler = WikiCompiler(store, chat)

# Hybrid retrieval + memory hierarchy (initialized after store.connect)
hybrid_retriever: Optional[HybridRetriever] = None
hierarchy_manager: Optional[MemoryHierarchyManager] = None

async def _init_advanced_modules():
    global hybrid_retriever, hierarchy_manager
    hybrid_retriever = HybridRetriever(store.pool, store.vtype, embedder)
    await hybrid_retriever.initialize()
    hierarchy_manager = MemoryHierarchyManager(store.pool, chat, embedder)
    await hierarchy_manager.initialize()
    log.info("Advanced modules initialized: hybrid retrieval + memory hierarchy")


async def handle_retain(request: Request) -> JSONResponse:
    body = await request.json()
    content = body.get("content", "")
    if not content:
        return JSONResponse({"error": "content required"}, status_code=400)
    result = await ingest_agent.ingest(
        content, source=body.get("source", "conversation"),
        domain=body.get("domain", "default"),
        event_at=body.get("event_at"),
        refs=body.get("refs"),
    )
    return JSONResponse(result)


async def handle_recall(request: Request) -> JSONResponse:
    body = await request.json()
    query = body.get("query", "")
    if not query:
        return JSONResponse({"error": "query required"}, status_code=400)

    # Use hybrid retriever if available, else fallback to old query_agent
    if hybrid_retriever:
        embedding = None
        try:
            embedding = await asyncio.get_event_loop().run_in_executor(embedder._executor, embedder.embed, query)
        except Exception as e:
            log.warning(f"Embedding failed for recall, falling back to keyword-only: {e}")
        try:
            result = await hybrid_retriever.search(
                query=query,
                embedding=embedding,
                top_k=body.get("top_k", 5),
                state_filter=body.get("state_filter"),
                domain=body.get("domain"),
            )
        except Exception as e:
            log.error(f"Hybrid retrieval failed: {e}, falling back to legacy recall")
            result = await query_agent.recall(
                query, top_k=body.get("top_k", 5),
                domain=body.get("domain"), expand=body.get("expand", True),
            )
    else:
        result = await query_agent.recall(
            query, top_k=body.get("top_k", 5),
            domain=body.get("domain"), expand=body.get("expand", True),
        )
    return JSONResponse(_serialize_result(result))


async def handle_reflect(request: Request) -> JSONResponse:
    body = await request.json()
    topic = body.get("topic", "")
    if not topic:
        return JSONResponse({"error": "topic required"}, status_code=400)

    # Use hybrid retriever for better recall, then hierarchy-aware synthesis
    if hybrid_retriever and hierarchy_manager:
        embedding = None
        try:
            embedding = await asyncio.get_event_loop().run_in_executor(embedder._executor, embedder.embed, topic)
        except Exception:
            pass
        recall_result = await hybrid_retriever.search(
            query=topic,
            embedding=embedding,
            top_k=body.get("top_k", 10),
            domain=body.get("domain"),
        )
        memories = recall_result
        if not memories:
            return JSONResponse({"synthesis": "No memories found for this topic.", "memories": []})

        # Apply hierarchy priority to synthesis context
        hierarchy_result = await asyncio.to_thread(
            hierarchy_manager.synthesize_with_priority, memories, topic
        )
        synthesis = chat.synthesize(hierarchy_result["sorted_memories"], topic)
        return JSONResponse(_serialize_result({
            "synthesis": synthesis,
            "memory_count": len(memories),
            "tier": "hybrid",
            "crystallized_count": sum(1 for m in memories if m.get("state") == "crystallized"),
            "hierarchy_context": hierarchy_result.get("context", ""),
        }))
    else:
        result = await query_agent.reflect(
            topic, top_k=body.get("top_k", 10), domain=body.get("domain"),
        )
        return JSONResponse(_serialize_result(result))


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
    # Record feedback for personalized ranking
    await store.add_feedback(mid, "confirm", weight)

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
    # Record strong positive feedback for freeze
    await store.add_feedback(mid, "freeze", weight=2.0)
    return JSONResponse(result)


async def handle_revert(request: Request) -> JSONResponse:
    body = await request.json()
    mid = body.get("memory_id", "")
    if not mid:
        return JSONResponse({"error": "memory_id required"}, status_code=400)
    result = await store.revert(mid, body.get("snapshot_id"))
    # Record negative feedback for revert
    await store.add_feedback(mid, "revert", weight=1.0)
    return JSONResponse(result)


async def handle_consolidate(request: Request) -> JSONResponse:
    result = await consolidate_agent.run_cycle()
    return JSONResponse(result)


async def handle_prefetch(request: Request) -> JSONResponse:
    """Predictive memory pre-fetching based on recent context."""
    body = await request.json()
    # Retrieve recent memories as context
    recent_query = body.get("context_query", "")
    top_k = body.get("top_k", 5)
    recent_memories = []
    if recent_query:
        emb = await asyncio.get_event_loop().run_in_executor(
            embedder._executor, embedder.embed, recent_query
        )
        recent_memories = await store.search(emb, top_k=top_k, state_filter=HOT_STATES)
    result = await prefetch_agent.predict_and_prefetch(recent_memories, top_k=top_k)
    # Also cache under the original context query for instant recall hits
    if recent_query and result.get("prefetched_ids"):
        prefetch_agent.tier0.set(recent_query, result["prefetched_ids"])
    return JSONResponse(result)


async def handle_dashboard(request: Request) -> JSONResponse:
    counts = await store.count_by_state()
    total = sum(counts.values())
    # Count contradictions
    async with store.pool.acquire() as conn:
        cnt_row = await conn.fetchrow("SELECT COUNT(*) as c FROM contradictions WHERE resolved = FALSE")
        unresolved_contradictions = cnt_row["c"] if cnt_row else 0
        edge_row = await conn.fetchrow("SELECT COUNT(*) as c FROM memory_edges")
        edge_count = edge_row["c"] if edge_row else 0
        type_rows = await conn.fetch("SELECT memory_type, COUNT(*) as c FROM memories GROUP BY memory_type")
        type_counts = {r["memory_type"]: r["c"] for r in type_rows}
    return JSONResponse({
        "lifecycle_counts": counts,
        "type_counts": type_counts,
        "total_memories": total,
        "unresolved_contradictions": unresolved_contradictions,
        "memory_edges": edge_count,
        "tier0_cache": tier0_cache.stats() if 'tier0_cache' in globals() else None,
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
            "provider": "ollama (local)" if "ollama" in OLLAMA_CHAT_BASE else ("azure" if USE_AZURE else "openai-compatible"),
            "sovereignty": "full — no cloud memory dependencies",
            "features": ["async_scoring", "memory_type_separation", "contradiction_detection",
                        "predictive_prefetch", "personalized_ranking", "graph_edges",
                        "tier0_cache", "auto_resolution", "graph_walk_recall", "tier0_fallback_cache",
                        "hybrid_retrieval", "bm25_search", "temporal_search", "rrf_fusion",
                        "memory_hierarchy", "entity_extraction", "auto_consolidation"],
        },
    })


async def handle_graph(request: Request) -> JSONResponse:
    """Return memory graph topology: nodes, edges, and analytics."""
    async with store.pool.acquire() as conn:
        edge_rows = await conn.fetch("""
            SELECT e.source_id, e.target_id, e.edge_type, e.weight,
                   s.content as source_content, t.content as target_content,
                   s.state as source_state, t.state as target_state
            FROM memory_edges e
            JOIN memories s ON s.id = e.source_id
            JOIN memories t ON t.id = e.target_id
        """)
        node_rows = await conn.fetch("""
            SELECT DISTINCT m.id, m.content, m.state, m.memory_type
            FROM memories m
            WHERE m.id IN (SELECT source_id FROM memory_edges
                           UNION SELECT target_id FROM memory_edges)
        """)
        degree_rows = await conn.fetch("""
            SELECT node_id, COUNT(*) as degree FROM (
                SELECT source_id as node_id FROM memory_edges
                UNION ALL
                SELECT target_id as node_id FROM memory_edges
            ) sub GROUP BY node_id ORDER BY degree DESC LIMIT 10
        """)
        type_dist = await conn.fetch("""
            SELECT edge_type, COUNT(*) as c FROM memory_edges GROUP BY edge_type
        """)
    nodes = []
    node_ids = set()
    for r in node_rows:
        nodes.append({
            "id": r["id"],
            "label": r["content"][:80] + "..." if len(r["content"]) > 80 else r["content"],
            "state": r["state"],
            "type": r["memory_type"],
        })
        node_ids.add(r["id"])
    edges = []
    for r in edge_rows:
        edges.append({
            "source": r["source_id"],
            "target": r["target_id"],
            "type": r["edge_type"],
            "weight": float(r["weight"]),
            "source_state": r["source_state"],
            "target_state": r["target_state"],
        })
    analytics = {
        "node_count": len(nodes),
        "edge_count": len(edges),
        "top_degree_nodes": [{"id": r["node_id"], "degree": r["degree"]} for r in degree_rows],
        "edge_type_distribution": {r["edge_type"]: r["c"] for r in type_dist},
        "avg_degree": round(2 * len(edges) / max(len(nodes), 1), 2),
        "density": round(len(edges) / max(len(nodes) * (len(nodes) - 1) / 2, 1), 4),
    }
    return JSONResponse({"nodes": nodes, "edges": edges, "analytics": analytics})


async def handle_health(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", "engine": "memibrium"})


async def handle_test_embeddings(request: Request) -> JSONResponse:
    """Test both ollama and Azure embedding endpoints and compare."""
    body = await request.json() if await request.body() else {}
    test_text = body.get("text", "The quick brown fox jumps over the lazy dog")

    import time

    # Test current (ollama) endpoint
    ollama_result = {}
    try:
        t0 = time.perf_counter()
        ollama_emb = embedder.embed(test_text)
        ollama_result = {
            "success": True,
            "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
            "dimensions": len(ollama_emb),
            "endpoint": EMBED_BASE,
            "model": EMBED_MODEL,
            "sample_prefix": ollama_emb[:3],
        }
    except Exception as e:
        ollama_result = {"success": False, "error": str(e), "endpoint": EMBED_BASE}

    # Test Azure endpoint (if configured)
    azure_result = embedder.test_azure_endpoint(test_text)

    return JSONResponse({
        "ollama": ollama_result,
        "azure": azure_result,
        "recommendation": (
            "switch_to_azure" if azure_result.get("success") and azure_result.get("latency_ms", 9999) < ollama_result.get("latency_ms", 9999)
            else "keep_ollama"
        ),
    })


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
                "domain": {"type": "string", "default": "default"},
                "event_at": {"type": "string", "description": "Optional ISO-8601 event timestamp to preserve original chronology"},
                "refs": {"type": "object", "description": "Optional chronology metadata like session_index, chunk_index, turn_start, turn_end"}}, "required": ["content"]}},
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
            {"name": "prefetch", "description": "Predictive memory pre-fetching based on recent conversation context.",
             "inputSchema": {"type": "object", "properties": {
                 "context_query": {"type": "string", "description": "Recent conversation context to base predictions on"},
                 "top_k": {"type": "integer", "default": 5}}, "required": []}},
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
        Route("/mcp/test_embeddings", handle_test_embeddings, methods=["POST"]),
        Route("/mcp/tools", handle_mcp_manifest, methods=["GET"]),
        Route("/mcp/retain", handle_retain, methods=["POST"]),
        Route("/mcp/recall", handle_recall, methods=["POST"]),
        Route("/mcp/reflect", handle_reflect, methods=["POST"]),
        Route("/mcp/confirm", handle_confirm, methods=["POST"]),
        Route("/mcp/freeze", handle_freeze, methods=["POST"]),
        Route("/mcp/revert", handle_revert, methods=["POST"]),
        Route("/mcp/consolidate", handle_consolidate, methods=["POST"]),
        Route("/mcp/dashboard", handle_dashboard, methods=["GET"]),
        Route("/mcp/graph", handle_graph, methods=["GET"]),
        Route("/mcp/prefetch", handle_prefetch, methods=["POST"]),
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
    await _init_advanced_modules()
    ingest_agent.start()
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
