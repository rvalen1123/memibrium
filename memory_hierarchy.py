#!/usr/bin/env python3
"""
memory_hierarchy.py — Memory Hierarchy + Entity Extraction + Auto-Consolidation
================================================================================

Manages:
  1. Entity extraction from memory content (LLM-assisted + regex fallback)
  2. Entity relationship graph (co-occurrence, temporal, semantic)
  3. Memory hierarchy levels (episodic → semantic → procedural promotion)
  4. Auto-consolidation: deduplicate entities, merge similar memories, promote
     frequently-accessed memories up the hierarchy.

PostgreSQL tables used:
    entities, entity_relationships, memory_edges, temporal_expressions
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional

import asyncpg


# ── Hierarchy Levels ──────────────────────────────────────────────

class HierarchyLevel(str, Enum):
    EPISODIC = "episodic"       # time-bound, specific events
    SEMANTIC = "semantic"       # facts, concepts
    PROCEDURAL = "procedural"   # how-to, workflows
    CRYSTALLIZED = "crystallized"  # confirmed + consensus


# ── Entity Extraction ─────────────────────────────────────────────

ENTITY_TYPES = {
    "person": r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\b",  # naive: two capitalized words
    "organization": r"\b[A-Z][a-z]*(?:\s+[A-Z][a-z]*)+\s+(?:Inc|LLC|Corp|Ltd|GmbH|Company)\b",
    "location": r"\b(?:New York|San Francisco|London|Paris|Tokyo|Berlin|Seattle|Austin|Boston)\b",
    "product": r"\b(?:Docker|Kubernetes|PostgreSQL|Python|JavaScript|React|TensorFlow|Ollama)\b",
    "technology": r"\b(?:AI|ML|LLM|API|GPU|CPU|RAM|SSD|HTTP|REST|gRPC|WebSocket)\b",
}


def _regex_extract_entities(content: str) -> list[dict]:
    """Fast regex-based entity extraction (fallback, no LLM)."""
    found = []
    seen = set()
    for etype, pattern in ENTITY_TYPES.items():
        for m in re.finditer(pattern, content, re.IGNORECASE):
            name = m.group(0)
            key = f"{name.lower()}:{etype}"
            if key in seen:
                continue
            seen.add(key)
            found.append({
                "name": name,
                "type": etype,
                "attributes": {},
            })
    return found


async def _llm_extract_entities(content: str, chat_client) -> list[dict]:
    """LLM-based entity extraction. Returns list of {name, type, attributes}."""
    if chat_client is None:
        return []
    try:
        resp = await asyncio.to_thread(
            chat_client.client.chat.completions.create,
            model=getattr(chat_client, "model", "gemma3:4b"),
            temperature=0.1, max_tokens=300,
            messages=[
                {"role": "system", "content": (
                    "Extract named entities from the text. "
                    "Return ONLY JSON array: [{\"name\":\"X\",\"type\":\"person\",\"attributes\":{}}]"
                )},
                {"role": "user", "content": content[:800]},
            ],
        )
        text = resp.choices[0].message.content.strip()
        text = text.removeprefix("```json").removesuffix("```").strip()
        entities = json.loads(text)
        if isinstance(entities, list):
            return entities
        if isinstance(entities, dict) and "entities" in entities:
            return entities["entities"]
    except Exception:
        pass
    return []


async def extract_entities(content: str, chat_client=None) -> list[dict]:
    """Hybrid extraction: LLM first, regex fallback."""
    llm_ents = await _llm_extract_entities(content, chat_client)
    if llm_ents:
        return llm_ents
    return _regex_extract_entities(content)


# ── Temporal Expression Parsing ───────────────────────────────────

TEMPORAL_PATTERNS = [
    (r"\b(\d{4}-\d{2}-\d{2})\b", "absolute_date"),
    (r"\b(\d{2}/\d{2}/\d{4})\b", "absolute_date"),
    (r"\b(?:\d{1,2}:\d{2}\s*(?:am|pm)\s+on\s+\d{1,2}\s+[A-Za-z]+,\s+\d{4})\b", "absolute_datetime"),
    (r"\b(last\s+week|this\s+week|next\s+week)\b", "relative_week"),
    (r"\b(yesterday|today|tomorrow)\b", "relative_day"),
    (r"\b(\d+)\s+(days?|weeks?|months?)\s+ago\b", "relative_ago"),
    (r"\b(in\s+\d+\s+(days?|weeks?|months?))\b", "relative_future"),
]


MONTH_NAMES = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
}


def _parse_absolute_temporal_expression(expr: str) -> tuple[Optional[datetime], Optional[datetime]]:
    expr = expr.strip()

    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", expr)
    if m:
        year, month, day = map(int, m.groups())
        start = datetime(year, month, day, tzinfo=timezone.utc)
        return start, start + timedelta(days=1)

    m = re.fullmatch(r"(\d{2})/(\d{2})/(\d{4})", expr)
    if m:
        month, day, year = map(int, m.groups())
        start = datetime(year, month, day, tzinfo=timezone.utc)
        return start, start + timedelta(days=1)

    m = re.fullmatch(r"(\d{1,2}):(\d{2})\s*(am|pm)\s+on\s+(\d{1,2})\s+([A-Za-z]+),\s+(\d{4})", expr, re.IGNORECASE)
    if m:
        hour = int(m.group(1))
        minute = int(m.group(2))
        meridiem = m.group(3).lower()
        day = int(m.group(4))
        month = MONTH_NAMES.get(m.group(5).lower())
        year = int(m.group(6))
        if month:
            if meridiem == "pm" and hour != 12:
                hour += 12
            elif meridiem == "am" and hour == 12:
                hour = 0
            start = datetime(year, month, day, hour, minute, tzinfo=timezone.utc)
            return start, start + timedelta(minutes=1)

    return None, None


def _resolve_temporal_bounds(expr: str, kind: str, reference_time: Optional[datetime] = None) -> tuple[Optional[datetime], Optional[datetime]]:
    if kind in {"absolute_date", "absolute_datetime"}:
        return _parse_absolute_temporal_expression(expr)

    now = reference_time or datetime.now(timezone.utc)
    lowered = expr.lower().strip()

    if kind == "relative_day":
        if lowered == "yesterday":
            start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc) - timedelta(days=1)
            return start, start + timedelta(days=1)
        if lowered == "today":
            start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
            return start, start + timedelta(days=1)
        if lowered == "tomorrow":
            start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc) + timedelta(days=1)
            return start, start + timedelta(days=1)

    if kind == "relative_week":
        if lowered == "last week":
            end = now
            return now - timedelta(days=7), end
        if lowered == "this week":
            return now - timedelta(days=7), now
        if lowered == "next week":
            start = now
            return start, start + timedelta(days=7)

    if kind == "relative_ago":
        m = re.fullmatch(r"(\d+)\s+(days?|weeks?|months?)\s+ago", lowered)
        if m:
            amount = int(m.group(1))
            unit = m.group(2)
            delta = timedelta(days=amount)
            if unit.startswith("week"):
                delta = timedelta(days=amount * 7)
            elif unit.startswith("month"):
                delta = timedelta(days=amount * 30)
            return now - delta, now

    if kind == "relative_future":
        m = re.fullmatch(r"in\s+(\d+)\s+(days?|weeks?|months?)", lowered)
        if m:
            amount = int(m.group(1))
            unit = m.group(2)
            delta = timedelta(days=amount)
            if unit.startswith("week"):
                delta = timedelta(days=amount * 7)
            elif unit.startswith("month"):
                delta = timedelta(days=amount * 30)
            return now, now + delta

    return None, None


def parse_temporal_expressions(content: str, reference_time: Optional[datetime] = None) -> list[dict]:
    """Extract temporal expressions from memory content."""
    found = []
    seen = set()
    for pat, kind in TEMPORAL_PATTERNS:
        for m in re.finditer(pat, content, re.IGNORECASE):
            expr = m.group(0)
            if expr.lower() in seen:
                continue
            seen.add(expr.lower())
            start_time, end_time = _resolve_temporal_bounds(expr, kind, reference_time)
            found.append({
                "expression": expr,
                "kind": kind,
                "start_time": start_time,
                "end_time": end_time,
            })
    return found


# ── MemoryHierarchyManager ────────────────────────────────────────

class MemoryHierarchyManager:
    """
    Orchestrates entity extraction, relationship building, hierarchy promotion,
    and auto-consolidation for the memory graph.
    """

    def __init__(self, pool: asyncpg.Pool, chat_client=None, embedder=None):
        self.pool = pool
        self.chat = chat_client
        self.embedder = embedder

    async def initialize(self):
        """No-op init for compatibility with server.py startup sequence."""
        pass

    # ── Entity CRUD ───────────────────────────────────────────────

    async def upsert_entity(self, name: str, entity_type: str = "unknown",
                            attributes: dict = None, memory_id: str = None) -> str:
        """Upsert entity and link to memory. Returns entity_id."""
        eid = f"ent_{hashlib.md5(f'{name.lower()}:{entity_type}'.encode()).hexdigest()[:12]}"
        attrs = json.dumps(attributes or {})
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO entities (entity_id, name, entity_type, attributes, memory_ids)
                VALUES ($1, $2, $3, $4::jsonb, $5::jsonb)
                ON CONFLICT (entity_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    entity_type = EXCLUDED.entity_type,
                    attributes = EXCLUDED.attributes,
                    memory_ids = entities.memory_ids || EXCLUDED.memory_ids,
                    updated_at = NOW()
            """, eid, name, entity_type, attrs, json.dumps([memory_id] if memory_id else []))
        return eid

    async def create_relationship(self, entity_a: str, entity_b: str,
                                   rel_type: str = "cooccurs", weight: float = 1.0,
                                   evidence: list = None) -> None:
        """Create or strengthen relationship between two entities."""
        if entity_a == entity_b:
            return
        rid = f"rel_{uuid.uuid4().hex[:12]}"
        ev = json.dumps(evidence or [])
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO entity_relationships (rel_id, entity_a, entity_b, rel_type, weight, evidence)
                VALUES ($1, $2, $3, $4, $5, $6::jsonb)
                ON CONFLICT (rel_id) DO UPDATE SET
                    weight = entity_relationships.weight + 1.0,
                    updated_at = NOW()
            """, rid, entity_a, entity_b, rel_type, weight, ev)

    # ── Memory Processing ───────────────────────────────────────────

    async def process_new_memory(self, memory_id: str, content: str,
                                 reference_time: Optional[datetime] = None) -> dict:
        """
        Full pipeline for a new memory:
        1. Extract entities
        2. Store temporal expressions
        3. Build entity co-occurrence relationships
        4. Create memory edges to related memories
        """
        entities = await extract_entities(content, self.chat)
        temporal = parse_temporal_expressions(content, reference_time=reference_time)

        entity_ids = []
        for ent in entities:
            eid = await self.upsert_entity(
                ent.get("name", "unknown"),
                ent.get("type", "unknown"),
                ent.get("attributes", {}),
                memory_id,
            )
            entity_ids.append(eid)

        # Entity co-occurrence relationships
        for i, a in enumerate(entity_ids):
            for b in entity_ids[i+1:]:
                await self.create_relationship(a, b, "cooccurs", 1.0,
                                               evidence=[memory_id])

        # Store temporal expressions
        for te in temporal:
            tid = f"te_{uuid.uuid4().hex[:12]}"
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO temporal_expressions (expr_id, memory_id, expression, kind, start_time, end_time)
                    VALUES ($1, $2, $3, $4, $5, $6)
                """, tid, memory_id, te["expression"], te["kind"], te.get("start_time"), te.get("end_time"))

        # Memory edges: link to existing memories sharing entities
        if entity_ids:
            async with self.pool.acquire() as conn:
                # Find memories that share any entity with this one
                related_rows = await conn.fetch("""
                    SELECT DISTINCT m.id
                    FROM memories m
                    WHERE m.id != $1
                      AND m.state != 'shed'
                      AND EXISTS (
                          SELECT 1 FROM jsonb_array_elements(m.entities) AS e
                          WHERE e->>'name' = ANY($2)
                      )
                    LIMIT 10
                """, memory_id, [e.split('_', 1)[1] if '_' in e else e for e in entity_ids])
                for row in related_rows:
                    await self.create_memory_edge(memory_id, row["id"], "shared_entity", 0.7)

        return {
            "memory_id": memory_id,
            "entities_extracted": len(entities),
            "entity_ids": entity_ids,
            "temporal_expressions": len(temporal),
            "relationships_created": len(entity_ids) * (len(entity_ids) - 1) // 2 if len(entity_ids) > 1 else 0,
        }

    async def create_memory_edge(self, source_id: str, target_id: str,
                                  edge_type: str = "related", weight: float = 1.0) -> None:
        """Create a graph edge between two memories."""
        if source_id == target_id:
            return
        eid = f"edge_{uuid.uuid4().hex[:12]}"
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO memory_edges (edge_id, source_id, target_id, edge_type, weight)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT DO NOTHING
            """, eid, source_id, target_id, edge_type, weight)

    # ── Auto-Consolidation ──────────────────────────────────────────

    async def consolidate_entities(self, similarity_threshold: float = 0.92) -> dict:
        """
        Deduplicate entities with similar names (exact or near-exact match).
        Merge their relationships and memory links.
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT entity_id, name, entity_type, memory_ids
                FROM entities
                ORDER BY name
            """)
        # Group by lowercase name + type
        groups: dict[str, list] = {}
        for r in rows:
            key = f"{r['name'].lower()}:{r['entity_type']}"
            groups.setdefault(key, []).append(r)

        merged = 0
        for key, ents in groups.items():
            if len(ents) < 2:
                continue
            # Pick canonical (most memory references)
            canonical = max(ents, key=lambda e: len(json.loads(e["memory_ids"])))
            canon_id = canonical["entity_id"]
            for dup in ents:
                if dup["entity_id"] == canon_id:
                    continue
                # Merge: update relationships to point to canonical
                async with self.pool.acquire() as conn:
                    await conn.execute("""
                        UPDATE entity_relationships
                        SET entity_a = $1
                        WHERE entity_a = $2 AND entity_a != $1
                    """, canon_id, dup["entity_id"])
                    await conn.execute("""
                        UPDATE entity_relationships
                        SET entity_b = $1
                        WHERE entity_b = $2 AND entity_b != $1
                    """, canon_id, dup["entity_id"])
                    # Merge memory_ids
                    await conn.execute("""
                        UPDATE entities
                        SET memory_ids = (
                            SELECT jsonb_agg(DISTINCT elem)
                            FROM jsonb_array_elements(memory_ids || $1) AS elem
                        ),
                        updated_at = NOW()
                        WHERE entity_id = $2
                    """, dup["memory_ids"], canon_id)
                    # Delete duplicate
                    await conn.execute("""
                        DELETE FROM entities WHERE entity_id = $1
                    """, dup["entity_id"])
                merged += 1

        return {"entities_merged": merged, "groups_examined": len(groups)}

    async def promote_memories(self, access_threshold: int = 3,
                                min_confirmations: int = 2) -> dict:
        """
        Promote heavily-accessed, confirmed memories up the hierarchy:
        episodic → semantic → procedural → crystallized.
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT m.id, m.memory_type, m.confirmation_count,
                       m.state, m.content,
                       COUNT(f.feedback_id) as access_count
                FROM memories m
                LEFT JOIN user_feedback f ON f.memory_id = m.id
                WHERE m.state IN ('observation', 'consideration', 'accepted')
                GROUP BY m.id
                HAVING COUNT(f.feedback_id) >= $1
                   AND m.confirmation_count >= $2
            """, access_threshold, min_confirmations)

        promoted = 0
        for r in rows:
            mid = r["id"]
            current_type = r["memory_type"]
            current_state = r["state"]

            # Promotion ladder
            new_type = current_type
            new_state = current_state
            if current_type == "episodic" and current_state == "accepted":
                new_type = "semantic"
                new_state = "accepted"
            elif current_type == "semantic" and current_state == "accepted" and r["confirmation_count"] >= 4:
                new_type = "procedural"
                new_state = "crystallized"

            if new_type != current_type or new_state != current_state:
                async with self.pool.acquire() as conn:
                    await conn.execute("""
                        UPDATE memories
                        SET memory_type = $1, state = $2, updated_at = NOW()
                        WHERE id = $3
                    """, new_type, new_state, mid)
                promoted += 1

        return {"promoted": promoted, "candidates": len(rows)}

    async def run_consolidation(self) -> dict:
        """Run full consolidation cycle: dedupe entities + promote memories."""
        entity_stats = await self.consolidate_entities()
        promotion_stats = await self.promote_memories()
        return {
            "entities": entity_stats,
            "promotions": promotion_stats,
            "total_changes": entity_stats.get("entities_merged", 0) + promotion_stats.get("promoted", 0),
        }

    # ── Hierarchy-Aware Synthesis ───────────────────────────────────

    def synthesize_with_priority(self, memories: list[dict], topic: str) -> dict:
        """
        Sort memories by hierarchy priority for synthesis context.

        Priority order (highest first):
            crystallized > procedural > semantic > episodic > observation/consideration

        Also boosts memories that share entities with keywords in the topic.
        Returns {"sorted_memories": [...], "context": "..."}.
        """
        # Priority score mapping
        priority_map = {
            "crystallized": 4,
            "procedural": 3,
            "semantic": 2,
            "episodic": 1,
            "observation": 0,
            "consideration": 0,
            "accepted": 1,
        }

        # Extract topic keywords for entity matching
        topic_words = set(re.findall(r"[a-zA-Z]+", topic.lower()))

        scored = []
        for mem in memories:
            # Base priority from memory_type + state
            mem_type = mem.get("memory_type", "semantic")
            state = mem.get("state", "observation")
            base_score = priority_map.get(mem_type, 1) + priority_map.get(state, 0)

            # Boost for recency (exponential decay over 30 days)
            created_at = mem.get("created_at")
            if created_at and hasattr(created_at, "isoformat"):
                # Already serialized — skip recency calc
                recency_boost = 0
            elif isinstance(created_at, str):
                try:
                    dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    days_old = (datetime.now(timezone.utc) - dt).total_seconds() / 86400
                    recency_boost = max(0, 1.0 - (days_old / 30.0))
                except Exception:
                    recency_boost = 0
            else:
                recency_boost = 0

            # Boost for entity/topic overlap
            entity_boost = 0
            entities = mem.get("entities", [])
            if isinstance(entities, str):
                try:
                    entities = json.loads(entities)
                except Exception:
                    entities = []
            if entities:
                entity_names = {e.get("name", "").lower() for e in entities if isinstance(e, dict)}
                overlap = len(topic_words & entity_names)
                entity_boost = overlap * 0.5

            # Combined score
            total_score = base_score + recency_boost + entity_boost
            scored.append((total_score, mem))

        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)
        sorted_memories = [m for _, m in scored]

        # Build context string
        type_counts: dict[str, int] = {}
        for m in sorted_memories:
            mt = m.get("memory_type", "unknown")
            type_counts[mt] = type_counts.get(mt, 0) + 1

        context_parts = []
        if type_counts.get("crystallized", 0) > 0:
            context_parts.append(f"{type_counts['crystallized']} crystallized")
        if type_counts.get("procedural", 0) > 0:
            context_parts.append(f"{type_counts['procedural']} procedural")
        if type_counts.get("semantic", 0) > 0:
            context_parts.append(f"{type_counts['semantic']} semantic")
        if type_counts.get("episodic", 0) > 0:
            context_parts.append(f"{type_counts['episodic']} episodic")

        context = f"Hierarchy mix: {', '.join(context_parts)}" if context_parts else "No hierarchy context"

        return {
            "sorted_memories": sorted_memories,
            "context": context,
        }
