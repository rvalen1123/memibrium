#!/usr/bin/env python3
"""Read-only evidence helpers for the LOCOMO telemetry instrumentation mutation window.

This script intentionally does not mutate Memibrium state. It captures health,
source/env/DB/log evidence, smoke hashes, and probe responses for the
preregistered telemetry instrumentation mutation window.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parents[1]
MCP = "http://localhost:9999/mcp"
HEALTH = "http://localhost:9999/health"
SMOKE_QUERIES = [
    "Caroline adoption agencies LGBTQ individuals",
    "Melanie charity race mental health self care",
    "LGBTQ counseling workshop therapeutic methods",
    "pottery workshop July Melanie",
    "beach with kids once or twice a year",
    "camping trip meteor shower family",
    "Grand Canyon accident children road trip",
    "necklace Sweden grandmother love faith strength",
    "pride parade school speech support group",
    "adoption council meeting loving homes children",
    "running de-stress clear her mind mental health",
    "Caroline picnic week before July 6 2023",
    "Nothing is Impossible book Melanie 2022",
    "The Four Seasons Vivaldi classical music",
    "safe and inviting place for people to grow",
    "hybrid active ruvector smoke probe",
]
SECRET_RE = re.compile(r"(KEY|TOKEN|PASSWORD|PASS|SECRET|CONNECTION|DATABASE_URL|POSTGRES_URI|URI|DSN)", re.I)
ENV_ALLOW_RE = re.compile(r"(RUVECTOR|VECTOR|EMBED|AZURE|OPENAI|CHAT|MODEL|TELEMETRY|USE_|DIM|POSTGRES|DATABASE)", re.I)


def run(cmd: list[str] | str, timeout: int = 60, check: bool = False) -> dict[str, Any]:
    shell = isinstance(cmd, str)
    proc = subprocess.run(
        cmd,
        shell=shell,
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=timeout,
    )
    if check and proc.returncode != 0:
        raise RuntimeError(f"command failed {cmd!r}: {proc.stderr or proc.stdout}")
    return {"cmd": cmd, "returncode": proc.returncode, "stdout": proc.stdout.strip(), "stderr": proc.stderr.strip()}


def http_json(url: str, payload: dict[str, Any] | None = None, timeout: int = 30) -> dict[str, Any]:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urlrequest.Request(url, data=data, headers=headers, method="POST" if payload is not None else "GET")
    try:
        with urlrequest.urlopen(req, timeout=timeout) as resp:
            text = resp.read().decode("utf-8")
            return {"ok": True, "status": resp.status, "text": text, "json": json.loads(text) if text.strip() else None}
    except HTTPError as e:
        text = e.read().decode("utf-8", errors="replace")
        return {"ok": False, "status": e.code, "text": text, "json": None}
    except (URLError, TimeoutError, json.JSONDecodeError) as e:
        return {"ok": False, "status": None, "text": str(e), "json": None}


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def file_hash(path: Path) -> str | None:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def projection_key(item: Any) -> str:
    if isinstance(item, dict):
        mid = item.get("id")
        if mid:
            return str(mid)
        content = item.get("content", "")
    else:
        content = str(item or "")
    return "sha256:" + hashlib.sha256(str(content).encode("utf-8")).hexdigest()


def smoke_hash() -> dict[str, Any]:
    per_query = []
    aggregate_lines = []
    for query in SMOKE_QUERIES:
        resp = http_json(f"{MCP}/recall", {"query": query, "top_k": 10}, timeout=60)
        rows = resp.get("json") if resp.get("ok") else None
        keys = [projection_key(item) for item in rows] if isinstance(rows, list) else []
        per_hash = sha256_text("\n".join(keys))
        per_query.append({
            "query": query,
            "ok": resp.get("ok"),
            "status": resp.get("status"),
            "result_count": len(keys),
            "ordered_result_keys": keys,
            "per_query_hash": per_hash,
            "response_shape": type(rows).__name__ if rows is not None else None,
        })
        aggregate_lines.append(f"{query}\t{per_hash}")
    return {
        "top_k": 10,
        "include_telemetry": False,
        "queries": per_query,
        "aggregate_hash": sha256_text("\n".join(aggregate_lines)),
    }


def docker_env() -> dict[str, str]:
    out = run(["docker", "exec", "memibrium-server", "env"], timeout=30)
    env: dict[str, str] = {}
    if out["returncode"] != 0:
        return {"__error__": out["stderr"] or out["stdout"]}
    for line in out["stdout"].splitlines():
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        if not ENV_ALLOW_RE.search(k):
            continue
        env[k] = "[REDACTED]" if SECRET_RE.search(k) else v
    return dict(sorted(env.items()))


def db_probe() -> dict[str, Any]:
    sql = r"""
