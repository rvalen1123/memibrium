#!/usr/bin/env python3
"""Step 5p full-repro execution harness.

Execution scope is constrained by:
  docs/eval/locomo_step5p_full_repro_preregistration_2026-05-03.md

This is an evaluation artifact, not product code. It performs the authorized
Step 5p_exec full 199Q telemetry-off corrected-slice reproduction, captures the
required stateful-substrate snapshots, enforces the startup slice guard, copies
artifacts, validates score/retrieval shape, cleans LOCOMO rows, and writes
comparison/label/verification artifacts.
"""
from __future__ import annotations

import collections
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import statistics
import subprocess
import sys
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
RESULTS_DIR = ROOT / "docs/eval/results"
DATA_PATH = Path("/tmp/locomo/data/locomo10.json")
TMP_RESULT = Path("/tmp/locomo_results_query_expansion_raw.json")
TMP_LOG = Path("/tmp/locomo_step5p_full_repro_2026-05-03.log")
RUN_ID = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
EXPECTED_DATA_SHA256 = "79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4"
EXPECTED_SOURCE_HASHES = {
    "benchmark_scripts/locomo_bench_v2.py": "32dd68d0a0bad7322e8eea67bea90628d0cf42415769802f9e48a4528f3454ff",
    "hybrid_retrieval.py": "2ba660f547432c7fa5ae88955ee97024f5c39848790060358c82dcf0a8259c07",
    "server.py": "150b161bd9bef5c021fd7f1b32472623b3cc03baac6d13ff42edd501ae3f6f1a",
}
TARGET_FILES = list(EXPECTED_SOURCE_HASHES)
COMMAND = ["python3", "benchmark_scripts/locomo_bench_v2.py", "--max-convs", "1", "--query-expansion"]
GUARD_TIMEOUT_SECONDS = 180

REDACT_TOKENS = ("KEY", "TOKEN", "SECRET", "PASSWORD", "PASS", "CREDENTIAL")
ENV_KEYS = [
    "MCP_URL",
    "OPENAI_BASE_URL", "OPENAI_API_KEY",
    "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_DEPLOYMENT", "AZURE_API_VERSION",
    "AZURE_CHAT_ENDPOINT", "AZURE_CHAT_DEPLOYMENT", "AZURE_CHAT_API_KEY",
    "AZURE_EMBEDDING_ENDPOINT", "AZURE_EMBEDDING_DEPLOYMENT", "AZURE_EMBEDDING_API_KEY",
    "ANSWER_MODEL", "JUDGE_MODEL", "CHAT_MODEL",
    "EMBEDDING_BASE_URL", "EMBEDDING_MODEL",
    "USE_QUERY_EXPANSION", "INCLUDE_RECALL_TELEMETRY", "LOCOMO_RETRIEVAL_TELEMETRY",
    "USE_CONTEXT_RERANK", "USE_APPEND_CONTEXT_EXPANSION", "USE_GATED_APPEND_CONTEXT_EXPANSION", "USE_LEGACY_CONTEXT_ASSEMBLY",
    "USE_RUVECTOR", "RUVECTOR_GNN",
    "ENABLE_BACKGROUND_SCORING", "ENABLE_CONTRADICTION_DETECTION", "ENABLE_HIERARCHY_PROCESSING",
    "DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD",
]
LOG_ERROR_PATTERNS = [
    "Hybrid retrieval failed",
    "type \"vector\" does not exist",
    "Decimal is not JSON serializable",
    "TypeError",
    "Internal Server Error",
    "HTTP 500",
    "Traceback",
]


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def run_cmd(cmd: list[str], *, cwd: Path = ROOT, env: dict[str, str] | None = None, input_text: str | None = None, timeout: int = 120, check: bool = True) -> subprocess.CompletedProcess[str]:
    res = subprocess.run(cmd, cwd=cwd, env=env, input=input_text, text=True, capture_output=True, timeout=timeout, check=False)
    if check and res.returncode != 0:
        raise RuntimeError(f"command failed ({res.returncode}): {' '.join(cmd)}\nSTDOUT:\n{res.stdout[-4000:]}\nSTDERR:\n{res.stderr[-4000:]}")
    return res


def git(*args: str, check: bool = True) -> str:
    return run_cmd(["git", *args], check=check).stdout.strip()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_dotenv(base: dict[str, str]) -> dict[str, str]:
    env = dict(base)
    env_file = ROOT / ".env"
    if env_file.exists():
        for raw in env_file.read_text().splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def benchmark_env() -> dict[str, str]:
    env = load_dotenv(os.environ.copy())
    env.update({
        "AZURE_CHAT_DEPLOYMENT": "gpt-4.1-mini",
        "AZURE_OPENAI_DEPLOYMENT": "gpt-4.1-mini",
        "ANSWER_MODEL": "gpt-4.1-mini",
        "JUDGE_MODEL": "gpt-4.1-mini",
        "CHAT_MODEL": "gpt-4.1-mini",
        "AZURE_EMBEDDING_DEPLOYMENT": "text-embedding-3-small",
        "USE_QUERY_EXPANSION": "1",
        "PYTHONUNBUFFERED": "1",
    })
    for k in [
        "INCLUDE_RECALL_TELEMETRY",
        "LOCOMO_RETRIEVAL_TELEMETRY",
        "USE_CONTEXT_RERANK",
        "USE_APPEND_CONTEXT_EXPANSION",
        "USE_GATED_APPEND_CONTEXT_EXPANSION",
        "USE_LEGACY_CONTEXT_ASSEMBLY",
    ]:
        env.pop(k, None)
    return env


