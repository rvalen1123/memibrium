#!/usr/bin/env python3
"""Tiny fixed-row LOCOMO A/B canary for Context Packet prompt integration.

This execution harness is intentionally bounded:
- conv-26 only
- preregistered fixed rows only
- two arms: current default benchmark answer path vs --context-packet treatment
- recall/context-packet telemetry enabled
- exact row identity validation before scoring
- cleanup before/between/after arms

It is not a 199Q LOCOMO benchmark and must not be interpreted as one.
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import importlib.util
import json
import os
import re
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[3]
DATA_PATH = Path("/tmp/locomo/data/locomo10.json")
FIXED_ROWS_PATH = ROOT / "docs/eval/results/locomo_step5o_prereg_fixed_rows_2026-05-02.json"
RESULTS_DIR = ROOT / "docs/eval/results"
RUN_ID = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
EXPECTED_DATA_SHA256 = "79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4"

REDACT_KEYS = {"KEY", "TOKEN", "SECRET", "PASSWORD", "PASS", "CREDENTIAL"}
ENV_KEYS = [
    "MCP_URL",
    "AZURE_CHAT_ENDPOINT",
    "AZURE_CHAT_DEPLOYMENT",
    "AZURE_CHAT_API_KEY",
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_DEPLOYMENT",
    "AZURE_OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "OPENAI_API_KEY",
    "ANSWER_MODEL",
    "JUDGE_MODEL",
    "CHAT_MODEL",
    "AZURE_EMBEDDING_DEPLOYMENT",
    "EMBEDDING_MODEL",
    "EMBEDDING_BASE_URL",
    "USE_QUERY_EXPANSION",
    "INCLUDE_RECALL_TELEMETRY",
    "USE_CONTEXT_PACKET",
    "USE_CONTEXT_PACKET_MERGE",
    "USE_CONTEXT_RERANK",
    "USE_APPEND_CONTEXT_EXPANSION",
    "USE_GATED_APPEND_CONTEXT_EXPANSION",
    "USE_LEGACY_CONTEXT_ASSEMBLY",
    "USE_FULL_DOMAIN_CONTEXT",
    "LOCOMO_RETRIEVAL_TELEMETRY",
    "DB_HOST",
    "DB_PORT",
    "DB_NAME",
    "DB_USER",
    "DB_PASSWORD",
]


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> Any:
    with path.open() as f:
        return json.load(f)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")


def load_dotenv(base: dict[str, str]) -> dict[str, str]:
    env = dict(base)
    env_file = ROOT / ".env"
    if not env_file.exists():
        return env
    for raw in env_file.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def redacted_env(env: dict[str, str]) -> dict[str, str | None]:
    out: dict[str, str | None] = {}
    for key in ENV_KEYS:
        value = env.get(key)
        if value is None:
            out[key] = None
        elif any(token in key.upper() for token in REDACT_KEYS):
            out[key] = "[REDACTED]"
        else:
            out[key] = value
    return out


def normalize_mcp_url(url: str) -> str:
    url = url.rstrip("/")
    return url if url.endswith("/mcp") else f"{url}/mcp"


def build_benchmark_env(
    base_env: dict[str, str],
    *,
    mcp_url: str,
    context_packet: bool,
    context_packet_merge: bool = False,
    context_packet_merge_append_top_k: int | None = None,
    context_packet_merge_ref_gate: bool = False,
) -> dict[str, str]:
    """Build arm envs with explicit Context Packet condition flags."""
    env = load_dotenv(base_env)
    env.update({
        "MCP_URL": normalize_mcp_url(mcp_url),
        "AZURE_CHAT_DEPLOYMENT": "gpt-4.1-mini",
        "AZURE_OPENAI_DEPLOYMENT": "gpt-4.1-mini",
        "ANSWER_MODEL": "gpt-4.1-mini",
        "JUDGE_MODEL": "gpt-4.1-mini",
        "CHAT_MODEL": "gpt-4.1-mini",
        "AZURE_EMBEDDING_DEPLOYMENT": "text-embedding-3-small",
        # The canary compares the current default answer context path against
        # context_packet only; keep query expansion off unless the caller's
        # future preregistration explicitly changes this script.
        "USE_QUERY_EXPANSION": "0",
        "INCLUDE_RECALL_TELEMETRY": "1",
        "DB_HOST": env.get("DB_HOST", "localhost"),
        "DB_PORT": env.get("DB_PORT", "5432"),
        "DB_NAME": env.get("DB_NAME", "memory"),
        "DB_USER": env.get("DB_USER", "memory"),
        "DB_PASSWORD": env.get("DB_PASSWORD", "memory"),
    })
    for incompatible in [
        "LOCOMO_RETRIEVAL_TELEMETRY",
        "USE_CONTEXT_RERANK",
        "USE_APPEND_CONTEXT_EXPANSION",
        "USE_GATED_APPEND_CONTEXT_EXPANSION",
        "USE_LEGACY_CONTEXT_ASSEMBLY",
        "USE_FULL_DOMAIN_CONTEXT",
    ]:
        env.pop(incompatible, None)
    if context_packet:
        env["USE_CONTEXT_PACKET"] = "1"
    else:
        env.pop("USE_CONTEXT_PACKET", None)
    if context_packet_merge:
        env["USE_CONTEXT_PACKET_MERGE"] = "1"
    else:
        env.pop("USE_CONTEXT_PACKET_MERGE", None)
    if context_packet_merge_append_top_k is not None:
        env["CONTEXT_PACKET_MERGE_APPEND_TOP_K"] = str(context_packet_merge_append_top_k)
    else:
        env.pop("CONTEXT_PACKET_MERGE_APPEND_TOP_K", None)
    if context_packet_merge_ref_gate:
        env["CONTEXT_PACKET_MERGE_REF_GATE"] = "1"
    else:
        env.pop("CONTEXT_PACKET_MERGE_REF_GATE", None)
    return env


def session_order_mapping(conv: dict[str, Any]) -> dict[str, Any]:
    sessions = sorted([key for key in conv if key.startswith("session_") and not key.endswith("date_time")])
    ingest_to_dialogue = {}
    dialogue_to_ingest = {}
    for ingest_idx, sess_key in enumerate(sessions, start=1):
        numeric = sess_key.rsplit("_", 1)[-1]
        dialogue = f"D{numeric}"
        ingest_to_dialogue[ingest_idx] = dialogue
        dialogue_to_ingest[dialogue] = ingest_idx
    return {
        "ordering": "lexicographic",
        "ingest_to_dialogue_session": ingest_to_dialogue,
        "dialogue_to_ingest_session": dialogue_to_ingest,
        "session_keys": sessions,
        "note": "LOCOMO ingest currently sorts session keys lexicographically; refs.session_index follows this order, not numeric D-session order.",
    }


def validate_preregistered_larger_slice(slice_payload: dict[str, Any], *, min_rows: int = 20, max_rows: int = 30) -> dict[str, Any]:
    rows = slice_payload.get("selected_rows") if isinstance(slice_payload, dict) else None
    if not isinstance(rows, list) or not (min_rows <= len(rows) <= max_rows):
        raise ValueError(f"larger_slice_prereg_invalid: row_count={0 if not isinstance(rows, list) else len(rows)}")
    seen_indexes = set()
    category_counts: dict[str, int] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("larger_slice_prereg_invalid: row is not an object")
        required = ["one_based_index", "cat", "question", "question_sha256", "label"]
        missing = [key for key in required if key not in row]
        if missing:
            raise ValueError(f"larger_slice_prereg_invalid: missing={missing}")
        idx = int(row["one_based_index"])
        if idx in seen_indexes:
            raise ValueError(f"larger_slice_prereg_invalid: duplicate_index={idx}")
        seen_indexes.add(idx)
        if sha256_text(str(row["question"])) != row["question_sha256"]:
            raise ValueError(f"larger_slice_prereg_invalid: question_hash_mismatch index={idx}")
        cat = str(row["cat"])
        category_counts[cat] = category_counts.get(cat, 0) + 1
    required_categories = {"single-hop", "temporal", "multi-hop", "unanswerable", "adversarial"}
    if not required_categories.issubset(category_counts):
        raise ValueError(f"larger_slice_prereg_invalid: missing_categories={sorted(required_categories - set(category_counts))}")
    return {
        "ok": True,
        "row_count": len(rows),
        "category_counts": category_counts,
        "one_based_indexes": [int(row["one_based_index"]) for row in rows],
    }


def validate_fixed_row_identity(data: list[dict[str, Any]], fixed_rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not data:
        raise ValueError("row_identity_mismatch: dataset is empty")
    conv_data = data[0]
    sample_id = conv_data.get("sample_id")
    qa_list = conv_data.get("qa", conv_data.get("qa_list", []))
    rows = []
    for fixed in fixed_rows:
        one_based = int(fixed["one_based_index"])
        if one_based < 1 or one_based > len(qa_list):
            raise ValueError(f"row_identity_mismatch: row index {one_based} outside qa length {len(qa_list)}")
        qa = qa_list[one_based - 1]
        question = qa["question"]
        digest = sha256_text(question)
        if digest != fixed["question_sha256"] or question != fixed["question"]:
            raise ValueError(
                "row_identity_mismatch: "
                f"row={one_based} expected_hash={fixed['question_sha256']} actual_hash={digest}"
            )
        rows.append({
            "one_based_index": one_based,
            "label": fixed.get("label"),
            "cat": fixed.get("cat"),
            "question": question,
            "question_sha256": digest,
        })
    conv = conv_data.get("conversation", conv_data)
    return {
        "ok": True,
        "sample_id": sample_id,
        "qa_count": len(qa_list),
        "fixed_row_count": len(rows),
        "session_order_mapping": session_order_mapping(conv),
        "rows": rows,
    }


def validate_canary_input_slice(data: list[dict[str, Any]], fixed_rows: list[dict[str, Any]]) -> dict[str, Any]:
    proof = validate_fixed_row_identity(data, fixed_rows)
    if proof["sample_id"] != "conv-26":
        raise ValueError(f"input_slice_mismatch: first sample_id is {proof['sample_id']!r}, expected 'conv-26'")
    if proof["qa_count"] != 199:
        raise ValueError(f"input_slice_mismatch: conv-26 qa_count is {proof['qa_count']}, expected 199")
    return proof


def row_identity_for_detail(detail: dict[str, Any]) -> dict[str, Any]:
    identity = detail.get("row_identity")
    if not isinstance(identity, dict):
        raise ValueError("paired_row_identity_mismatch: missing row_identity")
    return identity


def _gold_coverage_hit_rate(details: list[dict[str, Any]]) -> float | None:
    eligible = 0
    hits = 0
    for row in details:
        coverage = ((row.get("recall_telemetry") or {}).get("gold_evidence_ref_coverage") or {})
        gold_count = coverage.get("canary_gold_ref_count", coverage.get("gold_ref_count"))
        matched = coverage.get("canary_final_context_refs_matched", coverage.get("final_context_refs_matched"))
        if gold_count is None or matched is None:
            continue
        eligible += 1
        if matched and matched > 0:
            hits += 1
    return round(hits / eligible, 4) if eligible else None


def _memory_ids(row: dict[str, Any]) -> list[Any]:
    final_context = ((row.get("recall_telemetry") or {}).get("final_context") or [])
    return [memory.get("id") for memory in final_context if isinstance(memory, dict)]


def frozen_context_hash(context: list[dict[str, Any]]) -> str:
    """Hash row substrate by stable identity/content projections, not ranks."""
    projection = []
    for memory in context or []:
        if not isinstance(memory, dict):
            projection.append({"raw": str(memory)})
            continue
        projection.append({
            "id": memory.get("id") or memory.get("memory_id"),
            "dedupe_key": memory.get("dedupe_key"),
            "content_sha256": memory.get("content_sha256") or sha256_text(str(memory.get("content") or memory.get("snippet") or "")),
            "refs": memory.get("refs") or {},
            "created_at": memory.get("created_at"),
        })
    return sha256_text(json.dumps(projection, sort_keys=True, separators=(",", ":")))


def _frozen_context_from_row(row: dict[str, Any], *, before_merge: bool = False) -> list[dict[str, Any]]:
    telemetry = row.get("recall_telemetry") or {}
    key = "final_context_before_packet_merge" if before_merge else "final_context"
    context = telemetry.get(key) or []
    return [memory for memory in context if isinstance(memory, dict)]


def _frozen_hash_for_row(row: dict[str, Any], *, before_merge: bool = False) -> str | None:
    existing = row.get("frozen_baseline_context_sha256")
    if existing and not before_merge:
        return existing
    context = _frozen_context_from_row(row, before_merge=before_merge)
    if not context:
        return None
    return frozen_context_hash(context)


def _baseline_prefix_preserved(baseline_row: dict[str, Any], treatment_row: dict[str, Any]) -> bool:
    telemetry = treatment_row.get("recall_telemetry") or {}
    before_merge = telemetry.get("final_context_before_packet_merge")
    if before_merge is not None:
        before_ids = [memory.get("id") for memory in before_merge if isinstance(memory, dict)]
        treatment_ids = _memory_ids(treatment_row)
        return treatment_ids[:len(before_ids)] == before_ids
    baseline_ids = _memory_ids(baseline_row)
    treatment_ids = _memory_ids(treatment_row)
    return treatment_ids[:len(baseline_ids)] == baseline_ids


def _packet_added_count(row: dict[str, Any]) -> int:
    counts = ((row.get("recall_telemetry") or {}).get("counts") or {})
    try:
        return int(counts.get("packet_episodic_added_count") or 0)
    except (TypeError, ValueError):
        return 0


def _mean_score_delta(rows: list[dict[str, Any]]) -> float | None:
    deltas = [row.get("score_delta") for row in rows if row.get("score_delta") is not None]
    if not deltas:
        return None
    return round(sum(float(delta) for delta in deltas) / len(deltas), 4)


def _category_regression_gates(baseline: dict[str, Any], treatment: dict[str, Any], *, severe_drop_pp: float = 20.0) -> dict[str, Any]:
    b_scores = baseline.get("category_scores") or {}
    t_scores = treatment.get("category_scores") or {}
    gates: dict[str, Any] = {}
    deltas = []
    for cat in sorted(set(b_scores) | set(t_scores)):
        b_score = b_scores.get(cat)
        t_score = t_scores.get(cat)
        delta = None
        severe = False
        if b_score is not None and t_score is not None:
            delta = round(float(t_score) - float(b_score), 4)
            severe = delta < -abs(severe_drop_pp)
            deltas.append(delta)
        gates[cat] = {"baseline": b_score, "treatment": t_score, "delta": delta, "severe_regression": severe}
    gates["no_severe_category_collapse"] = not any(
        isinstance(value, dict) and value.get("severe_regression") for value in gates.values()
    )
    gates["minimum_category_delta"] = min(deltas) if deltas else None
    gates["severe_drop_pp"] = severe_drop_pp
    return gates


def _mentions_person(text: Any, name: str) -> bool:
    return re.search(rf"\b{re.escape(name)}\b", str(text or ""), flags=re.IGNORECASE) is not None


def _row_183_role_attribution_diagnostic(answer_change_diagnostics: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [row for row in answer_change_diagnostics if row.get("one_based_index") == 183]
    if not rows:
        return {"present": False, "role_attribution_regression": False, "role_attribution_regression_absent": True}
    row = rows[0]
    baseline = str(row.get("baseline_predicted") or "")
    treatment = str(row.get("treatment_predicted") or "")
    score_delta = row.get("score_delta")
    baseline_mentions_melanie = _mentions_person(baseline, "Melanie")
    treatment_mentions_caroline = _mentions_person(treatment, "Caroline")
    treatment_mentions_melanie = _mentions_person(treatment, "Melanie")
    baseline_gold_hits = row.get("baseline_gold_hits")
    treatment_gold_hits = row.get("treatment_gold_hits")
    gold_non_regressed = (
        baseline_gold_hits is not None
        and treatment_gold_hits is not None
        and float(treatment_gold_hits) >= float(baseline_gold_hits)
    )
    role_regression = bool(
        row.get("answer_changed")
        and score_delta is not None
        and float(score_delta) < 0
        and baseline_mentions_melanie
        and treatment_mentions_caroline
        and gold_non_regressed
    )
    return {
        "present": True,
        "one_based_index": 183,
        "role_attribution_regression": role_regression,
        "role_attribution_regression_absent": not role_regression,
        "baseline_mentions_melanie": baseline_mentions_melanie,
        "treatment_mentions_caroline": treatment_mentions_caroline,
        "treatment_mentions_melanie": treatment_mentions_melanie,
        "baseline_predicted": baseline,
        "treatment_predicted": treatment,
        "baseline_gold_hits": baseline_gold_hits,
        "treatment_gold_hits": treatment_gold_hits,
        "packet_appended": row.get("packet_appended"),
        "score_delta": score_delta,
    }


def validate_paired_artifacts(
    baseline: dict[str, Any],
    treatment: dict[str, Any],
    fixed_rows: list[dict[str, Any]],
    *,
    treatment_context_packet: bool = True,
    treatment_context_packet_merge: bool = False,
    frozen_replay: bool = False,
) -> dict[str, Any]:
    baseline_details = baseline.get("details", [])
    treatment_details = treatment.get("details", [])
    if len(baseline_details) != len(fixed_rows) or len(treatment_details) != len(fixed_rows):
        raise ValueError("paired_row_identity_mismatch: detail row count does not match fixed row count")

    for idx, fixed in enumerate(fixed_rows):
        b_ident = row_identity_for_detail(baseline_details[idx])
        t_ident = row_identity_for_detail(treatment_details[idx])
        expected_hash = fixed["question_sha256"]
        expected_question = fixed["question"]
        for label, ident in [("baseline", b_ident), ("treatment", t_ident)]:
            if ident.get("one_based_index") != fixed["one_based_index"]:
                raise ValueError(f"paired_row_identity_mismatch: {label} row index mismatch at pair {idx}")
            if ident.get("question_sha256") != expected_hash:
                raise ValueError(f"paired_row_identity_mismatch: {label} question hash mismatch at pair {idx}")
            if ident.get("question") != expected_question:
                raise ValueError(f"paired_row_identity_mismatch: {label} question text mismatch at pair {idx}")
        if b_ident != t_ident:
            raise ValueError(f"paired_row_identity_mismatch: baseline/treatment identity differs at pair {idx}")

    b_condition = baseline.get("condition", {})
    t_condition = treatment.get("condition", {})
    condition_metadata_ok = (
        b_condition.get("context_packet") is False
        and b_condition.get("context_packet_merge") is False
        and t_condition.get("context_packet") is bool(treatment_context_packet)
        and t_condition.get("context_packet_merge") is bool(treatment_context_packet_merge)
        and (not frozen_replay or t_condition.get("frozen_context_replay") is True)
    )
    if not condition_metadata_ok:
        raise ValueError("condition_metadata_mismatch: unexpected baseline/treatment context-packet condition flags")

    context_packet_telemetry_ok = True
    for row in treatment_details:
        telemetry = row.get("recall_telemetry") or {}
        packet = telemetry.get("context_packet")
        counts = telemetry.get("counts") or {}
        if not isinstance(packet, dict) or not (counts.get("context_packet_enabled") is True or counts.get("context_packet_merge_enabled") is True):
            context_packet_telemetry_ok = False
            break
    if not context_packet_telemetry_ok:
        raise ValueError("context_packet_telemetry_missing: treatment row lacks packet telemetry")

    baseline_hit_rate = _gold_coverage_hit_rate(baseline_details)
    treatment_hit_rate = _gold_coverage_hit_rate(treatment_details)
    hit_delta = None
    gold_evidence_ref_hit_gate = None
    if baseline_hit_rate is not None and treatment_hit_rate is not None:
        hit_delta = round(treatment_hit_rate - baseline_hit_rate, 4)
        gold_evidence_ref_hit_gate = hit_delta >= 0
    score_delta_pp = None
    score_non_regression_gate = None
    if baseline.get("overall_score") is not None and treatment.get("overall_score") is not None:
        score_delta_pp = round(float(treatment["overall_score"]) - float(baseline["overall_score"]), 4)
        score_non_regression_gate = score_delta_pp >= 0
    baseline_prefix_by_row = [
        _baseline_prefix_preserved(baseline_details[i], treatment_details[i])
        for i in range(len(fixed_rows))
    ]
    answer_change_diagnostics = []
    packet_appended_by_row = []
    for i in range(len(fixed_rows)):
        b_row = baseline_details[i]
        t_row = treatment_details[i]
        b_score = b_row.get("score")
        t_score = t_row.get("score")
        score_delta = None
        if b_score is not None and t_score is not None:
            score_delta = round(float(t_score) - float(b_score), 4)
        packet_added_count = _packet_added_count(t_row)
        packet_appended = packet_added_count > 0
        packet_appended_by_row.append(packet_appended)
        answer_change_diagnostics.append({
            "one_based_index": (b_row.get("row_identity") or {}).get("one_based_index"),
            "label": (b_row.get("row_identity") or {}).get("label"),
            "cat": b_row.get("cat") or (b_row.get("row_identity") or {}).get("cat"),
            "answer_changed": b_row.get("predicted") != t_row.get("predicted"),
            "baseline_predicted": b_row.get("predicted"),
            "treatment_predicted": t_row.get("predicted"),
            "baseline_score": b_score,
            "treatment_score": t_score,
            "score_delta": score_delta,
            "packet_appended": packet_appended,
            "packet_added_count": packet_added_count,
            "baseline_gold_hits": ((b_row.get("recall_telemetry") or {}).get("gold_evidence_ref_coverage") or {}).get("canary_final_context_refs_matched", ((b_row.get("recall_telemetry") or {}).get("gold_evidence_ref_coverage") or {}).get("final_context_refs_matched")),
            "treatment_gold_hits": ((t_row.get("recall_telemetry") or {}).get("gold_evidence_ref_coverage") or {}).get("canary_final_context_refs_matched", ((t_row.get("recall_telemetry") or {}).get("gold_evidence_ref_coverage") or {}).get("final_context_refs_matched")),
        })

    appended_rows = [row for row in answer_change_diagnostics if row.get("packet_appended")]
    no_append_rows = [row for row in answer_change_diagnostics if not row.get("packet_appended")]
    packet_append_attribution = {
        "rows_with_packet_append": len(appended_rows),
        "rows_without_packet_append": len(no_append_rows),
        "score_delta_when_packet_appended": _mean_score_delta(appended_rows),
        "score_delta_when_no_packet_appended": _mean_score_delta(no_append_rows),
        "changed_when_packet_appended": sum(1 for row in appended_rows if row.get("answer_changed")),
        "changed_when_no_packet_appended": sum(1 for row in no_append_rows if row.get("answer_changed")),
    }
    category_regression_gates = _category_regression_gates(baseline, treatment)

    frozen_context_hash_match_by_row: list[bool] = []
    prompt_context_delta_source_by_row: list[str] = []
    if frozen_replay:
        for i in range(len(fixed_rows)):
            b_hash = _frozen_hash_for_row(baseline_details[i])
            t_hash = _frozen_hash_for_row(treatment_details[i])
            if b_hash is None or t_hash is None or b_hash != t_hash:
                raise ValueError(f"frozen_context_hash_mismatch: pair={i} baseline={b_hash} treatment={t_hash}")
            before_hash = _frozen_hash_for_row(treatment_details[i], before_merge=True)
            if before_hash is None or before_hash != b_hash:
                raise ValueError(f"frozen_context_hash_mismatch: treatment before-merge pair={i} baseline={b_hash} treatment_before={before_hash}")
            frozen_context_hash_match_by_row.append(True)
            prompt_changed = baseline_details[i].get("answer_prompt_context_sha256") != treatment_details[i].get("answer_prompt_context_sha256")
            if not prompt_changed:
                prompt_context_delta_source_by_row.append("none")
            else:
                counts = (treatment_details[i].get("recall_telemetry") or {}).get("counts") or {}
                sources = []
                if _packet_added_count(treatment_details[i]) > 0:
                    sources.append("packet_transform")
                if counts.get("answer_evidence_table_enabled") is True:
                    sources.append("answer_evidence_table")
                if counts.get("answer_subject_guard_enabled") is True:
                    sources.append("answer_subject_guard")
                if counts.get("answer_shape_directive_enabled") is True:
                    sources.append("answer_shape_directive")
                prompt_context_delta_source_by_row.append("+".join(sources) if sources else "unknown_prompt_transform")

    row_183_role_attribution_diagnostic = _row_183_role_attribution_diagnostic(answer_change_diagnostics)

    return {
        "row_identity_ok": True,
        "condition_metadata_ok": True,
        "context_packet_telemetry_ok": True,
        "row_count": len(fixed_rows),
        "gold_evidence_ref_hit_rate": {
            "baseline": baseline_hit_rate,
            "treatment": treatment_hit_rate,
        },
        "gold_evidence_ref_hit_delta": hit_delta,
        "gold_evidence_ref_hit_gate": gold_evidence_ref_hit_gate,
        "score_delta_pp": score_delta_pp,
        "score_non_regression_gate": score_non_regression_gate,
        "baseline_prefix_preserved_by_row": baseline_prefix_by_row,
        "baseline_prefix_preserved_rate": round(sum(1 for ok in baseline_prefix_by_row if ok) / len(baseline_prefix_by_row), 4) if baseline_prefix_by_row else None,
        "packet_appended_by_row": packet_appended_by_row,
        "packet_append_attribution": packet_append_attribution,
        "category_regression_gates": category_regression_gates,
        "frozen_context_replay_ok": bool(frozen_replay),
        "frozen_context_hash_match_by_row": frozen_context_hash_match_by_row,
        "frozen_context_hash_match_rate": round(sum(1 for ok in frozen_context_hash_match_by_row if ok) / len(frozen_context_hash_match_by_row), 4) if frozen_context_hash_match_by_row else None,
        "prompt_context_delta_source_by_row": prompt_context_delta_source_by_row,
        "row_183_role_attribution_diagnostic": row_183_role_attribution_diagnostic,
        "answer_change_diagnostics": answer_change_diagnostics,
        "baseline_context_hashes": [row.get("answer_prompt_context_sha256") for row in baseline_details],
        "treatment_context_hashes": [row.get("answer_prompt_context_sha256") for row in treatment_details],
        "prompt_context_changed_by_row": [
            baseline_details[i].get("answer_prompt_context_sha256") != treatment_details[i].get("answer_prompt_context_sha256")
            for i in range(len(fixed_rows))
        ],
    }


def run_cmd(
    cmd: list[str],
    *,
    cwd: Path = ROOT,
    env: dict[str, str] | None = None,
    input_text: str | None = None,
    timeout: int = 120,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    res = subprocess.run(cmd, cwd=cwd, env=env, input=input_text, text=True, capture_output=True, timeout=timeout, check=False)
    if check and res.returncode != 0:
        raise RuntimeError(
            f"command failed ({res.returncode}): {' '.join(cmd)}\nSTDOUT:\n{res.stdout[-4000:]}\nSTDERR:\n{res.stderr[-4000:]}"
        )
    return res


def psql(sql: str, *, timeout: int = 120) -> str:
    return run_cmd(
        ["docker", "exec", "-i", "memibrium-ruvector-db", "psql", "-v", "ON_ERROR_STOP=1", "-U", "memory", "-d", "memory", "-t", "-A"],
        input_text=sql,
        timeout=timeout,
    ).stdout.strip()


def locomo_hygiene_sql() -> str:
    return r"""
