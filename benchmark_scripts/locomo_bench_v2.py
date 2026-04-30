#!/usr/bin/env python3
"""LOCOMO benchmark runner for Memibrium CT Memory server.

Flow per conversation:
1. Ingest all sessions as memories (each turn -> retain)
2. For each QA question, recall from Memibrium + answer with LLM
3. Score predicted answer vs ground truth using LLM judge
"""

import json, time, sys, os, statistics, re
import httpx
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor

MCP = os.environ.get("MCP_URL", "http://localhost:9999/mcp")


def _normalize_foundry_models_endpoint(endpoint: str) -> str:
    endpoint = endpoint.rstrip("/")
    if endpoint.endswith("/models"):
        return endpoint
    return endpoint + "/models" if endpoint else ""


def load_chat_config():
    """Load benchmark answer/judge chat config from env, matching server.py names."""
    endpoint = (
        os.environ.get("AZURE_CHAT_ENDPOINT")
        or os.environ.get("AZURE_OPENAI_ENDPOINT")
        or os.environ.get("OPENAI_BASE_URL")
        or ""
    )
    key = (
        os.environ.get("AZURE_CHAT_KEY")
        or os.environ.get("AZURE_CHAT_API_KEY")
        or os.environ.get("AZURE_OPENAI_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
        or ""
    )
    default_model = (
        os.environ.get("AZURE_CHAT_DEPLOYMENT")
        or os.environ.get("AZURE_OPENAI_DEPLOYMENT")
        or os.environ.get("CHAT_MODEL")
        or "gpt-4.1-mini"
    )
    judge_model = os.environ.get("JUDGE_MODEL", default_model)
    answer_model = os.environ.get("ANSWER_MODEL", default_model)
    return _normalize_foundry_models_endpoint(endpoint), key, judge_model, answer_model


AZURE_CHAT_ENDPOINT, AZURE_CHAT_KEY, JUDGE_MODEL, ANSWER_MODEL = load_chat_config()


def _env_flag(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() not in {"", "0", "false", "no", "off"}


# Query expansion is intentionally opt-in: useful for evaluation, too slow for default runs.
USE_QUERY_EXPANSION = _env_flag("USE_QUERY_EXPANSION", default=False)
# Context reranking is opt-in candidate precision recovery after recall/query expansion.
USE_CONTEXT_RERANK = _env_flag("USE_CONTEXT_RERANK", default=False)
# Append-only context expansion is an opt-in safer follow-up: preserve the
# original answer context exactly, then append a few extra candidates below it.
USE_APPEND_CONTEXT_EXPANSION = _env_flag("USE_APPEND_CONTEXT_EXPANSION", default=False)
# Gated append is the next precision experiment: preserve the original context,
# append only when the base context is weak, and require explicit query/context
# lexical overlap for extras. It is intentionally opt-in/evaluation-only.
USE_GATED_APPEND_CONTEXT_EXPANSION = _env_flag("USE_GATED_APPEND_CONTEXT_EXPANSION", default=False)
RECALL_TOP_K = 10
RERANK_RECALL_TOP_K = 20
APPEND_CONTEXT_RECALL_TOP_K = 20
ANSWER_CONTEXT_TOP_K = 15
APPEND_CONTEXT_EXTRA_K = 5
RERANK_PRESERVE_PREFIX_K = 2
GATED_APPEND_MIN_EXTRA_OVERLAP = 1
GATED_APPEND_STRONG_BASE_OVERLAP = 2
GATED_APPEND_STRONG_BASE_SCORE = 0.6
GATED_APPEND_STRONG_BASE_COUNT = 2


def validate_retrieval_modes(
    use_context_rerank=None,
    use_append_context_expansion=None,
    use_gated_append_context_expansion=None,
):
    """Reject retrieval modes whose metadata/prompt semantics would conflict."""
    if use_context_rerank is None:
        use_context_rerank = USE_CONTEXT_RERANK
    if use_append_context_expansion is None:
        use_append_context_expansion = USE_APPEND_CONTEXT_EXPANSION
    if use_gated_append_context_expansion is None:
        use_gated_append_context_expansion = USE_GATED_APPEND_CONTEXT_EXPANSION
    append_modes = [bool(use_append_context_expansion), bool(use_gated_append_context_expansion)]
    if use_context_rerank and any(append_modes):
        raise ValueError("--context-rerank cannot be combined with append context expansion modes")
    if sum(append_modes) > 1:
        raise ValueError("append context expansion modes are mutually exclusive")


CAT_MAP = {1: "single-hop", 2: "temporal", 3: "multi-hop", 4: "unanswerable", 5: "adversarial"}


def normalize_category(cat):
    """Return the benchmark/reporting category label for a LOCOMO category value."""
    return CAT_MAP.get(cat, str(cat)) if isinstance(cat, int) else cat


def should_skip_category(orig_cat, skip_cats):
    """Honor skip lists containing original numeric IDs or normalized labels."""
    cat = normalize_category(orig_cat)
    return orig_cat in skip_cats or cat in skip_cats or str(orig_cat) in skip_cats


# Categories. Numeric LOCOMO rows are normalized before scoring; keep this map
# aligned with CAT_MAP so reports do not drift if a helper receives raw IDs.
CAT_NAMES = CAT_MAP

client = httpx.Client(timeout=120)


def mcp_post(tool, payload, retries=3):
    last_error = None
    last_status = None
    last_response_text = None
    for attempt in range(retries):
        try:
            r = client.post(f"{MCP}/{tool}", json=payload)
            last_status = r.status_code
            last_response_text = r.text[:2000]
            if r.status_code == 200 and r.text.strip():
                return r.json()
            last_error = "empty response" if r.status_code == 200 else "non-200 response"
        except Exception as e:
            last_error = e
        if attempt < retries - 1:
            time.sleep(2 ** attempt)

    raise RuntimeError(
        f"MCP {tool} failed after {retries} attempts: {last_error}; "
        f"status={last_status}; response={last_response_text}"
    )


def mcp_get(tool):
    r = client.get(f"{MCP}/{tool}")
    return r.json()


def run_preflight_checks():
    """Fast fail before spending minutes ingesting benchmark data."""
    print("  Running preflight checks...")

    # MCP recall path should respond successfully.
    recall_resp = client.post(f"{MCP}/recall", json={"query": "test", "top_k": 1})
    recall_resp.raise_for_status()
    _ = recall_resp.json()

    # Answer/judge LLM path should respond successfully.
    llm_resp = llm_call([{"role": "user", "content": "What is 2+2?"}], max_tokens=10)
    if "4" not in llm_resp:
        raise RuntimeError(f"LLM preflight failed: {llm_resp!r}")

    print("  Preflight OK: recall + LLM reachable")


def llm_call(messages, model=ANSWER_MODEL, max_tokens=200, retries=3):
    """Call Azure Foundry LLM with retry.

    Fail closed: benchmarking must not silently turn auth/schema/network failures
    into "I don't know" answers, because that collapses scores to 0 invisibly.
    """
    last_error = None
    for attempt in range(retries):
        try:
            r = client.post(
                f"{AZURE_CHAT_ENDPOINT}/chat/completions",
                headers={"api-key": AZURE_CHAT_KEY, "Content-Type": "application/json"},
                json={"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": 0},
            )
            r.raise_for_status()
            data = r.json()
            content = data["choices"][0]["message"]["content"]
            if not isinstance(content, str) or not content.strip():
                raise RuntimeError(f"Empty or non-string LLM content: {data}")
            return content
        except Exception as e:
            last_error = e
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                response_text = None
                response_status = None
                if 'r' in locals():
                    response_status = getattr(r, 'status_code', None)
                    try:
                        response_text = r.text[:2000]
                    except Exception:
                        response_text = None
                raise RuntimeError(
                    f"Azure chat call failed after {retries} attempts: {e}; "
                    f"status={response_status}; response={response_text}"
                ) from e


def _parse_locomo_datetime(date_str: str) -> str | None:
    date_str = (date_str or "").strip()
    if not date_str:
        return None
    for fmt in (
        "%I:%M %p on %d %B, %Y",
        "%I:%M %p on %d %b, %Y",
        "%H:%M on %d %B, %Y",
        "%H:%M on %d %b, %Y",
    ):
        try:
            dt = __import__("datetime").datetime.strptime(date_str, fmt)
            return dt.replace(tzinfo=__import__("datetime").timezone.utc).isoformat()
        except ValueError:
            continue
    return None


def _normalize_relative_dates(text: str, anchor_date: __import__("datetime").datetime) -> str:
    """Normalize relative date expressions in text to absolute dates.
    
    In scope: yesterday, today, tomorrow, last week, this week, next week,
    last month, this month, next month, weekday names, a few days ago,
    two weekends ago, last year, this year, next year.
    
    Out of scope: vague references like 'when we first met', 'after the promotion'.
    
    Fallback: unparseable expressions stay as-is (safe default).
    """
    import re
    from datetime import timedelta
    
    result = text
    
    # Helper to format date
    def fmt(dt):
        return dt.strftime("%d %B %Y")
    
    # day before yesterday (must come before "yesterday")
    if re.search(r'\bday before yesterday\b', result, re.IGNORECASE):
        db_yesterday = anchor_date - timedelta(days=2)
        result = re.sub(r'\bday before yesterday\b', fmt(db_yesterday), result, flags=re.IGNORECASE)
    
    # yesterday / today / tomorrow / last night
    if re.search(r'\byesterday\b', result, re.IGNORECASE):
        yesterday = anchor_date - timedelta(days=1)
        result = re.sub(r'\byesterday\b', fmt(yesterday), result, flags=re.IGNORECASE)
    if re.search(r'\blast night\b', result, re.IGNORECASE):
        last_night = anchor_date - timedelta(days=1)
        result = re.sub(r'\blast night\b', fmt(last_night), result, flags=re.IGNORECASE)
    if re.search(r'\btoday\b', result, re.IGNORECASE):
        result = re.sub(r'\btoday\b', fmt(anchor_date), result, flags=re.IGNORECASE)
    if re.search(r'\btomorrow\b', result, re.IGNORECASE):
        tomorrow = anchor_date + timedelta(days=1)
        result = re.sub(r'\btomorrow\b', fmt(tomorrow), result, flags=re.IGNORECASE)
    
    # last week / this week / next week
    if re.search(r'\blast week\b', result, re.IGNORECASE):
        last_week = anchor_date - timedelta(days=7)
        result = re.sub(r'\blast week\b', f"the week of {fmt(last_week)}", result, flags=re.IGNORECASE)
    if re.search(r'\bthis week\b', result, re.IGNORECASE):
        result = re.sub(r'\bthis week\b', f"the week of {fmt(anchor_date)}", result, flags=re.IGNORECASE)
    if re.search(r'\bnext week\b', result, re.IGNORECASE):
        next_week = anchor_date + timedelta(days=7)
        result = re.sub(r'\bnext week\b', f"the week of {fmt(next_week)}", result, flags=re.IGNORECASE)
    
    # last weekend / this weekend / next weekend
    if re.search(r'\blast weekend\b', result, re.IGNORECASE):
        # Find previous Saturday
        days_since_sat = (anchor_date.weekday() - 5) % 7
        if days_since_sat == 0:
            days_since_sat = 7
        prev_sat = anchor_date - timedelta(days=days_since_sat)
        result = re.sub(r'\blast weekend\b', f"the weekend of {fmt(prev_sat)}", result, flags=re.IGNORECASE)
    if re.search(r'\bthis weekend\b', result, re.IGNORECASE):
        # Find upcoming Saturday
        days_until_sat = (5 - anchor_date.weekday()) % 7
        if days_until_sat == 0:
            days_until_sat = 7
        this_sat = anchor_date + timedelta(days=days_until_sat)
        result = re.sub(r'\bthis weekend\b', f"the weekend of {fmt(this_sat)}", result, flags=re.IGNORECASE)
    if re.search(r'\bnext weekend\b', result, re.IGNORECASE):
        # Find upcoming Saturday, then add 7 days
        days_until_sat = (5 - anchor_date.weekday()) % 7
        if days_until_sat == 0:
            days_until_sat = 7
        next_sat = anchor_date + timedelta(days=days_until_sat) + timedelta(days=7)
        result = re.sub(r'\bnext weekend\b', f"the weekend of {fmt(next_sat)}", result, flags=re.IGNORECASE)
    
    # last month / this month / next month
    if re.search(r'\blast month\b', result, re.IGNORECASE):
        # Approximate: go back 30 days
        last_month = anchor_date - timedelta(days=30)
        result = re.sub(r'\blast month\b', f"{last_month.strftime('%B %Y')}", result, flags=re.IGNORECASE)
    if re.search(r'\bthis month\b', result, re.IGNORECASE):
        result = re.sub(r'\bthis month\b', f"{anchor_date.strftime('%B %Y')}", result, flags=re.IGNORECASE)
    if re.search(r'\bnext month\b', result, re.IGNORECASE):
        next_month = anchor_date + timedelta(days=30)
        result = re.sub(r'\bnext month\b', f"{next_month.strftime('%B %Y')}", result, flags=re.IGNORECASE)
    
    # last year / this year / next year
    if re.search(r'\blast year\b', result, re.IGNORECASE):
        last_year = anchor_date.year - 1
        result = re.sub(r'\blast year\b', str(last_year), result, flags=re.IGNORECASE)
    if re.search(r'\bthis year\b', result, re.IGNORECASE):
        result = re.sub(r'\bthis year\b', str(anchor_date.year), result, flags=re.IGNORECASE)
    if re.search(r'\bnext year\b', result, re.IGNORECASE):
        next_year = anchor_date.year + 1
        result = re.sub(r'\bnext year\b', str(next_year), result, flags=re.IGNORECASE)
    
    # a few days ago -> 3 days ago (approximate)
    if re.search(r'\ba few days ago\b', result, re.IGNORECASE):
        few_days = anchor_date - timedelta(days=3)
        result = re.sub(r'\ba few days ago\b', fmt(few_days), result, flags=re.IGNORECASE)
    
    # two weekends ago
    if re.search(r'\btwo weekends ago\b', result, re.IGNORECASE):
        # Find previous Saturday, then go back another 7 days
        days_to_prev_sat = (anchor_date.weekday() + 2) % 7  # Mon=0, Sat=5, so Mon->Sat = 5 days forward, but we want backward
        # Actually: weekday() gives Mon=0...Sun=6. Saturday=5.
        # Days since last Saturday = (weekday + 2) % 7
        # If today is Monday (0): (0+2)%7 = 2. But Monday is 2 days AFTER Saturday.
        # We want days BEFORE = 5 (Mon->Sun->Sat->Fri->Thu->Wed->Tue->Mon... wait)
        # Monday to previous Saturday: Mon(0) -> Sun(-1) -> Sat(-2). So 2 days back.
        # Actually let me just use: days_since_sat = (weekday - 5) % 7
        # Mon(0): (0-5)%7 = 2. Correct! 2 days ago was Saturday.
        # But if today IS Saturday (5): (5-5)%7 = 0. That means "today is Saturday", 
        # so "two weekends ago" would be the Saturday 7 days before.
        days_since_sat = (anchor_date.weekday() - 5) % 7
        if days_since_sat == 0:
            days_since_sat = 7  # If today is Saturday, last Saturday was 7 days ago
        prev_sat = anchor_date - timedelta(days=days_since_sat)
        two_weekends_sat = prev_sat - timedelta(days=7)
        result = re.sub(r'\btwo weekends ago\b', f"the weekend of {fmt(two_weekends_sat)}", result, flags=re.IGNORECASE)
    
    # last Friday / next Tuesday etc. - weekday names
    weekday_map = {
        'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
        'friday': 4, 'saturday': 5, 'sunday': 6
    }
    for day_name, day_num in weekday_map.items():
        # last {day}
        pattern = rf'\blast {day_name}\b'
        if re.search(pattern, result, re.IGNORECASE):
            days_ago = (anchor_date.weekday() - day_num) % 7
            if days_ago == 0:
                days_ago = 7
            last_day = anchor_date - timedelta(days=days_ago)
            result = re.sub(pattern, fmt(last_day), result, flags=re.IGNORECASE)
        
        # next {day}
        pattern = rf'\bnext {day_name}\b'
        if re.search(pattern, result, re.IGNORECASE):
            days_until = (day_num - anchor_date.weekday()) % 7
            if days_until == 0:
                days_until = 7
            next_day = anchor_date + timedelta(days=days_until)
            result = re.sub(pattern, fmt(next_day), result, flags=re.IGNORECASE)
    
    return result


def ingest_conversation(conv, sample_id, chunk_size=10, normalize_dates=False):
    """Ingest all sessions of a conversation into Memibrium.
    
    Args:
        normalize_dates: If True, resolve relative dates (yesterday, last week, etc.)
                         to absolute dates using the session timestamp as anchor.
    """
    speaker_a = conv.get("speaker_a", "A")
    speaker_b = conv.get("speaker_b", "B")
    domain = f"locomo-{sample_id}"

    sessions = sorted([k for k in conv if k.startswith("session_") and not k.endswith("date_time")])
    total_turns = 0

    for session_idx, sess_key in enumerate(sessions, start=1):
        date_key = f"{sess_key}_date_time"
        date_str = conv.get(date_key, "")
        event_at = _parse_locomo_datetime(date_str)
        turns = conv[sess_key]

        chunk = []
        chunk_turn_start = 0
        for turn_idx, turn in enumerate(turns):
            speaker = turn["speaker"]
            text = turn["text"]
            
            # Normalize relative dates if enabled
            if normalize_dates and event_at:
                from datetime import datetime
                anchor = datetime.fromisoformat(event_at.replace('Z', '+00:00'))
                text = _normalize_relative_dates(text, anchor)
            
            if not chunk:
                chunk_turn_start = turn_idx
            chunk.append(f"{speaker}: {text}")

            if len(chunk) >= chunk_size:
                content = f"[{date_str}] {' | '.join(chunk)}"
                payload = {"content": content, "domain": domain}
                if event_at:
                    payload["event_at"] = event_at
                payload["refs"] = {
                    "session_index": session_idx,
                    "chunk_index": chunk_turn_start // max(chunk_size, 1),
                    "turn_start": chunk_turn_start,
                    "turn_end": turn_idx,
                }
                mcp_post("retain", payload)
                total_turns += len(chunk)
                chunk = []

        if chunk:
            content = f"[{date_str}] {' | '.join(chunk)}"
            payload = {"content": content, "domain": domain}
            if event_at:
                payload["event_at"] = event_at
            payload["refs"] = {
                "session_index": session_idx,
                "chunk_index": chunk_turn_start // max(chunk_size, 1),
                "turn_start": chunk_turn_start,
                "turn_end": len(turns) - 1,
            }
            mcp_post("retain", payload)
            total_turns += len(chunk)

    return total_turns, domain


def expand_query(question):
    """Generate a few diverse query reformulations for recall-time fusion."""
    try:
        resp = llm_call([
            {
                "role": "system",
                "content": (
                    "Generate 3 diverse reformulations of the question focused on different aspects "
                    "(entities, time, relationships). Return a JSON array of 3 strings only."
                ),
            },
            {"role": "user", "content": question},
        ], max_tokens=200)
        paraphrases = json.loads(resp.strip())
        return [question] + [p for p in paraphrases if isinstance(p, str)][:3]
    except Exception:
        expand_query.fail_count = getattr(expand_query, 'fail_count', 0) + 1
        return [question]


def _tokenize_for_rerank(text):
    """Tokenize text for lightweight lexical reranking."""
    stopwords = {
        "a", "an", "and", "are", "as", "at", "be", "by", "did", "do", "does",
        "for", "from", "happen", "happened", "how", "i", "in", "is", "it",
        "of", "on", "or", "the", "to", "was", "were", "what", "when", "where",
        "who", "why", "with", "would",
    }
    return [
        token
        for token in re.findall(r"[a-z0-9]+", str(text).lower())
        if len(token) > 2 and token not in stopwords
    ]


def _memory_dedupe_key(memory):
    """Stable key for deduplicating recall results with or without ids."""
    if isinstance(memory, dict):
        if memory.get("id"):
            return f"id::{memory.get('id')}"
        content = " ".join(str(memory.get("content", "")).split())
        refs = memory.get("refs") or ""
        created_at = memory.get("created_at") or ""
        return f"content::{content}::refs::{refs}::created::{created_at}"
    return f"raw::{str(memory)}"


def rerank_memories_for_question(question, memories, top_k=ANSWER_CONTEXT_TOP_K, preserve_prefix_k=RERANK_PRESERVE_PREFIX_K):
    """Lightweight precision recovery with an original-order safety prefix.

    The first lexical-rerank canary reduced latency but harmed paired LOCOMO
    quality, especially unanswerable and multi-hop questions, by demoting
    evidence needed for abstention/composition. Keep a small prefix in original
    retriever order, then fill the remaining context budget with lexical-ranked
    candidates. Stable tie-breaking preserves original recall order.
    """
    memories = list(memories)
    if top_k <= 0:
        return []
    preserve_count = max(0, min(preserve_prefix_k, top_k, len(memories)))
    preserved = memories[:preserve_count]
    remaining_slots = top_k - len(preserved)
    if remaining_slots <= 0:
        return preserved

    query_terms = _tokenize_for_rerank(question)
    candidates = memories[preserve_count:]
    if not query_terms:
        return preserved + candidates[:remaining_slots]

    query_counts = Counter(query_terms)
    ranked = []
    for offset, memory in enumerate(candidates, start=preserve_count):
        content = memory.get("content", "") if isinstance(memory, dict) else str(memory)
        content_terms = Counter(_tokenize_for_rerank(content))
        overlap = sum(min(query_counts[t], content_terms.get(t, 0)) for t in query_counts)
        # Preserve existing retriever scores as a weak tie-breaker when available.
        retriever_score = memory.get("score", memory.get("combined_score", memory.get("rrf_score", 0))) if isinstance(memory, dict) else 0
        try:
            retriever_score = float(retriever_score or 0)
        except (TypeError, ValueError):
            retriever_score = 0
        ranked.append((overlap, retriever_score, -offset, memory))
    ranked.sort(reverse=True)
    return preserved + [memory for _overlap, _score, _neg_idx, memory in ranked][:remaining_slots]


def _memory_lexical_overlap(question, memory):
    """Count overlap between query terms and a memory's content."""
    query_terms = Counter(_tokenize_for_rerank(question))
    if not query_terms:
        return 0
    content = memory.get("content", "") if isinstance(memory, dict) else str(memory)
    content_terms = Counter(_tokenize_for_rerank(content))
    return sum(min(query_terms[t], content_terms.get(t, 0)) for t in query_terms)


def _memory_retriever_score(memory):
    """Best-effort numeric score from recall payloads."""
    if not isinstance(memory, dict):
        return 0.0
    score = memory.get("score", memory.get("combined_score", memory.get("rrf_score", 0)))
    try:
        return float(score or 0)
    except (TypeError, ValueError):
        return 0.0


def base_context_is_strong(question, base_memories):
    """Return True when the base context already has enough direct signal.

    This gates append-only expansion to avoid adding noise when the original
    retrieval prefix already contains multiple high-confidence, query-overlapping
    memories.
    """
    strong = 0
    for memory in base_memories:
        if (
            _memory_lexical_overlap(question, memory) >= GATED_APPEND_STRONG_BASE_OVERLAP
            and _memory_retriever_score(memory) >= GATED_APPEND_STRONG_BASE_SCORE
        ):
            strong += 1
            if strong >= GATED_APPEND_STRONG_BASE_COUNT:
                return True
    return False


def append_memories_for_question(
    question,
    base_memories,
    candidate_memories,
    extra_k=APPEND_CONTEXT_EXTRA_K,
    min_extra_overlap=0,
):
    """Preserve original answer context exactly and append lexical extras.

    Rerank harm audits showed context replacement was the failure mode: useful
    original-order evidence was displaced from the answer prompt. This helper is
    deliberately append-only. The caller supplies the already-budgeted original
    answer context as ``base_memories``; those items remain prefix-identical, and
    only non-duplicate candidates beyond that prefix can be appended.
    """
    base = list(base_memories)
    if extra_k <= 0:
        return base

    seen_keys = {_memory_dedupe_key(memory) for memory in base}
    candidates = []
    for idx, memory in enumerate(candidate_memories):
        key = _memory_dedupe_key(memory)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        overlap = _memory_lexical_overlap(question, memory)
        if overlap < min_extra_overlap:
            continue
        retriever_score = _memory_retriever_score(memory)
        candidates.append((overlap, retriever_score, -idx, memory))
    candidates.sort(reverse=True)
    return base + [memory for _overlap, _score, _neg_idx, memory in candidates[:extra_k]]


def answer_question(question, domain):
    """Recall from Memibrium and generate answer."""
    validate_retrieval_modes()
    memories = []
    base_seen = {}
    recall_top_k = RECALL_TOP_K
    if USE_CONTEXT_RERANK:
        recall_top_k = RERANK_RECALL_TOP_K
    append_context_enabled = USE_APPEND_CONTEXT_EXPANSION or USE_GATED_APPEND_CONTEXT_EXPANSION
    candidate_recall_top_k = APPEND_CONTEXT_RECALL_TOP_K if append_context_enabled else recall_top_k
    candidate_limit = max(ANSWER_CONTEXT_TOP_K, candidate_recall_top_k)
    queries = expand_query(question) if USE_QUERY_EXPANSION else [question]
    candidate_memories = []
    for query in queries:
        recall_result = mcp_post("recall", {"query": query, "top_k": candidate_recall_top_k, "domain": domain})
        if isinstance(recall_result, list):
            recalled = recall_result
        else:
            recalled = recall_result.get("results", recall_result.get("memories", []))
        candidate_memories.extend(recalled)
        for memory in recalled[:recall_top_k]:
            memory_id = _memory_dedupe_key(memory)
            if memory_id not in base_seen:
                base_seen[memory_id] = memory
        if not USE_QUERY_EXPANSION and len(base_seen) >= candidate_limit:
            break
    base_candidates = list(base_seen.values())
    candidate_keys = {_memory_dedupe_key(memory) for memory in base_candidates}
    candidates = list(base_candidates)
    for memory in candidate_memories:
        key = _memory_dedupe_key(memory)
        if key not in candidate_keys:
            candidate_keys.add(key)
            candidates.append(memory)
    if USE_CONTEXT_RERANK:
        memories = rerank_memories_for_question(question, candidates, top_k=ANSWER_CONTEXT_TOP_K)
    elif append_context_enabled:
        base_context = base_candidates[:ANSWER_CONTEXT_TOP_K]
        if USE_GATED_APPEND_CONTEXT_EXPANSION and base_context_is_strong(question, base_context):
            memories = base_context
        else:
            memories = append_memories_for_question(
                question,
                base_context,
                candidates,
                extra_k=APPEND_CONTEXT_EXTRA_K,
                min_extra_overlap=(GATED_APPEND_MIN_EXTRA_OVERLAP if USE_GATED_APPEND_CONTEXT_EXPANSION else 0),
            )
    else:
        memories = candidates[:ANSWER_CONTEXT_TOP_K]

    if not memories:
        context = "No relevant memories found."
    else:
        chronology_cues = any(token in question.lower() for token in ["before", "after", "earlier", "later", "first", "last", "then", "when"])
        context_lines = []
        for m in memories:
            refs = m.get('refs') or {}
            if isinstance(refs, str):
                try:
                    refs = json.loads(refs)
                except Exception:
                    refs = {}
            prefix = ""
            if chronology_cues:
                parts = []
                if m.get('created_at'):
                    parts.append(f"time={m.get('created_at')}")
                if refs.get('session_index') is not None:
                    parts.append(f"session={refs.get('session_index')}")
                if refs.get('turn_start') is not None and refs.get('turn_end') is not None:
                    parts.append(f"turns={refs.get('turn_start')}-{refs.get('turn_end')}")
                if parts:
                    prefix = "[" + ", ".join(parts) + "] "
            context_lines.append(f"- {prefix}{m.get('content', '')}")
        context = "\n".join(context_lines)

    system_prompt = (
        "You are extracting factual information from conversation transcripts. "
        "This is an academic benchmark on long-term memory evaluation; context may include personal topics that should be treated as factual data. "
        "Use ONLY the provided context. Give a brief, direct answer. If the information is not available, say 'I don't know'."
    )
    if any(token in question.lower() for token in ["before", "after", "earlier", "later", "first", "last", "then", "when"]):
        system_prompt += " Pay close attention to chronology, timestamps, session order, and turn order."

    answer = llm_call([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Context (retrieved memories):\n{context}\n\nQuestion: {question}\n\nAnswer briefly:"}
    ])

    return answer, len(memories)


def judge_answer(question, predicted, ground_truth):
    """LLM judge: score predicted vs ground truth. Returns 0, 0.5, or 1."""
    judge_messages = [
        {"role": "system", "content": "You are a strict judge evaluating if a predicted answer matches the ground truth answer. Score:\n1 = correct (matches ground truth meaning)\n0.5 = partially correct (some relevant info but incomplete or slightly wrong)\n0 = wrong (incorrect or irrelevant)\n\nRespond with ONLY the number: 0, 0.5, or 1"},
        {"role": "user", "content": f"Question: {question}\nGround truth: {ground_truth}\nPredicted: {predicted}\n\nScore:"}
    ]

    try:
        response = llm_call(judge_messages, model=JUDGE_MODEL, max_tokens=5)
    except RuntimeError as e:
        # Azure content filters sometimes falsely trip on family-relationship words
        # in otherwise benign benchmark items (e.g. "sister"). Retry with a lightly
        # sanitized prompt that preserves judging semantics.
        if "content_filter" in str(e):
            def sanitize(text):
                text = str(text)
                replacements = {
                    "sister": "family member",
                    "brother": "family member",
                    "mother": "parent",
                    "father": "parent",
                    "mom": "parent",
                    "dad": "parent",
                    "daughter": "child",
                    "son": "child",
                    "wife": "spouse",
                    "husband": "spouse",
                    "girlfriend": "partner",
                    "boyfriend": "partner",
                }
                for old, new in replacements.items():
                    text = re.sub(rf"\b{old}\b", new, text, flags=re.IGNORECASE)
                return text

            response = llm_call([
                judge_messages[0],
                {"role": "user", "content": f"Question: {sanitize(question)}\nGround truth: {sanitize(ground_truth)}\nPredicted: {sanitize(predicted)}\n\nScore:"}
            ], model=JUDGE_MODEL, max_tokens=5)
        else:
            raise

    # Parse score
    try:
        score = float(response.strip())
        if score not in (0, 0.5, 1):
            score = 0
    except:
        score = 0
    return score


def result_suffix(
    normalize_dates=False,
    use_query_expansion=None,
    use_context_rerank=None,
    use_append_context_expansion=None,
    use_gated_append_context_expansion=None,
):
    if use_query_expansion is None:
        use_query_expansion = USE_QUERY_EXPANSION
    if use_context_rerank is None:
        use_context_rerank = USE_CONTEXT_RERANK
    if use_append_context_expansion is None:
        use_append_context_expansion = USE_APPEND_CONTEXT_EXPANSION
    if use_gated_append_context_expansion is None:
        use_gated_append_context_expansion = USE_GATED_APPEND_CONTEXT_EXPANSION
    validate_retrieval_modes(use_context_rerank, use_append_context_expansion, use_gated_append_context_expansion)
    suffix = ""
    if normalize_dates and use_query_expansion:
        suffix = "_query_expansion"
    elif normalize_dates:
        suffix = "_normalized"
    elif use_query_expansion:
        suffix = "_query_expansion_raw"
    if use_context_rerank:
        suffix += "_reranked"
    if use_gated_append_context_expansion:
        suffix += "_gated_appended"
    elif use_append_context_expansion:
        suffix += "_appended"
    return suffix


def result_output_path(
    normalize_dates=False,
    use_query_expansion=None,
    use_context_rerank=None,
    use_append_context_expansion=None,
    use_gated_append_context_expansion=None,
):
    return f"/tmp/locomo_results{result_suffix(normalize_dates, use_query_expansion, use_context_rerank, use_append_context_expansion, use_gated_append_context_expansion)}.json"


def _category_name(cat):
    return CAT_NAMES.get(cat, f"cat-{cat}") if isinstance(cat, int) else f"cat-{cat}"


def _protocol_4cat_overall(cat_scores):
    vals = []
    for cat, scores in cat_scores.items():
        cat_key = str(cat)
        if cat_key in {"5", "adversarial", "cat-5"}:
            continue
        vals.extend(scores)
    return round(statistics.mean(vals) * 100, 2) if vals else 0


def build_results_payload(
    all_scores,
    cat_scores,
    query_times,
    results_log,
    normalize_dates=False,
    use_query_expansion=None,
    use_context_rerank=None,
    use_append_context_expansion=None,
    use_gated_append_context_expansion=None,
    expand_fallback_count=0,
    expand_fallback_rate=0.0,
    cleaned=None,
):
    if use_query_expansion is None:
        use_query_expansion = USE_QUERY_EXPANSION
    if use_context_rerank is None:
        use_context_rerank = USE_CONTEXT_RERANK
    if use_append_context_expansion is None:
        use_append_context_expansion = USE_APPEND_CONTEXT_EXPANSION
    if use_gated_append_context_expansion is None:
        use_gated_append_context_expansion = USE_GATED_APPEND_CONTEXT_EXPANSION
    validate_retrieval_modes(use_context_rerank, use_append_context_expansion, use_gated_append_context_expansion)
    full_overall = statistics.mean(all_scores) * 100 if all_scores else 0
    category_scores = {
        _category_name(k): round(statistics.mean(v) * 100, 2)
        for k, v in cat_scores.items()
    }
    return {
        "overall_score": round(full_overall, 2),
        "full_5cat_overall": round(full_overall, 2),
        "protocol_4cat_overall": _protocol_4cat_overall(cat_scores),
        "category_scores": category_scores,
        "total_questions": len(all_scores),
        "avg_query_ms": round(statistics.mean(query_times) * 1000) if query_times else 0,
        "condition": {
            "cleaned": cleaned,
            "normalize_dates": bool(normalize_dates),
            "query_expansion": bool(use_query_expansion),
            "context_rerank": bool(use_context_rerank),
            "append_context_expansion": bool(use_append_context_expansion or use_gated_append_context_expansion),
            "gated_append_context_expansion": bool(use_gated_append_context_expansion),
        },
        "expand_query_fallback_count": expand_fallback_count,
        "expand_query_fallback_rate": round(expand_fallback_rate, 4),
        "details": results_log,
    }


def _save_results(all_scores, cat_scores, query_times, ingest_times, results_log, suffix=None, expand_fallback_count=0, expand_fallback_rate=0.0, normalize_dates=False, use_query_expansion=None, use_context_rerank=None, use_append_context_expansion=None, use_gated_append_context_expansion=None, cleaned=None):
    """Save incremental results."""
    output_path = result_output_path(normalize_dates, use_query_expansion, use_context_rerank, use_append_context_expansion, use_gated_append_context_expansion) if suffix is None else f"/tmp/locomo_results{suffix}.json"
    payload = build_results_payload(
        all_scores,
        cat_scores,
        query_times,
        results_log,
        normalize_dates=normalize_dates,
        use_query_expansion=use_query_expansion,
        use_context_rerank=use_context_rerank,
        use_append_context_expansion=use_append_context_expansion,
        use_gated_append_context_expansion=use_gated_append_context_expansion,
        expand_fallback_count=expand_fallback_count,
        expand_fallback_rate=expand_fallback_rate,
        cleaned=cleaned,
    )
    with open(output_path, "w") as f:
        json.dump(payload, f, indent=2)


def run_benchmark(
    data_path,
    max_convs=None,
    skip_cats=None,
    start_conv=0,
    normalize_dates=False,
    cleaned=None,
    max_questions=None,
):
    """Run LOCOMO benchmark, optionally capped by conversations/questions for canaries."""
    use_query_expansion = USE_QUERY_EXPANSION
    use_context_rerank = USE_CONTEXT_RERANK
    use_append_context_expansion = USE_APPEND_CONTEXT_EXPANSION
    use_gated_append_context_expansion = USE_GATED_APPEND_CONTEXT_EXPANSION
    validate_retrieval_modes(use_context_rerank, use_append_context_expansion, use_gated_append_context_expansion)
    expand_query.fail_count = 0
    with open(data_path) as f:
        data = json.load(f)

    if max_convs:
        data = data[:max_convs]

    skip_cats = skip_cats or set()

    print("=" * 70)
    print("  LOCOMO Benchmark — Memibrium CT Memory")
    if normalize_dates:
        print("  [DATE NORMALIZATION ENABLED]")
    print("=" * 70)

    # Get baseline state
    dashboard = mcp_get("dashboard")
    print(f"  Starting memories: {dashboard.get('total_memories', '?')}")
    print(f"  Conversations to process: {len(data)}")
    total_qs = sum(len(d['qa']) for d in data)
    raw_eval_qs = sum(1 for d in data for q in d['qa'] if not should_skip_category(q['category'], skip_cats))
    eval_qs = min(raw_eval_qs, max_questions) if max_questions else raw_eval_qs
    cap_note = f", question cap {max_questions}" if max_questions else ""
    print(f"  Total questions: {total_qs} ({eval_qs} evaluated{cap_note}, skipping cats {skip_cats})")
    print()

    all_scores = []
    cat_scores = defaultdict(list)
    cat_latencies = defaultdict(list)
    ingest_times = []
    query_times = []
    results_log = []

    # Resume support: if skipping conversations, seed metrics from existing partial output.
    output_path = result_output_path(
        normalize_dates=normalize_dates,
        use_query_expansion=use_query_expansion,
        use_context_rerank=use_context_rerank,
        use_append_context_expansion=use_append_context_expansion,
        use_gated_append_context_expansion=use_gated_append_context_expansion,
    )
    if start_conv > 0 and os.path.exists(output_path):
        with open(output_path) as f:
            prior = json.load(f)
        results_log = prior.get("details", [])
        for row in results_log:
            score = row.get("score", 0)
            cat = row.get("cat")
            q_ms = row.get("query_time_ms", 0) / 1000.0
            all_scores.append(score)
            cat_scores[cat].append(score)
            cat_latencies[cat].append(q_ms)
            query_times.append(q_ms)
        print(f"  Resumed prior partial: {len(results_log)} questions loaded from {output_path}")
        print()

    for ci, conv_data in enumerate(data):
        if max_questions and len(all_scores) >= max_questions:
            break
        sample_id = conv_data.get("sample_id", ci)
        qa_list = conv_data.get("qa", conv_data.get("qa_list", []))
        conv = conv_data.get("conversation", conv_data)

        print(f"  [{ci+1}/{len(data)}] Conv {sample_id}: {conv.get('speaker_a','?')} & {conv.get('speaker_b','?')}")

        if ci < start_conv:
            print(f"    Skipping (already processed)")
            continue

        # Phase 1: Ingest
        t0 = time.monotonic()
        n_turns, domain = ingest_conversation(conv, sample_id, normalize_dates=normalize_dates)
        ingest_time = time.monotonic() - t0
        ingest_times.append(ingest_time)
        print(f"    Ingested {n_turns} turns in {ingest_time:.1f}s")

        # Wait a bit for background processing
        time.sleep(2)

        # Phase 2: QA
        conv_scores = []
        for qi, qa in enumerate(qa_list):
            if max_questions and len(all_scores) >= max_questions:
                break
            orig_cat = qa["category"]
            cat = normalize_category(orig_cat)
            if should_skip_category(orig_cat, skip_cats):
                continue

            question = qa["question"]
            ground_truth = qa.get("answer", qa.get("adversarial_answer", ""))

            t0 = time.monotonic()
            predicted, n_mems = answer_question(question, domain)
            query_time = time.monotonic() - t0
            query_times.append(query_time)

            score = judge_answer(question, predicted, ground_truth)
            all_scores.append(score)
            cat_scores[cat].append(score)
            cat_latencies[cat].append(query_time)
            conv_scores.append(score)

            results_log.append({
                "conv": sample_id, "cat": cat, "question": question,
                "ground_truth": ground_truth, "predicted": predicted,
                "score": score, "query_time_ms": int(query_time * 1000),
                "n_memories": n_mems
            })

            if (qi + 1) % 20 == 0:
                running_acc = statistics.mean(conv_scores) * 100
                remaining_qs = len([q for q in qa_list if not should_skip_category(q['category'], skip_cats)])
                print(f"    ... {qi+1}/{remaining_qs} questions, running acc: {running_acc:.1f}%")

        conv_acc = statistics.mean(conv_scores) * 100 if conv_scores else 0
        print(f"    Conv accuracy: {conv_acc:.1f}% ({len(conv_scores)} questions)")
        print()

        # Incremental save
        questions_seen = len(all_scores)
        expand_fallback_count = getattr(expand_query, 'fail_count', 0)
        expand_fallback_rate = (expand_fallback_count / questions_seen) if questions_seen else 0.0
        _save_results(
            all_scores,
            cat_scores,
            query_times,
            ingest_times,
            results_log,
            normalize_dates=normalize_dates,
            use_query_expansion=use_query_expansion,
            use_context_rerank=use_context_rerank,
            use_append_context_expansion=use_append_context_expansion,
            use_gated_append_context_expansion=use_gated_append_context_expansion,
            expand_fallback_count=expand_fallback_count,
            expand_fallback_rate=expand_fallback_rate,
            cleaned=cleaned,
        )

    # Final report
    print("=" * 70)
    print("  RESULTS")
    print("=" * 70)

    overall = statistics.mean(all_scores) * 100
    expand_fallback_count = getattr(expand_query, 'fail_count', 0)
    expand_fallback_rate = (expand_fallback_count / len(all_scores)) if all_scores else 0.0
    print(f"\n  Overall accuracy (J-Score): {overall:.1f}%")
    print(f"  Query expansion fallback: {expand_fallback_count}/{len(all_scores)} ({expand_fallback_rate*100:.2f}%)")
    print()

    print(f"  {'Category':<15} {'Score':>8} {'Count':>7} {'Avg Latency':>12}")
    print(f"  {'-'*15} {'-'*8} {'-'*7} {'-'*12}")
    for cat in sorted(cat_scores.keys()):
        name = CAT_NAMES.get(cat, f"cat-{cat}")
        acc = statistics.mean(cat_scores[cat]) * 100
        count = len(cat_scores[cat])
        lat = statistics.mean(cat_latencies[cat]) * 1000
        print(f"  {name:<15} {acc:>7.1f}% {count:>7} {lat:>10.0f}ms")

    print(f"\n  Ingest: {statistics.mean(ingest_times):.1f}s avg per conversation")
    print(f"  Query:  {statistics.mean(query_times)*1000:.0f}ms avg per question")
    print(f"  Total:  {sum(ingest_times) + sum(query_times):.0f}s")

    # Comparison
    print()
    print("=" * 70)
    print("  COMPARISON (LOCOMO J-Score)")
    print("=" * 70)
    comparisons = [
        ("Remembra", 94.2),
        ("MemMachine", 84.9),
        ("Mem0 (new algo)", 91.6),
        ("Zep", 80.3),
        ("Memobase", 75.8),
        ("Mem0 (original)", 66.9),
        ("LangMem", 58.1),
        (f">>> MEMIBRIUM", overall),
    ]
    comparisons.sort(key=lambda x: -x[1])
    for name, score in comparisons:
        marker = " <<<" if "MEMIBRIUM" in name else ""
        print(f"  {name:<25} {score:>6.1f}%{marker}")

    # Save detailed results
    output_path = result_output_path(
        normalize_dates=normalize_dates,
        use_query_expansion=use_query_expansion,
        use_context_rerank=use_context_rerank,
        use_append_context_expansion=use_append_context_expansion,
        use_gated_append_context_expansion=use_gated_append_context_expansion,
    )
    payload = build_results_payload(
        all_scores,
        cat_scores,
        query_times,
        results_log,
        normalize_dates=normalize_dates,
        use_query_expansion=use_query_expansion,
        use_context_rerank=use_context_rerank,
        use_append_context_expansion=use_append_context_expansion,
        use_gated_append_context_expansion=use_gated_append_context_expansion,
        expand_fallback_count=expand_fallback_count,
        expand_fallback_rate=expand_fallback_rate,
        cleaned=cleaned,
    )
    with open(output_path, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"\n  Detailed results saved to {output_path}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-convs", type=int, default=None, help="Limit conversations (for testing)")
    parser.add_argument("--max-questions", type=int, default=None, help="Limit evaluated questions (for smoke tests)")
    parser.add_argument("--skip-adversarial", action="store_true", help="Skip category 5 (adversarial)")
    parser.add_argument("--start-conv", type=int, default=0, help="Skip first N conversations (already ingested)")
    parser.add_argument("--cleaned", action="store_true", help="Use cleaned dataset (/tmp/locomo10_cleaned.json)")
    parser.add_argument("--normalize-dates", action="store_true", help="Enable ingest-time date normalization")
    parser.add_argument("--query-expansion", action="store_true", help="Enable opt-in recall-time query expansion")
    parser.add_argument("--context-rerank", action="store_true", help="Enable opt-in lexical reranking before answer synthesis")
    parser.add_argument("--append-context-expansion", action="store_true", help="Enable opt-in append-only extra context after the original answer context")
    parser.add_argument("--gated-append-context-expansion", action="store_true", help="Enable opt-in gated append-only context expansion")
    args = parser.parse_args()

    if args.max_questions is not None and args.max_questions <= 0:
        parser.error("--max-questions must be a positive integer")

    if args.query_expansion:
        USE_QUERY_EXPANSION = True
    if args.context_rerank:
        USE_CONTEXT_RERANK = True
    if args.append_context_expansion:
        USE_APPEND_CONTEXT_EXPANSION = True
    if args.gated_append_context_expansion:
        USE_GATED_APPEND_CONTEXT_EXPANSION = True
    validate_retrieval_modes()

    skip = {5} if args.skip_adversarial else set()
    data_path = "/tmp/locomo10_cleaned.json" if args.cleaned else "/tmp/locomo/data/locomo10.json"
    run_preflight_checks()
    run_benchmark(
        data_path,
        max_convs=args.max_convs,
        max_questions=args.max_questions,
        skip_cats=skip,
        start_conv=args.start_conv,
        normalize_dates=args.normalize_dates,
        cleaned=args.cleaned,
    )