def redact_value(key: str, value: str | None) -> str | None:
    if value is None:
        return None
    if any(token in key.upper() for token in REDACT_TOKENS):
        return "[REDACTED]"
    return value


def redacted_env(env: dict[str, str]) -> dict[str, str | None]:
    return {k: redact_value(k, env.get(k)) for k in ENV_KEYS}


def docker_env(container: str) -> dict[str, str | None]:
    res = run_cmd(["docker", "inspect", container, "--format", "{{range .Config.Env}}{{println .}}{{end}}"], check=False)
    if res.returncode != 0:
        return {"error": res.stderr[-1000:]}
    raw: dict[str, str] = {}
    for line in res.stdout.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            raw[k] = v
    return {k: redact_value(k, raw.get(k)) for k in ENV_KEYS}


def psql(sql: str, *, timeout: int = 120, check: bool = True) -> str:
    return run_cmd(["docker", "exec", "-i", "memibrium-ruvector-db", "psql", "-U", "memory", "-d", "memory", "-t", "-A"], input_text=sql, timeout=timeout, check=check).stdout.strip()


def psql_safe(sql: str, *, timeout: int = 120) -> dict[str, Any]:
    res = run_cmd(["docker", "exec", "-i", "memibrium-ruvector-db", "psql", "-U", "memory", "-d", "memory", "-t", "-A"], input_text=sql, timeout=timeout, check=False)
    return {"returncode": res.returncode, "stdout": res.stdout.strip(), "stderr": res.stderr.strip()}


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
    counts["ok"] = all(v == 0 for k, v in counts.items())
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
    # A short second pass is intentional for background tasks that may have raced after benchmark completion.
    time.sleep(2)
    psql(sql, timeout=180)
    return locomo_hygiene()


def health() -> dict[str, Any]:
    res = run_cmd(["curl", "-fsS", "http://localhost:9999/health"], check=False, timeout=30)
    out = {"returncode": res.returncode, "stdout": res.stdout.strip(), "stderr": res.stderr.strip()}
    try:
        out["json"] = json.loads(res.stdout)
    except Exception:
        out["json"] = None
    return out


def host_source_hashes() -> dict[str, str]:
    return {rel: sha256_file(ROOT / rel) for rel in TARGET_FILES}


def container_source_hashes() -> dict[str, str | None]:
    out: dict[str, str | None] = {}
    for rel in TARGET_FILES:
        res = run_cmd(["docker", "exec", "memibrium-server", "sha256sum", f"/app/{rel}"], check=False, timeout=30)
        out[rel] = res.stdout.split()[0] if res.returncode == 0 and res.stdout.split() else None
    return out


def docker_identity(container: str) -> dict[str, Any]:
    res = run_cmd(["docker", "inspect", container], check=False, timeout=30)
    if res.returncode != 0:
        return {"available": False, "stderr": res.stderr.strip()}
    info = json.loads(res.stdout)[0]
    return {
        "available": True,
        "id": info.get("Id"),
        "name": info.get("Name"),
        "image": info.get("Image"),
        "config_image": info.get("Config", {}).get("Image"),
        "state": info.get("State"),
    }


def process_matches() -> list[str]:
    res = run_cmd(["ps", "-eo", "pid,args"], check=False)
    pats = ["run_locomo_step5p", "locomo_bench_v2.py", "run_locomo_step5o", "uvicorn server:app"]
    matches = []
    for line in res.stdout.splitlines():
        if any(p in line for p in pats) and "ps -eo" not in line:
            if str(os.getpid()) not in line:
                matches.append(line.strip())
    return matches