SELECT jsonb_build_object(
  'ruvector_type_count', (SELECT count(*) FROM pg_type WHERE typname='ruvector'),
  'vector_type_count', (SELECT count(*) FROM pg_type WHERE typname='vector'),
  'memories_embedding_type', (
    SELECT data_type || ':' || udt_name
    FROM information_schema.columns
    WHERE table_name='memories' AND column_name='embedding'
    LIMIT 1
  ),
  'ruvector_extension_version', (SELECT extversion FROM pg_extension WHERE extname='ruvector' LIMIT 1),
  'nonnull_embeddings', (SELECT count(id) FROM memories WHERE embedding IS NOT NULL),
  'locomo_contamination_count', (SELECT count(id) FROM memories WHERE domain LIKE 'locomo-%'),
  'self_distance', (SELECT (embedding <=> embedding)::text FROM memories WHERE embedding IS NOT NULL LIMIT 1)
)::text;
""".strip()
    with tempfile.NamedTemporaryFile("w", delete=False) as tmp:
        tmp.write(sql)
        tmp_path = tmp.name
    try:
        copy = run(["docker", "cp", tmp_path, "memibrium-ruvector-db:/tmp/locomo_telemetry_probe.sql"], timeout=30)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
    cmd = [
        "docker", "exec", "memibrium-ruvector-db", "psql",
        "-U", "memory", "-d", "memory", "-tA", "-f", "/tmp/locomo_telemetry_probe.sql",
    ]
    out = run(cmd, timeout=60)
    result = {"command_returncode": out["returncode"], "copy_returncode": copy["returncode"], "stderr": out["stderr"] or copy["stderr"]}
    if out["returncode"] == 0 and out["stdout"]:
        try:
            result["json"] = json.loads(out["stdout"].splitlines()[-1])
        except json.JSONDecodeError:
            result["raw_stdout"] = out["stdout"]
    else:
        result["raw_stdout"] = out["stdout"]
    return result


def source_checks() -> dict[str, Any]:
    checks: dict[str, Any] = {}
    for path in ["/app/server.py", "/app/hybrid_retrieval.py", "/app/benchmark_scripts/locomo_bench_v2.py"]:
        out = run(["docker", "exec", "memibrium-server", "sha256sum", path], timeout=30)
        checks[f"container_sha256_{path}"] = out
    for path in ["server.py", "hybrid_retrieval.py", "benchmark_scripts/locomo_bench_v2.py", "test_server_recall_telemetry.py"]:
        checks[f"host_sha256_{path}"] = file_hash(ROOT / path)
    probe = """
