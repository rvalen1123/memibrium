# LOCOMO canonical substrate env-alignment mutation pre-registration — 2026-05-01

Repo: `/home/zaddy/src/Memibrium`
Branch: `query-expansion`
Prerequisite docs:
- `docs/eval/locomo_hybrid_rebuild_restart_probe_preregistration_2026-05-01.md`
- `docs/eval/results/locomo_hybrid_rebuild_restart_probe_result_2026-05-01.md`
- `docs/eval/locomo_hybrid_active_substrate_baseline_preregistration_2026-05-01.md`
- `docs/eval/results/locomo_hybrid_active_substrate_baseline_blocked_2026-05-01.md`
- `docs/eval/env_drift_diagnostic_2026-05-01.md`

## Purpose

Align the live server runtime to the canonical LOCOMO comparison substrate after hybrid retrieval has already been proven active.

This is a separate, smaller mutation window from the source rebuild/restart mutation. It changes runtime env only, then recreates/restarts only `memibrium-server` so the existing canonical hybrid-active substrate baseline preregistration can be evaluated without triple-coupled substrate drift.

## Scope

Allowed mutations in this window:

1. Backup ignored local `.env` to a timestamped file outside git, e.g. `/tmp/memibrium_env_backup_2026-05-01_<timestamp>.env`.
2. Edit only these ignored `.env` keys:
   - `AZURE_CHAT_ENDPOINT`
   - `AZURE_CHAT_DEPLOYMENT`
   - `AZURE_EMBEDDING_ENDPOINT`
   - `AZURE_EMBEDDING_DEPLOYMENT`
   - optionally `CHAT_MODEL` to remove misleading `openai/` prefix for local consistency, even though compose hard-codes container `CHAT_MODEL`.
3. Recreate/restart only the `memibrium` service container using current image/source, with no rebuild:
   - `docker compose -f docker-compose.ruvector.yml up -d --no-build --no-deps --force-recreate memibrium`
4. Run read-only probes to verify env/source/health/DB/hybrid status.
5. If all gates pass, proceed to the already-preregistered no-intervention substrate baseline.

Disallowed in this window:

- No image rebuild.
- No DB schema changes.
- No DB cleanup unless a LOCOMO baseline is subsequently launched and cleanup becomes mandatory under the baseline preregistration.
- No Phase C intervention selection or code changes.
- No retry loop that repeatedly mutates env/restarts to chase success. If the first alignment fails, stop and document.

## Target canonical server env

The server container must resolve to:

```text
AZURE_CHAT_ENDPOINT=https://sector-7.services.ai.azure.com
AZURE_CHAT_DEPLOYMENT=gpt-4.1-mini
AZURE_EMBEDDING_ENDPOINT=https://sector-7.openai.azure.com/
AZURE_EMBEDDING_DEPLOYMENT=text-embedding-3-small
AZURE_OPENAI_DEPLOYMENT=gpt-4.1-mini
USE_RUVECTOR=true
RUVECTOR_GNN=true
```

Notes:

- `AZURE_CHAT_ENDPOINT` should remain the base Foundry endpoint because `ChatClient` appends `/models` internally.
- `AZURE_EMBEDDING_ENDPOINT=https://sector-7.openai.azure.com/` is the preferred recovered-floor candidate from the text-embedding-3-small reproduction preregistration.
- If that endpoint fails during the probe, stop. Do not silently fall back to `https://sector-7.services.ai.azure.com` without a separate documented decision because that weakens historical comparability.

## Pre-mutation snapshot

Before editing `.env`, capture:

1. UTC/local timestamp.
2. `git status --short`, branch, HEAD.
3. `/health` response.
4. `docker ps` for Memibrium containers.
5. Current server image id and container started time.
6. Redacted current live server env for DB/vector/chat/embedding keys.
7. Sanitized current `.env` values for the same keys.
8. `sha256sum server.py hybrid_retrieval.py` on host and inside container.
9. Read-only DB probe:
   - `SELECT count(id) FROM memories WHERE domain LIKE 'locomo-%';`
   - `memories.embedding` type/udt name;
   - ruvector extension version;
   - ruvector self-distance smoke query.
10. Fresh server log tail filtered for `Hybrid retrieval failed`, `type "vector" does not exist`, `text-embedding`, `ChatClient`, and `Vector extension`.

If LOCOMO contamination count is nonzero before mutation, stop and document. Cleanup would be a separate DB mutation.

## Mutation procedure

