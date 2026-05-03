#!/usr/bin/env python3
"""One-last-go LOCOMO spike: full-domain context.

This is deliberately lighter than the Step 5 prereg harness. It runs the
corrected conv-26 slice once with --query-expansion plus --full-domain-context,
archives the raw result/log, validates basic shape, cleans LOCOMO rows, and
writes a compact summary. No Phase C/baseline promotion is implied.
"""
from __future__ import annotations

import collections
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
RESULTS_DIR = ROOT / "docs/eval/results"
DATA_PATH = Path("/tmp/locomo/data/locomo10.json")
RUN_ID = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
TMP_RESULT = Path("/tmp/locomo_results_query_expansion_raw_full_domain_context.json")
TMP_LOG = Path(f"/tmp/locomo_last_go_full_domain_context_{RUN_ID}.log")
EXPECTED_DATA_SHA256 = "79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4"
COMMAND = [
    "python3",
    "benchmark_scripts/locomo_bench_v2.py",
    "--max-convs",
    "1",
    "--query-expansion",
    "--full-domain-context",
]


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def run_cmd(cmd: list[str], *, input_text: str | None = None, env: dict[str, str] | None = None, timeout: int = 120, check: bool = True) -> subprocess.CompletedProcess[str]:
    res = subprocess.run(cmd, cwd=ROOT, input=input_text, env=env, text=True, capture_output=True, timeout=timeout, check=False)
    if check and res.returncode != 0:
        raise RuntimeError(f"command failed {res.returncode}: {' '.join(cmd)}\nSTDOUT:\n{res.stdout[-4000:]}\nSTDERR:\n{res.stderr[-4000:]}")
    return res


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
        "USE_FULL_DOMAIN_CONTEXT": "1",
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


def psql(sql: str, *, timeout: int = 120, check: bool = True) -> str:
    return run_cmd(
        ["docker", "exec", "-i", "memibrium-ruvector-db", "psql", "-U", "memory", "-d", "memory", "-t", "-A"],
        input_text=sql,
        timeout=timeout,
        check=check,
    ).stdout.strip()


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
    time.sleep(2)
    psql(sql, timeout=180)
    return locomo_hygiene()


def health() -> dict[str, Any]:
    res = run_cmd(["curl", "-fsS", "http://localhost:9999/health"], check=False, timeout=30)
    out: dict[str, Any] = {"returncode": res.returncode, "stdout": res.stdout.strip(), "stderr": res.stderr.strip()}
    try:
        out["json"] = json.loads(res.stdout)
    except Exception:
        out["json"] = None
    return out


def prove_slice() -> dict[str, Any]:
    raw = DATA_PATH.read_bytes()
    data = json.loads(raw)
    conv0 = data[0]
    conv = conv0.get("conversation") or conv0
    qas = conv0.get("qa") or []
    proof = {
        "path": str(DATA_PATH),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "top_level_type": type(data).__name__,
        "index0_sample_id": conv0.get("sample_id"),
        "index0_speaker_a": conv.get("speaker_a"),
        "index0_speaker_b": conv.get("speaker_b"),
        "index0_qa_count": len(qas),
        "ok": False,
    }
    proof["ok"] = (
        proof["sha256"] == EXPECTED_DATA_SHA256
        and proof["top_level_type"] == "list"
        and proof["index0_sample_id"] == "conv-26"
        and proof["index0_speaker_a"] == "Caroline"
        and proof["index0_speaker_b"] == "Melanie"
        and proof["index0_qa_count"] == 199
    )
    return proof


def validate_result(raw: dict[str, Any]) -> dict[str, Any]:
    details = raw.get("details", [])
    scores = [float(r.get("score", 0)) for r in details]
    cats: dict[str, list[float]] = collections.defaultdict(list)
    n_mems = []
    for row in details:
        cats[str(row.get("cat"))].append(float(row.get("score", 0)))
        n_mems.append(int(row.get("n_memories", 0)))
    non_adv = [s for cat, vals in cats.items() if cat != "adversarial" for s in vals]
    return {
        "ok": (
            len(details) == 199
            and all(row.get("conv") == "conv-26" for row in details)
            and raw.get("condition", {}).get("query_expansion") is True
            and raw.get("condition", {}).get("full_domain_context") is True
            and raw.get("expand_query_fallback_count") == 0
        ),
        "detail_rows": len(details),
        "all_conv26": all(row.get("conv") == "conv-26" for row in details),
        "full_5cat_overall": raw.get("full_5cat_overall", raw.get("overall_score")),
        "protocol_4cat_overall": raw.get("protocol_4cat_overall"),
        "category_scores": raw.get("category_scores"),
        "fallback_count": raw.get("expand_query_fallback_count"),
        "condition": raw.get("condition"),
        "mean_n_memories": round(statistics.mean(n_mems), 4) if n_mems else None,
        "n_memories_distribution": dict(sorted(collections.Counter(n_mems).items())),
        "adversarial_score": round(statistics.mean(cats.get("adversarial", [])) * 100, 2) if cats.get("adversarial") else None,
        "non_adversarial_score": round(statistics.mean(non_adv) * 100, 2) if non_adv else None,
    }