def prove_input_slice() -> dict[str, Any]:
    proof: dict[str, Any] = {"path": str(DATA_PATH), "exists": DATA_PATH.exists()}
    if not DATA_PATH.exists():
        proof["ok"] = False
        return proof
    raw = DATA_PATH.read_bytes()
    data = json.loads(raw)
    conv0 = data[0] if isinstance(data, list) and data else {}
    qas = conv0.get("qa") or conv0.get("qas") or conv0.get("questions") or []
    conversation = conv0.get("conversation") or {}
    proof.update({
        "sha256": hashlib.sha256(raw).hexdigest(),
        "top_level_type": type(data).__name__,
        "conversation_count": len(data) if isinstance(data, list) else None,
        "sample_order": [d.get("sample_id") for d in data] if isinstance(data, list) else None,
        "index0_sample_id": conv0.get("sample_id"),
        "index0_speaker_a": conversation.get("speaker_a"),
        "index0_speaker_b": conversation.get("speaker_b"),
        "index0_qa_count": len(qas),
        "index0_category_counts_raw": dict(collections.Counter(str(q.get("category")) for q in qas)),
        "total_qa_count": sum(len(d.get("qa") or d.get("qas") or d.get("questions") or []) for d in data) if isinstance(data, list) else None,
    })
    proof["ok"] = (
        proof["sha256"] == EXPECTED_DATA_SHA256
        and proof["top_level_type"] == "list"
        and proof["index0_sample_id"] == "conv-26"
        and proof["index0_speaker_a"] == "Caroline"
        and proof["index0_speaker_b"] == "Melanie"
        and proof["index0_qa_count"] == 199
        and bool(proof["sample_order"] and proof["sample_order"][0] == "conv-26")
    )
    return proof


def db_snapshot() -> dict[str, Any]:
    return {
        "locomo_hygiene": locomo_hygiene(),
        "table_counts_sizes": psql_safe("""
SELECT relname || '|' || n_live_tup || '|' || pg_total_relation_size(relid)
FROM pg_stat_user_tables
WHERE relname IN ('memories','entities','entity_relationships','memory_edges','temporal_expressions','memory_snapshots','user_feedback','contradictions')
ORDER BY relname;
"""),
        "extensions": psql_safe("SELECT extname || '|' || extversion FROM pg_extension ORDER BY extname;"),
        "postgres_version": psql_safe("SELECT version();"),
        "vector_column": psql_safe("SELECT column_name||'|'||udt_name||'|'||data_type FROM information_schema.columns WHERE table_name='memories' AND column_name='embedding';"),
        "indexes": psql_safe("SELECT tablename||'|'||indexname||'|'||indexdef FROM pg_indexes WHERE tablename IN ('memories','entities','memory_edges') ORDER BY tablename,indexname;"),
        "pg_stat_user_tables": psql_safe("""
SELECT relname || '|' || COALESCE(last_vacuum::text,'') || '|' || COALESCE(last_autovacuum::text,'') || '|' || COALESCE(last_analyze::text,'') || '|' || COALESCE(last_autoanalyze::text,'')
FROM pg_stat_user_tables
WHERE relname IN ('memories','entities','entity_relationships','memory_edges','temporal_expressions','memory_snapshots','user_feedback','contradictions')
ORDER BY relname;
"""),
        "planner_settings": psql_safe("SELECT name||'='||setting FROM pg_settings WHERE name IN ('enable_seqscan','work_mem','random_page_cost','effective_cache_size') ORDER BY name;"),
    }


def source_behavior_probes() -> dict[str, Any]:
    bench = (ROOT / "benchmark_scripts/locomo_bench_v2.py").read_text()
    server = (ROOT / "server.py").read_text()
    hybrid = (ROOT / "hybrid_retrieval.py").read_text()
    return {
        "max_convs_is_slice_cap": "data = data[:max_convs]" in bench,
        "include_recall_telemetry_flag": "INCLUDE_RECALL_TELEMETRY" in bench,
        "query_expansion_flag": "USE_QUERY_EXPANSION" in bench,
        "legacy_context_assembly_flag": "USE_LEGACY_CONTEXT_ASSEMBLY" in bench,
        "n_memories_field": "n_memories" in bench,
        "fallback_count_field": "expand_query_fallback_count" in bench,
        "serialize_result_helper": "def _serialize_result" in server,
        "hybrid_uses_dynamic_vector_type": "self.vtype" in hybrid,
    }


def archive_stale_tmp() -> list[dict[str, Any]]:
    archived = []
    for p in [TMP_RESULT, TMP_LOG]:
        if p.exists():
            dest = RESULTS_DIR / f"locomo_step5p_stale_{p.name}_{RUN_ID}"
            shutil.copy2(p, dest)
            info = {"path": str(p), "sha256": sha256_file(p), "size": p.stat().st_size, "archived_to": str(dest)}
            p.unlink()
            info["removed"] = True
            archived.append(info)
    return archived


def docker_logs_tail(lines: int = 300) -> str:
    res = run_cmd(["docker", "logs", "--tail", str(lines), "memibrium-server"], check=False, timeout=30)
    return (res.stdout + res.stderr)[-30000:]


