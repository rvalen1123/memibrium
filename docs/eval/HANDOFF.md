# Memibrium Evaluation Handoff — 2026-05-12

## Current Active Work

LongMemEval retrieval bridge Phase A live-adapter PR is open and ready from the code/CI side.

- PR: https://github.com/rvalen1123/memibrium/pull/4
- Branch: `feat/longmemeval-phase-a-live-adapters`
- Base: `main`
- Latest branch HEAD checked locally: `068a6d6 fix: avoid dynamic cleanup SQL composition`
- Prior PR commits on this branch:
  - `db25fc8 feat: wire LongMemEval Phase A live adapters`
  - `53deaa1 fix: address Phase A adapter review comments`
  - `068a6d6 fix: avoid dynamic cleanup SQL composition`

## What PR #4 Does

This PR wires real Memibrium adapters into the existing LongMemEval retrieval bridge Phase A runner seam, while keeping the runner fail-closed.

Code changed:

- `docs/eval/results/run_longmemeval_oracle_canary.py`
- `test_longmemeval_oracle_canary.py`

Implemented surfaces:

- HTTP ingest adapter posting planned memories to `/mcp/retain`.
- HTTP retrieval adapter calling `/mcp/context_packet` with source attribution enabled and decision traces disabled.
- DB cleanup adapter for the exact Phase A domain.
- CLI wiring for `--run-retrieval-bridge-phase-a` behind explicit side-effect flags.
- Redacted runtime metadata for Memibrium base URL; DB DSN is not printed or written to artifacts.

Safety gates preserved:

- No answer model calls.
- No judge calls.
- No full LongMemEval `_s` / `_m` run.
- No `/mcp/tools` inspection.
- Runtime Phase A path requires explicit approval flags for DB writes, runtime retrieval/context calls, and cleanup deletes.
- Runtime Phase A path requires `--memibrium-db-dsn` or `MEMIBRIUM_DB_DSN` so cleanup verification is available.

## Code Review Fixes Already Addressed

Review comments from Sourcery/CodeRabbit were verified against current code and fixed only where still valid.

Fixed:

- `memibrium_http_post` now rejects non-`http`/`https` base URLs before `urlopen`.
- Non-JSON 200 responses now raise a dedicated `RuntimeError("memibrium_http_invalid_json:...")` path.
- `_parse_longmemeval_session_date` now returns `None` for unparseable LongMemEval timestamps instead of raw non-ISO text.
- `_parse_longmemeval_session_date` has a docstring documenting ISO8601-or-None behavior and the UTC assumption for naive parsed datetimes.
- `make_memibrium_ingest_fn` raises `MemibriumIngestError` on partial ingest failure, carrying already-created memory IDs and the original exception.
- `run_retrieval_bridge_phase_a` wraps ingest/retrieval in `try/finally` and always calls cleanup with created IDs, or an empty list when none are known.
- `make_memibrium_cleanup_fn` initializes `conn = None` before connecting and closes only if a connection exists, preserving connection failures.
- `connect_fn` typing is narrowed to an awaitable callable.
- The sync cleanup wrapper no longer blindly calls `asyncio.run` inside an already-running event loop; it exposes `cleanup.async_cleanup` and raises a clear `memibrium_cleanup_requires_async_cleanup_in_running_loop` error in that case.
- Cleanup DELETEs use `memory_ids` to reduce blast radius when IDs are available.
- Empty `memory_ids` remains an intentional domain-wide cleanup fallback for failure recovery.
- Cleanup destructive DELETEs plus final count verification run inside `async with conn.transaction()`.
- Cleanup SQL uses static scoped-vs-domain-wide SQL branches, not f-string filter composition, satisfying the Sourcery security finding.

Added/expanded tests:

