#!/usr/bin/env python3
"""Step 5o bounded checkpoint / trace-lite execution harness.

Execution scope is constrained by docs/eval/locomo_step5o_bounded_checkpoint_trace_lite_preregistration_2026-05-02.md.
This artifact is intentionally outside product/benchmark source. It may check out
checkpoint commits and start temporary server processes only when explicitly run.
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[3]
DATA_PATH = Path("/tmp/locomo/data/locomo10.json")
FIXED_ROWS_PATH = ROOT / "docs/eval/results/locomo_step5o_prereg_fixed_rows_2026-05-02.json"
with FIXED_ROWS_PATH.open() as _fixed_rows_f:
    FIXED_ROWS = json.load(_fixed_rows_f)["selected_rows"]
RESULTS_DIR = ROOT / "docs/eval/results"
RUN_ID = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")

EXPECTED_DATA_SHA256 = "79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4"
TARGET_FILES = ["benchmark_scripts/locomo_bench_v2.py", "hybrid_retrieval.py", "server.py"]

ARMS = {
    "A_f2466c9": {
        "checkpoint": "f2466c9",
        "purpose": "test whether f2466c9 source/runtime reproduces low-context family on fixed rows",
        "expected_hashes": {
            "benchmark_scripts/locomo_bench_v2.py": "78721cdc4b76e41b1960b1f8340469e048b3808b62f0889d94cae8921850d57b",
            "hybrid_retrieval.py": "a35fe1624ff17bc19190a8ee5959a767b690cb44303907fbfb7f5373fb771fce",
            "server.py": "5efefae8f05b45974dab6a379403e1a94d00a60e2bfb76b403d4ebe4a7e360d5",
        },
    },
    "B_current": {
        "checkpoint": "8a0e421",
        "purpose": "test whether current/post-cb56559 source reproduces high-context trace mechanics",
        "expected_hashes": {
            "benchmark_scripts/locomo_bench_v2.py": "32dd68d0a0bad7322e8eea67bea90628d0cf42415769802f9e48a4528f3454ff",
            "hybrid_retrieval.py": "2ba660f547432c7fa5ae88955ee97024f5c39848790060358c82dcf0a8259c07",
            "server.py": "150b161bd9bef5c021fd7f1b32472623b3cc03baac6d13ff42edd501ae3f6f1a",
        },
    },
}

REDACT_KEYS = {"KEY", "TOKEN", "SECRET", "PASSWORD", "PASS", "CREDENTIAL"}
ENV_KEYS = [
    "MCP_URL",
    "OPENAI_BASE_URL",
    "OPENAI_API_KEY",
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_API_KEY",
    "AZURE_OPENAI_DEPLOYMENT",
    "AZURE_API_VERSION",
    "AZURE_EMBEDDING_ENDPOINT",
    "AZURE_EMBEDDING_DEPLOYMENT",
    "AZURE_EMBEDDING_API_KEY",
    "AZURE_CHAT_ENDPOINT",
    "AZURE_CHAT_DEPLOYMENT",
    "AZURE_CHAT_API_KEY",
    "ANSWER_MODEL",
    "JUDGE_MODEL",
    "CHAT_MODEL",
    "EMBEDDING_MODEL",
    "EMBEDDING_BASE_URL",
    "USE_QUERY_EXPANSION",
    "INCLUDE_RECALL_TELEMETRY",
    "LOCOMO_RETRIEVAL_TELEMETRY",
    "USE_CONTEXT_RERANK",
    "USE_APPEND_CONTEXT_EXPANSION",
    "USE_GATED_APPEND_CONTEXT_EXPANSION",
    "USE_LEGACY_CONTEXT_ASSEMBLY",
    "DB_HOST",
    "DB_PORT",
    "DB_NAME",
    "DB_USER",
    "DB_PASSWORD",
    "ENABLE_BACKGROUND_SCORING",
    "ENABLE_CONTRADICTION_DETECTION",
    "ENABLE_HIERARCHY_PROCESSING",
]


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def run_cmd(cmd: list[str], *, cwd: Path = ROOT, env: dict[str, str] | None = None, input_text: str | None = None, timeout: int = 120, check: bool = True) -> subprocess.CompletedProcess[str]:
    res = subprocess.run(cmd, cwd=cwd, env=env, input=input_text, text=True, capture_output=True, timeout=timeout, check=False)
    if check and res.returncode != 0:
        raise RuntimeError(
            f"command failed ({res.returncode}): {' '.join(cmd)}\nSTDOUT:\n{res.stdout[-4000:]}\nSTDERR:\n{res.stderr[-4000:]}"
        )
    return res


def git(*args: str, check: bool = True) -> str:
    return run_cmd(["git", *args], check=check).stdout.strip()


def redacted_env(env: dict[str, str]) -> dict[str, str | None]:
    out: dict[str, str | None] = {}
    for k in ENV_KEYS:
        value = env.get(k)
        if value is None:
            out[k] = None
        elif any(token in k.upper() for token in REDACT_KEYS):
            out[k] = "[REDACTED]"
        else:
            out[k] = value
    return out


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
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        env[key] = value
    return env


def benchmark_env(mcp_url: str, include_recall_telemetry: bool = True) -> dict[str, str]:
    env = load_dotenv(os.environ.copy())
    env.update({
        "MCP_URL": mcp_url.rstrip("/") + "/mcp",
        "AZURE_CHAT_DEPLOYMENT": "gpt-4.1-mini",
        "AZURE_OPENAI_DEPLOYMENT": "gpt-4.1-mini",
        "ANSWER_MODEL": "gpt-4.1-mini",
        "JUDGE_MODEL": "gpt-4.1-mini",
        "CHAT_MODEL": "gpt-4.1-mini",
        "AZURE_EMBEDDING_DEPLOYMENT": "text-embedding-3-small",
        "USE_QUERY_EXPANSION": "1",
        "DB_HOST": env.get("DB_HOST", "localhost"),
        "DB_PORT": env.get("DB_PORT", "5432"),
        "DB_NAME": env.get("DB_NAME", "memory"),
        "DB_USER": env.get("DB_USER", "memory"),
        "DB_PASSWORD": "memory",
    })
    env.pop("LOCOMO_RETRIEVAL_TELEMETRY", None)
    env.pop("USE_CONTEXT_RERANK", None)
    env.pop("USE_APPEND_CONTEXT_EXPANSION", None)
    env.pop("USE_GATED_APPEND_CONTEXT_EXPANSION", None)
    env.pop("USE_LEGACY_CONTEXT_ASSEMBLY", None)
    if include_recall_telemetry:
        env["INCLUDE_RECALL_TELEMETRY"] = "1"
    else:
        env.pop("INCLUDE_RECALL_TELEMETRY", None)
    return env


def server_env(port: int) -> dict[str, str]:
    env = load_dotenv(os.environ.copy())
    env.update({
        "DB_HOST": "localhost",
        "DB_PORT": env.get("DB_PORT", "5432"),
        "DB_NAME": env.get("DB_NAME", "memory"),
        "DB_USER": env.get("DB_USER", "memory"),
        "DB_PASSWORD": "memory",
        "AZURE_CHAT_DEPLOYMENT": "gpt-4.1-mini",
        "AZURE_OPENAI_DEPLOYMENT": "gpt-4.1-mini",
        "CHAT_MODEL": "gpt-4.1-mini",
        "AZURE_EMBEDDING_DEPLOYMENT": "text-embedding-3-small",
        "PORT": str(port),
    })
    # server.py currently ignores PORT when run as a script, so start via uvicorn below.
    return env


def psql(sql: str, *, timeout: int = 120) -> str:
    return run_cmd(["docker", "exec", "-i", "memibrium-ruvector-db", "psql", "-U", "memory", "-d", "memory", "-t", "-A"], input_text=sql, timeout=timeout).stdout.strip()


def locomo_hygiene() -> dict[str, Any]:
    sql = r"""