def snapshot(stage: str, env: dict[str, str] | None = None, result_path_hygiene: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    env = env or benchmark_env()
    snap = {
        "schema": "memibrium.locomo.step5p.snapshot.v1",
        "run_id": RUN_ID,
        "stage": stage,
        "captured_at": utc_now(),
        "authorization": "user said proceed after Step 5p preregistration",
        "preregistration": "docs/eval/locomo_step5p_full_repro_preregistration_2026-05-03.md",
        "git": {
            "branch": git("branch", "--show-current", check=False),
            "head": git("rev-parse", "HEAD", check=False),
            "short": git("rev-parse", "--short", "HEAD", check=False),
            "status_short": git("status", "--short", check=False),
            "log_1": git("log", "-1", "--oneline", check=False),
        },
        "health": health(),
        "docker_identity": {
            "memibrium_server": docker_identity("memibrium-server"),
            "ruvector_db": docker_identity("memibrium-ruvector-db"),
        },
        "process_matches": process_matches(),
        "source_hashes_host": host_source_hashes(),
        "source_hashes_container": container_source_hashes(),
        "source_behavior_probes": source_behavior_probes(),
        "benchmark_env_redacted": redacted_env(env),
        "server_env_redacted": docker_env("memibrium-server"),
        "input_slice_proof": prove_input_slice(),
        "db_snapshot": db_snapshot(),
        "embedding_cache_state": "not_discoverable_read_only",
        "bounded_server_log_tail": docker_logs_tail(300),
    }
    if result_path_hygiene is not None:
        snap["result_path_hygiene"] = result_path_hygiene
    return snap


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, default=str))


def preflight(snapshot_obj: dict[str, Any], env: dict[str, str]) -> list[str]:
    blocked: list[str] = []
    if snapshot_obj["health"].get("json") != {"status": "ok", "engine": "memibrium"}:
        blocked.append("full_repro_blocked_health_or_hygiene")
    if not snapshot_obj["db_snapshot"]["locomo_hygiene"].get("ok"):
        blocked.append("full_repro_blocked_health_or_hygiene")
    if not snapshot_obj["input_slice_proof"].get("ok"):
        blocked.append("full_repro_blocked_slice_identity_mismatch")
    host = snapshot_obj["source_hashes_host"]
    cont = snapshot_obj["source_hashes_container"]
    if host != EXPECTED_SOURCE_HASHES or any(cont.get(k) != host.get(k) for k in TARGET_FILES):
        blocked.append("full_repro_blocked_source_or_env_mismatch")
    probes = snapshot_obj["source_behavior_probes"]
    if not all(probes.values()):
        blocked.append("full_repro_blocked_source_or_env_mismatch")
    env_ok = (
        env.get("USE_QUERY_EXPANSION") == "1"
        and "INCLUDE_RECALL_TELEMETRY" not in env
        and "LOCOMO_RETRIEVAL_TELEMETRY" not in env
        and env.get("ANSWER_MODEL") == "gpt-4.1-mini"
        and env.get("JUDGE_MODEL") == "gpt-4.1-mini"
        and env.get("CHAT_MODEL") == "gpt-4.1-mini"
        and env.get("AZURE_OPENAI_DEPLOYMENT") == "gpt-4.1-mini"
        and env.get("AZURE_CHAT_DEPLOYMENT") == "gpt-4.1-mini"
        and env.get("AZURE_EMBEDDING_DEPLOYMENT") == "text-embedding-3-small"
        and "USE_CONTEXT_RERANK" not in env
        and "USE_APPEND_CONTEXT_EXPANSION" not in env
        and "USE_GATED_APPEND_CONTEXT_EXPANSION" not in env
        and "USE_LEGACY_CONTEXT_ASSEMBLY" not in env
    )
    if not env_ok:
        blocked.append("full_repro_blocked_source_or_env_mismatch")
    # Snapshot completeness gate: required core sections must be present and parseable.
    for key in ["docker_identity", "source_hashes_host", "source_hashes_container", "benchmark_env_redacted", "server_env_redacted", "db_snapshot"]:
        if key not in snapshot_obj or snapshot_obj[key] is None:
            blocked.append("full_repro_blocked_runtime_state_snapshot_failure")
            break
    return sorted(set(blocked))