Single allowed mutation sequence:

```bash
cd /home/zaddy/src/Memibrium
TS=$(date -u +%Y%m%dT%H%M%SZ)
cp .env "/tmp/memibrium_env_backup_2026-05-01_${TS}.env"
python3 - <<'PY'
from pathlib import Path
p = Path('.env')
lines = p.read_text().splitlines()
updates = {
    'AZURE_CHAT_ENDPOINT': 'https://sector-7.services.ai.azure.com',
    'AZURE_CHAT_DEPLOYMENT': 'gpt-4.1-mini',
    'AZURE_EMBEDDING_ENDPOINT': 'https://sector-7.openai.azure.com/',
    'AZURE_EMBEDDING_DEPLOYMENT': 'text-embedding-3-small',
    'CHAT_MODEL': 'gpt-4.1-mini',
}
seen = set()
out = []
for line in lines:
    if '=' in line and not line.lstrip().startswith('#'):
        key = line.split('=', 1)[0]
        if key in updates:
            out.append(f'{key}={updates[key]}')
            seen.add(key)
            continue
    out.append(line)
for key, value in updates.items():
    if key not in seen:
        out.append(f'{key}={value}')
p.write_text('\n'.join(out) + '\n')
PY

docker compose -f docker-compose.ruvector.yml up -d --no-build --no-deps --force-recreate memibrium
```

This recreates only `memibrium-server`. It should not rebuild the image and should not restart DB or Ollama.

## Rollback path

If post-mutation gates fail:

1. Do not run LOCOMO.
2. Restore `.env` from the captured backup:
   - `cp /tmp/memibrium_env_backup_2026-05-01_<timestamp>.env .env`
3. Recreate only the server container without build:
   - `docker compose -f docker-compose.ruvector.yml up -d --no-build --no-deps --force-recreate memibrium`
4. Capture rollback health/env/logs.
5. Commit a blocked/rollback result doc.

Rollback is a second mutation, but it is pre-authorized only as a clean-stop path if the single alignment attempt fails its gates.

## Post-mutation gates

The alignment succeeds only if all are true:

1. `/health` returns OK.
2. Live server env shows:
   - `AZURE_CHAT_DEPLOYMENT=gpt-4.1-mini`
   - `AZURE_CHAT_ENDPOINT=https://sector-7.services.ai.azure.com`
   - `AZURE_EMBEDDING_DEPLOYMENT=text-embedding-3-small`
   - `AZURE_EMBEDDING_ENDPOINT=https://sector-7.openai.azure.com/`
   - `USE_RUVECTOR=true`
3. Live `/app/hybrid_retrieval.py` still satisfies:
   - `contains_literal_vector_cast False`
   - `contains_dynamic_vtype_cast True`
4. DB still has `memories.embedding` as `USER-DEFINED:ruvector` and ruvector self-distance succeeds.
5. LOCOMO contamination count remains `0`.
6. `/mcp/test_embeddings` returns Azure success for deployment `text-embedding-3-small` with `1536` dimensions.
7. Fresh server logs show:
   - `ChatClient: Azure Foundry (... model=gpt-4.1-mini)`
   - Azure embedding request path includes `/deployments/text-embedding-3-small/embeddings`
   - no `Hybrid retrieval failed`
   - no `type "vector" does not exist`
8. A non-LOCOMO recall probe returns HTTP 200 without fallback logs. The probe must not retain/write memories.

If any gate fails, stop and document. Do not run the baseline.

## Baseline handoff if gates pass

If all gates pass, the existing baseline preregistration becomes launch-ready:

`docs/eval/locomo_hybrid_active_substrate_baseline_preregistration_2026-05-01.md`

Required immediate prelaunch rechecks remain in force:

- mutation result and alignment result committed;
- health OK;
- canonical substrate identity still confirmed;
- LOCOMO contamination count still `0`;
- fresh logs have no hybrid fallback strings.

Then run the canonical conv-26 query-expansion baseline exactly as registered there. This is still not Phase C; it is the no-intervention hybrid-active substrate baseline.

## Result artifact

Write and commit one of:

- success: `docs/eval/results/locomo_substrate_env_alignment_result_2026-05-01.md`
- blocked/rollback: `docs/eval/results/locomo_substrate_env_alignment_blocked_2026-05-01.md`

The result must include:

- backup path;
- pre/post sanitized env;
- restart/recreate command output;
- health/source/DB/probe/log evidence;
- explicit `baseline_launch_ready=true|false`.