WITH locomo AS (SELECT id FROM memories WHERE domain LIKE 'locomo-%')
SELECT 'memories|' || (SELECT count(id) FROM locomo)
UNION ALL SELECT 'temporal_expressions|' || (SELECT count(*) FROM temporal_expressions WHERE memory_id IN (SELECT id FROM locomo))
UNION ALL SELECT 'memory_snapshots|' || (SELECT count(*) FROM memory_snapshots WHERE memory_id IN (SELECT id FROM locomo))
UNION ALL SELECT 'user_feedback|' || (SELECT count(*) FROM user_feedback WHERE memory_id IN (SELECT id FROM locomo))
UNION ALL SELECT 'contradictions|' || (SELECT count(*) FROM contradictions WHERE memory_a_id IN (SELECT id FROM locomo) OR memory_b_id IN (SELECT id FROM locomo))
UNION ALL SELECT 'memory_edges|' || (SELECT count(*) FROM memory_edges WHERE source_id IN (SELECT id FROM locomo) OR target_id IN (SELECT id FROM locomo));
"""
    lines = [line.strip() for line in psql(sql).splitlines() if "|" in line]
    counts = {k: int(v) for k, v in (line.split("|", 1) for line in lines)}
    counts["ok"] = all(v == 0 for k, v in counts.items() if k != "ok")
    return counts


def clean_locomo_domains() -> dict[str, Any]:
    sql = r"""