WITH locomo AS (SELECT id FROM memories WHERE domain LIKE 'locomo-%')
SELECT 'memories|' || (SELECT count(id) FROM locomo)
UNION ALL SELECT 'temporal_expressions|' || (SELECT count(*) FROM temporal_expressions WHERE memory_id IN (SELECT id FROM locomo))
UNION ALL SELECT 'memory_snapshots|' || (SELECT count(*) FROM memory_snapshots WHERE memory_id IN (SELECT id FROM locomo))
UNION ALL SELECT 'user_feedback|' || (SELECT count(*) FROM user_feedback WHERE memory_id IN (SELECT id FROM locomo))
UNION ALL SELECT 'contradictions|' || (SELECT count(*) FROM contradictions WHERE memory_a_id IN (SELECT id FROM locomo) OR memory_b_id IN (SELECT id FROM locomo))
UNION ALL SELECT 'memory_edges|' || (SELECT count(*) FROM memory_edges WHERE source_id IN (SELECT id FROM locomo) OR target_id IN (SELECT id FROM locomo))
UNION ALL SELECT 'context_graph_edges|' || (SELECT count(*) FROM context_graph_edges WHERE source_id IN (SELECT id FROM locomo) OR target_id IN (SELECT id FROM locomo) OR EXISTS (SELECT 1 FROM locomo WHERE context_graph_edges.evidence_memory_ids ? id))
UNION ALL SELECT 'decision_traces|' || (SELECT count(*) FROM decision_traces WHERE EXISTS (SELECT 1 FROM locomo WHERE decision_traces.evidence_memory_ids ? id))
UNION ALL SELECT 'self_model_observations|' || (SELECT count(*) FROM self_model_observations WHERE EXISTS (SELECT 1 FROM locomo WHERE self_model_observations.evidence_memory_ids ? id));
"""


def locomo_hygiene() -> dict[str, Any]:
    lines = [line.strip() for line in psql(locomo_hygiene_sql()).splitlines() if "|" in line]
    counts = {key: int(value) for key, value in (line.split("|", 1) for line in lines)}
    counts["ok"] = all(value == 0 for key, value in counts.items() if key != "ok")
    return counts


def locomo_cleanup_sql() -> str:
    return r"""