def process_matches() -> list[str]:
    res = run_cmd(["ps", "-eo", "pid,args"], check=False)
    pats = ["run_locomo_last_go_full_domain_context.py", "locomo_bench_v2.py"]
    matches = []
    for line in res.stdout.splitlines():
        if any(p in line for p in pats) and "ps -eo" not in line and str(os.getpid()) not in line:
            matches.append(line.strip())
    return matches


def main() -> int:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    env = benchmark_env()
    summary: dict[str, Any] = {
        "schema": "memibrium.locomo.last_go_full_domain_context.v1",
        "run_id": RUN_ID,
        "started_at": utc_now(),
        "command": COMMAND,
        "purpose": "one last opt-in spike: full conversation context to test retrieval/context-selection ceiling",
        "phase_c": "blocked; this run is not a baseline promotion",
        "git_before": run_cmd(["git", "rev-parse", "--short", "HEAD"], check=False).stdout.strip(),
        "health_before": health(),
        "hygiene_before": locomo_hygiene(),
        "slice_proof": prove_slice(),
        "host_benchmark_sha256": sha256_file(ROOT / "benchmark_scripts/locomo_bench_v2.py"),
    }
    if not summary["slice_proof"].get("ok"):
        raise RuntimeError(f"slice proof failed: {summary['slice_proof']}")
    if not summary["hygiene_before"].get("ok"):
        raise RuntimeError(f"pre-run LOCOMO hygiene failed: {summary['hygiene_before']}")

    if TMP_RESULT.exists():
        stale = RESULTS_DIR / f"locomo_last_go_stale_{TMP_RESULT.name}_{RUN_ID}"
        shutil.copy2(TMP_RESULT, stale)
        TMP_RESULT.unlink()
        summary["stale_tmp_result_archived_to"] = str(stale)

    with TMP_LOG.open("w") as log:
        proc = subprocess.Popen(COMMAND, cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        assert proc.stdout is not None
        for line in proc.stdout:
            sys.stdout.write(line)
            log.write(line)
            log.flush()
        rc = proc.wait()
    summary["returncode"] = rc
    if rc != 0:
        summary["completed_at"] = utc_now()
        summary_path = RESULTS_DIR / f"locomo_last_go_full_domain_context_summary_{RUN_ID}.json"
        summary_path.write_text(json.dumps(summary, indent=2))
        raise RuntimeError(f"benchmark failed with return code {rc}; see {TMP_LOG}")
    if not TMP_RESULT.exists():
        raise RuntimeError(f"expected result not found: {TMP_RESULT}")

    raw_dest = RESULTS_DIR / f"locomo_last_go_full_domain_context_raw_{RUN_ID}.json"
    log_dest = RESULTS_DIR / f"locomo_last_go_full_domain_context_log_{RUN_ID}.txt"
    shutil.copy2(TMP_RESULT, raw_dest)
    shutil.copy2(TMP_LOG, log_dest)
    raw = json.loads(raw_dest.read_text())
    summary["validation"] = validate_result(raw)
    summary["raw_result"] = str(raw_dest)
    summary["raw_sha256"] = sha256_file(raw_dest)
    summary["log"] = str(log_dest)
    summary["cleanup"] = clean_locomo_domains()
    summary["health_after"] = health()
    summary["process_matches_after"] = process_matches()
    summary["completed_at"] = utc_now()

    summary_path = RESULTS_DIR / f"locomo_last_go_full_domain_context_summary_{RUN_ID}.json"
    summary_path.write_text(json.dumps(summary, indent=2))

    md = RESULTS_DIR / f"locomo_last_go_full_domain_context_result_{RUN_ID}.md"
    v = summary["validation"]
    md.write_text(
        f"# LOCOMO one-last-go full-domain-context spike ({RUN_ID})\n\n"
        "## Intent\n"
        "Give the conv-26 corrected slice one final opt-in try by bypassing retrieval/context selection and feeding the answer model the full ingested conversation-domain context in chronological chunk order. This is a spike, not a canonical baseline or Phase C authorization.\n\n"
        "## Condition\n"
        "- Command: `python3 benchmark_scripts/locomo_bench_v2.py --max-convs 1 --query-expansion --full-domain-context`\n"
        "- Query expansion: on\n"
        "- Full-domain context: on\n"
        "- Context rerank / append / legacy: off\n\n"
        "## Result\n"
        f"- Valid shape: {v['ok']}\n"
        f"- Full 5-cat overall: {v['full_5cat_overall']}%\n"
        f"- Protocol 4-cat overall: {v['protocol_4cat_overall']}%\n"
        f"- Category scores: `{json.dumps(v['category_scores'], sort_keys=True)}`\n"
        f"- Mean n_memories: {v['mean_n_memories']}\n"
        f"- n_memories distribution: `{json.dumps(v['n_memories_distribution'], sort_keys=True)}`\n"
        f"- Query-expansion fallback count: {v['fallback_count']}\n\n"
        "## Interpretation boundary\n"
        "If this improves materially, the ceiling is mostly context selection/retrieval under the LOCOMO harness. If it does not, LOCOMO is not worth further score-chasing here. Phase C remains blocked either way.\n\n"
        "## Artifacts\n"
        f"- Raw: `{raw_dest}`\n"
        f"- Summary: `{summary_path}`\n"
        f"- Log: `{log_dest}`\n"
    )
    print(f"Summary: {summary_path}")
    print(f"Result MD: {md}")
    return 0 if summary["validation"].get("ok") and summary["cleanup"].get("ok") and not summary["process_matches_after"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