def run_benchmark_with_guard(env: dict[str, str]) -> dict[str, Any]:
    summary = {
        "schema": "memibrium.locomo.step5p.guarded_launch.v1",
        "run_id": RUN_ID,
        "started_at": utc_now(),
        "command": COMMAND,
        "log_path": str(TMP_LOG),
        "guard_timeout_seconds": GUARD_TIMEOUT_SECONDS,
        "env_assertions": {
            "INCLUDE_RECALL_TELEMETRY_absent": "INCLUDE_RECALL_TELEMETRY" not in env,
            "LOCOMO_RETRIEVAL_TELEMETRY_absent": "LOCOMO_RETRIEVAL_TELEMETRY" not in env,
            "USE_QUERY_EXPANSION": env.get("USE_QUERY_EXPANSION"),
            "AZURE_EMBEDDING_DEPLOYMENT": env.get("AZURE_EMBEDDING_DEPLOYMENT"),
            "AZURE_CHAT_DEPLOYMENT": env.get("AZURE_CHAT_DEPLOYMENT"),
            "AZURE_OPENAI_DEPLOYMENT": env.get("AZURE_OPENAI_DEPLOYMENT"),
            "ANSWER_MODEL": env.get("ANSWER_MODEL"),
            "JUDGE_MODEL": env.get("JUDGE_MODEL"),
            "CHAT_MODEL": env.get("CHAT_MODEL"),
        },
        "observed": {},
        "guard_status": "running",
        "abort_reason": None,
    }
    TMP_LOG.parent.mkdir(parents=True, exist_ok=True)
    with TMP_LOG.open("w", buffering=1) as log:
        log.write(f"# Step 5p guarded launch started {summary['started_at']}\n")
        log.write("# command: " + " ".join(COMMAND) + "\n")
        proc = subprocess.Popen(
            COMMAND,
            cwd=str(ROOT),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            start_new_session=True,
        )
        start = time.monotonic()
        convs_ok = total_ok = convline_ok = False
        mismatch = None
        while True:
            line = proc.stdout.readline() if proc.stdout else ""
            if line:
                sys.stdout.write(line)
                sys.stdout.flush()
                log.write(line)
                stripped = line.strip()
                m = re.search(r"Conversations to process:\s*(\d+)", stripped)
                if m:
                    val = int(m.group(1))
                    summary["observed"]["conversations_to_process"] = val
                    convs_ok = val == 1
                    if not convs_ok:
                        mismatch = f"conversations_to_process_{val}"
                m = re.search(r"Total questions:\s*(\d+)\s*\((\d+)\s+evaluated.*skipping cats (.*)\)", stripped)
                if m:
                    total = int(m.group(1)); evaluated = int(m.group(2)); skip_txt = m.group(3)
                    summary["observed"]["total_questions"] = total
                    summary["observed"]["evaluated_questions"] = evaluated
                    summary["observed"]["skipping_cats_text"] = skip_txt
                    total_ok = total == 199 and evaluated == 199 and "set()" in stripped
                    if not total_ok:
                        mismatch = f"total_{total}_evaluated_{evaluated}_skip_{skip_txt}"
                if "[1/1] Conv " in stripped:
                    summary["observed"]["first_conversation_line"] = stripped
                    convline_ok = stripped.startswith("[1/1] Conv conv-26: Caroline & Melanie")
                    if not convline_ok:
                        mismatch = f"first_conversation_line_{stripped}"
                if mismatch:
                    summary["guard_status"] = "killed"
                    summary["abort_reason"] = "full_repro_blocked_slice_identity_mismatch:" + mismatch
                    try:
                        os.killpg(proc.pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
                    break
                if convs_ok and total_ok and convline_ok:
                    summary["guard_status"] = "passed_startup_guard"
                    for rest in proc.stdout:
                        sys.stdout.write(rest)
                        sys.stdout.flush()
                        log.write(rest)
                    break
            else:
                if proc.poll() is not None:
                    break
                if time.monotonic() - start > GUARD_TIMEOUT_SECONDS:
                    summary["guard_status"] = "killed"
                    summary["abort_reason"] = "slice_guard_timeout"
                    try:
                        os.killpg(proc.pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
                    break
                time.sleep(0.1)
        rc = proc.wait()
        summary["returncode"] = rc
        summary["completed_at"] = utc_now()
        if summary["guard_status"] == "running":
            summary["guard_status"] = "process_exited_before_guard_pass"
            summary["abort_reason"] = summary["abort_reason"] or "full_repro_blocked_runtime_error"
        log.write(f"# Step 5p guarded launch completed rc={rc} guard_status={summary['guard_status']} abort_reason={summary['abort_reason']}\n")
    return summary


def summarize_result(raw: dict[str, Any], log_text: str) -> dict[str, Any]:
    details = raw.get("details", [])
    n_values = [row.get("n_memories") for row in details if isinstance(row.get("n_memories"), int)]
    dist = dict(sorted(collections.Counter(n_values).items()))
    cats: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for row in details:
        cats[str(row.get("cat"))].append(row)
    category_summary = {}
    for cat, rows in sorted(cats.items()):
        scores = [float(r.get("score", 0)) for r in rows]
        ns = [r.get("n_memories") for r in rows if isinstance(r.get("n_memories"), int)]
        category_summary[cat] = {
            "count": len(rows),
            "score_pct": round(statistics.mean(scores) * 100, 2) if scores else None,
            "mean_n_memories": round(statistics.mean(ns), 4) if ns else None,
            "n_memories_distribution": dict(sorted(collections.Counter(ns).items())),
            "n_le_4": sum(1 for n in ns if n <= 4),
            "n_eq_15": sum(1 for n in ns if n == 15),
        }
    adv_rows = cats.get("adversarial", [])
    non_adv_rows = [row for cat, rows in cats.items() if cat != "adversarial" for row in rows]
    adv_ns = [r.get("n_memories") for r in adv_rows if isinstance(r.get("n_memories"), int)]
    non_adv_ns = [r.get("n_memories") for r in non_adv_rows if isinstance(r.get("n_memories"), int)]
    condition = raw.get("condition", {})
    log_flags = {pat: (pat in log_text) for pat in LOG_ERROR_PATTERNS}
    valid = {
        "result_parseable": True,
        "detail_rows_199": len(details) == 199,
        "all_rows_conv26": all(row.get("conv") == "conv-26" for row in details),
        "telemetry_absent": all("recall_telemetry" not in row for row in details),
        "query_expansion_on": condition.get("query_expansion") is True,
        "legacy_context_assembly_off": condition.get("legacy_context_assembly") is False,
        "context_rerank_off": condition.get("context_rerank") is False,
        "append_context_expansion_off": condition.get("append_context_expansion") is False,
        "gated_append_context_expansion_off": condition.get("gated_append_context_expansion") is False,
        "no_expansion_arm_b_off": condition.get("no_expansion_arm_b") is False,
        "normalize_dates_off": condition.get("normalize_dates") is False,
        "fallback_present": "expand_query_fallback_count" in raw,
        "n_memories_present_all_rows": len(n_values) == len(details) == 199,
        "no_fresh_log_error_flags": not any(log_flags.values()),
    }
    full_5cat = raw.get("full_5cat_overall", raw.get("overall_score"))
    protocol_4cat = raw.get("protocol_4cat_overall")
    score_reproduces = isinstance(full_5cat, (int, float)) and isinstance(protocol_4cat, (int, float)) and 53.28 <= full_5cat <= 57.28 and 68.07 <= protocol_4cat <= 72.07
    bimodality_reproduces = (
        all(valid.values())
        and len(adv_rows) == 47
        and adv_ns
        and abs(statistics.mean(adv_ns) - 4.0) <= 0.25
        and sum(1 for n in adv_ns if n <= 4) >= 45
        and non_adv_ns
        and 14.06 <= statistics.mean(non_adv_ns) <= 14.77
        and abs(sum(1 for n in n_values if n == 15) - 120) <= 10
        and raw.get("expand_query_fallback_count") == 0
    )
    labels = []
    if all(valid.values()):
        labels.append("full_repro_execution_complete_valid")
        labels.append("5j_v2_exec_bimodality_reproduces" if bimodality_reproduces else "5j_v2_exec_bimodality_does_not_reproduce")
        labels.append("score_reproduces_within_tolerance" if score_reproduces else "score_drifts_significantly")
    else:
        labels.append("full_repro_blocked_runtime_error")
    labels.append("no_go_phase_c_still_blocked")
    return {
        "schema": "memibrium.locomo.step5p.validation.v1",
        "run_id": RUN_ID,
        "validated_at": utc_now(),
        "validity_checks": valid,
        "condition": condition,
        "total_questions": raw.get("total_questions"),
        "full_5cat_overall": full_5cat,
        "protocol_4cat_overall": protocol_4cat,
        "category_scores": raw.get("category_scores"),
        "category_summary": category_summary,
        "expand_query_fallback_count": raw.get("expand_query_fallback_count"),
        "expand_query_fallback_rate": raw.get("expand_query_fallback_rate"),
        "avg_query_ms": raw.get("avg_query_ms"),
        "n_memories_summary": {
            "count": len(n_values),
            "mean": round(statistics.mean(n_values), 4) if n_values else None,
            "min": min(n_values) if n_values else None,
            "max": max(n_values) if n_values else None,
            "distribution": dist,
            "n_eq_15": sum(1 for n in n_values if n == 15),
            "n_eq_4": sum(1 for n in n_values if n == 4),
            "n_le_4": sum(1 for n in n_values if n <= 4),
            "n_ge_11": sum(1 for n in n_values if n >= 11),
        },
        "adversarial_summary": {
            "count": len(adv_rows),
            "mean_n_memories": round(statistics.mean(adv_ns), 4) if adv_ns else None,
            "n_le_4": sum(1 for n in adv_ns if n <= 4),
            "distribution": dict(sorted(collections.Counter(adv_ns).items())),
        },
        "non_adversarial_summary": {
            "count": len(non_adv_rows),
            "mean_n_memories": round(statistics.mean(non_adv_ns), 4) if non_adv_ns else None,
            "n_eq_15": sum(1 for n in non_adv_ns if n == 15),
            "distribution": dict(sorted(collections.Counter(non_adv_ns).items())),
        },
        "log_error_flags": log_flags,
        "comparison_targets": {
            "step5j_v2_exec": {
                "full_5cat_overall": 55.28,
                "protocol_4cat_overall": 70.07,
                "mean_n_memories": 11.9296,
                "distribution": {"4": 51, "12": 6, "13": 10, "14": 12, "15": 120},
                "n_eq_15": 120,
                "adversarial_mean_n": 4.0,
                "fallback": 0,
            }
        },
        "decision_labels": labels,
    }


def write_markdown(validation: dict[str, Any], labels: list[str], paths: dict[str, str], cleanup: dict[str, Any], preflight_labels: list[str] | None = None) -> str:
    ns = validation.get("n_memories_summary", {})
    adv = validation.get("adversarial_summary", {})
    nonadv = validation.get("non_adversarial_summary", {})
    lines = [
        "# LOCOMO Step 5p full-repro execution result",
        "",
        f"Run ID: `{RUN_ID}`",
        f"Date: {utc_now()}",
        "Repo: `/home/zaddy/src/Memibrium`",
        "Preregistration: `docs/eval/locomo_step5p_full_repro_preregistration_2026-05-03.md`",
        "",
        "## Labels",
        "",
    ]
    for label in labels:
        lines.append(f"- `{label}`")
    if preflight_labels:
        lines.extend(["", "Preflight blocked labels:"])
        lines.extend(f"- `{label}`" for label in preflight_labels)
    lines.extend([
        "",
        "## Scope",
        "",
        "- Executed authorized Step 5p_exec full 199Q telemetry-off corrected-slice reproduction.",
        "- No Phase C intervention was selected or implemented.",
        "- No Docker rebuild/restart was performed.",
        "- Retrieval shape remains the primary comparability axis; score is secondary.",
        "",
        "## Results",
        "",
        f"- 5-cat overall: `{validation.get('full_5cat_overall')}`",
        f"- Protocol 4-cat overall: `{validation.get('protocol_4cat_overall')}`",
        f"- Fallback: `{validation.get('expand_query_fallback_count')}` / `{validation.get('total_questions')}`",
        f"- Mean n_memories: `{ns.get('mean')}`",
        f"- n_memories distribution: `{ns.get('distribution')}`",
        f"- n=15: `{ns.get('n_eq_15')}/199`",
        f"- adversarial mean n_memories: `{adv.get('mean_n_memories')}`, n<=4 `{adv.get('n_le_4')}/{adv.get('count')}`",
        f"- non-adversarial mean n_memories: `{nonadv.get('mean_n_memories')}`, n=15 `{nonadv.get('n_eq_15')}/{nonadv.get('count')}`",
        "",
        "## Interpretation",
        "",
    ])
    label_set = set(labels)
    if "5j_v2_exec_bimodality_reproduces" in label_set and "score_reproduces_within_tolerance" in label_set:
        lines.append("Step 5j_v2_exec Regime C reproduced at both retrieval-shape and score gates. This supports stable current run-to-run behavior at the regime level, but Phase C remains blocked pending a later explicit baseline-decision preregistration.")
    elif "5j_v2_exec_bimodality_reproduces" in label_set:
        lines.append("Step 5j_v2_exec bimodality reproduced but score drifted. Treat retrieval substrate as comparatively stable, but answer/judge variability needs separate audit before any baseline promotion.")
    elif "5j_v2_exec_bimodality_does_not_reproduce" in label_set and "score_reproduces_within_tolerance" in label_set:
        lines.append("Scores reproduced within tolerance, but retrieval shape did not. Do not call the baseline stable; retrieval shape controls comparability. Phase C remains blocked pending substrate nondeterminism audit.")
    elif "5j_v2_exec_bimodality_does_not_reproduce" in label_set:
        lines.append("Step 5j_v2_exec did not reproduce at retrieval-shape and/or score gates. No single-run baseline is canonical. Phase C remains blocked pending substrate nondeterminism audit.")
    else:
        lines.append("The run was blocked or invalid under preregistered gates. Do not interpret score/retrieval shape as a valid reproduction result. Phase C remains blocked.")
    lines.extend([
        "",
        "## Cleanup",
        "",
        f"Cleanup hygiene: `{cleanup}`",
        "",
        "## Artifacts",
        "",
    ])
    for k, v in paths.items():
        lines.append(f"- {k}: `{v}`")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    env = benchmark_env()
    paths = {
        "runner": str(Path(__file__).relative_to(ROOT)),
        "prelaunch_snapshot": str(RESULTS_DIR / f"locomo_step5p_full_repro_prelaunch_snapshot_{RUN_ID}.json"),
        "guard_summary": str(RESULTS_DIR / f"locomo_step5p_full_repro_guard_summary_{RUN_ID}.json"),
        "raw_result": str(RESULTS_DIR / f"locomo_step5p_full_repro_raw_{RUN_ID}.json"),
        "run_log": str(RESULTS_DIR / f"locomo_step5p_full_repro_log_{RUN_ID}.log"),
        "validation": str(RESULTS_DIR / f"locomo_step5p_full_repro_validation_{RUN_ID}.json"),
        "labels": str(RESULTS_DIR / f"locomo_step5p_full_repro_labels_{RUN_ID}.json"),
        "postrun_snapshot": str(RESULTS_DIR / f"locomo_step5p_full_repro_postrun_snapshot_{RUN_ID}.json"),
        "cleanup": str(RESULTS_DIR / f"locomo_step5p_full_repro_cleanup_{RUN_ID}.json"),
        "comparison": str(RESULTS_DIR / f"locomo_step5p_full_repro_comparison_{RUN_ID}.md"),
        "post_execution_verification": str(RESULTS_DIR / f"locomo_step5p_full_repro_post_execution_verification_{RUN_ID}.json"),
    }
    labels: list[str] = []
    cleanup_result: dict[str, Any] = {}
    prelaunch = None
    validation: dict[str, Any] = {"schema": "memibrium.locomo.step5p.validation.v1", "run_id": RUN_ID, "decision_labels": []}
    guard = None
    try:
        stale = archive_stale_tmp()
        prelaunch = snapshot("prelaunch", env=env, result_path_hygiene=stale)
        preflight_labels = preflight(prelaunch, env)
        write_json(Path(paths["prelaunch_snapshot"]), prelaunch)
        if preflight_labels:
            labels = preflight_labels + ["no_go_phase_c_still_blocked"]
            validation.update({"status": "blocked_preflight", "decision_labels": labels, "preflight_blocked_labels": preflight_labels})
            write_json(Path(paths["validation"]), validation)
            write_json(Path(paths["labels"]), {"run_id": RUN_ID, "decision_labels": labels})
            return 70
        guard = run_benchmark_with_guard(env)
        write_json(Path(paths["guard_summary"]), guard)
        shutil.copy2(TMP_LOG, Path(paths["run_log"]))
        if guard.get("guard_status") != "passed_startup_guard":
            labels = ["full_repro_blocked_slice_identity_mismatch" if "slice" in str(guard.get("abort_reason")) else "full_repro_blocked_runtime_error", "no_go_phase_c_still_blocked"]
            validation.update({"status": "blocked_guard", "guard_summary": guard, "decision_labels": labels})
        elif guard.get("returncode") != 0:
            labels = ["full_repro_blocked_runtime_error", "no_go_phase_c_still_blocked"]
            validation.update({"status": "blocked_runtime", "guard_summary": guard, "decision_labels": labels})
        elif not TMP_RESULT.exists():
            labels = ["full_repro_blocked_runtime_error", "no_go_phase_c_still_blocked"]
            validation.update({"status": "missing_result", "guard_summary": guard, "decision_labels": labels})
        else:
            shutil.copy2(TMP_RESULT, Path(paths["raw_result"]))
            raw = json.loads(TMP_RESULT.read_text())
            log_text = TMP_LOG.read_text(errors="replace")
            validation = summarize_result(raw, log_text)
            labels = validation["decision_labels"]
        postrun = snapshot("postrun_before_cleanup", env=env)
        write_json(Path(paths["postrun_snapshot"]), postrun)
    finally:
        try:
            cleanup_result = {
                "schema": "memibrium.locomo.step5p.cleanup.v1",
                "run_id": RUN_ID,
                "started_at": utc_now(),
                "hygiene_after_cleanup": clean_locomo_domains(),
                "completed_at": utc_now(),
            }
        except Exception as exc:
            cleanup_result = {"schema": "memibrium.locomo.step5p.cleanup.v1", "run_id": RUN_ID, "error": repr(exc), "completed_at": utc_now()}
        if not cleanup_result.get("hygiene_after_cleanup", {}).get("ok"):
            if "full_repro_blocked_cleanup_failure" not in labels:
                labels = [l for l in labels if l != "full_repro_execution_complete_valid"] + ["full_repro_blocked_cleanup_failure", "no_go_phase_c_still_blocked"]
        write_json(Path(paths["cleanup"]), cleanup_result)
        validation["cleanup"] = cleanup_result
        validation["decision_labels"] = sorted(set(labels), key=labels.index if labels else None)
        write_json(Path(paths["validation"]), validation)
        write_json(Path(paths["labels"]), {"schema": "memibrium.locomo.step5p.labels.v1", "run_id": RUN_ID, "decision_labels": validation["decision_labels"]})
        comparison_md = write_markdown(validation, validation["decision_labels"], paths, cleanup_result.get("hygiene_after_cleanup", cleanup_result))
        Path(paths["comparison"]).write_text(comparison_md)
        final_verification = {
            "schema": "memibrium.locomo.step5p.post_execution_verification.v1",
            "run_id": RUN_ID,
            "captured_at": utc_now(),
            "health": health(),
            "locomo_hygiene": locomo_hygiene(),
            "process_matches": process_matches(),
            "git_status_short": git("status", "--short", check=False),
            "decision_labels": validation["decision_labels"],
            "artifact_paths": paths,
        }
        write_json(Path(paths["post_execution_verification"]), final_verification)
    print(json.dumps({"run_id": RUN_ID, "labels": validation.get("decision_labels"), "paths": paths}, indent=2))
    return 0 if "full_repro_blocked_cleanup_failure" not in validation.get("decision_labels", []) else 80


if __name__ == "__main__":
    raise SystemExit(main())