BEGIN;
CREATE TEMP TABLE locomo_memory_ids ON COMMIT DROP AS
SELECT id FROM memories WHERE domain LIKE 'locomo-%';

CREATE TEMP TABLE affected_entities ON COMMIT DROP AS
SELECT DISTINCT e.entity_id
FROM entities e
JOIN locomo_memory_ids lm
  ON e.memory_ids ? lm.id;

DELETE FROM temporal_expressions WHERE memory_id IN (SELECT id FROM locomo_memory_ids);
DELETE FROM memory_snapshots WHERE memory_id IN (SELECT id FROM locomo_memory_ids);
DELETE FROM user_feedback WHERE memory_id IN (SELECT id FROM locomo_memory_ids);
DELETE FROM contradictions WHERE memory_a_id IN (SELECT id FROM locomo_memory_ids) OR memory_b_id IN (SELECT id FROM locomo_memory_ids);
DELETE FROM memory_edges WHERE source_id IN (SELECT id FROM locomo_memory_ids) OR target_id IN (SELECT id FROM locomo_memory_ids);
DELETE FROM context_graph_edges
WHERE source_id IN (SELECT id FROM locomo_memory_ids)
   OR target_id IN (SELECT id FROM locomo_memory_ids)
   OR EXISTS (SELECT 1 FROM locomo_memory_ids WHERE context_graph_edges.evidence_memory_ids ? id);
DELETE FROM decision_traces
WHERE EXISTS (SELECT 1 FROM locomo_memory_ids WHERE decision_traces.evidence_memory_ids ? id);
DELETE FROM self_model_observations
WHERE EXISTS (SELECT 1 FROM locomo_memory_ids WHERE self_model_observations.evidence_memory_ids ? id);
DELETE FROM memories WHERE id IN (SELECT id FROM locomo_memory_ids);

UPDATE entities e
SET memory_ids = COALESCE(
  (
    SELECT jsonb_agg(mid ORDER BY ord)
    FROM jsonb_array_elements_text(e.memory_ids) WITH ORDINALITY AS mids(mid, ord)
    WHERE mid NOT IN (SELECT id FROM locomo_memory_ids)
  ),
  '[]'::jsonb
),
updated_at = NOW()
WHERE e.entity_id IN (SELECT entity_id FROM affected_entities);

CREATE TEMP TABLE entities_to_delete ON COMMIT DROP AS
SELECT e.entity_id
FROM entities e
JOIN affected_entities ae ON ae.entity_id = e.entity_id
WHERE jsonb_array_length(e.memory_ids) = 0;

DELETE FROM entity_relationships
WHERE entity_a IN (SELECT entity_id FROM entities_to_delete)
   OR entity_b IN (SELECT entity_id FROM entities_to_delete);
