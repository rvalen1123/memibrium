# LongMemEval Retrieval Bridge Phase A Live Attempt — 2026-05-12T08:45:46Z

## Status

Failed before retrieval. This is not a Phase A retrieval result and is not benchmark evidence.

No answer model calls, judge calls, full LongMemEval `_s` / `_m`, or `/mcp/tools` inspection were performed.

## Approved Scope Used

- DB ingest writes: yes
- Runtime retrieval/context calls: yes
- Cleanup deletes: yes
- Server action: use current server
- Answer model calls: no
- Judge calls: no
- Full LongMemEval `_s` / `_m`: no
- `/mcp/tools` inspection: no

## Read-Only Preflight Summary

- Branch: `main`
- HEAD before live attempt: `7cc489c docs: refresh LongMemEval Phase A handoff after merge`
- Server health endpoint: HTTP 200, `status=ok`, `engine=memibrium`
- CLI gate check: runtime Phase A path rejects missing DB DSN as expected
- DB config: `.env` had DB parts available, but the later `.env`-derived localhost DSN failed authentication during cleanup
- Current server containers were running and healthy before failure inspection:
  - `memibrium-server`
  - `memibrium-ruvector-db`
  - `memibrium-ollama`

## Attempt Notes

### Attempt 0 — no side effects

Command used the default selection file by mistake. The runner failed before creating the output directory or making runtime side effects:

```text
ValueError: retrieval_bridge_requires_second_slice_seed
```

### Attempt 1 — approved live path with second-slice selection

Selection file:

```text
docs/eval/results/longmemeval_oracle_canary_25_second_slice_selection_20260508.json
```

Planned manifest properties, recomputed from the runner:

- selected questions: 25
- planned memories: 446
- source sessions: 40
- answer sessions: 40
- domain: `longmemeval-bridge-v1-20260508-second-slice`
- selection seed: `memibrium-longmemeval-oracle-canary-2026-05-08-v2`

The live run timed out during `/mcp/retain` ingest before retrieval began:

```text
RuntimeError: memibrium_http_call_failed:/mcp/retain:timed out
MemibriumIngestError: memibrium_ingest_partial_failure
```

The runner then attempted cleanup with the provided `.env`-derived DB DSN, but that DSN failed authentication:

```text
asyncpg.exceptions.InvalidPasswordError: password authentication failed for user "memory"
```

Because the failure happened before ingest completed, the runner did not write a Phase A gate report or retrieval artifacts.

## Cleanup Recovery

A separate approved domain-wide cleanup recovery was performed using the running `memibrium-server` container's DB environment without printing secrets.

Cleanup result:

- domain before cleanup: 52 memories
- deleted memories: 52
- deleted memory edges: 11
- final domain count verified: 0

No Phase A domain residue remained after this recovery cleanup according to the cleanup verification result.

## Interpretation

This attempt proves that the merged live-adapter path reached real `/mcp/retain`, but it did not complete Phase A ingest and did not reach retrieval/context calls.

The immediate blocker is operational, not a LongMemEval retrieval-quality signal:

1. current server `/mcp/retain` timed out during bulk Phase A ingest;
2. the repo `.env` DB credentials did not match the running DB credentials used by the live server.

## Next Valid Rung

Do not rerun blindly.

Recommended next step is a separately explicit corrective runtime window choosing one of:

1. use current server again, but supply a DB DSN derived from the running server container environment and use a longer retain timeout through a controlled wrapper; or
2. rebuild/restart Memibrium, verify the DB DSN against the running server environment, then rerun exactly one no-answer/no-judge Phase A live retrieval pass.

Either path still requires explicit approval for DB ingest writes, runtime retrieval/context calls, cleanup deletes, and server action.
