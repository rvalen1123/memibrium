"""Hybrid retrieval engine for Memibrium.

Combines semantic (HNSW cosine), lexical (BM25), and temporal search
with optional RRF fusion, cross-encoder re-ranking, and multi-hop expansion.
"""

import asyncio
import json
import re
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any


# ── Token estimation ────────────────────────────────────────────

def approximate_tokens(text: str) -> int:
    """Rough token count for budget planning."""
    return len(text.split()) + len(re.findall(r"[.,!?;:]", text))


# ── Temporal window parsing ─────────────────────────────────────

def _parse_relative(expr: str, now: datetime) -> tuple[Optional[datetime], Optional[datetime]]:
    """Parse relative temporal expressions."""
    lowered = expr.lower().strip()
    
    if lowered.startswith("before "):
        rest = lowered[7:].strip()
        try:
            dt = datetime.fromisoformat(rest.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return datetime.min.replace(tzinfo=timezone.utc), dt
        except ValueError:
            pass
        # Try common date formats
        for fmt in ("%Y-%m-%d", "%B %d, %Y", "%d %B %Y", "%b %d, %Y"):
            try:
                dt = datetime.strptime(rest, fmt)
                dt = dt.replace(tzinfo=timezone.utc)
                return datetime.min.replace(tzinfo=timezone.utc), dt
            except ValueError:
                continue
    
    if lowered.startswith("after "):
        rest = lowered[6:].strip()
        try:
            dt = datetime.fromisoformat(rest.replace("Z", "+00:00"))
            # "after 2023-05-08" means from the NEXT day
            return (dt + timedelta(days=1)).replace(tzinfo=timezone.utc), datetime.max.replace(tzinfo=timezone.utc)
        except ValueError:
            pass
        for fmt in ("%Y-%m-%d", "%B %d, %Y", "%d %B %Y", "%b %d, %Y"):
            try:
                dt = datetime.strptime(rest, fmt).replace(tzinfo=timezone.utc)
                return (dt + timedelta(days=1)).replace(tzinfo=timezone.utc), datetime.max.replace(tzinfo=timezone.utc)
            except ValueError:
                continue
    
    # "last N days/weeks/months"
    m = re.match(r"last\s+(\d+)\s+(days?|weeks?|months?)", lowered)
    if m:
        amount = int(m.group(1))
        unit = m.group(2)
        delta = timedelta(days=amount)
        if unit.startswith("week"):
            delta = timedelta(days=amount * 7)
        elif unit.startswith("month"):
            delta = timedelta(days=amount * 30)
        return now - delta, now
    
    return None, None


def _parse_absolute(expr: str) -> tuple[Optional[datetime], Optional[datetime]]:
    """Parse absolute date/datetime expressions."""
    expr = expr.strip()
    
    # ISO formats
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(expr, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if fmt == "%Y-%m-%d":
                return dt, dt + timedelta(days=1)
            return dt, dt + timedelta(minutes=1)
        except ValueError:
            continue
    
    # LOCOMO style: "1:56 pm on 8 May, 2023"
    for fmt in (
        "%I:%M %p on %d %B, %Y",
        "%I:%M %p on %d %b, %Y",
        "%H:%M on %d %B, %Y",
        "%H:%M on %d %b, %Y",
    ):
        try:
            dt = datetime.strptime(expr, fmt)
            dt = dt.replace(tzinfo=timezone.utc)
            return dt, dt + timedelta(minutes=1)
        except ValueError:
            continue
    
    # "8 May 2023" or "May 8, 2023"
    for fmt in ("%d %B %Y", "%d %b %Y", "%B %d, %Y", "%b %d, %Y"):
        try:
            dt = datetime.strptime(expr, fmt)
            dt = dt.replace(tzinfo=timezone.utc)
            return dt, dt + timedelta(days=1)
        except ValueError:
            continue
    
    return None, None


def parse_temporal_window(query: str, now: Optional[datetime] = None) -> Optional[tuple[datetime, datetime]]:
    """Extract temporal window from a query string.
    
    Returns (start, end) if a temporal constraint is found, else None.
    """
    now = now or datetime.now(timezone.utc)
    lowered = query.lower()
    
    # before/after patterns
    for prefix in ("before ", "after "):
        if prefix in lowered:
            # Extract the phrase after before/after
            idx = lowered.find(prefix)
            rest = query[idx + len(prefix):].strip()
            # Take up to next punctuation or 20 chars
            rest = re.split(r"[.,;!?]", rest)[0].strip()
            start, end = _parse_relative(f"{prefix}{rest}", now)
            if start and end:
                return start, end
    
    # "between X and Y"
    m = re.search(r"between\s+(.+?)\s+and\s+(.+?)(?:[.,;!?]|$)", lowered)
    if m:
        s1, e1 = _parse_absolute(m.group(1).strip())
        s2, e2 = _parse_absolute(m.group(2).strip())
        if s1 and e2:
            return s1, e2
    
    # "from X to Y"
    m = re.search(r"from\s+(.+?)\s+to\s+(.+?)(?:[.,;!?]|$)", lowered)
    if m:
        s1, _ = _parse_absolute(m.group(1).strip())
        _, e2 = _parse_absolute(m.group(2).strip())
        if s1 and e2:
            return s1, e2
    
    # "in May 2023", "on 2023-05-08"
    m = re.search(r"\b(in|on|during)\s+([A-Z][a-z]+\s+\d{4}|\d{4}-\d{2}-\d{2}|[A-Z][a-z]+\s+\d{1,2},?\s+\d{4})\b", query)
    if m:
        start, end = _parse_absolute(m.group(2).strip())
        if start and end:
            return start, end
    
    return None


# ── Hybrid Retriever ────────────────────────────────────────────

class HybridRetriever:
    """Hybrid search: semantic + lexical + temporal, with optional reranking."""

    _VECTOR_TYPE_ALIASES = {
        "pgvector": "vector",
        "vector": "vector",
        "ruvector": "ruvector",
    }

    @classmethod
    def _normalize_vtype(cls, vtype: str) -> str:
        try:
            return cls._VECTOR_TYPE_ALIASES[vtype]
        except KeyError as exc:
            raise ValueError(f"Unsupported vector type: {vtype!r}") from exc

    def __init__(self, pool=None, vtype: str = "pgvector", embedder=None):
        self.pool = pool
        self.vtype = self._normalize_vtype(vtype)
        self.embedder = embedder
        self._ce = None  # cross-encoder placeholder

    async def initialize(self):
        """No-op for compatibility."""
        pass

    def _parse_chronology_key(self, memory: dict) -> tuple:
        """Extract sortable chronology tuple from memory."""
        created = memory.get("created_at")
        if isinstance(created, str):
            try:
                created = datetime.fromisoformat(created.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                created = datetime.min.replace(tzinfo=timezone.utc)
        elif not isinstance(created, datetime):
            created = datetime.min.replace(tzinfo=timezone.utc)
        
        refs = memory.get("refs") or {}
        if isinstance(refs, str):
            try:
                refs = json.loads(refs)
            except Exception:
                refs = {}
        
        return (
            created,
            refs.get("session_index", 0),
            refs.get("chunk_index", 0),
            refs.get("turn_start", 0),
            refs.get("turn_end", 0),
        )

    def sort_by_chronology(self, memories: List[dict]) -> List[dict]:
        """Sort memories by event time, then session/chunk/turn order."""
        return sorted(memories, key=self._parse_chronology_key)

    def is_multihop_query(self, query: str) -> bool:
        """Detect queries likely requiring multi-hop reasoning."""
        lowered = query.lower()
        # Multi-hop indicators: multiple entities + relationship words
        indicators = ["how did", "how does", "what led to", "why did", "after", "before",
                      "between", "from", "to", "through", "via", "and then", "later"]
        has_indicator = any(ind in lowered for ind in indicators)
        # Count named entities (capitalized words)
        entities = set(re.findall(r"\b[A-Z][a-z]+\b", query))
        return has_indicator and len(entities) >= 2

    def expand_with_session_adjacency(self, base_results: List[dict],
                                     candidates: List[dict], window: int = 1) -> List[dict]:
        """Expand results with adjacent chunks from the same session."""
        if not base_results:
            return base_results
        
        base_ids = {m["id"] for m in base_results}
        expanded = list(base_results)
        
        for base in base_results:
            refs = base.get("refs") or {}
            if isinstance(refs, str):
                try:
                    refs = json.loads(refs)
                except Exception:
                    continue
            base_session = refs.get("session_index")
            base_chunk = refs.get("chunk_index")
            if base_session is None or base_chunk is None:
                continue
            
            for cand in candidates:
                if cand["id"] in base_ids:
                    continue
                c_refs = cand.get("refs") or {}
                if isinstance(c_refs, str):
                    try:
                        c_refs = json.loads(c_refs)
                    except Exception:
                        continue
                if c_refs.get("session_index") == base_session:
                    c_chunk = c_refs.get("chunk_index")
                    if c_chunk is not None and abs(c_chunk - base_chunk) <= window:
                        expanded.append(cand)
                        base_ids.add(cand["id"])
        
        # Deduplicate and sort chronologically
        seen = set()
        deduped = []
        for m in expanded:
            if m["id"] not in seen:
                seen.add(m["id"])
                deduped.append(m)
        return self.sort_by_chronology(deduped)

    def extract_bridge_terms(self, query: str, memories: List[dict],
                            exclude_query_terms: Optional[set] = None) -> set:
        """Extract bridge entities/terms connecting query to memories."""
        # Get entities from memories (preserve original case)
        memory_entities = {}
        for m in memories:
            ents = m.get("entities", [])
            if isinstance(ents, str):
                try:
                    ents = json.loads(ents)
                except Exception:
                    ents = []
            for e in ents:
                name = e.get("name", "") if isinstance(e, dict) else str(e)
                if name:
                    memory_entities[name.lower()] = name  # map lower->original
        
        # Get query entities (capitalized words, preserve case)
        query_entities = set(re.findall(r"\b[A-Z][a-z]+\b", query))
        
        # Bridge terms = entities in memories that also appear in query (case-insensitive match, original case returned)
        bridge = set()
        for qe in query_entities:
            if qe.lower() in memory_entities:
                bridge.add(memory_entities[qe.lower()])
        
        # Exclude common words and query terms if requested
        if exclude_query_terms:
            bridge -= {t for t in bridge if t.lower() in {x.lower() for x in exclude_query_terms}}
        
        return bridge

    def filter_second_hop_candidates(self, first_hop: List[dict],
                                      candidates: List[dict]) -> List[dict]:
        """Filter second-hop candidates by session overlap or entity overlap."""
        first_sessions = set()
        first_entities = set()
        
        for m in first_hop:
            refs = m.get("refs") or {}
            if isinstance(refs, str):
                try:
                    refs = json.loads(refs)
                except Exception:
                    refs = {}
            if refs.get("session_index") is not None:
                first_sessions.add(refs["session_index"])
            
            ents = m.get("entities", [])
            if isinstance(ents, str):
                try:
                    ents = json.loads(ents)
                except Exception:
                    ents = []
            for e in ents:
                name = e.get("name", "") if isinstance(e, dict) else str(e)
                if name:
                    first_entities.add(name.lower())
        
        filtered = []
        for cand in candidates:
            refs = cand.get("refs") or {}
            if isinstance(refs, str):
                try:
                    refs = json.loads(refs)
                except Exception:
                    refs = {}
            
            # Session overlap
            if refs.get("session_index") in first_sessions:
                filtered.append(cand)
                continue
            
            # Entity overlap
            ents = cand.get("entities", [])
            if isinstance(ents, str):
                try:
                    ents = json.loads(ents)
                except Exception:
                    ents = []
            for e in ents:
                name = e.get("name", "") if isinstance(e, dict) else str(e)
                if name and name.lower() in first_entities:
                    filtered.append(cand)
                    break
        
        return filtered

    def merge_multihop_results(self, first_hop: List[dict],
                              second_hop: List[dict]) -> List[dict]:
        """Merge first-hop and second-hop results, filtering by entity/session overlap."""
        # Filter second-hop to only include candidates related to first-hop
        filtered_second = self.filter_second_hop_candidates(first_hop, second_hop)
        
        seen = set()
        merged = []
        for m in first_hop + filtered_second:
            if m["id"] not in seen:
                seen.add(m["id"])
                merged.append(m)
        return self.sort_by_chronology(merged)

    # ── Search sub-methods (async, require DB pool) ───────────────

    async def _semantic_search(self, embedding: list, top_k: int,
                                state_filter: Optional[list] = None,
                                domain: Optional[str] = None) -> List[dict]:
        """Vector similarity search via pgvector or ruvector."""
        if not self.pool or embedding is None:
            return []

        params = [json.dumps(embedding), top_k]
        where_clauses = ["state != 'shed'"]

        if state_filter:
            placeholders = ", ".join(f"${i+3}" for i in range(len(state_filter)))
            where_clauses.append(f"state IN ({placeholders})")
            params.extend(state_filter)

        if domain:
            where_clauses.append(f"domain = ${len(params)+1}")
            params.append(domain)

        query = f"""
            SELECT id, content, state, memory_type, created_at, updated_at, frozen_at,
                   entities, topics, refs, witness_chain, embedding,
                   1 - (embedding <=> $1::{self.vtype}) AS cosine_score
            FROM memories
            WHERE {" AND ".join(where_clauses)}
            ORDER BY embedding <=> $1::{self.vtype}
            LIMIT $2
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [dict(r) for r in rows]

    async def _lexical_search(self, query: str, top_k: int,
                             state_filter: Optional[list] = None,
                             domain: Optional[str] = None) -> List[dict]:
        """BM25-style text search. Falls back to ILIKE if no full-text index."""
        if not self.pool:
            return []
        
        # Extract keywords
        words = re.findall(r"[a-zA-Z]{3,}", query.lower())
        if not words:
            return []
        
        async with self.pool.acquire() as conn:
            # Try tsvector search first
            try:
                tsquery = " | ".join(words)
                params = [tsquery, top_k]
                where_clauses = ["state != 'shed'", "to_tsvector('english', content) @@ to_tsquery('english', $1)"]
                if state_filter:
                    placeholders = ", ".join(f"${i+3}" for i in range(len(state_filter)))
                    where_clauses.append(f"state IN ({placeholders})")
                    params.extend(state_filter)
                if domain:
                    where_clauses.append(f"domain = ${len(params)+1}")
                    params.append(domain)
                query_sql = f"""
                    SELECT id, content, state, memory_type, created_at, updated_at, frozen_at,
                           entities, topics, refs, witness_chain, embedding,
                           ts_rank(to_tsvector('english', content), to_tsquery('english', $1)) AS bm25_score
                    FROM memories
                    WHERE {" AND ".join(where_clauses)}
                    ORDER BY bm25_score DESC
                    LIMIT $2
                    """
                rows = await conn.fetch(query_sql, *params)
                if rows:
                    return [dict(r) for r in rows]
            except Exception:
                pass
            
            # Fallback: ILIKE with OR
            patterns = [f"%{w}%" for w in words[:5]]
            where_clauses = ["state != 'shed'"]
            params = [top_k]
            
            if state_filter:
                placeholders = ", ".join(f"${i+2}" for i in range(len(state_filter)))
                where_clauses.append(f"state IN ({placeholders})")
                params.extend(state_filter)
            
            if domain:
                where_clauses.append(f"domain = ${len(params)+1}")
                params.append(domain)
            
            or_clauses = " OR ".join(f"content ILIKE ${i+len(params)+1}" for i in range(len(patterns)))
            where_clauses.append(f"({or_clauses})")
            params.extend(patterns)
            
            query_sql = f"""
                SELECT id, content, state, memory_type, created_at, updated_at, frozen_at,
                       entities, topics, refs, witness_chain, embedding,
                       0.5 AS bm25_score
                FROM memories
                WHERE {" AND ".join(where_clauses)}
                LIMIT $1
            """
            rows = await conn.fetch(query_sql, *params)
            return [dict(r) for r in rows]

    async def _temporal_search(self, start: datetime, end: datetime, top_k: int,
                                state_filter: Optional[list] = None,
                                domain: Optional[str] = None) -> List[dict]:
        """Search memories within a temporal window."""
        if not self.pool:
            return []
        
        async with self.pool.acquire() as conn:
            where_clauses = ["state != 'shed'", "created_at >= $1", "created_at < $2"]
            params = [start, end, top_k]
            
            if state_filter:
                placeholders = ", ".join(f"${i+4}" for i in range(len(state_filter)))
                where_clauses.append(f"state IN ({placeholders})")
                params.extend(state_filter)
            
            if domain:
                where_clauses.append(f"domain = ${len(params)+1}")
                params.append(domain)
            
            query = f"""
                SELECT id, content, state, memory_type, created_at, updated_at, frozen_at,
                       entities, topics, refs, witness_chain, embedding,
                       1.0 AS temporal_score
                FROM memories
                WHERE {" AND ".join(where_clauses)}
                ORDER BY created_at
                LIMIT $3
            """
            rows = await conn.fetch(query, *params)
            return [dict(r) for r in rows]

    def _normalize_scores(self, results: List[dict], score_key: str) -> List[dict]:
        """Min-max normalize scores to [0, 1]."""
        if not results:
            return results
        scores = [r.get(score_key, 0) for r in results]
        min_s, max_s = min(scores), max(scores)
        if max_s == min_s:
            for r in results:
                r[score_key] = 1.0
            return results
        for r in results:
            r[score_key] = (r.get(score_key, 0) - min_s) / (max_s - min_s)
        return results

    def _rrf_fuse(self, streams: List[List[dict]], k: int = 60) -> List[dict]:
        """Reciprocal Rank Fusion across multiple result streams."""
        scores: Dict[str, dict] = {}
        
        for stream in streams:
            for rank, item in enumerate(stream, start=1):
                item_id = item["id"]
                if item_id not in scores:
                    scores[item_id] = dict(item)
                    scores[item_id]["rrf_score"] = 0.0
                scores[item_id]["rrf_score"] += 1.0 / (k + rank)
        
        # Normalize by number of streams that contributed
        fused = sorted(scores.values(), key=lambda x: x["rrf_score"], reverse=True)
        return fused

    async def _cross_encoder_rerank(self, query: str, candidates: List[dict],
                                     top_k: int) -> List[dict]:
        """Re-rank candidates with cross-encoder if available."""
        if not self._ce or not candidates:
            return candidates[:top_k]
        
        # Placeholder: would use sentence-transformers cross-encoder
        # For now, return top candidates by existing score
        scored = sorted(candidates, key=lambda x: x.get("rrf_score", x.get("cosine_score", 0)), reverse=True)
        return scored[:top_k]

    # ── Main search entrypoint ────────────────────────────────────

    async def search(self, query: str, embedding: list, top_k: int = 10,
                     state_filter: Optional[list] = None,
                     domain: Optional[str] = None,
                     temporal_window: Optional[tuple] = None,
                     use_rrf: bool = True,
                     rerank: bool = False) -> List[dict]:
        """
        Full hybrid search.

        Args:
            query: raw text query (for BM25 + temporal parsing + cross-encoder)
            embedding: query embedding vector (for semantic search)
            top_k: final number of results
            state_filter: e.g. ["accepted", "crystallized"]
            domain: filter by domain string
            temporal_window: explicit (start, end) override; if None, parsed from query
            use_rrf: if False, return semantic-only (legacy mode)
            rerank: if True and cross-encoder available, re-rank top 2*top_k candidates

        Returns:
            List of memory dicts with keys: id, content, state, memory_type,
            created_at, rrf_score, plus stream-specific scores.
        """
        # Parse temporal window from query if not provided
        if temporal_window is None:
            temporal_window = parse_temporal_window(query)
        
        fetch_k = top_k * 2
        
        # Launch searches concurrently
        semantic_task = self._semantic_search(embedding, fetch_k, state_filter, domain)
        lexical_task = self._lexical_search(query, fetch_k, state_filter, domain)
        tasks = [semantic_task, lexical_task]
        
        if temporal_window:
            start, end = temporal_window
            temporal_task = self._temporal_search(start, end, fetch_k, state_filter, domain)
            tasks.append(temporal_task)
        
        results = await asyncio.gather(*tasks)
        semantic_results = results[0]
        lexical_results = results[1]
        temporal_results = results[2] if temporal_window else []
        
        if not use_rrf:
            # Legacy: return semantic-only, normalized
            if len(semantic_results) < top_k:
                # Pad with lexical if needed
                seen = {r["id"] for r in semantic_results}
                for r in lexical_results:
                    if r["id"] not in seen:
                        semantic_results.append(r)
                        seen.add(r["id"])
                        if len(semantic_results) >= top_k:
                            break
            return self._normalize_scores(semantic_results, "cosine_score")[:top_k]
        
        # Normalize each stream
        semantic_results = self._normalize_scores(semantic_results, "cosine_score")
        lexical_results = self._normalize_scores(lexical_results, "bm25_score")
        if temporal_results:
            temporal_results = self._normalize_scores(temporal_results, "temporal_score")
        
        # Fuse
        streams = [semantic_results, lexical_results]
        if temporal_results:
            streams.append(temporal_results)
        
        fused = self._rrf_fuse(streams)
        
        # Optional rerank
        if rerank and self._ce:
            rerank_k = min(top_k * 2, len(fused))
            final = await self._cross_encoder_rerank(query, fused, rerank_k)
        else:
            final = fused
        
        # Multi-hop expansion for multi-hop queries
        if self.is_multihop_query(query):
            # Session adjacency expansion only (safe baseline per benchmark findings)
            all_candidates = semantic_results + lexical_results
            seen = {r["id"] for r in all_candidates}
            # Deduplicate candidates
            candidates = []
            for r in all_candidates:
                if r["id"] not in seen:
                    seen.add(r["id"])
                    candidates.append(r)
            expanded = self.expand_with_session_adjacency(final, candidates, window=1)
            # Re-sort and limit
            final = self.sort_by_chronology(expanded)
        
        # Chronology sort for temporal queries
        temporal_cues = ("before", "after", "earlier", "later", "first", "last", "then")
        if any(token in query.lower() for token in temporal_cues):
            final = self.sort_by_chronology(final)
        
        return final[:top_k]