- non-HTTP base URL rejection before `urlopen`
- non-JSON HTTP response wrapping
- partial ingest exception carrying created IDs
- partial ingest failure triggers cleanup
- unparseable LongMemEval timestamp returns `None`
- cleanup connection failure is not masked
- running-event-loop cleanup wrapper behavior
- cleanup memory-ID scoping
- cleanup transactional rollback semantics
- missing DB DSN parse failure for runtime Phase A
- empty/None redacted runtime metadata behavior

## Verification

Local verification after review fixes:

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

Remote PR checks after latest push:

- unit-tests 3.11: pass
- unit-tests 3.12: pass
- unit-tests 3.13: pass
- CodeQL: pass
- Snyk: pass
- Socket Security: pass
- Sourcery: pass
- Semgrep: pass
- CodeRabbit: pass / review skipped after latest push

## Current Repo State Notes

Current branch is expected to be:

```bash
feat/longmemeval-phase-a-live-adapters
```

Expected latest commit:

```bash
068a6d6 fix: avoid dynamic cleanup SQL composition
```

Expected command to verify:

```bash
git status --short --branch
git log --oneline -5 --decorate
gh pr checks 4
```

Known pre-existing untracked noise remains intentionally untouched:

- `docs/reference/`
- `docs/eval/results/locomo_context_packet_canary_*`

Do not stage or commit those unless explicitly asked.

## What This Is Not

This PR is readiness plumbing only.

It does not claim:

- LongMemEval retrieval performance
- product benchmark performance
- answer-side score improvement
- judge-verified benchmark progress

No live side-effectful LongMemEval retrieval run was performed during this PR unless explicitly authorized later.

## Next Valid Step

If the user wants to continue, the next rung is one of:

1. Merge PR #4 after final review comfort.
2. If PR #4 is merged, plan an explicitly approved no-answer/no-judge live Phase A retrieval run.
3. If running Phase A live, require explicit approval for all of:
   - DB ingest writes
   - runtime retrieval/context calls
   - cleanup deletes
   - whether to rebuild/restart Memibrium or use the currently running server

Do not infer runtime approval from PR merge or from the word “proceed” alone.

## Copy-Paste Live Phase A Approval Checklist

Before any live Phase A retrieval run, get explicit confirmation for:

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

## Suggested Handoff Prompt

```text
Continue Memibrium PR #4 / LongMemEval retrieval bridge Phase A work.
Repo: /home/zaddy/src/Memibrium
Branch: feat/longmemeval-phase-a-live-adapters
PR: https://github.com/rvalen1123/memibrium/pull/4
Latest expected commit: 068a6d6 fix: avoid dynamic cleanup SQL composition

Current state:
- PR #4 wires live Memibrium HTTP ingest/retrieval/cleanup adapters into the existing Phase A runner seam.
- It keeps Phase A fail-closed: no answer calls, no judge calls, no full LongMemEval run, no /mcp/tools inspection.
- Runtime path requires explicit DB write, runtime retrieval, cleanup delete gates and a DB DSN for cleanup verification.
- Review comments were addressed: URL scheme validation, non-JSON HTTP wrapping, date parse failure -> None, partial ingest cleanup, cleanup async wrapper safety, connection failure safety, memory_id scoping, transactional cleanup, and static SQL branches.
- Local verification passed: test_longmemeval_oracle_canary 46 tests, unittest discover 195 tests, py_compile all tracked Python, git diff --check.
- Remote checks after latest push passed: CI 3.11/3.12/3.13, CodeQL, Snyk, Socket, Sourcery, Semgrep, CodeRabbit skipped/pass.
- Known untracked noise remains untouched: docs/reference/ and docs/eval/results/locomo_context_packet_canary_*.

Next action:
- Verify `git status --short --branch`, `git log --oneline -5 --decorate`, and `gh pr checks 4`.
- If everything is still green, decide whether to merge PR #4 or wait for review.
- Do not run live Phase A retrieval unless explicitly approved for DB writes, runtime retrieval/context calls, and cleanup deletes.
- Do not make answer/judge/model calls or full LongMemEval _s/_m runs.
```