from pathlib import Path
text=Path('/app/hybrid_retrieval.py').read_text()
server=Path('/app/server.py').read_text()
print('hardcoded_vector_cast_present=' + str('$1::vector' in text))
print('dynamic_vtype_cast_present=' + str('$1::{self.vtype}' in text))
print('hybrid_telemetry_schema_present=' + str('memibrium.hybrid_retrieval.telemetry.v1' in text))
print('server_include_telemetry_present=' + str('include_telemetry' in server))
""".strip()
    checks["live_source_feature_probe"] = run(["docker", "exec", "-i", "memibrium-server", "python3", "-c", probe], timeout=30)
    return checks


def log_tail() -> dict[str, Any]:
    out = run(["docker", "logs", "--tail", "200", "memibrium-server"], timeout=30)
    text = (out["stdout"] + "\n" + out["stderr"]).strip()
    return {
        "returncode": out["returncode"],
        "tail": text,
        "contains_hybrid_retrieval_failed": "Hybrid retrieval failed" in text,
        "contains_type_vector_missing": 'type "vector" does not exist' in text,
        "contains_telemetry_serialization": "telemetry" in text.lower() and ("error" in text.lower() or "exception" in text.lower()),
    }


def snapshot(label: str, include_smoke: bool = True) -> dict[str, Any]:
    snap: dict[str, Any] = {
        "label": label,
        "captured_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "git": {
            "branch": run(["git", "branch", "--show-current"], timeout=20)["stdout"],
            "head": run(["git", "rev-parse", "HEAD"], timeout=20)["stdout"],
            "status_short": run(["git", "status", "--short"], timeout=20)["stdout"],
        },
        "health": http_json(HEALTH, timeout=15),
        "docker_ps": run("docker ps --format '{{.Names}}|{{.Status}}|{{.Image}}' | grep -E 'memibrium|ruvector|ollama'", timeout=30),
        "server_container_inspect": run(["docker", "inspect", "memibrium-server", "--format", "server_image={{.Image}} created={{.Created}} started={{.State.StartedAt}}"], timeout=30),
        "server_env_redacted": docker_env(),
        "source_checks": source_checks(),
        "db_probe": db_probe(),
        "log_tail": log_tail(),
    }
    image_id = snap["server_container_inspect"].get("stdout", "")
    m = re.search(r"server_image=([^ ]+)", image_id)
    if m:
        snap["server_image_inspect"] = run(["docker", "image", "inspect", m.group(1), "--format", "image_created={{.Created}} repo_tags={{json .RepoTags}}"], timeout=30)
    if include_smoke:
        snap["smoke_hash"] = smoke_hash()
    return snap


def hybrid_probe() -> dict[str, Any]:
    before = log_tail()
    resp = http_json(f"{MCP}/recall", {"query": "hybrid active ruvector smoke probe", "top_k": 1, "domain": "__hybrid_active_probe_no_rows__"}, timeout=60)
    after = log_tail()
    return {"response": resp, "log_before_flags": {k: before[k] for k in before if k.startswith("contains_")}, "log_after": after}


def telemetry_probe() -> dict[str, Any]:
    payload = {"query": "hybrid telemetry ruvector smoke probe", "top_k": 3, "domain": "__hybrid_telemetry_probe_no_rows__", "include_telemetry": True}
    telem = http_json(f"{MCP}/recall", payload, timeout=60)
    plain = http_json(f"{MCP}/recall", {"query": payload["query"], "top_k": 3, "domain": payload["domain"]}, timeout=60)
    after = log_tail()
    return {"telemetry_response": telem, "plain_response": plain, "log_after": after}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["snapshot", "smoke", "hybrid-probe", "telemetry-probe"])
    ap.add_argument("--label", default="snapshot")
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    if args.command == "snapshot":
        data = snapshot(args.label, include_smoke=True)
    elif args.command == "smoke":
        data = {"label": args.label, "captured_at": dt.datetime.now(dt.timezone.utc).isoformat(), "smoke_hash": smoke_hash()}
    elif args.command == "hybrid-probe":
        data = {"label": args.label, "captured_at": dt.datetime.now(dt.timezone.utc).isoformat(), "hybrid_probe": hybrid_probe()}
    elif args.command == "telemetry-probe":
        data = {"label": args.label, "captured_at": dt.datetime.now(dt.timezone.utc).isoformat(), "telemetry_probe": telemetry_probe()}
    else:
        raise AssertionError(args.command)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