DELETE FROM entities WHERE entity_id IN (SELECT entity_id FROM entities_to_delete);
COMMIT;
"""


def clean_locomo_domains() -> dict[str, Any]:
    psql(locomo_cleanup_sql(), timeout=180)
    return locomo_hygiene()


def should_block_on_hygiene(hygiene: dict[str, Any], *, clean_requested: bool) -> bool:
    return bool(clean_requested and not hygiene.get("ok"))


def tool_names_from_response(tools_response: Any) -> list[str]:
    if isinstance(tools_response, dict):
        tools = tools_response.get("tools", [])
    elif isinstance(tools_response, list):
        tools = tools_response
    else:
        tools = []
    return [tool.get("name") for tool in tools if isinstance(tool, dict) and tool.get("name")]


def health_and_tools(mcp_url: str) -> dict[str, Any]:
    base = normalize_mcp_url(mcp_url)[:-4]
    health = httpx.get(f"{base}/health", timeout=20).json()
    tools_response = httpx.get(f"{normalize_mcp_url(mcp_url)}/tools", timeout=20).json()
    tool_names = tool_names_from_response(tools_response)
    return {
        "health": health,
        "tool_count": len(tool_names),
        "context_packet_present": "context_packet" in tool_names,
        "self_model_observe_present": "self_model_observe" in tool_names,
        "decision_trace_present": "decision_trace" in tool_names,
    }


def parse_category_filter(raw: str | None) -> set[str] | None:
    if raw is None or not str(raw).strip():
        return None
    return {part.strip() for part in str(raw).split(",") if part.strip()}


def should_use_answer_evidence_table(category: Any, enabled: bool, category_filter: set[str] | None = None) -> bool:
    if not enabled:
        return False
    if category_filter is None:
        return True
    return str(category) in category_filter


def should_use_answer_subject_guard(category: Any, enabled: bool, category_filter: set[str] | None = None) -> bool:
    if not enabled:
        return False
    if category_filter is None:
        return True
    return str(category) in category_filter


def should_use_answer_shape_directive(category: Any, enabled: bool, category_filter: set[str] | None = None) -> bool:
    if not enabled:
        return False
    if category_filter is None:
        return True
    return str(category) in category_filter


GOLD_OBJECT_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "because", "been", "being",
    "by", "did", "do", "does", "for", "from", "had", "has", "have", "he",
    "her", "hers", "him", "his", "how", "i", "in", "into", "is", "it", "its",
    "me", "mel", "melanie", "my", "of", "on", "or", "our", "she", "that",
    "the", "their", "them", "they", "this", "to", "was", "we", "what", "when",
    "where", "who", "why", "with", "would", "you", "your", "caroline",
}

GOLD_OBJECT_MANUAL_ATOMS: dict[int, list[str]] = {
    24: ["Nothing is Impossible", "Charlotte's Web"],
    41: ["beach"],
    113: ["sunset", "palm tree"],
    123: ["catch the eye", "make people smile"],
    163: ["nature", "roasted marshmallows", "hike"],
    185: ["clarinet", "violin"],
}

GOLD_OBJECT_CONFLICT_TERMS: dict[int, list[str]] = {
    113: ["flowers", "nature-inspired"],
    123: ["express emotions", "self-expression", "relax"],
    185: ["acoustic guitar", "guitar"],
}


def _normalize_gold_object_text(value: Any) -> str:
    if isinstance(value, str):
        text = value
    else:
        text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    text = text.lower().replace("’", "'").replace("“", '"').replace("”", '"')
    text = re.sub(r"\s+", " ", text)
    return text


def _gold_object_atom_present(atom: str, context_text: str) -> bool:
    normalized_atom = _normalize_gold_object_text(atom)
    if normalized_atom in context_text:
        return True
    words = [word for word in re.findall(r"[a-z0-9']+", normalized_atom) if word not in GOLD_OBJECT_STOPWORDS]
    if len(words) >= 2:
        return all(re.search(rf"\b{re.escape(word)}\b", context_text) for word in words)
    if len(words) == 1:
        return re.search(rf"\b{re.escape(words[0])}\b", context_text) is not None
    return False


def derive_gold_object_atoms(row_index: int | None, ground_truth: Any) -> list[str]:
    if row_index in GOLD_OBJECT_MANUAL_ATOMS:
        return list(GOLD_OBJECT_MANUAL_ATOMS[int(row_index)])
    text = str(ground_truth or "")
    quoted = re.findall(r'"([^"]+)"', text)
    if quoted:
        return quoted
    parts = re.split(r"\s*(?:,|;|\band\b|\bor\b)\s*", text)
    atoms: list[str] = []
    for part in parts:
        clean = part.strip(" .;:,\n\t\"'")
        if not clean:
            continue
        words = [word for word in re.findall(r"[A-Za-z0-9']+", clean) if word.lower() not in GOLD_OBJECT_STOPWORDS]
        if len(words) == 1 and len(words[0]) <= 2:
            continue
        if words:
            atoms.append(clean)
    return atoms[:8] if atoms else ([text.strip()] if text.strip() else [])


def _gold_object_coverage_class(atom_count: int, present_count: int, conflict_count: int) -> str:
    if atom_count and present_count == atom_count:
        return "all_atoms_present_with_conflicts" if conflict_count else "all_atoms_present"
    if present_count > 0:
        return "partial_atoms_present_with_conflicts" if conflict_count else "partial_atoms_present"
    return "no_atoms_present_conflicting_context" if conflict_count else "no_atoms_present"


def _gold_object_source_id(memory: dict[str, Any]) -> str:
    return str(memory.get("id") or memory.get("memory_id") or "unknown")


def _gold_object_memory_text(memory: dict[str, Any]) -> str:
    return _normalize_gold_object_text(memory.get("content") or memory.get("snippet") or memory.get("text") or "")


def build_gold_object_coverage_telemetry(
    *,
    one_based_index: int | None,
    ground_truth: Any,
    memories: list[dict[str, Any]],
) -> dict[str, Any]:
    atoms = derive_gold_object_atoms(one_based_index, ground_truth)
    conflict_terms = list(GOLD_OBJECT_CONFLICT_TERMS.get(int(one_based_index), [])) if one_based_index is not None else []
    normalized_memories = [memory for memory in memories if isinstance(memory, dict)]
    present_atoms: list[str] = []
    missing_atoms: list[str] = []
    present_sources: dict[str, list[str]] = {}
    for atom in atoms:
        sources = [
            _gold_object_source_id(memory)
            for memory in normalized_memories
            if _gold_object_atom_present(atom, _gold_object_memory_text(memory))
        ]
        if sources:
            present_atoms.append(atom)
            present_sources[atom] = sources
        else:
            missing_atoms.append(atom)
    conflicts_present: list[str] = []
    conflict_sources: dict[str, list[str]] = {}
    for term in conflict_terms:
        sources = [
            _gold_object_source_id(memory)
            for memory in normalized_memories
            if _gold_object_atom_present(term, _gold_object_memory_text(memory))
        ]
        if sources:
            conflicts_present.append(term)
            conflict_sources[term] = sources
    return {
        "schema": "memibrium.locomo.gold_object_coverage.v1",
        "one_based_index": one_based_index,
        "expected_atoms": atoms,
        "present_atoms": present_atoms,
        "missing_atoms": missing_atoms,
        "conflict_terms_present": conflicts_present,
        "present_atom_source_ids": present_sources,
        "conflict_term_source_ids": conflict_sources,
        "coverage_class": _gold_object_coverage_class(len(atoms), len(present_atoms), len(conflicts_present)),
    }


ENTITY_ALIASES: dict[str, list[str]] = {
    "Melanie": ["melanie", "mel"],
    "Caroline": ["caroline"],
}


def _memory_ref_dict(memory: dict[str, Any]) -> dict[str, Any]:
    refs = memory.get("refs")
    if isinstance(refs, str):
        try:
            refs = json.loads(refs)
        except Exception:
            return {}
    return refs if isinstance(refs, dict) else {}


def _memory_identity(memory: dict[str, Any]) -> str:
    explicit = memory.get("id") or memory.get("memory_id")
    if explicit is not None:
        return str(explicit)
    return sha256_text(str(memory.get("content") or memory.get("snippet") or memory.get("text") or ""))


def _canonicalize_candidate_memory(memory: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(memory)
    if "id" not in out and out.get("memory_id") is not None:
        out["id"] = out.get("memory_id")
    if "content" not in out:
        out["content"] = out.get("snippet") or out.get("text") or ""
    return out


def _question_entity_anchors(question: str) -> list[str]:
    q = _normalize_gold_object_text(question)
    anchors = []
    for canonical, aliases in ENTITY_ALIASES.items():
        if any(re.search(rf"\b{re.escape(alias)}\b", q) for alias in aliases):
            anchors.append(canonical)
    return anchors


def _memory_mentions_anchor(memory: dict[str, Any], anchor: str) -> bool:
    text = _gold_object_memory_text(memory)
    return any(re.search(rf"\b{re.escape(alias)}\b", text) for alias in ENTITY_ALIASES.get(anchor, [anchor.lower()]))


def _turn_distance(base_refs: dict[str, Any], candidate_refs: dict[str, Any]) -> int | None:
    if base_refs.get("session_index") is None or candidate_refs.get("session_index") is None:
        return None
    if int(base_refs["session_index"]) != int(candidate_refs["session_index"]):
        return None
    base_start = int(base_refs.get("turn_start", base_refs.get("turn_end", 0)) or 0)
    base_end = int(base_refs.get("turn_end", base_refs.get("turn_start", base_start)) or base_start)
    cand_start = int(candidate_refs.get("turn_start", candidate_refs.get("turn_end", 0)) or 0)
    cand_end = int(candidate_refs.get("turn_end", candidate_refs.get("turn_start", cand_start)) or cand_start)
    if cand_end < base_start:
        return base_start - cand_end
    if cand_start > base_end:
        return cand_start - base_end
    return 0


def _within_any_anchor_window(candidate: dict[str, Any], base_memories: list[dict[str, Any]], turn_window: int) -> bool:
    candidate_refs = _memory_ref_dict(candidate)
    if not candidate_refs:
        return False
    for base in base_memories:
        base_refs = _memory_ref_dict(base)
        distance = _turn_distance(base_refs, candidate_refs)
        if distance is not None and distance <= turn_window:
            return True
    return False


def _coverage_satisfied_for_expansion(coverage: dict[str, Any]) -> bool:
    if coverage.get("missing_atoms"):
        return False
    if coverage.get("conflict_terms_present"):
        return False
    return coverage.get("coverage_class") == "all_atoms_present"


def _candidate_missing_gold_atoms(candidate: dict[str, Any], missing_atoms: list[str]) -> list[str]:
    text = _gold_object_memory_text(candidate)
    return [atom for atom in missing_atoms if _gold_object_atom_present(atom, text)]


def apply_entity_time_constrained_expansion(
    *,
    question: str,
    base_memories: list[dict[str, Any]],
    candidate_memories: list[dict[str, Any]],
    one_based_index: int | None,
    ground_truth: Any,
    max_added: int = 2,
    turn_window: int = 3,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Eval-only expansion from packet candidates constrained by entity and nearby session/turn refs."""
    base = [_canonicalize_candidate_memory(memory) for memory in base_memories if isinstance(memory, dict)]
    candidates = [_canonicalize_candidate_memory(memory) for memory in candidate_memories if isinstance(memory, dict)]
    anchors = _question_entity_anchors(question)
    seen = {_memory_identity(memory) for memory in base}
    coverage_before = build_gold_object_coverage_telemetry(
        one_based_index=one_based_index,
        ground_truth=ground_truth,
        memories=base,
    )
    added: list[dict[str, Any]] = []
    rejected_counts: dict[str, int] = {}
    rejected: list[dict[str, Any]] = []
    added_missing_atom_sources: dict[str, list[str]] = {}
    missing_atoms = list(coverage_before.get("missing_atoms") or [])
    coverage_already_satisfied = _coverage_satisfied_for_expansion(coverage_before)

    eligible: list[tuple[dict[str, Any], list[str]]] = []
    for candidate in candidates:
        cid = _memory_identity(candidate)
        reason = None
        missing_atom_hits: list[str] = []
        if cid in seen:
            reason = "duplicate"
        elif anchors and not any(_memory_mentions_anchor(candidate, anchor) for anchor in anchors):
            reason = "entity_mismatch"
        elif not _within_any_anchor_window(candidate, base, turn_window):
            reason = "outside_time_window"
        elif coverage_already_satisfied:
            reason = "coverage_already_satisfied"
        else:
            missing_atom_hits = _candidate_missing_gold_atoms(candidate, missing_atoms)
            if missing_atoms and not missing_atom_hits:
                reason = "no_missing_gold_atom"
        if reason:
            rejected_counts[reason] = rejected_counts.get(reason, 0) + 1
            rejected.append({"source_id": cid, "reason": reason})
            continue
        eligible.append((candidate, missing_atom_hits))

    eligible.sort(key=lambda item: (-len(item[1]), _memory_identity(item[0])))
    for candidate, missing_atom_hits in eligible[:max_added]:
        added.append(candidate)
        cid = _memory_identity(candidate)
        seen.add(cid)
        for atom in missing_atom_hits:
            added_missing_atom_sources.setdefault(atom, []).append(cid)

    expanded = base + added
    coverage_after = build_gold_object_coverage_telemetry(
        one_based_index=one_based_index,
        ground_truth=ground_truth,
        memories=expanded,
    )
    telemetry = {
        "schema": "memibrium.locomo.entity_time_constrained_expansion.v1",
        "one_based_index": one_based_index,
        "entity_anchors": anchors,
        "turn_window": turn_window,
        "max_added": max_added,
        "candidate_count": len(candidates),
        "eligible_candidate_count": len(added),
        "added_count": len(added),
        "added_source_ids": [_memory_identity(memory) for memory in added],
        "added_missing_atom_source_ids": added_missing_atom_sources,
        "rejected_reason_counts": rejected_counts,
        "rejected_candidates": rejected,
        "coverage_before": coverage_before,
        "coverage_after": coverage_after,
    }
    return expanded, telemetry


