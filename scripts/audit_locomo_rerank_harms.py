#!/usr/bin/env python3
"""Audit LOCOMO query-expansion -> prefix-rerank harmed cases.

This script is deliberately diagnostic. It does not call the answer or judge LLM.
It re-ingests the target conversation, replays retrieval for harmed questions, and
compares the original candidate order against prefix-preserving lexical rerank.

Outputs:
- docs/eval/results/locomo_prefix_rerank_harm_audit_YYYY-MM-DD.json
- docs/eval/results/locomo_prefix_rerank_harm_audit_YYYY-MM-DD.md
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import importlib.util
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BENCH_PATH = ROOT / "benchmark_scripts" / "locomo_bench_v2.py"
RESULTS_DIR = ROOT / "docs" / "eval" / "results"
PRIOR_QUERY_EXPANSION = RESULTS_DIR / "locomo_conv26_query_expansion_2026-04-24.json"
PREFIX_RERANK = RESULTS_DIR / "locomo_conv26_query_expansion_prefix_rerank_2026-04-26.json"
DEFAULT_DATA = Path("/tmp/locomo10_cleaned.json")

ANSWER_CONTEXT_TOP_K = 15
RERANK_RECALL_TOP_K = 20
PRESERVE_PREFIX_K = 2


def load_bench_module():
    spec = importlib.util.spec_from_file_location("locomo_bench_v2_audit", BENCH_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def run_cmd(cmd: list[str], timeout: int = 120, input_text: str | None = None) -> str:
    res = subprocess.run(
        cmd,
        input=input_text,
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    if res.returncode != 0:
        rendered = " ".join(cmd)
        raise RuntimeError(f"command failed ({res.returncode}): {rendered}\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}")
    return res.stdout.strip()


def clean_locomo_domains() -> None:
    sql = r"""
