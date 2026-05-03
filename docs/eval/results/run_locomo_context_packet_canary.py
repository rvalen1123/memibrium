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


def build_benchmark_env(base_env: dict[str, str], *, mcp_url: str, context_packet: bool, context_packet_merge: bool = False) -> dict[str, str]:
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


def validate_paired_artifacts(
    baseline: dict[str, Any],
    treatment: dict[str, Any],
    fixed_rows: list[dict[str, Any]],
    *,
    treatment_context_packet: bool = True,
    treatment_context_packet_merge: bool = False,
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
    if baseline_hit_rate is not None and treatment_hit_rate is not None:
        hit_delta = round(treatment_hit_rate - baseline_hit_rate, 4)

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


def configure_benchmark_module(module: Any, *, context_packet: bool, context_packet_merge: bool = False) -> None:
    module.USE_QUERY_EXPANSION = False
    module.USE_CONTEXT_PACKET = bool(context_packet)
    module.USE_CONTEXT_PACKET_MERGE = bool(context_packet_merge)
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


def run_arm(
    arm_name: str,
    *,
    context_packet: bool,
    context_packet_merge: bool = False,
    data: list[dict[str, Any]],
    fixed_rows: list[dict[str, Any]],
    env: dict[str, str],
) -> dict[str, Any]:
    module = import_benchmark_module(env)
    configure_benchmark_module(module, context_packet=context_packet, context_packet_merge=context_packet_merge)
    conv_data = data[0]
    conv = conv_data.get("conversation", conv_data)
    qa_list = conv_data.get("qa", conv_data.get("qa_list", []))
    session_mapping = session_order_mapping(conv)

    hygiene_before = clean_locomo_domains()
    if not hygiene_before.get("ok"):
        raise RuntimeError(f"cleanup_before_failed: {hygiene_before}")

    t0 = time.monotonic()
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
        capture: dict[str, Any] = {}
        original_llm_call = module.llm_call
        module.llm_call = capture_answer_prompt_wrapper(module, capture)
        try:
            t1 = time.monotonic()
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
    payload.update({
        "schema": "memibrium.locomo.context_packet_canary.arm.v1",
        "run_id": RUN_ID,
        "arm": arm_name,
        "purpose": "tiny fixed-row context-packet A/B canary; not a 199Q LOCOMO benchmark",
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
    hygiene_after = clean_locomo_domains()
    payload["hygiene_after_cleanup"] = hygiene_after
    if not hygiene_after.get("ok"):
        raise RuntimeError(f"cleanup_after_failed: {hygiene_after}")
    return payload


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
        f"- Gold-evidence hit rates: `baseline={comparison.get('gold_evidence_ref_hit_rate', {}).get('baseline')}`, `treatment={comparison.get('gold_evidence_ref_hit_rate', {}).get('treatment')}`, `delta={comparison.get('gold_evidence_ref_hit_delta')}`",
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
    parser.add_argument("--mcp-url", default=os.environ.get("MCP_URL", "http://localhost:9999/mcp"))
    parser.add_argument("--identity-only", action="store_true", help="Validate data/fixed-row identity without DB or benchmark mutation")
    parser.add_argument("--merge-treatment", action="store_true", help="Use baseline+packet append/dedupe treatment instead of packet replacement")
    args = parser.parse_args(argv)

    data_path = Path(args.data_path)
    fixed_rows_path = Path(args.fixed_rows_path)
    data = load_json(data_path)
    fixed_rows = load_json(fixed_rows_path)["selected_rows"]
    input_identity = validate_canary_input_slice(data, fixed_rows)
    data_sha = sha256_file(data_path)
    if data_path == DATA_PATH and data_sha != EXPECTED_DATA_SHA256:
        raise ValueError(f"data_sha256_mismatch: {data_sha} != {EXPECTED_DATA_SHA256}")

    if args.identity_only:
        print(json.dumps({"ok": True, "identity": input_identity, "data_sha256": data_sha}, indent=2))
        return 0

    base_env = os.environ.copy()
    baseline_env = build_benchmark_env(base_env, mcp_url=args.mcp_url, context_packet=False)
    treatment_env = build_benchmark_env(
        base_env,
        mcp_url=args.mcp_url,
        context_packet=not args.merge_treatment,
        context_packet_merge=args.merge_treatment,
    )
    live_status = health_and_tools(args.mcp_url)
    if not live_status.get("context_packet_present"):
        raise RuntimeError(f"context_packet tool missing: {live_status}")

    baseline = run_arm("baseline_default", context_packet=False, data=data, fixed_rows=fixed_rows, env=baseline_env)
    treatment_arm = "treatment_context_packet_merge" if args.merge_treatment else "treatment_context_packet"
    treatment = run_arm(
        treatment_arm,
        context_packet=not args.merge_treatment,
        context_packet_merge=args.merge_treatment,
        data=data,
        fixed_rows=fixed_rows,
        env=treatment_env,
    )
    comparison = validate_paired_artifacts(
        baseline,
        treatment,
        fixed_rows,
        treatment_context_packet=not args.merge_treatment,
        treatment_context_packet_merge=args.merge_treatment,
    )
    final_hygiene = locomo_hygiene()

    paths = {
        "baseline": str(RESULTS_DIR / f"locomo_context_packet_canary_baseline_{RUN_ID}.json"),
        "treatment": str(RESULTS_DIR / f"locomo_context_packet_canary_treatment{'_merge' if args.merge_treatment else ''}_{RUN_ID}.json"),
        "summary": str(RESULTS_DIR / f"locomo_context_packet_canary_summary{'_merge' if args.merge_treatment else ''}_{RUN_ID}.json"),
        "markdown": str(RESULTS_DIR / f"locomo_context_packet_canary_result{'_merge' if args.merge_treatment else ''}_{RUN_ID}.md"),
    }
    summary = {
        "schema": "memibrium.locomo.context_packet_canary.summary.v1",
        "run_id": RUN_ID,
        "created_at": utc_now(),
        "purpose": "prove context_packet changes prompt context on exact fixed rows without changing unrelated benchmark mechanics",
        "treatment_mode": "context_packet_merge" if args.merge_treatment else "context_packet_replacement",
        "input_identity": input_identity,
        "data_sha256": data_sha,
        "fixed_rows_path": str(fixed_rows_path),
        "live_status": live_status,
        "baseline_env": redacted_env(baseline_env),
        "treatment_env": redacted_env(treatment_env),
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