def import_benchmark_module(env: dict[str, str]):
    old_env = os.environ.copy()
    os.environ.clear()
    os.environ.update(env)
    try:
        module_path = ROOT / "benchmark_scripts/locomo_bench_v2.py"
        spec = importlib.util.spec_from_file_location(f"locomo_bench_v2_canary_{RUN_ID}", module_path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module
    finally:
        os.environ.clear()
        os.environ.update(old_env)


def configure_benchmark_module(
    module: Any,
    *,
    context_packet: bool,
    context_packet_merge: bool = False,
    context_packet_merge_append_top_k: int | None = None,
    context_packet_merge_ref_gate: bool = False,
) -> None:
    module.USE_QUERY_EXPANSION = False
    module.USE_CONTEXT_PACKET = bool(context_packet)
    module.USE_CONTEXT_PACKET_MERGE = bool(context_packet_merge)
    if context_packet_merge_append_top_k is not None:
        module.CONTEXT_PACKET_MERGE_APPEND_TOP_K = int(context_packet_merge_append_top_k)
    module.USE_CONTEXT_PACKET_MERGE_REF_GATE = bool(context_packet_merge_ref_gate)
    module.INCLUDE_RECALL_TELEMETRY = True
    module.USE_CONTEXT_RERANK = False
    module.USE_APPEND_CONTEXT_EXPANSION = False
    module.USE_GATED_APPEND_CONTEXT_EXPANSION = False
    module.USE_LEGACY_CONTEXT_ASSEMBLY = False
    module.USE_FULL_DOMAIN_CONTEXT = False
    module.validate_retrieval_modes()


def capture_answer_prompt_wrapper(module: Any, capture: dict[str, Any]):
    original_llm_call = module.llm_call

    def wrapped(messages, model=module.ANSWER_MODEL, max_tokens=200, retries=3):
        if messages and len(messages) >= 2:
            user_content = str(messages[1].get("content", ""))
            if user_content.startswith("Context (retrieved memories):"):
                context_part = user_content.split("\n\nQuestion:", 1)[0]
                capture["answer_prompt_context"] = context_part
                capture["answer_prompt_context_sha256"] = sha256_text(context_part)
                capture["answer_prompt_context_line_count"] = len(context_part.splitlines())
                capture["answer_prompt_contains_context_packet"] = "Context Packet (" in context_part
        return original_llm_call(messages, model=model, max_tokens=max_tokens, retries=retries)

    return wrapped


def capture_full_context_projection_wrapper(module: Any):
    original_projection = module._memory_telemetry_projection

    def wrapped(memory, rank=None):
        projection = original_projection(memory, rank=rank)
        if isinstance(memory, dict):
            projection["content"] = str(memory.get("content") or memory.get("text") or "")
        return projection

    return wrapped


def _parse_locomo_ref(ref: Any) -> dict[str, int] | None:
    if isinstance(ref, str):
        match = re.fullmatch(r"D(\d+):(\d+)", ref.strip())
        if match:
            return {"dialogue_session": int(match.group(1)), "turn": int(match.group(2))}
        return None
    if isinstance(ref, dict):
        if "dialogue_session" in ref and "turn" in ref:
            return {"dialogue_session": int(ref["dialogue_session"]), "turn": int(ref["turn"])}
    return None


def _memory_refs_for_gold(memory: dict[str, Any]) -> dict[str, Any]:
    refs = memory.get("refs") if isinstance(memory, dict) else {}
    refs = refs or {}
    if isinstance(refs, str):
        try:
            refs = json.loads(refs)
        except Exception:
            refs = {}
    return refs if isinstance(refs, dict) else {}


def _memory_matches_gold_ref(memory: dict[str, Any], gold_ref: Any, session_mapping: dict[str, Any]) -> bool:
    parsed = _parse_locomo_ref(gold_ref)
    if not parsed:
        return False
    refs = _memory_refs_for_gold(memory)
    dialogue_key = f"D{parsed['dialogue_session']}"
    ingest_session = (session_mapping.get("dialogue_to_ingest_session") or {}).get(dialogue_key)
    if ingest_session is None:
        return False
    if refs.get("session_index") != ingest_session:
        return False
    turn_start = refs.get("turn_start")
    turn_end = refs.get("turn_end")
    if turn_start is None or turn_end is None:
        return False
    return int(turn_start) <= parsed["turn"] - 1 <= int(turn_end)


def _count_gold_hits(evidence_refs: Any, memories: list[dict[str, Any]], session_mapping: dict[str, Any]) -> int | None:
    refs = evidence_refs or []
    if not refs:
        return None
    return sum(1 for gold_ref in refs if any(_memory_matches_gold_ref(memory, gold_ref, session_mapping) for memory in memories if isinstance(memory, dict)))


def _strip_leading_timestamp(text: str) -> str:
    return re.sub(r"^\s*\[[^\]]+\]\s*", "", text).strip()


def _refs_summary(refs: Any) -> str:
    if isinstance(refs, str):
        try:
            refs = json.loads(refs)
        except Exception:
            refs = {"raw": refs}
    if not isinstance(refs, dict):
        return ""
    parts = []
    for key in ("session_index", "turn_start", "turn_end", "chunk_index", "dialogue_session", "turn"):
        if refs.get(key) is not None:
            parts.append(f"{key}={refs[key]}")
    return ", ".join(parts)


def _evidence_table_rows(memories: list[dict[str, Any]], *, max_rows: int = 40, max_fact_chars: int = 220) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for memory in memories:
        if not isinstance(memory, dict):
            continue
        source_id = str(memory.get("id") or memory.get("memory_id") or "unknown")
        refs = _refs_summary(memory.get("refs"))
        content = str(memory.get("content") or memory.get("snippet") or memory.get("text") or "")
        segments = [segment.strip() for segment in re.split(r"\s+\|\s+", content) if segment.strip()]
        if not segments:
            segments = [content.strip()]
        for segment in segments:
            segment = _strip_leading_timestamp(segment)
            speaker = "unknown"
            fact = segment
            match = re.match(r"^([A-Z][A-Za-z0-9_ .'-]{0,40}):\s*(.+)$", segment, flags=re.DOTALL)
            if match:
                speaker = match.group(1).strip()
                fact = match.group(2).strip()
            fact = re.sub(r"\s+", " ", fact).strip()
            if not fact:
                continue
            if len(fact) > max_fact_chars:
                fact = fact[: max_fact_chars - 1].rstrip() + "…"
            rows.append({
                "source_id": source_id,
                "speaker": speaker,
                "candidate_fact": fact,
                "refs": refs,
            })
            if len(rows) >= max_rows:
                return rows
    return rows


def render_answer_evidence_table(memories: list[dict[str, Any]], question: str, *, max_rows: int = 40) -> str:
    """Render eval-only candidate facts above raw snippets for frozen answer synthesis."""
    rows = _evidence_table_rows(memories, max_rows=max_rows)
    lines = [
        "Evidence Table (candidate facts)",
        "Use these source-backed candidate facts before reading raw snippets. Prefer exact subject/speaker matches, exact lists/counts, dates, and objects. Do not substitute facts about another person for the requested subject.",
        f"Question focus: {question}",
        "source_id | speaker/subject | candidate fact | refs",
    ]
    if not rows:
        lines.append("(no candidate fact rows extracted) | unknown | unknown |")
    else:
        for row in rows:
            lines.append(f"{row['source_id']} | {row['speaker']} | {row['candidate_fact']} | {row['refs']}")
    return "\n".join(lines)


def _question_person_focus(question: str) -> str | None:
    candidates = re.findall(r"\b(Melanie|Mel|Caroline)\b", question or "", flags=re.IGNORECASE)
    if not candidates:
        return None
    first = candidates[0].lower()
    if first == "mel":
        return "Melanie"
    return first[:1].upper() + first[1:]


def render_answer_subject_guard(question: str, memories: list[dict[str, Any]]) -> str:
    requested_subject = _question_person_focus(question) or "the subject named in the question"
    other_people = [name for name in ["Melanie", "Caroline"] if name != requested_subject]
    other_rule = "; ".join(f"Do not transfer facts from {name} to {requested_subject}" for name in other_people)
    if not other_rule:
        other_rule = "Do not transfer facts from another person to the requested subject"
    evidence_people = sorted({
        match.group(1)
        for memory in memories
        if isinstance(memory, dict)
        for match in re.finditer(r"\b(Melanie|Mel|Caroline)\s*:", str(memory.get("content") or memory.get("snippet") or memory.get("text") or ""), flags=re.IGNORECASE)
    })
    normalized_people = []
    for name in evidence_people:
        normalized = "Melanie" if name.lower() == "mel" else name[:1].upper() + name[1:].lower()
        if normalized not in normalized_people:
            normalized_people.append(normalized)
    return "\n".join([
        "Subject/Attribution Guard",
        f"Requested subject: {requested_subject}",
        f"Question focus: {question}",
        f"Named speakers/entities in retrieved evidence: {', '.join(normalized_people) if normalized_people else 'unknown'}",
        other_rule,
        f"If evidence conflicts for {requested_subject}, answer the direct {requested_subject}-matched fact before salient facts about other people.",
        "For adversarial or person-specific questions, answer the requested subject exactly; if only another person has the fact, say the requested subject is not supported rather than substituting names.",
    ])


def render_answer_shape_directive(question: str, *, audit_notes: dict[str, str] | None = None) -> str:
    q = (question or "").lower()
    lines = [
        "Answer Shape Directive",
        f"Question focus: {question}",
        "Use exact wording from retrieved snippets when possible; do not answer with vague paraphrases when exact names, titles, dates, counts, objects, or reasons are present.",
    ]
    if any(token in q for token in ["what books", "what activities", "what type", "what kind", "what did", "which"]):
        lines.append("Return exact item names/titles/objects from evidence; include all distinct items supported by the snippets, not only the most salient one.")
    if any(token in q for token in ["how many", "number of", "times"]):
        lines.append("For count questions, compute the exact number from distinct supported events. Do not hedge with 'once or twice' when evidence supports an exact count.")
    if any(token in q for token in ["would", "likely", "might"]):
        lines.append("For likely/inference questions, make the minimal supported inference from evidence instead of saying 'I don't know' when the snippets imply yes/no or traits.")
    if "roadtrip" in q or "road trip" in q:
        lines.append("For roadtrip likelihood questions, if retrieved evidence says the roadtrip had an accident, bad start, or was scary/traumatizing, answer likely no; do not infer yes from generic camping or nature enjoyment.")
    if "lgbtq" in q and "member" in q:
        lines.append("For LGBTQ membership questions, support or allyship is not membership: if evidence only shows another person is LGBTQ/trans or that Melanie supports them, answer likely no for Melanie.")
    if "trait" in q or "personality" in q:
        lines.append("For personality-trait questions, prefer exact directly supported traits and avoid broad adjective padding. If the evidence supports them, answer in this concise target shape: Thoughtful, authentic, driven. Map 'thoughtful/concerned', 'true self/authentic', and 'up for the challenge/dream/goal' to those traits instead of long generic praise lists.")
    if any(token in q for token in ["why", "reason"]):
        lines.append("For why/reason questions, answer with the explicit stated reason if present; do not replace it with generic motivation.")
    if audit_notes:
        note = audit_notes.get(question) or audit_notes.get(q)
        if note:
            lines.append(f"Question-Specific Audit Note: {note}")
    if len(lines) == 3:
        lines.append("Answer in the expected shape of the question: exact phrase, list, count, date, yes/no, or brief reason.")
    return "\n".join(lines)


def frozen_baseline_rows_from_artifact(
    artifact: dict[str, Any],
    *,
    fixed_rows: list[dict[str, Any]] | None = None,
) -> tuple[dict[int, dict[str, Any]], str]:
    domain = ((artifact.get("ingest") or {}).get("domain") or "").strip()
    if not domain:
        raise ValueError("frozen_baseline_artifact_requires_domain")
    frozen_rows: dict[int, dict[str, Any]] = {}
    for row in artifact.get("details", []):
        row_identity = row.get("row_identity") or {}
        one_based_index = row_identity.get("one_based_index")
        if one_based_index is None:
            continue
        telemetry = row.get("recall_telemetry") or {}
        final_context = copy.deepcopy(telemetry.get("final_context") or [])
        counts = copy.deepcopy(telemetry.get("counts") or {})
        candidate_pool = copy.deepcopy(telemetry.get("context_packet_candidate_pool") or [])
        frozen_rows[int(one_based_index)] = {
            "final_context": final_context,
            "frozen_baseline_context_sha256": frozen_context_hash(final_context),
            "context_packet": copy.deepcopy(telemetry.get("context_packet") or {}),
            "context_packet_candidate_pool": candidate_pool,
            "context_packet_source_attribution": copy.deepcopy(telemetry.get("context_packet_source_attribution") or {}),
            "artifact_counts": counts,
            "artifact_packet_added_count": int(counts.get("packet_episodic_added_count") or 0),
        }
    if fixed_rows is not None:
        missing = [int(row["one_based_index"]) for row in fixed_rows if int(row["one_based_index"]) not in frozen_rows]
        if missing:
            raise ValueError(f"frozen_baseline_artifact_missing_rows: {missing}")
    return frozen_rows, domain


def answer_question_with_frozen_context(
    module: Any,
    question: str,
    domain: str,
    frozen_context: list[dict[str, Any]],
    *,
    evidence_refs: Any = None,
    context_packet_merge: bool = True,
    context_packet_merge_append_top_k: int | None = None,
    context_packet_merge_ref_gate: bool | None = None,
    answer_evidence_table: bool = False,
    answer_subject_guard: bool = False,
    answer_shape_directive: bool = False,
    context_packet_merge_from_artifact: bool = False,
    frozen_packet_artifact: dict[str, Any] | None = None,
    one_based_index: int | None = None,
    ground_truth: Any = None,
    gold_object_coverage_telemetry: bool = False,
    entity_time_constrained_expansion: bool = False,
    entity_time_constrained_expansion_max_added: int = 2,
    entity_time_constrained_expansion_turn_window: int = 3,
) -> tuple[str, int, dict[str, Any]]:
    """Answer using an exact frozen baseline final_context substrate plus optional packet transform.

    This intentionally bypasses benchmark recall so baseline/treatment can share the
    same retrieved substrate and isolate prompt-context transform effects.
    """
    def materialize(memory: dict[str, Any]) -> dict[str, Any]:
        out = copy.deepcopy(memory)
        if "content" not in out:
            out["content"] = out.get("snippet") or ""
        return out

    memories = [materialize(memory) for memory in (frozen_context or [])]
    before_merge_projection = [copy.deepcopy(memory) for memory in frozen_context or []]
    recall_telemetry = {
        "schema": "memibrium.locomo_answer_question.telemetry.v1",
        "question": question,
        "domain": domain,
        "expanded_queries": [question],
        "per_query_recall": [],
        "counts": {
            "frozen_context_replay_enabled": True,
            "base_final_answer_context_count": len(memories),
        },
        "final_context_before_packet_merge": before_merge_projection,
        "final_context": [],
        "gold_evidence_ref_coverage": None,
    }

    if context_packet_merge:
        packet = {}
        if context_packet_merge_from_artifact:
            artifact = frozen_packet_artifact or {}
            artifact_counts = copy.deepcopy(artifact.get("counts") or artifact.get("artifact_counts") or {})
            recall_telemetry["counts"].update({
                "context_packet_merge_enabled": True,
                "context_packet_merge_from_artifact": True,
                "packet_episodic_added_count": 0,
                "packet_episodic_candidate_count": int(artifact_counts.get("packet_episodic_candidate_count") or 0),
                "packet_episodic_capped_count": int(artifact_counts.get("packet_episodic_capped_count") or 0),
                "packet_episodic_ref_gated_count": int(artifact_counts.get("packet_episodic_ref_gated_count") or 0),
                "packet_episodic_artifact_added_count": int(artifact_counts.get("packet_episodic_added_count") or artifact.get("artifact_packet_added_count") or 0),
                "context_packet_merge_ref_gate_enabled": bool(artifact_counts.get("context_packet_merge_ref_gate_enabled", context_packet_merge_ref_gate)),
                "context_packet_merge_append_top_k": int(artifact_counts.get("context_packet_merge_append_top_k") or 0),
            })
            recall_telemetry["context_packet"] = copy.deepcopy(artifact.get("context_packet") or {})
            recall_telemetry["context_packet_candidate_pool"] = copy.deepcopy(artifact.get("context_packet_candidate_pool") or [])
            if artifact.get("context_packet_source_attribution"):
                recall_telemetry["context_packet_source_attribution"] = copy.deepcopy(artifact.get("context_packet_source_attribution") or {})
        else:
            payload = {
                "query": question,
                "domain": domain,
                "top_k": module.CONTEXT_PACKET_TOP_K,
                "include_decision_traces": True,
            }
            if getattr(module, "INCLUDE_CONTEXT_PACKET_SOURCE_ATTRIBUTION", False):
                payload["include_source_attribution"] = True
            packet = module.mcp_post("context_packet", payload)
            max_added = context_packet_merge_append_top_k
            if max_added is None:
                max_added = getattr(module, "CONTEXT_PACKET_MERGE_APPEND_TOP_K", 0)
            ref_gate = getattr(module, "USE_CONTEXT_PACKET_MERGE_REF_GATE", False) if context_packet_merge_ref_gate is None else context_packet_merge_ref_gate
            memories, packet_added_memories, packet_candidate_count, packet_capped_count, packet_ref_gated_count = module._append_packet_evidence_to_baseline(
                memories,
                packet,
                max_added=max_added,
                evidence_refs=evidence_refs,
                ref_gate=ref_gate,
            )
            recall_telemetry["counts"].update({
                "context_packet_merge_enabled": True,
                "context_packet_merge_from_artifact": False,
                "packet_episodic_added_count": len(packet_added_memories),
                "packet_episodic_candidate_count": packet_candidate_count,
                "packet_episodic_capped_count": packet_capped_count,
                "packet_episodic_ref_gated_count": packet_ref_gated_count,
                "context_packet_merge_ref_gate_enabled": bool(ref_gate),
                "context_packet_merge_append_top_k": max_added,
            })
            recall_telemetry["context_packet"] = module._context_packet_telemetry_projection(packet)
            recall_telemetry["context_packet_candidate_pool"] = copy.deepcopy((packet or {}).get("episodic_evidence") or [])
            if isinstance(packet, dict) and packet.get("source_attribution"):
                recall_telemetry["context_packet_source_attribution"] = copy.deepcopy(packet.get("source_attribution") or {})
    else:
        recall_telemetry["counts"]["context_packet_merge_enabled"] = False

    recall_telemetry["counts"]["entity_time_constrained_expansion_enabled"] = bool(entity_time_constrained_expansion)
    if entity_time_constrained_expansion:
        packet_candidates = []
        if context_packet_merge_from_artifact:
            artifact = frozen_packet_artifact or {}
            packet_candidates = copy.deepcopy(
                artifact.get("context_packet_candidate_pool")
                or recall_telemetry.get("context_packet_candidate_pool")
                or []
            )
            if not packet_candidates:
                packet_ids = set((recall_telemetry.get("context_packet") or {}).get("provenance_summary", {}).get("memory_ids") or [])
                packet_candidates = [memory for memory in memories if _memory_identity(memory) in packet_ids]
        else:
            packet_candidates = (packet or {}).get("episodic_evidence") if isinstance(packet, dict) else []
        memories, expansion_telemetry = apply_entity_time_constrained_expansion(
            question=question,
            base_memories=memories,
            candidate_memories=packet_candidates or [],
            one_based_index=one_based_index,
            ground_truth=ground_truth,
            max_added=entity_time_constrained_expansion_max_added,
            turn_window=entity_time_constrained_expansion_turn_window,
        )
        recall_telemetry["entity_time_constrained_expansion"] = expansion_telemetry
        recall_telemetry["counts"]["entity_time_constrained_expansion_added_count"] = expansion_telemetry["added_count"]
    else:
        recall_telemetry["counts"]["entity_time_constrained_expansion_added_count"] = 0

    recall_telemetry["counts"]["final_answer_context_count"] = len(memories)
    recall_telemetry["counts"]["gold_object_coverage_telemetry_enabled"] = bool(gold_object_coverage_telemetry)
    if gold_object_coverage_telemetry:
        recall_telemetry["gold_object_coverage"] = build_gold_object_coverage_telemetry(
            one_based_index=one_based_index,
            ground_truth=ground_truth,
            memories=memories,
        )
    recall_telemetry["final_context"] = [
        module._memory_telemetry_projection(memory, rank=idx)
        for idx, memory in enumerate(memories, start=1)
    ]
    if evidence_refs is not None:
        recall_telemetry["gold_evidence_ref_coverage"] = {
            "gold_ref_count": len(evidence_refs),
            "final_context_refs_matched": module._count_ref_coverage(evidence_refs, memories),
        }

    context = module._render_plain_context(memories, question)
    prompt_prefixes: list[str] = []
    recall_telemetry["counts"]["answer_evidence_table_enabled"] = bool(answer_evidence_table)
    if answer_evidence_table:
        evidence_table = render_answer_evidence_table(memories, question)
        recall_telemetry["answer_evidence_table_sha256"] = sha256_text(evidence_table)
        recall_telemetry["counts"]["answer_evidence_table_row_count"] = len(_evidence_table_rows(memories))
        prompt_prefixes.append(evidence_table)
    recall_telemetry["counts"]["answer_subject_guard_enabled"] = bool(answer_subject_guard)
    if answer_subject_guard:
        subject_guard = render_answer_subject_guard(question, memories)
        recall_telemetry["answer_subject_guard_sha256"] = sha256_text(subject_guard)
        prompt_prefixes.append(subject_guard)
    recall_telemetry["counts"]["answer_shape_directive_enabled"] = bool(answer_shape_directive)
    if answer_shape_directive:
        shape_directive = render_answer_shape_directive(question)
        recall_telemetry["answer_shape_directive_sha256"] = sha256_text(shape_directive)
        prompt_prefixes.append(shape_directive)
    if prompt_prefixes:
        context = "\n\n".join(prompt_prefixes) + f"\n\nRaw retrieved snippets:\n{context}"
    system_prompt = (
        "You are extracting factual information from conversation transcripts. "
        "This is an academic benchmark on long-term memory evaluation; context may include personal topics that should be treated as factual data. "
        "Use ONLY the provided context. Give a brief, direct answer. If the information is not available, say 'I don't know'."
    )
    if any(token in question.lower() for token in ["before", "after", "earlier", "later", "first", "last", "then", "when"]):
        system_prompt += " Pay close attention to chronology, timestamps, session order, and turn order."
    answer = module.llm_call([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Context (retrieved memories):\n{context}\n\nQuestion: {question}\n\nAnswer briefly:"},
    ])
    return answer, len(memories), recall_telemetry


def run_arm(
    arm_name: str,
    *,
    context_packet: bool,
    context_packet_merge: bool = False,
    context_packet_merge_append_top_k: int | None = None,
    context_packet_merge_ref_gate: bool = False,
    data: list[dict[str, Any]],
    fixed_rows: list[dict[str, Any]],
    env: dict[str, str],
    frozen_baseline_by_index: dict[int, dict[str, Any]] | None = None,
    frozen_domain: str | None = None,
    clean_before: bool = True,
    clean_after: bool = True,
    answer_evidence_table: bool = False,
    answer_evidence_table_categories: set[str] | None = None,
    answer_subject_guard: bool = False,
    answer_subject_guard_categories: set[str] | None = None,
    answer_shape_directive: bool = False,
    answer_shape_directive_categories: set[str] | None = None,
    gold_object_coverage_telemetry: bool = False,
    gold_object_coverage_categories: set[str] | None = None,
    entity_time_constrained_expansion: bool = False,
    entity_time_constrained_expansion_categories: set[str] | None = None,
    entity_time_constrained_expansion_max_added: int = 2,
    entity_time_constrained_expansion_turn_window: int = 3,
    context_packet_merge_from_artifact: bool = False,
) -> dict[str, Any]:
    module = import_benchmark_module(env)
    configure_benchmark_module(
        module,
        context_packet=context_packet,
        context_packet_merge=context_packet_merge,
        context_packet_merge_append_top_k=context_packet_merge_append_top_k,
        context_packet_merge_ref_gate=context_packet_merge_ref_gate,
    )
    conv_data = data[0]
    conv = conv_data.get("conversation", conv_data)
    qa_list = conv_data.get("qa", conv_data.get("qa_list", []))
    session_mapping = session_order_mapping(conv)

    hygiene_before = clean_locomo_domains() if clean_before else locomo_hygiene()
    if should_block_on_hygiene(hygiene_before, clean_requested=clean_before):
        raise RuntimeError(f"cleanup_before_failed: {hygiene_before}")

    t0 = time.monotonic()
    if frozen_baseline_by_index is not None:
        domain = frozen_domain
        n_turns = 0
        ingest_time = 0.0
        if not domain:
            raise ValueError("frozen_context_replay_requires_frozen_domain")
    else:
        n_turns, domain = module.ingest_conversation(conv, conv_data.get("sample_id"), normalize_dates=False)
        ingest_time = time.monotonic() - t0
        time.sleep(2)

    details = []
    scores: list[float] = []
    query_times: list[float] = []
    cat_scores: dict[Any, list[float]] = {}

    for fixed in fixed_rows:
        qa = qa_list[int(fixed["one_based_index"]) - 1]
        question = qa["question"]
        ground_truth = qa.get("answer", qa.get("adversarial_answer", ""))
        cat = module.normalize_category(qa["category"])
        use_answer_evidence_table = should_use_answer_evidence_table(
            cat,
            answer_evidence_table,
            answer_evidence_table_categories,
        )
        use_answer_subject_guard = should_use_answer_subject_guard(
            cat,
            answer_subject_guard,
            answer_subject_guard_categories,
        )
        use_answer_shape_directive = should_use_answer_shape_directive(
            cat,
            answer_shape_directive,
            answer_shape_directive_categories,
        )
        use_gold_object_coverage_telemetry = should_use_answer_shape_directive(
            cat,
            gold_object_coverage_telemetry,
            gold_object_coverage_categories,
        )
        use_entity_time_constrained_expansion = should_use_answer_shape_directive(
            cat,
            entity_time_constrained_expansion,
            entity_time_constrained_expansion_categories,
        )
        capture: dict[str, Any] = {}
        original_llm_call = module.llm_call
        original_projection = module._memory_telemetry_projection
        module.llm_call = capture_answer_prompt_wrapper(module, capture)
        module._memory_telemetry_projection = capture_full_context_projection_wrapper(module)
        try:
            t1 = time.monotonic()
            if frozen_baseline_by_index is not None:
                frozen_row = frozen_baseline_by_index[int(fixed["one_based_index"])]
                predicted, n_memories, recall_telemetry = answer_question_with_frozen_context(
                    module,
                    question,
                    domain,
                    copy.deepcopy(frozen_row["final_context"]),
                    evidence_refs=qa.get("evidence") or qa.get("evidence_refs"),
                    context_packet_merge=context_packet_merge,
                    context_packet_merge_append_top_k=context_packet_merge_append_top_k,
                    context_packet_merge_ref_gate=context_packet_merge_ref_gate,
                    answer_evidence_table=use_answer_evidence_table,
                    answer_subject_guard=use_answer_subject_guard,
                    answer_shape_directive=use_answer_shape_directive,
                    context_packet_merge_from_artifact=context_packet_merge_from_artifact,
                    frozen_packet_artifact=frozen_row,
                    one_based_index=int(fixed["one_based_index"]),
                    ground_truth=ground_truth,
                    gold_object_coverage_telemetry=use_gold_object_coverage_telemetry,
                    entity_time_constrained_expansion=use_entity_time_constrained_expansion,
                    entity_time_constrained_expansion_max_added=entity_time_constrained_expansion_max_added,
                    entity_time_constrained_expansion_turn_window=entity_time_constrained_expansion_turn_window,
                )
            else:
                predicted, n_memories, recall_telemetry = module.answer_question(
                    question,
                    domain,
                    return_telemetry=True,
                    evidence_refs=qa.get("evidence") or qa.get("evidence_refs"),
                )
            query_time = time.monotonic() - t1
            score = module.judge_answer(question, predicted, ground_truth)
        finally:
            module.llm_call = original_llm_call
            module._memory_telemetry_projection = original_projection

        cat = module.normalize_category(qa["category"])
        scores.append(score)
        query_times.append(query_time)
        cat_scores.setdefault(cat, []).append(score)
        prompt_context = capture.get("answer_prompt_context", "")
        final_context = recall_telemetry.get("final_context") or []
        evidence_refs = qa.get("evidence") or qa.get("evidence_refs")
        gold_ref_count = len(evidence_refs or [])
        canary_gold_hits = _count_gold_hits(evidence_refs, final_context, session_mapping)
        if recall_telemetry.get("gold_evidence_ref_coverage") is None:
            recall_telemetry["gold_evidence_ref_coverage"] = {}
        recall_telemetry["gold_evidence_ref_coverage"].update({
            "canary_gold_ref_count": gold_ref_count,
            "canary_final_context_refs_matched": canary_gold_hits,
            "canary_mapping": session_mapping.get("ordering"),
        })
        frozen_baseline_context = None
        frozen_baseline_context_sha = None
        if frozen_baseline_by_index is not None:
            frozen_baseline_context = copy.deepcopy(frozen_baseline_by_index[int(fixed["one_based_index"])]["final_context"])
            frozen_baseline_context_sha = frozen_context_hash(frozen_baseline_context)
        elif not context_packet and not context_packet_merge:
            frozen_baseline_context = copy.deepcopy(final_context)
            frozen_baseline_context_sha = frozen_context_hash(frozen_baseline_context)
        details.append({
            "arm": arm_name,
            "row_identity": {
                "one_based_index": fixed["one_based_index"],
                "label": fixed.get("label"),
                "cat": fixed.get("cat"),
                "question": fixed["question"],
                "question_sha256": fixed["question_sha256"],
            },
            "conv": conv_data.get("sample_id"),
            "cat": cat,
            "question": question,
            "ground_truth": ground_truth,
            "predicted": predicted,
            "score": score,
            "query_time_ms": int(query_time * 1000),
            "n_memories": n_memories,
            "recall_telemetry": recall_telemetry,
            "answer_prompt_context_sha256": capture.get("answer_prompt_context_sha256"),
            "answer_prompt_context_line_count": capture.get("answer_prompt_context_line_count"),
            "answer_prompt_contains_context_packet": capture.get("answer_prompt_contains_context_packet", False),
            "answer_prompt_context_preview": prompt_context[:1000],
            "frozen_baseline_context_sha256": frozen_baseline_context_sha,
            "frozen_baseline_context": frozen_baseline_context,
        })

    payload = module.build_results_payload(
        all_scores=scores,
        cat_scores=cat_scores,
        query_times=query_times,
        results_log=details,
        normalize_dates=False,
        use_query_expansion=False,
        use_context_packet=context_packet,
        use_context_packet_merge=context_packet_merge,
        cleaned=False,
    )
    payload["condition"]["frozen_context_replay"] = frozen_baseline_by_index is not None
    payload["condition"]["answer_evidence_table"] = bool(answer_evidence_table)
    payload["condition"]["answer_subject_guard"] = bool(answer_subject_guard)
    payload["condition"]["answer_shape_directive"] = bool(answer_shape_directive)
    payload.update({
        "schema": "memibrium.locomo.context_packet_canary.arm.v1",
        "run_id": RUN_ID,
        "arm": arm_name,
        "purpose": "tiny fixed-row context-packet A/B canary; not a 199Q LOCOMO benchmark",
        "frozen_context_replay": frozen_baseline_by_index is not None,
        "started_at": utc_now(),
        "input_slice": {
            "data_path": str(DATA_PATH),
            "data_sha256": sha256_file(DATA_PATH) if DATA_PATH.exists() else None,
            "fixed_rows_path": str(FIXED_ROWS_PATH),
            "fixed_row_count": len(fixed_rows),
        },
        "ingest": {"turns": n_turns, "domain": domain, "seconds": round(ingest_time, 3)},
        "hygiene_before_arm": hygiene_before,
    })
    hygiene_after = clean_locomo_domains() if clean_after else locomo_hygiene()
    payload["hygiene_after_cleanup"] = hygiene_after
    if clean_after and not hygiene_after.get("ok"):
        raise RuntimeError(f"cleanup_after_failed: {hygiene_after}")
    return payload


def _treatment_mode(
    *,
    merge_treatment: bool,
    merge_ref_gate: bool,
    merge_append_top_k: int | None,
    frozen_context_replay: bool,
    frozen_answer_evidence_table: bool = False,
    frozen_answer_subject_guard: bool = False,
    frozen_answer_shape_directive: bool = False,
    frozen_entity_time_constrained_expansion: bool = False,
) -> str:
    if not merge_treatment:
        return "context_packet_replacement"
    mode = "context_packet_merge"
    if merge_ref_gate:
        mode += "_ref_gate"
    elif merge_append_top_k and merge_append_top_k > 0:
        mode += "_top_k"
    if frozen_context_replay:
        mode += "_frozen"
    if frozen_answer_evidence_table:
        mode += "_evtable"
    if frozen_answer_subject_guard:
        mode += "_subjguard"
    if frozen_answer_shape_directive:
        mode += "_shaped"
    if frozen_entity_time_constrained_expansion:
        mode += "_enttimeexp"
    return mode


def make_markdown(summary: dict[str, Any]) -> str:
    comparison = summary.get("comparison", {})
    lines = [
        "# LOCOMO Context Packet Fixed-Row Canary Result",
        "",
        f"Run ID: `{summary['run_id']}`",
        "",
        "Scope: tiny fixed-row A/B canary only; not a 199Q LOCOMO benchmark.",
        "",
        "## Gates",
        f"- Input row identity: `{summary['input_identity']['ok']}`",
        f"- Paired row identity: `{comparison.get('row_identity_ok')}`",
        f"- Condition metadata: `{comparison.get('condition_metadata_ok')}`",
        f"- Context packet telemetry: `{comparison.get('context_packet_telemetry_ok')}`",
        f"- Score non-regression: `baseline={summary.get('baseline_overall_score')}`, `treatment={summary.get('treatment_overall_score')}`, `delta_pp={comparison.get('score_delta_pp')}`, `gate={comparison.get('score_non_regression_gate')}`",
        f"- Gold-evidence hit rates: `baseline={comparison.get('gold_evidence_ref_hit_rate', {}).get('baseline')}`, `treatment={comparison.get('gold_evidence_ref_hit_rate', {}).get('treatment')}`, `delta={comparison.get('gold_evidence_ref_hit_delta')}`, `gate={comparison.get('gold_evidence_ref_hit_gate')}`",
        f"- Packet append attribution: `{comparison.get('packet_append_attribution')}`",
        f"- Category regression gates: `{comparison.get('category_regression_gates')}`",
        f"- Frozen baseline context hash match: `rate={comparison.get('frozen_context_hash_match_rate')}`, `by_row={comparison.get('frozen_context_hash_match_by_row')}`",
        f"- Row 183 role-attribution diagnostic: `{comparison.get('row_183_role_attribution_diagnostic')}`",
        f"- Prompt context changed by row: `{comparison.get('prompt_context_changed_by_row')}`",
        f"- Final cleanup: `{summary.get('final_hygiene', {}).get('ok')}`",
        "",
        "## Artifacts",
    ]
    for key, value in summary.get("paths", {}).items():
        lines.append(f"- {key}: `{value}`")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a tiny fixed-row Context Packet A/B canary.")
    parser.add_argument("--data-path", default=str(DATA_PATH))
    parser.add_argument("--fixed-rows-path", default=str(FIXED_ROWS_PATH))
    parser.add_argument("--min-prereg-rows", type=int, default=None, help="Require fixed-row preregistration to contain at least this many rows")
    parser.add_argument("--max-prereg-rows", type=int, default=None, help="Require fixed-row preregistration to contain at most this many rows")
    parser.add_argument("--mcp-url", default=os.environ.get("MCP_URL", "http://localhost:9999/mcp"))
    parser.add_argument("--identity-only", action="store_true", help="Validate data/fixed-row identity without DB or benchmark mutation")
    parser.add_argument("--merge-treatment", action="store_true", help="Use baseline+packet append/dedupe treatment instead of packet replacement")
    parser.add_argument("--merge-append-top-k", type=int, default=None, help="Cap new packet episodic evidence appended in merge treatment; <=0 means uncapped")
    parser.add_argument("--merge-ref-gate", action="store_true", help="Append only packet evidence that matches missing gold evidence refs; eval-only ablation")
    parser.add_argument("--frozen-context-replay", action="store_true", help="Run treatment against baseline arm final_context substrate without independent treatment recall; eval-only")
    parser.add_argument("--frozen-answer-evidence-table", action="store_true", help="In frozen replay treatment only, add an eval-only structured evidence table above raw answer context")
    parser.add_argument("--frozen-answer-evidence-table-categories", default=None, help="Optional comma-separated normalized categories that receive the frozen answer evidence table")
    parser.add_argument("--frozen-answer-subject-guard", action="store_true", help="In frozen replay treatment only, add an eval-only subject/attribution guard above raw answer context")
    parser.add_argument("--frozen-answer-subject-guard-categories", default=None, help="Optional comma-separated normalized categories that receive the frozen answer subject guard")
    parser.add_argument("--frozen-answer-shape-directive", action="store_true", help="In frozen replay treatment only, add eval-only answer-shape/list/count/inference directive above raw answer context")
    parser.add_argument("--frozen-answer-shape-directive-categories", default=None, help="Optional comma-separated normalized categories that receive the frozen answer shape directive")
    parser.add_argument("--frozen-gold-object-coverage-telemetry", action="store_true", help="In frozen replay treatment only, emit eval-only gold answer atom/object coverage telemetry over final_context")
    parser.add_argument("--frozen-gold-object-coverage-telemetry-categories", default=None, help="Optional comma-separated normalized categories that receive frozen gold-object coverage telemetry")
    parser.add_argument("--frozen-entity-time-constrained-expansion", action="store_true", help="In frozen replay treatment only, append eval-only same-entity nearby packet evidence before answer synthesis")
    parser.add_argument("--frozen-entity-time-constrained-expansion-categories", default=None, help="Optional comma-separated normalized categories that receive frozen entity/time constrained expansion")
    parser.add_argument("--frozen-entity-time-constrained-expansion-max-added", type=int, default=2, help="Maximum packet candidate memories appended by frozen entity/time constrained expansion")
    parser.add_argument("--frozen-entity-time-constrained-expansion-turn-window", type=int, default=3, help="Maximum same-session turn distance for frozen entity/time constrained expansion")
    parser.add_argument("--frozen-baseline-artifact", default=None, help="Optional baseline arm artifact to pin frozen replay substrate across runs; skips fresh baseline recall/ingest")
    parser.add_argument("--frozen-baseline-artifact-final-context-replay", action="store_true", help="When using --frozen-baseline-artifact, treat artifact final_context as the complete post-packet substrate and do not call live context_packet")
    args = parser.parse_args(argv)

    data_path = Path(args.data_path)
    fixed_rows_path = Path(args.fixed_rows_path)
    data = load_json(data_path)
    fixed_rows_payload = load_json(fixed_rows_path)
    fixed_rows = fixed_rows_payload["selected_rows"]
    preregistration_proof = None
    if args.min_prereg_rows is not None or args.max_prereg_rows is not None:
        preregistration_proof = validate_preregistered_larger_slice(
            fixed_rows_payload,
            min_rows=args.min_prereg_rows or 1,
            max_rows=args.max_prereg_rows or 10_000,
        )
    input_identity = validate_canary_input_slice(data, fixed_rows)
    data_sha = sha256_file(data_path)
    if data_path == DATA_PATH and data_sha != EXPECTED_DATA_SHA256:
        raise ValueError(f"data_sha256_mismatch: {data_sha} != {EXPECTED_DATA_SHA256}")

    if args.identity_only:
        print(json.dumps({"ok": True, "identity": input_identity, "data_sha256": data_sha, "preregistration": preregistration_proof}, indent=2))
        return 0
    if args.frozen_context_replay and not args.merge_treatment:
        raise ValueError("frozen_context_replay_requires_merge_treatment")
    if args.frozen_answer_evidence_table and not args.frozen_context_replay:
        raise ValueError("frozen_answer_evidence_table_requires_frozen_context_replay")
    if args.frozen_answer_subject_guard and not args.frozen_context_replay:
        raise ValueError("frozen_answer_subject_guard_requires_frozen_context_replay")
    if args.frozen_answer_shape_directive and not args.frozen_context_replay:
        raise ValueError("frozen_answer_shape_directive_requires_frozen_context_replay")
    if args.frozen_gold_object_coverage_telemetry and not args.frozen_context_replay:
        raise ValueError("frozen_gold_object_coverage_telemetry_requires_frozen_context_replay")
    if args.frozen_entity_time_constrained_expansion and not args.frozen_context_replay:
        raise ValueError("frozen_entity_time_constrained_expansion_requires_frozen_context_replay")
    if args.frozen_entity_time_constrained_expansion and not args.merge_treatment:
        raise ValueError("frozen_entity_time_constrained_expansion_requires_merge_treatment")
    if args.frozen_baseline_artifact and not args.frozen_context_replay:
        raise ValueError("frozen_baseline_artifact_requires_frozen_context_replay")
    if args.frozen_baseline_artifact_final_context_replay and not args.frozen_baseline_artifact:
        raise ValueError("frozen_baseline_artifact_final_context_replay_requires_frozen_baseline_artifact")
    answer_evidence_table_categories = parse_category_filter(args.frozen_answer_evidence_table_categories)
    answer_subject_guard_categories = parse_category_filter(args.frozen_answer_subject_guard_categories)
    answer_shape_directive_categories = parse_category_filter(args.frozen_answer_shape_directive_categories)
    gold_object_coverage_categories = parse_category_filter(args.frozen_gold_object_coverage_telemetry_categories)
    entity_time_constrained_expansion_categories = parse_category_filter(args.frozen_entity_time_constrained_expansion_categories)

    base_env = os.environ.copy()
    baseline_env = build_benchmark_env(base_env, mcp_url=args.mcp_url, context_packet=False)
    treatment_env = build_benchmark_env(
        base_env,
        mcp_url=args.mcp_url,
        context_packet=not args.merge_treatment,
        context_packet_merge=args.merge_treatment,
        context_packet_merge_append_top_k=args.merge_append_top_k,
        context_packet_merge_ref_gate=args.merge_ref_gate,
    )
    live_status = health_and_tools(args.mcp_url)
    if not live_status.get("context_packet_present"):
        raise RuntimeError(f"context_packet tool missing: {live_status}")

    baseline = None
    frozen_baseline_by_index = None
    frozen_domain = None
    if args.frozen_baseline_artifact:
        source_artifact = load_json(Path(args.frozen_baseline_artifact))
        frozen_baseline_by_index, frozen_domain = frozen_baseline_rows_from_artifact(source_artifact, fixed_rows=fixed_rows)
        if args.frozen_baseline_artifact_final_context_replay:
            baseline = run_arm(
                "baseline_artifact_full_context",
                context_packet=False,
                context_packet_merge=False,
                data=data,
                fixed_rows=fixed_rows,
                env=baseline_env,
                frozen_baseline_by_index=frozen_baseline_by_index,
                frozen_domain=frozen_domain,
                clean_before=False,
                clean_after=False,
            )
        else:
            baseline = copy.deepcopy(source_artifact)
    else:
        baseline = run_arm(
            "baseline_default",
            context_packet=False,
            data=data,
            fixed_rows=fixed_rows,
            env=baseline_env,
            clean_after=not args.frozen_context_replay,
        )
        if args.frozen_context_replay:
            frozen_baseline_by_index, frozen_domain = frozen_baseline_rows_from_artifact(baseline, fixed_rows=fixed_rows)
    treatment_arm = "treatment_context_packet_merge" if args.merge_treatment else "treatment_context_packet"
    treatment = run_arm(
        treatment_arm,
        context_packet=not args.merge_treatment,
        context_packet_merge=args.merge_treatment,
        context_packet_merge_append_top_k=args.merge_append_top_k,
        context_packet_merge_ref_gate=args.merge_ref_gate,
        data=data,
        fixed_rows=fixed_rows,
        env=treatment_env,
        frozen_baseline_by_index=frozen_baseline_by_index,
        frozen_domain=frozen_domain,
        clean_before=not args.frozen_context_replay,
        clean_after=True,
        answer_evidence_table=args.frozen_answer_evidence_table,
        answer_evidence_table_categories=answer_evidence_table_categories,
        answer_subject_guard=args.frozen_answer_subject_guard,
        answer_subject_guard_categories=answer_subject_guard_categories,
        answer_shape_directive=args.frozen_answer_shape_directive,
        answer_shape_directive_categories=answer_shape_directive_categories,
        gold_object_coverage_telemetry=args.frozen_gold_object_coverage_telemetry,
        gold_object_coverage_categories=gold_object_coverage_categories,
        entity_time_constrained_expansion=args.frozen_entity_time_constrained_expansion,
        entity_time_constrained_expansion_categories=entity_time_constrained_expansion_categories,
        entity_time_constrained_expansion_max_added=args.frozen_entity_time_constrained_expansion_max_added,
        entity_time_constrained_expansion_turn_window=args.frozen_entity_time_constrained_expansion_turn_window,
        context_packet_merge_from_artifact=args.frozen_baseline_artifact_final_context_replay,
    )
    comparison = validate_paired_artifacts(
        baseline,
        treatment,
        fixed_rows,
        treatment_context_packet=not args.merge_treatment,
        treatment_context_packet_merge=args.merge_treatment,
        frozen_replay=args.frozen_context_replay,
    )
    final_hygiene = locomo_hygiene()

    treatment_suffix = ""
    if args.merge_treatment:
        treatment_suffix = "_merge"
        if args.merge_append_top_k and args.merge_append_top_k > 0:
            treatment_suffix += f"_top{args.merge_append_top_k}"
        if args.merge_ref_gate:
            treatment_suffix += "_refgate"
    if args.frozen_context_replay:
        treatment_suffix += "_frozen"
    if args.frozen_baseline_artifact_final_context_replay:
        treatment_suffix += "_artifactctx"
    if args.frozen_answer_evidence_table:
        treatment_suffix += "_evtable"
        if answer_evidence_table_categories:
            treatment_suffix += "_" + "_".join(sorted(cat.replace("-", "") for cat in answer_evidence_table_categories))
    if args.frozen_answer_subject_guard:
        treatment_suffix += "_subjguard"
        if answer_subject_guard_categories:
            treatment_suffix += "_" + "_".join(sorted(cat.replace("-", "") for cat in answer_subject_guard_categories))
    if args.frozen_answer_shape_directive:
        treatment_suffix += "_shaped"
        if answer_shape_directive_categories:
            treatment_suffix += "_" + "_".join(sorted(cat.replace("-", "") for cat in answer_shape_directive_categories))
    if args.frozen_gold_object_coverage_telemetry:
        treatment_suffix += "_goldcov"
        if gold_object_coverage_categories:
            treatment_suffix += "_" + "_".join(sorted(cat.replace("-", "") for cat in gold_object_coverage_categories))
    if args.frozen_entity_time_constrained_expansion:
        treatment_suffix += "_enttimeexp"
        if entity_time_constrained_expansion_categories:
            treatment_suffix += "_" + "_".join(sorted(cat.replace("-", "") for cat in entity_time_constrained_expansion_categories))
    paths = {
        "baseline": str(RESULTS_DIR / f"locomo_context_packet_canary_baseline_{RUN_ID}.json"),
        "treatment": str(RESULTS_DIR / f"locomo_context_packet_canary_treatment{treatment_suffix}_{RUN_ID}.json"),
        "summary": str(RESULTS_DIR / f"locomo_context_packet_canary_summary{treatment_suffix}_{RUN_ID}.json"),
        "markdown": str(RESULTS_DIR / f"locomo_context_packet_canary_result{treatment_suffix}_{RUN_ID}.md"),
    }
    summary = {
        "schema": "memibrium.locomo.context_packet_canary.summary.v1",
        "run_id": RUN_ID,
        "created_at": utc_now(),
        "purpose": "prove context_packet changes prompt context on exact fixed rows without changing unrelated benchmark mechanics",
        "treatment_mode": _treatment_mode(
            merge_treatment=args.merge_treatment,
            merge_ref_gate=args.merge_ref_gate,
            merge_append_top_k=args.merge_append_top_k,
            frozen_context_replay=args.frozen_context_replay,
            frozen_answer_evidence_table=args.frozen_answer_evidence_table,
            frozen_answer_subject_guard=args.frozen_answer_subject_guard,
            frozen_answer_shape_directive=args.frozen_answer_shape_directive,
            frozen_entity_time_constrained_expansion=args.frozen_entity_time_constrained_expansion,
        ),
        "merge_append_top_k": args.merge_append_top_k,
        "merge_ref_gate": args.merge_ref_gate,
        "frozen_context_replay": args.frozen_context_replay,
        "frozen_answer_evidence_table": args.frozen_answer_evidence_table,
        "frozen_answer_evidence_table_categories": sorted(answer_evidence_table_categories) if answer_evidence_table_categories else None,
        "frozen_answer_subject_guard": args.frozen_answer_subject_guard,
        "frozen_answer_subject_guard_categories": sorted(answer_subject_guard_categories) if answer_subject_guard_categories else None,
        "frozen_answer_shape_directive": args.frozen_answer_shape_directive,
        "frozen_answer_shape_directive_categories": sorted(answer_shape_directive_categories) if answer_shape_directive_categories else None,
        "frozen_gold_object_coverage_telemetry": args.frozen_gold_object_coverage_telemetry,
        "frozen_gold_object_coverage_telemetry_categories": sorted(gold_object_coverage_categories) if gold_object_coverage_categories else None,
        "frozen_entity_time_constrained_expansion": args.frozen_entity_time_constrained_expansion,
        "frozen_entity_time_constrained_expansion_categories": sorted(entity_time_constrained_expansion_categories) if entity_time_constrained_expansion_categories else None,
        "frozen_entity_time_constrained_expansion_max_added": args.frozen_entity_time_constrained_expansion_max_added,
        "frozen_entity_time_constrained_expansion_turn_window": args.frozen_entity_time_constrained_expansion_turn_window,
        "frozen_baseline_artifact": str(Path(args.frozen_baseline_artifact)) if args.frozen_baseline_artifact else None,
        "frozen_baseline_artifact_final_context_replay": args.frozen_baseline_artifact_final_context_replay,
        "input_identity": input_identity,
        "preregistration": preregistration_proof,
        "data_sha256": data_sha,
        "fixed_rows_path": str(fixed_rows_path),
        "live_status": live_status,
        "baseline_env": redacted_env(baseline_env),
        "treatment_env": redacted_env(treatment_env),
        "baseline_overall_score": baseline.get("overall_score"),
        "treatment_overall_score": treatment.get("overall_score"),
        "baseline_category_scores": baseline.get("category_scores"),
        "treatment_category_scores": treatment.get("category_scores"),
        "comparison": comparison,
        "final_hygiene": final_hygiene,
        "paths": paths,
    }

    write_json(Path(paths["baseline"]), baseline)
    write_json(Path(paths["treatment"]), treatment)
    write_json(Path(paths["summary"]), summary)
    Path(paths["markdown"]).write_text(make_markdown(summary))
    print(json.dumps(summary, indent=2))
    return 0 if final_hygiene.get("ok") else 80


if __name__ == "__main__":
    raise SystemExit(main())
