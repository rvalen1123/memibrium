# Memibrium Evaluation Handoff — LongMemEval Phase A

## Current Active Work

LongMemEval retrieval bridge Phase A live adapters have landed on `main`.

This is still readiness/retrieval plumbing only. No live LongMemEval retrieval run has been approved or performed unless a later artifact explicitly records a live Phase A launch.

## Repo State

- Repo: `/home/zaddy/src/Memibrium`
- Current branch: `main`
- Remote: `https://github.com/rvalen1123/memibrium.git`
- PR #4: https://github.com/rvalen1123/memibrium/pull/4
- PR #4 status: `MERGED`
- PR #4 merge commit: `9213b081d16fe2c12547faf71b871781f07286b3`
- Handoff docs commit on main before this refresh: `e3083aa docs: update LongMemEval Phase A handoff`

Known pre-existing untracked noise remains intentionally untouched:

- `docs/reference/`
- `docs/eval/results/locomo_context_packet_canary_*`

Do not stage or commit those unless explicitly asked.

## What Landed In PR #4

PR #4 wires real Memibrium adapters into the existing LongMemEval retrieval bridge Phase A runner seam, while keeping the runtime path fail-closed behind explicit side-effect gates.

Code changed:

- `docs/eval/results/run_longmemeval_oracle_canary.py`
- `test_longmemeval_oracle_canary.py`

Implemented surfaces:

- HTTP ingest adapter posts planned memories to `/mcp/retain`.
- HTTP retrieval adapter calls `/mcp/context_packet` with source attribution enabled and decision traces disabled.
- DB cleanup adapter is constrained to the exact Phase A domain.
- CLI wiring for `--run-retrieval-bridge-phase-a` requires explicit side-effect flags.
- Runtime metadata is redacted; Memibrium base URL credentials/query strings and DB DSNs must not be printed or written to artifacts.

Runtime Phase A path requires all of:

- `--run-retrieval-bridge-phase-a`
- `--allow-db-writes`
- `--allow-runtime-retrieval`
- `--allow-cleanup-deletes`
- `--memibrium-db-dsn` or `MEMIBRIUM_DB_DSN`

Safety prohibitions preserved:

- No answer model calls.
- No judge calls.
- No full LongMemEval `_s` / `_m` run.
- No `/mcp/tools` inspection unless separately approved.

## Review Fixes Included Before Merge

- `memibrium_http_post` validates Memibrium base URL scheme before `urlopen`; only `http`/`https` are allowed.
- Non-JSON HTTP 200 responses raise `RuntimeError("memibrium_http_invalid_json:...")`.
- `_parse_longmemeval_session_date` returns `None` on parse failure instead of raw non-ISO text.
- `_parse_longmemeval_session_date` has a docstring documenting ISO8601-or-None behavior and the UTC stamping assumption for naive parsed datetimes.
- `MemibriumIngestError` carries partial `created_ids` and the original exception.
- `run_retrieval_bridge_phase_a` cleans up in `finally`, including after partial ingest failure.
- Cleanup initializes `conn = None` and does not mask connection failures.
- Cleanup exposes an async variant and avoids blind `asyncio.run` inside running event loops.
- Cleanup scopes DELETEs by `memory_ids` when available.
- Empty `memory_ids` remains intentional domain-wide failure recovery.
- Cleanup destructive DELETEs and final zero-count verification are transactional.
- Cleanup SQL uses static scoped/domain-wide branches, not dynamic filter interpolation.

## Verification Before Merge

Local verification before merge:

```bash
python3 -m unittest test_longmemeval_oracle_canary -v
# Ran 46 tests: OK

python3 -m unittest discover -v
# Ran 195 tests: OK

git ls-files '*.py' | xargs python3 -m py_compile
# OK

git diff --check
# OK
```

Remote PR checks passed before merge:

- CI 3.11 / 3.12 / 3.13
- CodeQL
- Snyk
- Socket
- Sourcery
- Semgrep
- CodeRabbit

## What This Is Not

This merged work is not retrieval-performance evidence and does not claim:

- LongMemEval retrieval performance
- product benchmark performance
- answer-side score improvement
- judge-verified benchmark progress

It only makes the next retrieval-only Phase A live run possible under explicit approvals.

## Next Valid Rung

The next valid rung is a no-answer/no-judge live Phase A retrieval run using the existing gates, but only after explicit approval for each side effect.

Do not infer runtime approval from:

- PR #4 being merged
- code readiness
- review completion
- a generic “proceed”

Before any live Phase A retrieval run, collect explicit confirmation for:

```text
Approve LongMemEval Phase A live retrieval run with:
- DB ingest writes: yes/no
- Runtime retrieval/context calls: yes/no
- Cleanup deletes: yes/no
- Server action: use current server / rebuild+restart / no server mutation
- Answer model calls: no
- Judge calls: no
- Full LongMemEval _s/_m: no
- /mcp/tools inspection: no unless separately approved
```

Recommended conservative launch sequence after approval:

1. Run a read-only preflight: git state, known untracked noise, CLI gate checks, server health, and DB DSN availability. No DB writes, retrieval/context calls, cleanup deletes, `/mcp/tools`, rebuild, or restart.
2. If current server is healthy, use current server first to avoid restart/rebuild confounds.
3. Run exactly one Phase A live retrieval pass with explicit DB-write, runtime-retrieval, and cleanup-delete flags.
4. Inspect emitted Phase A artifacts and cleanup verification.
5. Stop at the retrieval coverage gate. Do not make answer or judge calls without a separate approval rung.

## Suggested Handoff Prompt

```text
Continue Memibrium / LongMemEval retrieval bridge Phase A work.

Repo:
/home/zaddy/src/Memibrium

Current branch:
main

PR #4:
https://github.com/rvalen1123/memibrium/pull/4

PR #4 status:
MERGED

PR #4 merge commit:
9213b081d16fe2c12547faf71b871781f07286b3

State:
- Phase A live Memibrium adapters are merged on main.
- HTTP ingest posts planned memories to /mcp/retain.
- HTTP retrieval calls /mcp/context_packet with source attribution enabled and decision traces disabled.
- DB cleanup is constrained to the exact Phase A domain.
- Runtime metadata redacts endpoint secrets and never writes/prints DB DSNs.
- No live LongMemEval retrieval run is approved or performed unless a later artifact says so.
- No answer model calls, judge calls, full LongMemEval _s/_m, or /mcp/tools inspection.

Known untracked noise:
- docs/reference/
- docs/eval/results/locomo_context_packet_canary_*
Do not stage/commit these unless explicitly asked.

Next valid rung:
Plan or run one no-answer/no-judge live Phase A retrieval pass only after explicit approval for DB ingest writes, runtime retrieval/context calls, cleanup deletes, and server action.
```
