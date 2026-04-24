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

MCP = "http://localhost:9999/mcp"
# Use the same Azure Foundry endpoint as Memibrium for judging
AZURE_CHAT_ENDPOINT = "https://sector-7.services.ai.azure.com/models"
AZURE_CHAT_KEY = os.environ.get("AZURE_CHAT_API_KEY", "")
JUDGE_MODEL = "gpt-4.1-mini"
ANSWER_MODEL = "gpt-4.1-mini"

# Categories
CAT_NAMES = {1: "multi-hop", 2: "temporal", 3: "open-domain", 4: "single-hop", 5: "adversarial"}

client = httpx.Client(timeout=120)


def mcp_post(tool, payload, retries=3):
    for attempt in range(retries):
        try:
            r = client.post(f"{MCP}/{tool}", json=payload)
            if r.status_code == 200 and r.text.strip():
                return r.json()
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
                continue
            return [] if tool == "recall" else {}
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                print(f"    [WARN] {tool} failed after {retries} attempts: {e}")
                return [] if tool == "recall" else {}


def mcp_get(tool):
    r = client.get(f"{MCP}/{tool}")
    return r.json()


def llm_call(messages, model=ANSWER_MODEL, max_tokens=200, retries=3):
    """Call Azure Foundry LLM with retry."""
    for attempt in range(retries):
        try:
            r = client.post(
                f"{AZURE_CHAT_ENDPOINT}/chat/completions",
                headers={"api-key": AZURE_CHAT_KEY, "Content-Type": "application/json"},
                json={"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": 0},
            )
            data = r.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                return "I don't know"


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


def answer_question(question, domain):
    """Recall from Memibrium and generate answer."""
    recall_result = mcp_post("recall", {"query": question, "top_k": 10, "domain": domain})
    if isinstance(recall_result, list):
        memories = recall_result
    else:
        memories = recall_result.get("results", recall_result.get("memories", []))

    if not memories:
        context = "No relevant memories found."
    else:
        chronology_cues = any(token in question.lower() for token in ["before", "after", "earlier", "later", "first", "last", "then", "when"])
        context_lines = []
        for m in memories[:10]:
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

    system_prompt = "You are answering questions about past conversations. Use ONLY the provided context. Give a brief, direct answer. If the information is not available, say 'I don't know'."
    if any(token in question.lower() for token in ["before", "after", "earlier", "later", "first", "last", "then", "when"]):
        system_prompt += " Pay close attention to chronology, timestamps, session order, and turn order."

    answer = llm_call([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Context (retrieved memories):\n{context}\n\nQuestion: {question}\n\nAnswer briefly:"}
    ])

    return answer, len(memories)


def judge_answer(question, predicted, ground_truth):
    """LLM judge: score predicted vs ground truth. Returns 0, 0.5, or 1."""
    response = llm_call([
        {"role": "system", "content": "You are a strict judge evaluating if a predicted answer matches the ground truth answer. Score:\n1 = correct (matches ground truth meaning)\n0.5 = partially correct (some relevant info but incomplete or slightly wrong)\n0 = wrong (incorrect or irrelevant)\n\nRespond with ONLY the number: 0, 0.5, or 1"},
        {"role": "user", "content": f"Question: {question}\nGround truth: {ground_truth}\nPredicted: {predicted}\n\nScore:"}
    ], max_tokens=5)

    # Parse score
    try:
        score = float(response.strip())
        if score not in (0, 0.5, 1):
            score = 0
    except:
        score = 0
    return score


def _save_results(all_scores, cat_scores, query_times, ingest_times, results_log, suffix=""):
    """Save incremental results."""
    output_path = f"/tmp/locomo_results{suffix}.json"
    overall = statistics.mean(all_scores) * 100 if all_scores else 0
    with open(output_path, "w") as f:
        json.dump({
            "overall_score": round(overall, 2),
            "category_scores": {CAT_NAMES.get(k, f"cat-{k}"): round(statistics.mean(v)*100, 2) for k, v in cat_scores.items()},
            "total_questions": len(all_scores),
            "avg_query_ms": round(statistics.mean(query_times)*1000) if query_times else 0,
            "details": results_log
        }, f, indent=2)


def run_benchmark(data_path, max_convs=None, skip_cats=None, start_conv=0, normalize_dates=False):
    """Run full LOCOMO benchmark."""
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
    eval_qs = sum(1 for d in data for q in d['qa'] if q['category'] not in skip_cats)
    print(f"  Total questions: {total_qs} ({eval_qs} evaluated, skipping cats {skip_cats})")
    print()

    all_scores = []
    cat_scores = defaultdict(list)
    cat_latencies = defaultdict(list)
    ingest_times = []
    query_times = []
    results_log = []

    for ci, conv_data in enumerate(data):
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
            cat = qa["category"]
            # Normalize LOCOMO numeric categories to strings
            if isinstance(cat, int):
                cat_map = {1: "single-hop", 2: "temporal", 3: "multi-hop", 4: "unanswerable"}
                cat = cat_map.get(cat, str(cat))
            if cat in skip_cats:
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
                print(f"    ... {qi+1}/{len([q for q in qa_list if q['category'] not in skip_cats])} questions, running acc: {running_acc:.1f}%")

        conv_acc = statistics.mean(conv_scores) * 100 if conv_scores else 0
        print(f"    Conv accuracy: {conv_acc:.1f}% ({len(conv_scores)} questions)")
        print()

        # Incremental save
        _save_results(all_scores, cat_scores, query_times, ingest_times, results_log, suffix="_normalized" if normalize_dates else "")

    # Final report
    print("=" * 70)
    print("  RESULTS")
    print("=" * 70)

    overall = statistics.mean(all_scores) * 100
    print(f"\n  Overall accuracy (J-Score): {overall:.1f}%")
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
    output_path = f"/tmp/locomo_results{'_normalized' if normalize_dates else ''}.json"
    with open(output_path, "w") as f:
        json.dump({
            "overall_score": round(overall, 2),
            "category_scores": {CAT_NAMES.get(k, f"cat-{k}"): round(statistics.mean(v)*100, 2) for k, v in cat_scores.items()},
            "total_questions": len(all_scores),
            "avg_query_ms": round(statistics.mean(query_times)*1000),
            "details": results_log
        }, f, indent=2)
    print(f"\n  Detailed results saved to {output_path}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-convs", type=int, default=None, help="Limit conversations (for testing)")
    parser.add_argument("--skip-adversarial", action="store_true", help="Skip category 5 (adversarial)")
    parser.add_argument("--start-conv", type=int, default=0, help="Skip first N conversations (already ingested)")
    parser.add_argument("--cleaned", action="store_true", help="Use cleaned dataset (/tmp/locomo10_cleaned.json)")
    parser.add_argument("--normalize-dates", action="store_true", help="Enable ingest-time date normalization")
    args = parser.parse_args()

    skip = {5} if args.skip_adversarial else set()
    data_path = "/tmp/locomo10_cleaned.json" if args.cleaned else "/tmp/locomo/data/locomo10.json"
    run_benchmark(data_path, max_convs=args.max_convs, skip_cats=skip, start_conv=args.start_conv, normalize_dates=args.normalize_dates)