BEGIN;
DELETE FROM temporal_expressions WHERE memory_id IN (SELECT id FROM memories WHERE domain LIKE 'locomo-%');
DELETE FROM memory_snapshots WHERE memory_id IN (SELECT id FROM memories WHERE domain LIKE 'locomo-%');
DELETE FROM user_feedback WHERE memory_id IN (SELECT id FROM memories WHERE domain LIKE 'locomo-%');
DELETE FROM contradictions WHERE memory_a_id IN (SELECT id FROM memories WHERE domain LIKE 'locomo-%') OR memory_b_id IN (SELECT id FROM memories WHERE domain LIKE 'locomo-%');
DELETE FROM memory_edges WHERE source_id IN (SELECT id FROM memories WHERE domain LIKE 'locomo-%') OR target_id IN (SELECT id FROM memories WHERE domain LIKE 'locomo-%');
DELETE FROM memories WHERE domain LIKE 'locomo-%';
COMMIT;
"""
    run_cmd(["docker", "exec", "-i", "memibrium-ruvector-db", "psql", "-U", "memory", "-d", "memory"], input_text=sql, timeout=120)


def locomo_count() -> int:
    out = run_cmd([
        "docker",
        "exec",
        "-i",
        "memibrium-ruvector-db",
        "psql",
        "-U",
        "memory",
        "-d",
        "memory",
        "-t",
        "-A",
        "-c",
        "SELECT count(*) FROM memories WHERE domain LIKE 'locomo-%';",
    ], timeout=30)
    return int(out.strip() or "0")


def mcp_post(tool: str, payload: dict[str, Any], retries: int = 3) -> Any:
    import requests

    url = f"http://localhost:9999/mcp/{tool}"
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            r = requests.post(url, json=payload, timeout=60)
            r.raise_for_status()
            return r.json()
        except Exception as exc:  # noqa: BLE001 - diagnostic retry
            last_exc = exc
            time.sleep(1 + attempt)
    raise RuntimeError(f"MCP POST failed for {tool}: {last_exc}")


def key(row: dict[str, Any]) -> tuple[str, str, str]:
    return (str(row.get("conv")), str(row.get("cat")), str(row.get("question")))


def load_harmed_cases() -> list[dict[str, Any]]:
    with PRIOR_QUERY_EXPANSION.open() as f:
        prior = json.load(f)
    with PREFIX_RERANK.open() as f:
        prefix = json.load(f)
    a = {key(r): r for r in prior["details"]}
    b = {key(r): r for r in prefix["details"]}
    harmed = []
    for k in sorted(set(a) & set(b), key=lambda x: (x[1], x[2])):
        before = a[k]
        after = b[k]
        if float(before.get("score", 0)) == 1.0 and float(after.get("score", 0)) < 1.0:
            harmed.append({"key": k, "prior": before, "prefix": after})
    return harmed


def load_conv(data_path: Path, sample_id: str) -> dict[str, Any]:
    with data_path.open() as f:
        data = json.load(f)
    for row in data:
        if row.get("sample_id") == sample_id:
            return row.get("conversation", row)
    raise KeyError(f"sample_id not found in {data_path}: {sample_id}")


def normalize_memory(memory: dict[str, Any], index: int) -> dict[str, Any]:
    refs = memory.get("refs") or {}
    if isinstance(refs, str):
        try:
            refs = json.loads(refs)
        except Exception:  # noqa: BLE001
            refs = {}
    content = memory.get("content", "") or ""
    return {
        "index": index,
        "id": memory.get("id"),
        "score": memory.get("score", memory.get("combined_score", memory.get("rrf_score"))),
        "created_at": memory.get("created_at"),
        "refs": refs,
        "content": content,
        "snippet": content[:500].replace("\n", " "),
    }


def expand_question(bench: Any, question: str) -> list[str]:
    # Use the benchmark expansion function to mirror the canaries. It fails open.
    queries = bench.expand_query(question)
    out = []
    seen = set()
    for q in queries:
        if isinstance(q, str) and q not in seen:
            out.append(q)
            seen.add(q)
    return out or [question]


def retrieve_candidates(question: str, domain: str, bench: Any) -> tuple[list[str], list[dict[str, Any]], list[dict[str, Any]]]:
    queries = expand_question(bench, question)
    seen: dict[str, dict[str, Any]] = {}
    recall_stats = []
    for query in queries:
        result = mcp_post("recall", {"query": query, "top_k": RERANK_RECALL_TOP_K, "domain": domain})
        recalled = result if isinstance(result, list) else result.get("results", result.get("memories", []))
        recall_stats.append({"query": query, "returned": len(recalled)})
        for memory in recalled:
            mid = memory.get("id") or f"no-id::{memory.get('content', '')}::{len(seen)}"
            if mid not in seen:
                seen[mid] = memory
    candidates = list(seen.values())
    return queries, candidates, recall_stats


def token_set(text: str, bench: Any) -> set[str]:
    return set(bench._tokenize_for_rerank(text))


def evidence_terms(question: str, answer: str, bench: Any) -> set[str]:
    stop = {"unknown", "know", "answer", "briefly", "available", "information", "specified"}
    return {t for t in (token_set(question, bench) | token_set(answer, bench)) if t not in stop}


def classify_case(
    case: dict[str, Any],
    original_context: list[dict[str, Any]],
    reranked_context: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    bench: Any,
) -> tuple[str, list[str], dict[str, Any]]:
    question = case["prior"]["question"]
    gt = case["prior"].get("ground_truth", "")
    prior_pred = case["prior"].get("predicted", "")
    prefix_pred = case["prefix"].get("predicted", "")
    cat = case["prior"].get("cat")

    original_ids = [m.get("id") for m in original_context]
    reranked_ids = [m.get("id") for m in reranked_context]
    candidate_ids = [m.get("id") for m in candidates]
    lost_ids = [mid for mid in original_ids if mid not in reranked_ids]
    gained_ids = [mid for mid in reranked_ids if mid not in original_ids]

    terms = evidence_terms(question, str(gt) + " " + str(prior_pred), bench)

    def overlap(m: dict[str, Any]) -> int:
        return len(token_set(m.get("content", ""), bench) & terms)

    original_overlap = [(m.get("id"), overlap(m), m.get("content", "")[:160]) for m in original_context]
    reranked_overlap = [(m.get("id"), overlap(m), m.get("content", "")[:160]) for m in reranked_context]
    lost_overlap = [item for item in original_overlap if item[0] in lost_ids]
    top_original_lost = original_ids[:PRESERVE_PREFIX_K] != reranked_ids[:PRESERVE_PREFIX_K]

    reasons = []
    if lost_ids:
        reasons.append("context_changed_by_topk_fill")
    if any(score >= 2 for _mid, score, _snippet in lost_overlap):
        reasons.append("candidate_evidence_dropped")
    if str(prefix_pred).lower().strip().startswith("i don't know") or "don't know" in str(prefix_pred).lower():
        reasons.append("answer_became_idk")
    if cat in {"unanswerable", "multi-hop"}:
        reasons.append("sensitive_category")
    if not lost_ids and case["prefix"].get("score") != case["prior"].get("score"):
        reasons.append("answer_model_or_retrieval_variance")
    if top_original_lost:
        reasons.append("prefix_not_preserved_unexpected")

    # Primary class. Keep this deterministic and conservative.
    if "prefix_not_preserved_unexpected" in reasons:
        primary = "audit_invariant_failure"
    elif "answer_became_idk" in reasons and lost_ids:
        primary = "evidence_loss_or_demoted_to_idk"
    elif "candidate_evidence_dropped" in reasons:
        primary = "evidence_dropped_by_context_budget"
    elif cat == "unanswerable" and lost_ids:
        primary = "negative_or_specific_evidence_changed"
    elif cat == "multi-hop" and lost_ids:
        primary = "multi_hop_context_changed"
    elif lost_ids:
        primary = "context_changed_unclear"
    else:
        primary = "answer_variance_or_equivalent_context"

    diagnostics = {
        "candidate_count": len(candidates),
        "original_context_count": len(original_context),
        "reranked_context_count": len(reranked_context),
        "lost_from_original_context_count": len(lost_ids),
        "gained_in_reranked_context_count": len(gained_ids),
        "lost_ids": lost_ids,
        "gained_ids": gained_ids,
        "top_prefix_preserved": not top_original_lost,
        "evidence_terms": sorted(terms)[:50],
        "original_overlap": original_overlap,
        "reranked_overlap": reranked_overlap,
        "lost_overlap": lost_overlap,
        "candidate_ids_first_20": candidate_ids[:20],
    }
    return primary, reasons, diagnostics


def make_md(report: dict[str, Any]) -> str:
    lines = []
    lines.append("# LOCOMO Prefix-Rerank Harm Audit")
    lines.append("")
    lines.append(f"Generated: `{report['generated_at']}`")
    lines.append("")
    lines.append("## Scope")
    lines.append("")
    lines.append("Audited paired cases where prior query expansion scored `1.0` and prefix-preserving rerank scored `<1.0`.")
    lines.append("")
    lines.append(f"Harmed cases audited: `{report['summary']['harmed_cases']}`")
    lines.append(f"LOCOMO memories ingested for replay: `{report['summary']['locomo_memory_count_after_ingest']}`")
    lines.append(f"Expansion fallback during audit: `{report['summary']['expand_fallback_count']}`")
    lines.append("")
    lines.append("## Primary mechanism counts")
    lines.append("")
    lines.append("| Mechanism | Count |")
    lines.append("|---|---:|")
    for k, v in report["summary"]["primary_mechanism_counts"].items():
        lines.append(f"| {k} | {v} |")
    lines.append("")
    lines.append("## Category counts")
    lines.append("")
    lines.append("| Category | Count |")
    lines.append("|---|---:|")
    for k, v in report["summary"]["category_counts"].items():
        lines.append(f"| {k} | {v} |")
    lines.append("")
    lines.append("## Key aggregate diagnostics")
    lines.append("")
    lines.append(f"- Cases with any original context item dropped by prefix-rerank top-k fill: `{report['summary']['cases_with_context_drops']}`")
    lines.append(f"- Cases where answer became I-don't-know: `{report['summary']['cases_answer_became_idk']}`")
    lines.append(f"- Cases with identical context IDs but worse answer: `{report['summary']['cases_equivalent_context']}`")
    lines.append(f"- Prefix preservation invariant failures: `{report['summary']['prefix_invariant_failures']}`")
    lines.append("")
    lines.append("## Per-case audit")
    lines.append("")
    for item in report["cases"]:
        prior = item["prior"]
        prefix = item["prefix"]
        diag = item["diagnostics"]
        lines.append(f"### {item['case_index']}. {prior['cat']} — {item['primary_mechanism']}")
        lines.append("")
        lines.append(f"Question: {prior['question']}")
        lines.append("")
        lines.append(f"Ground truth: {prior.get('ground_truth')}")
        lines.append("")
        lines.append(f"Prior correct answer: {prior.get('predicted')}")
        lines.append("")
        lines.append(f"Prefix-rerank answer (score {prefix.get('score')}): {prefix.get('predicted')}")
        lines.append("")
        lines.append(f"Reasons: `{', '.join(item['reasons'])}`")
        lines.append("")
        lines.append(f"Dropped original-context items: `{diag['lost_from_original_context_count']}`; gained reranked items: `{diag['gained_in_reranked_context_count']}`; candidate count: `{diag['candidate_count']}`")
        if diag["lost_overlap"]:
            lines.append("")
            lines.append("Dropped items with lexical overlap:")
            for mid, score, snippet in diag["lost_overlap"][:5]:
                lines.append(f"- overlap={score} id={mid}: {snippet}")
        lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append(report["interpretation"])
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=dt.date.today().isoformat())
    parser.add_argument("--data", default=str(DEFAULT_DATA))
    parser.add_argument("--keep-db", action="store_true", help="Do not clean locomo-% domains after audit")
    args = parser.parse_args()

    data_path = Path(args.data)
    if not data_path.exists():
        raise FileNotFoundError(data_path)

    health = run_cmd(["curl", "-s", "http://localhost:9999/health"], timeout=30)
    if '"ok"' not in health:
        raise RuntimeError(f"Memibrium health check failed: {health}")

    bench = load_bench_module()
    bench.expand_query.fail_count = 0

    harmed = load_harmed_cases()
    if not harmed:
        raise RuntimeError("No harmed cases found")

    sample_ids = sorted({case["prior"]["conv"] for case in harmed})
    if sample_ids != ["conv-26"]:
        raise RuntimeError(f"This audit currently expects only conv-26, got {sample_ids}")

    print("Cleaning LOCOMO domains before replay...")
    clean_locomo_domains()
    if locomo_count() != 0:
        raise RuntimeError("LOCOMO cleanup failed")

    print("Ingesting conv-26 with cleaned + normalized settings...")
    conv = load_conv(data_path, "conv-26")
    n_turns, domain = bench.ingest_conversation(conv, "conv-26", normalize_dates=True)
    time.sleep(2)
    count_after_ingest = locomo_count()
    print(f"Ingested {n_turns} turns into {domain}; DB locomo memories={count_after_ingest}")

    cases = []
    for idx, case in enumerate(harmed, start=1):
        question = case["prior"]["question"]
        print(f"[{idx}/{len(harmed)}] {case['prior']['cat']}: {question[:100]}")
        queries, candidates, recall_stats = retrieve_candidates(question, domain, bench)
        original_context = candidates[:ANSWER_CONTEXT_TOP_K]
        reranked_context = bench.rerank_memories_for_question(
            question,
            candidates,
            top_k=ANSWER_CONTEXT_TOP_K,
            preserve_prefix_k=PRESERVE_PREFIX_K,
        )
        primary, reasons, diagnostics = classify_case(case, original_context, reranked_context, candidates, bench)
        cases.append(
            {
                "case_index": idx,
                "key": list(case["key"]),
                "primary_mechanism": primary,
                "reasons": reasons,
                "queries": queries,
                "recall_stats": recall_stats,
                "prior": case["prior"],
                "prefix": case["prefix"],
                "diagnostics": diagnostics,
                "original_context": [normalize_memory(m, i) for i, m in enumerate(original_context, start=1)],
                "reranked_context": [normalize_memory(m, i) for i, m in enumerate(reranked_context, start=1)],
            }
        )

    primary_counts = collections.Counter(item["primary_mechanism"] for item in cases)
    cat_counts = collections.Counter(item["prior"]["cat"] for item in cases)
    cases_with_context_drops = sum(1 for item in cases if item["diagnostics"]["lost_from_original_context_count"] > 0)
    cases_answer_became_idk = sum(1 for item in cases if "answer_became_idk" in item["reasons"])
    cases_equivalent_context = sum(1 for item in cases if item["diagnostics"]["lost_from_original_context_count"] == 0 and item["diagnostics"]["gained_in_reranked_context_count"] == 0)
    prefix_invariant_failures = sum(1 for item in cases if not item["diagnostics"]["top_prefix_preserved"])

    # Basic interpretation from diagnostics.
    if cases_with_context_drops >= len(cases) * 0.75:
        interpretation = (
            "Most harms coincide with context-set changes from lexical fill/top-k budgeting. "
            "The reranker is not merely reordering equivalent evidence; it changes which memories reach the answer model. "
            "Do not broaden lexical rerank. Next policy should either disable rerank for sensitive categories/query types or treat lexical scoring only as a diagnostic/diversity feature while preserving a much larger original-order context."
        )
    elif cases_equivalent_context >= len(cases) * 0.5:
        interpretation = (
            "Most harms occurred with equivalent context IDs, suggesting answer-model variance or prompt sensitivity rather than retrieval ordering. "
            "Rerank policy changes are unlikely to help until answer stability is improved."
        )
    else:
        interpretation = (
            "Harms are mixed. Inspect the per-case dropped/gained memories before choosing another rerank policy."
        )

    expand_fallback_count = getattr(bench.expand_query, "fail_count", 0)
    if expand_fallback_count:
        raise RuntimeError(
            f"Audit contaminated: expand_query fell back {expand_fallback_count} times. "
            "Load benchmark env first, e.g. `set -a && source .env && set +a`, and rerun."
        )

    report = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "inputs": {
            "prior_query_expansion": str(PRIOR_QUERY_EXPANSION),
            "prefix_rerank": str(PREFIX_RERANK),
            "data": str(data_path),
        },
        "settings": {
            "answer_context_top_k": ANSWER_CONTEXT_TOP_K,
            "rerank_recall_top_k": RERANK_RECALL_TOP_K,
            "preserve_prefix_k": PRESERVE_PREFIX_K,
        },
        "summary": {
            "harmed_cases": len(cases),
            "category_counts": dict(sorted(cat_counts.items())),
            "primary_mechanism_counts": dict(primary_counts.most_common()),
            "cases_with_context_drops": cases_with_context_drops,
            "cases_answer_became_idk": cases_answer_became_idk,
            "cases_equivalent_context": cases_equivalent_context,
            "prefix_invariant_failures": prefix_invariant_failures,
            "locomo_memory_count_after_ingest": count_after_ingest,
            "expand_fallback_count": getattr(bench.expand_query, "fail_count", 0),
        },
        "interpretation": interpretation,
        "cases": cases,
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    json_path = RESULTS_DIR / f"locomo_prefix_rerank_harm_audit_{args.date}.json"
    md_path = RESULTS_DIR / f"locomo_prefix_rerank_harm_audit_{args.date}.md"
    json_path.write_text(json.dumps(report, indent=2))
    md_path.write_text(make_md(report))
    print(f"Saved {json_path}")
    print(f"Saved {md_path}")

    if not args.keep_db:
        print("Cleaning LOCOMO domains after audit...")
        clean_locomo_domains()
        print(f"Post-cleanup locomo memories={locomo_count()}")

    print(json.dumps(report["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