BEGIN;
CREATE TEMP TABLE locomo_memory_ids AS
SELECT id FROM memories WHERE domain LIKE 'locomo-%';

CREATE TEMP TABLE affected_entities AS
SELECT DISTINCT e.entity_id
FROM entities e
JOIN locomo_memory_ids lm
  ON e.memory_ids ? lm.id;

DELETE FROM temporal_expressions WHERE memory_id IN (SELECT id FROM locomo_memory_ids);
DELETE FROM memory_snapshots WHERE memory_id IN (SELECT id FROM locomo_memory_ids);
DELETE FROM user_feedback WHERE memory_id IN (SELECT id FROM locomo_memory_ids);
DELETE FROM contradictions WHERE memory_a_id IN (SELECT id FROM locomo_memory_ids) OR memory_b_id IN (SELECT id FROM locomo_memory_ids);
DELETE FROM memory_edges WHERE source_id IN (SELECT id FROM locomo_memory_ids) OR target_id IN (SELECT id FROM locomo_memory_ids);
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

CREATE TEMP TABLE entities_to_delete AS
SELECT e.entity_id
FROM entities e
JOIN affected_entities ae ON ae.entity_id = e.entity_id
WHERE jsonb_array_length(e.memory_ids) = 0;

DELETE FROM entity_relationships
WHERE entity_a IN (SELECT entity_id FROM entities_to_delete)
   OR entity_b IN (SELECT entity_id FROM entities_to_delete)
   OR entity_a NOT IN (SELECT entity_id FROM entities)
   OR entity_b NOT IN (SELECT entity_id FROM entities);

