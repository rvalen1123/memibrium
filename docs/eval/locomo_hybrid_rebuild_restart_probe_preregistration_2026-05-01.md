# LOCOMO hybrid-active mutation-window pre-registration — 2026-05-01

Repo: `/home/zaddy/src/Memibrium`
Branch: `query-expansion`
Phase B artifact commit before this document: `b4590d3` (`docs: record LOCOMO phase B audit artifacts`)

## Scope

This document pre-registers exactly one atomic rebuild/restart/probe mutation window whose only goal is to make the live Memibrium server run the current host source and then determine whether hybrid retrieval is positively active under the existing `ruvector` DB schema.

This is not Phase C. This is not a LOCOMO benchmark. This is not an intervention-selection window. No benchmark may be launched from this procedure.

## Locked factual basis

Phase B/B.5 found:

- Host `hybrid_retrieval.py` uses `embedding <=> $1::{self.vtype}`.
- Live container `/app/hybrid_retrieval.py` hard-codes `embedding <=> $1::vector`.
- The DB has `ruvector` and does not have `vector`.
- The live server logs `Hybrid retrieval failed: type "vector" does not exist, falling back to legacy recall`.

Therefore prior live-server LOCOMO scores are legacy-recall fallback floors unless a specific run independently proves hybrid-active status.

## Mutation authorization boundary

Authorized side effects in this window:

1. Capture pre-mutation snapshots.
2. Rebuild/recreate/restart only the `memibrium` server service from current host source using `docker compose -f docker-compose.ruvector.yml up -d --build memibrium`.
3. Run read-only DB/source/env/log/health probes.
4. Run a minimal positive-evidence recall probe that must not ingest LOCOMO data and must not require any DB writes.
5. If the positive-evidence probe fails, stop and document; do not retry blindly.

Not authorized in this window:

- LOCOMO benchmark launch.
- LOCOMO ingest.
- LOCOMO cleanup/deletion except for read-only count checks.
- Feature changes or Phase C intervention code changes.
- Multiple rebuild/retry cycles without a written failure note and new approval.

## Clean-stop and rollback path

Before mutation, capture the current server container image ID and inspect metadata. If the rebuilt server is unhealthy or hybrid probe fails due to unexpected runtime breakage, use this stop path:

1. Capture health/log/source/env evidence of failure.
2. Stop further mutation immediately.
3. If service health is broken, restore service availability by either:
   - re-running `docker compose -f docker-compose.ruvector.yml up -d memibrium` if the current image is usable; or
   - documenting the previous image ID so it can be retagged/restored manually if needed.
4. Do not run LOCOMO, do not choose a Phase C intervention, and do not do repeated rebuilds.

The expected preferred rollback is documentation-first because the pre-mutation state was already known to be methodologically invalid for hybrid LOCOMO measurement but operationally healthy.

## Decision tree

### Step 0 — pre-mutation snapshot

Record all of the following before rebuild:

- `date -Is`
- `git branch --show-current`
- `git rev-parse HEAD`
- `git status --short`
- `curl -fsS http://localhost:9999/health`
- `docker ps --format '{{.Names}}|{{.Status}}|{{.Image}}' | grep -E 'memibrium|ruvector|ollama'`
- `docker inspect memibrium-server --format 'server_image={{.Image}} created={{.Created}} started={{.State.StartedAt}}'`
- `docker image inspect <pre_image_id> --format 'image_created={{.Created}} repo_tags={{json .RepoTags}}'`
- redacted `docker exec memibrium-server env` for DB/vector/embedding/chat keys
- host/container source hashes for `server.py` and `hybrid_retrieval.py`
- read-only DB probe for `ruvector`/`vector` type visibility, `memories.embedding` type, extension version, non-null embeddings, and `(embedding <=> embedding)` self-distance
- read-only LOCOMO contamination count: `SELECT count(id) FROM memories WHERE domain LIKE 'locomo-%';`
- tail recent server logs and explicitly record whether the old fallback string appears

### Step 1 — rebuild/restart once

Run exactly once:

```bash
cd /home/zaddy/src/Memibrium
docker compose -f docker-compose.ruvector.yml up -d --build memibrium
```

Then wait for health using bounded polling. Do not rebuild a second time in the same window.

### Step 2 — post-restart configuration/source proof

Record:

- post image/container IDs and started timestamp
- `/health`
- redacted server env, especially `USE_RUVECTOR=true`
- `docker exec memibrium-server sha256sum /app/server.py /app/hybrid_retrieval.py`
- `sha256sum server.py hybrid_retrieval.py`
- source grep proving `/app/hybrid_retrieval.py` no longer hard-codes `$1::vector` and does contain `$1::{self.vtype}`
- DB read-only probe still showing `ruvector`, no `vector`, and a successful self-distance operator call

### Step 3 — positive-evidence hybrid-active probe

Run a minimal non-LOCOMO recall probe against a nonexistent domain so no LOCOMO ingest/cleanup is involved:

```bash
curl -fsS -X POST http://localhost:9999/mcp/recall \
  -H 'Content-Type: application/json' \
  -d '{"query":"hybrid active ruvector smoke probe", "top_k":1, "domain":"__hybrid_active_probe_no_rows__"}'
```

Then inspect logs after the probe.

Positive evidence requires all of the following:

1. Server health is OK.
2. `USE_RUVECTOR=true` is visible in the running container.
3. Live `/app/hybrid_retrieval.py` does not contain the semantic-search hard-code `$1::vector`.
4. Live `/app/hybrid_retrieval.py` does contain `$1::{self.vtype}` or equivalent safe dynamic cast.
5. DB probe confirms `memories.embedding` is `USER-DEFINED:ruvector` and the self-distance operator succeeds.
6. The recall probe returns a valid response, even if empty because the domain is intentionally nonexistent.
7. Fresh logs after the probe do not contain `Hybrid retrieval failed` or `type "vector" does not exist`.

### Step 4 — stop/go decision

- If all positive-evidence criteria pass: record `hybrid_active=true`; Phase C remains blocked until the separate no-intervention hybrid-active substrate baseline policy/run is handled.
- If any criterion fails: record `hybrid_active=false`; stop; do not benchmark; do not pick Phase C intervention.

## Evidence artifact to write after execution

Write the execution result to:

`docs/eval/results/locomo_hybrid_rebuild_restart_probe_result_2026-05-01.md`

The result document must include commands, timestamps, key outputs, decision-tree verdict, and whether Phase C remains blocked.