DELETE FROM entities
WHERE entity_id IN (SELECT entity_id FROM entities_to_delete);
COMMIT;
"""
    psql(sql, timeout=180)
    return locomo_hygiene()


def source_hashes() -> dict[str, str]:
    return {path: sha256_file(ROOT / path) for path in TARGET_FILES}


def docker_identity() -> dict[str, Any]:
    res = run_cmd([
        "docker", "inspect", "memibrium-server", "--format",
        "{{json .}}",
    ], check=False)
    if res.returncode != 0:
        return {"available": False, "error": res.stderr.strip()[-1000:]}
    info = json.loads(res.stdout)
    return {
        "available": True,
        "id": info.get("Id"),
        "image": info.get("Image"),
        "name": info.get("Name"),
        "state": info.get("State"),
        "config_image": (info.get("Config") or {}).get("Image"),
    }


def git_state() -> dict[str, Any]:
    return {
        "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
        "head": git("rev-parse", "HEAD"),
        "short": git("rev-parse", "--short", "HEAD"),
        "status_short": git("status", "--short"),
        "log_1": git("log", "-1", "--oneline"),
    }


def health(base_url: str) -> dict[str, Any]:
    try:
        r = httpx.get(base_url.rstrip("/") + "/health", timeout=15)
        return {"ok": r.status_code == 200, "status_code": r.status_code, "json": r.json()}
    except Exception as exc:
        return {"ok": False, "error": repr(exc)}


def load_fixed_rows_from_path() -> list[dict[str, Any]]:
    with FIXED_ROWS_PATH.open() as f:
        return json.load(f)["selected_rows"]


def load_locomo_data() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    info: dict[str, Any] = {"path": str(DATA_PATH), "exists": DATA_PATH.exists()}
    if not DATA_PATH.exists():
        return [], info
    info["sha256"] = sha256_file(DATA_PATH)
    data = json.loads(DATA_PATH.read_text())
    info["top_level_type"] = type(data).__name__
    info["conversation_count"] = len(data) if isinstance(data, list) else None
    if isinstance(data, list) and data:
        first = data[0]
        conv = first.get("conversation", first)
        qa = first.get("qa", first.get("qa_list", []))
        info.update({
            "sample_order": [row.get("sample_id") for row in data],
            "index0_sample_id": first.get("sample_id"),
            "index0_speaker_a": conv.get("speaker_a"),
            "index0_speaker_b": conv.get("speaker_b"),
            "index0_qa_count": len(qa),
            "total_qa_count": sum(len(row.get("qa", row.get("qa_list", []))) for row in data),
        })
        cats: dict[str, int] = {}
        for row in qa:
            cats[str(row.get("category"))] = cats.get(str(row.get("category")), 0) + 1
        info["index0_category_counts_raw"] = cats
    return data, info


def prove_fixed_rows(data: list[dict[str, Any]], fixed_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not isinstance(data, list) or not data:
        raise RuntimeError("LOCOMO data missing or not list")
    first = data[0]
    qa = first.get("qa", first.get("qa_list", []))
    proofs = []
    for row in fixed_rows:
        idx = int(row["one_based_index"]) - 1
        actual = qa[idx]
        q = actual["question"]
        q_hash = sha256_text(q)
        ok = q_hash == row["question_sha256"] and q == row["question"]
        proofs.append({
            "label": row["label"],
            "one_based_index": row["one_based_index"],
            "expected_question_sha256": row["question_sha256"],
            "actual_question_sha256": q_hash,
            "expected_question": row["question"],
            "actual_question": q,
            "expected_category": row["cat"],
            "actual_category": actual.get("category"),
            "ok": ok,
        })
    return proofs


def import_bench(env: dict[str, str]):
    # Import under current working tree/checkpoint after env is set so module-level flags/config bind correctly.
    for k, v in env.items():
        os.environ[k] = v
    for k in ["LOCOMO_RETRIEVAL_TELEMETRY", "USE_CONTEXT_RERANK", "USE_APPEND_CONTEXT_EXPANSION", "USE_GATED_APPEND_CONTEXT_EXPANSION", "USE_LEGACY_CONTEXT_ASSEMBLY"]:
        os.environ.pop(k, None)
    spec = importlib.util.spec_from_file_location(f"locomo_bench_v2_step5o_{RUN_ID}", ROOT / "benchmark_scripts/locomo_bench_v2.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    module.USE_QUERY_EXPANSION = True
    module.USE_CONTEXT_RERANK = False
    module.USE_APPEND_CONTEXT_EXPANSION = False
    module.USE_GATED_APPEND_CONTEXT_EXPANSION = False
    module.USE_LEGACY_CONTEXT_ASSEMBLY = False
    if hasattr(module, "INCLUDE_RECALL_TELEMETRY"):
        module.INCLUDE_RECALL_TELEMETRY = True
    return module


def normalize_memory_projection(memory: Any, rank: int, bench: Any) -> dict[str, Any]:
    content = memory.get("content", "") if isinstance(memory, dict) else str(memory)
    refs = {}
    if isinstance(memory, dict):
        refs = memory.get("refs") or {}
        if isinstance(refs, str):
            try:
                refs = json.loads(refs)
            except Exception:
                refs = {}
    return {
        "rank": rank,
        "id": memory.get("id") if isinstance(memory, dict) else None,
        "dedupe_key": bench._memory_dedupe_key(memory) if hasattr(bench, "_memory_dedupe_key") else None,
        "refs": refs if isinstance(refs, dict) else {},
        "created_at": memory.get("created_at") if isinstance(memory, dict) else None,
        "score": memory.get("score", memory.get("combined_score", memory.get("rrf_score"))) if isinstance(memory, dict) else None,
        "content_sha256": sha256_text(content),
        "snippet": content[:200].replace("\n", " "),
    }


def trace_question(bench: Any, question: str, domain: str, evidence_refs: Any = None) -> dict[str, Any]:
    queries = bench.expand_query(question) if getattr(bench, "USE_QUERY_EXPANSION", False) else [question]
    per_query = []
    candidate_memories = []
    base_seen: dict[str, Any] = {}
    recall_top_k = getattr(bench, "RECALL_TOP_K", 10)
    candidate_recall_top_k = recall_top_k
    client = httpx.Client(timeout=120)
    mcp = os.environ["MCP_URL"].rstrip("/")
    for query in queries:
        payload = {"query": query, "top_k": candidate_recall_top_k, "domain": domain, "include_telemetry": True}
        r = client.post(f"{mcp}/recall", json=payload)
        r.raise_for_status()
        recall_result = r.json()
        if isinstance(recall_result, list):
            recalled, server_telemetry = recall_result, None
        else:
            recalled = recall_result.get("results", recall_result.get("memories", []))
            server_telemetry = recall_result.get("telemetry")
        candidate_memories.extend(recalled)
        for memory in recalled[:recall_top_k]:
            key = bench._memory_dedupe_key(memory) if hasattr(bench, "_memory_dedupe_key") else memory.get("id")
            if key not in base_seen:
                base_seen[key] = memory
        per_query.append({
            "query": query,
            "query_sha256": sha256_text(query),
            "requested_top_k": candidate_recall_top_k,
            "result_count": len(recalled),
            "result_ids": [m.get("id") for m in recalled if isinstance(m, dict)],
            "result_content_hashes": [sha256_text(str(m.get("content") if isinstance(m, dict) else m or "")) for m in recalled],
            "server_telemetry": server_telemetry,
        })
    base_candidates = list(base_seen.values())
    candidate_keys = {bench._memory_dedupe_key(m) if hasattr(bench, "_memory_dedupe_key") else m.get("id") for m in base_candidates}
    candidates = list(base_candidates)
    for memory in candidate_memories:
        key = bench._memory_dedupe_key(memory) if hasattr(bench, "_memory_dedupe_key") else memory.get("id")
        if key not in candidate_keys:
            candidate_keys.add(key)
            candidates.append(memory)
    final_context = candidates[: getattr(bench, "ANSWER_CONTEXT_TOP_K", 15)]
    coverage = None
    if evidence_refs is not None and hasattr(bench, "_count_ref_coverage"):
        coverage = {
            "gold_ref_count": len(evidence_refs),
            "final_context_refs_matched": bench._count_ref_coverage(evidence_refs, final_context),
        }
    return {
        "schema": "memibrium.locomo.step5o.trace_lite.v1",
        "expanded_queries": list(queries),
        "expanded_query_count": len(queries),
        "per_query_recall": per_query,
        "counts": {
            "candidate_memories_before_dedupe": len(candidate_memories),
            "base_candidate_count_after_dedupe": len(base_candidates),
            "candidate_count_after_dedupe": len(candidates),
            "final_answer_context_count": len(final_context),
        },
        "final_context": [normalize_memory_projection(m, i, bench) for i, m in enumerate(final_context, 1)],
        "gold_evidence_ref_coverage": coverage,
    }


def start_temp_server(port: int, env: dict[str, str], log_path: Path) -> subprocess.Popen[str]:
    cmd = [sys.executable, "-m", "uvicorn", "server:app", "--host", "127.0.0.1", "--port", str(port), "--log-level", "info"]
    log_fh = log_path.open("w")
    proc = subprocess.Popen(cmd, cwd=ROOT, env=env, text=True, stdout=log_fh, stderr=subprocess.STDOUT)
    # Give ownership of fd to subprocess; close parent handle.
    log_fh.close()
    base = f"http://127.0.0.1:{port}"
    deadline = time.time() + 90
    last = None
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"temporary server exited early with {proc.returncode}; log={log_path.read_text(errors='replace')[-4000:]}")
        last = health(base)
        if last.get("ok") and last.get("json") == {"status": "ok", "engine": "memibrium"}:
            return proc
        time.sleep(2)
    raise RuntimeError(f"temporary server did not become healthy; last={last}; log={log_path.read_text(errors='replace')[-4000:]}")


def stop_proc(proc: subprocess.Popen[str] | None) -> None:
    if not proc or proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=20)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=10)


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n")


def run_arm(arm_name: str, args: argparse.Namespace) -> dict[str, Any]:
    arm = ARMS[arm_name]
    report: dict[str, Any] = {
        "schema": "memibrium.locomo.step5o.arm_result.v1",
        "run_id": RUN_ID,
        "arm": arm_name,
        "started_at": utc_now(),
        "purpose": arm["purpose"],
        "checkpoint": arm["checkpoint"],
        "blocked_labels": [],
        "events": [],
    }
    proc: subprocess.Popen[str] | None = None
    original_head = git("rev-parse", "HEAD")
    try:
        # Ensure only this execution artifact set is dirty before checkout operations.
        status = git("status", "--porcelain")
        report["initial_git_state"] = git_state()
        report["initial_status_porcelain"] = status

        git("checkout", arm["checkpoint"])
        report["checked_out_git_state"] = git_state()
        hashes = source_hashes()
        report["source_hashes"] = hashes
        if hashes != arm["expected_hashes"]:
            report["blocked_labels"].append("checkpoint_blocked_source_hash_mismatch")
            report["status"] = "blocked"
            report["expected_hashes"] = arm["expected_hashes"]
            return report

        data, data_info = load_locomo_data()
        fixed_rows = copy.deepcopy(FIXED_ROWS)
        row_proofs = prove_fixed_rows(data, fixed_rows)
        report["input_identity"] = data_info
        report["fixed_row_proofs"] = row_proofs
        if data_info.get("sha256") != EXPECTED_DATA_SHA256 or data_info.get("index0_sample_id") != "conv-26" or data_info.get("index0_qa_count") != 199:
            report["blocked_labels"].append("checkpoint_blocked_row_identity_mismatch")
            report["status"] = "blocked"
            return report
        if not all(p.get("ok") for p in row_proofs):
            report["blocked_labels"].append("checkpoint_blocked_row_identity_mismatch")
            report["status"] = "blocked"
            return report

        before = locomo_hygiene()
        report["locomo_hygiene_before"] = before
        if not before.get("ok"):
            report["blocked_labels"].append("checkpoint_blocked_health_or_hygiene")
            report["status"] = "blocked"
            return report

        port = int(args.base_port) + (0 if arm_name.startswith("A_") else 1)
        base_url = f"http://127.0.0.1:{port}"
        log_path = RESULTS_DIR / f"locomo_step5o_{arm_name}_server_{RUN_ID}.log"
        srv_env = server_env(port)
        report["server_env_redacted"] = redacted_env(srv_env)
        report["server_start_mode"] = "temporary_uvicorn_no_docker_rebuild"
        proc = start_temp_server(port, srv_env, log_path)
        report["server_log_path"] = str(log_path)
        report["server_pid"] = proc.pid
        h = health(base_url)
        report["health"] = h
        if not h.get("ok") or h.get("json") != {"status": "ok", "engine": "memibrium"}:
            report["blocked_labels"].append("checkpoint_blocked_health_or_hygiene")
            report["status"] = "blocked"
            return report

        env = benchmark_env(base_url, include_recall_telemetry=True)
        report["benchmark_env_redacted"] = redacted_env(env)
        bench = import_bench(env)
        if not getattr(bench, "USE_QUERY_EXPANSION", False):
            raise RuntimeError("USE_QUERY_EXPANSION is not effective in imported benchmark module")
        for attr in ["USE_CONTEXT_RERANK", "USE_APPEND_CONTEXT_EXPANSION", "USE_GATED_APPEND_CONTEXT_EXPANSION", "USE_LEGACY_CONTEXT_ASSEMBLY"]:
            if bool(getattr(bench, attr, False)):
                raise RuntimeError(f"forbidden retrieval mode enabled: {attr}")

        conv_row = data[0]
        conv = conv_row.get("conversation", conv_row)
        qa_list = conv_row.get("qa", conv_row.get("qa_list", []))
        report["slice_guard"] = {
            "conversations_to_process": 1,
            "total_questions": len(qa_list),
            "evaluated_fixed_rows": len(fixed_rows),
            "conv": conv_row.get("sample_id"),
            "speaker_a": conv.get("speaker_a"),
            "speaker_b": conv.get("speaker_b"),
            "full_199q_launched": False,
        }
        n_turns, domain = bench.ingest_conversation(conv, "conv-26", normalize_dates=False)
        report["ingest"] = {"n_turns": n_turns, "domain": domain, "normalize_dates": False}
        time.sleep(float(args.background_wait_seconds))

        rows = []
        for fixed in fixed_rows:
            idx = int(fixed["one_based_index"]) - 1
            qa = qa_list[idx]
            question = qa["question"]
            trace = trace_question(bench, question, domain, evidence_refs=qa.get("evidence") or qa.get("evidence_refs"))
            # Secondary answer/score intentionally omitted by default; retrieval-count path is primary.
            rows.append({
                "label": fixed["label"],
                "one_based_index": fixed["one_based_index"],
                "category": fixed["cat"],
                "question": question,
                "question_sha256": sha256_text(question),
                "expected_question_sha256": fixed["question_sha256"],
                "A_n": fixed.get("A_n"),
                "B_n": fixed.get("B_n"),
                "C_n": fixed.get("C_n"),
                "ground_truth": qa.get("answer", qa.get("adversarial_answer", "")),
                "trace_lite": trace,
                "n_memories": trace["counts"]["final_answer_context_count"],
                "fallback_or_error": None,
            })
        report["rows"] = rows
        report["row_count"] = len(rows)
        report["status"] = "completed"
    except Exception as exc:
        report["status"] = "blocked"
        report["blocked_labels"].append("checkpoint_blocked_runtime_error")
        report["error"] = repr(exc)
    finally:
        stop_proc(proc)
        try:
            cleanup_after = clean_locomo_domains()
            report["locomo_hygiene_after_cleanup"] = cleanup_after
            if not cleanup_after.get("ok"):
                report.setdefault("blocked_labels", []).append("checkpoint_blocked_cleanup_failure")
                report["status"] = "blocked"
        except Exception as exc:
            report.setdefault("blocked_labels", []).append("checkpoint_blocked_cleanup_failure")
            report["cleanup_error"] = repr(exc)
            report["status"] = "blocked"
        try:
            git("checkout", original_head)
            report["restored_git_state"] = git_state()
        except Exception as exc:
            report["restore_error"] = repr(exc)
        report["ended_at"] = utc_now()
    return report


def classify(arm_reports: list[dict[str, Any]]) -> dict[str, Any]:
    completed = [r for r in arm_reports if r.get("status") == "completed"]
    labels: dict[str, Any] = {"secondary_labels": ["no_go_phase_c_still_blocked"]}
    if len(completed) < 2:
        labels["primary_label"] = "checkpoint_inconclusive_runtime_state"
        labels["blocked_labels"] = sorted({lab for r in arm_reports for lab in r.get("blocked_labels", [])})
        return labels
    by_arm = {r["arm"]: r for r in completed}
    a = by_arm.get("A_f2466c9")
    b = by_arm.get("B_current")
    if not a or not b:
        labels["primary_label"] = "checkpoint_inconclusive_runtime_state"
        return labels

    a_counts = {row["label"]: row["n_memories"] for row in a["rows"]}
    b_counts = {row["label"]: row["n_memories"] for row in b["rows"]}
    non_adv = ["unanswerable_high_context", "temporal_high_context", "single_hop_high_context", "multi_hop_high_context"]
    adv = ["adversarial_split_early", "adversarial_split_late"]
    a_low = sum(1 for v in a_counts.values() if v <= 4) >= 5
    b_high_non_adv = all(b_counts.get(label, 0) >= 12 for label in non_adv)
    b_adv_split = all(b_counts.get(label, 99) <= 6 for label in adv)
    if a_low and b_high_non_adv:
        labels["primary_label"] = "checkpoint_reproduces_low_context_at_f2466c9"
        labels["secondary_labels"].append("supports_effective_harness_mismatch")
        labels["secondary_labels"].append("requires_full_repro_prereg")
    elif b_high_non_adv:
        # Arm A also reached the high-context family, so the checkpoint contrast
        # did not reproduce a static f2466c9..post-cb56559 boundary. Preserve
        # Arm B high-context support as secondary evidence.
        labels["primary_label"] = "checkpoint_shows_no_static_boundary_effect"
        labels["secondary_labels"].append("supports_post_cb56559_high_context_path")
        labels["secondary_labels"].append("supports_effective_harness_mismatch")
        labels["secondary_labels"].append("requires_full_repro_prereg")
    else:
        labels["primary_label"] = "checkpoint_inconclusive_runtime_state"
        labels["secondary_labels"].append("supports_runtime_state_nondeterminism")
    if b_adv_split:
        labels["secondary_labels"].append("supports_adversarial_category_split")
    labels["counts_by_arm"] = {"A_f2466c9": a_counts, "B_current": b_counts}
    return labels


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--arms", default="A_f2466c9,B_current", help="Comma-separated arms: A_f2466c9,B_current")
    parser.add_argument("--base-port", type=int, default=10080)
    parser.add_argument("--background-wait-seconds", type=float, default=2.0)
    args = parser.parse_args()

    requested = [x.strip() for x in args.arms.split(",") if x.strip()]
    invalid = [x for x in requested if x not in ARMS]
    if invalid:
        raise SystemExit(f"invalid arms: {invalid}")

    top_report: dict[str, Any] = {
        "schema": "memibrium.locomo.step5o.execution.v1",
        "run_id": RUN_ID,
        "started_at": utc_now(),
        "authorization": "user said proceed after Step 5o preregistration handoff",
        "preregistration": "docs/eval/locomo_step5o_bounded_checkpoint_trace_lite_preregistration_2026-05-02.md",
        "fixed_rows_artifact": str(FIXED_ROWS_PATH.relative_to(ROOT)),
        "host_git_state_start": git_state(),
        "docker_identity_start": docker_identity(),
        "arms_requested": requested,
        "full_199q_launched": False,
    }
    if git("status", "--porcelain"):
        # Allow this script itself if newly created, but record dirty state. Do not block here because the prereg allows execution artifacts.
        top_report["dirty_state_note"] = git("status", "--porcelain")

    arm_reports = []
    for arm_name in requested:
        arm_report = run_arm(arm_name, args)
        arm_path = RESULTS_DIR / f"locomo_step5o_{arm_name}_trace_lite_{RUN_ID}.json"
        write_json(arm_path, arm_report)
        arm_report["artifact_path"] = str(arm_path)
        arm_reports.append(arm_report)
        if arm_report.get("status") != "completed":
            # Stop on blocked arm per guardrails.
            break

    top_report["arms"] = arm_reports
    top_report["labels"] = classify(arm_reports)
    top_report["locomo_hygiene_final"] = locomo_hygiene()
    top_report["host_git_state_end"] = git_state()
    top_report["ended_at"] = utc_now()
    summary_path = RESULTS_DIR / f"locomo_step5o_trace_lite_summary_{RUN_ID}.json"
    write_json(summary_path, top_report)
    print(str(summary_path))
    print(json.dumps(top_report["labels"], indent=2))
    if not top_report["locomo_hygiene_final"].get("ok"):
        return 2
    return 0 if all(r.get("status") == "completed" for r in arm_reports) else 1


if __name__ == "__main__":
    raise SystemExit(main())
