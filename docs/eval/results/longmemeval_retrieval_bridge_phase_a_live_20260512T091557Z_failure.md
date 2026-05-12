# LongMemEval retrieval bridge Phase A live attempt timeout — 2026-05-12T09:15:57Z

## Scope

Approved no-answer/no-judge Phase A live retrieval rerun using the current Memibrium server.

Approved side effects:
- DB ingest writes: yes
- Runtime retrieval/context calls: yes
- Cleanup deletes: yes
- Server action: use current server; no rebuild/restart

Still explicitly excluded:
- Answer model calls
- Judge calls
- Full LongMemEval `_s` / `_m`
- `/mcp/tools` inspection

## Runner changes applied before launch

TDD-backed operational fixes were added before the rerun:
- `--run-retrieval-bridge-phase-a` now defaults from the first-slice selection file to the preregistered second-slice selection file when `--selection` is not explicitly supplied.
- Added `--memibrium-http-timeout` and wired it into both `/mcp/retain` and `/mcp/context_packet` live adapters.
- Added cleanup DSN derivation from `memibrium-server` container DB env without printing secrets or writing the DSN to artifacts/stdout.
- Container-derived DSN maps Docker-internal DB hostnames to `localhost` for host-side cleanup access.

## Verification before launch

Non-runtime verification passed:
- `python3 -m unittest test_longmemeval_oracle_canary -v` — 47 tests passed.
- `python3 -m unittest discover -v` — 196 tests passed.
- `git ls-files '*.py' | xargs python3 -m py_compile` — passed.
- `git diff --check` — passed.

Read-only current-server preflight passed:
- Health endpoint returned HTTP 200, `status=ok`, `engine=memibrium`.
- `memibrium-server` container was running.
- DB env keys were present in container env; values were not printed.
- Host-side DB connectivity via derived, redacted container env succeeded.
- Phase A domain count before launch: 0.

## Launch command shape

The rerun used:
- `--run-retrieval-bridge-phase-a`
- `--allow-db-writes`
- `--allow-runtime-retrieval`
- `--allow-cleanup-deletes`
- `--memibrium-base-url http://localhost:9999`
- `--memibrium-db-dsn-source container`
- `--memibrium-server-container memibrium-server`
- `--memibrium-http-timeout 180`

No explicit `--selection` was passed; the patched runtime path selected the second-slice file.

## Outcome

The parent command timed out at 600 seconds before writing normal Phase A artifacts.

Observed after timeout:
- Empty output directory existed: `docs/eval/results/longmemeval_retrieval_bridge_phase_a_live_20260512T091557Z/`
- No `ingest_manifest.json` was written.
- No `retrieval_results.jsonl` was written.
- No Phase A gate report was written.
- No answer or judge artifacts were written.
- No matching Phase A runner process remained after timeout.

DB state after timeout showed partial ingest residue:
- Phase A domain memories before recovery cleanup: 200
- Memory edges before recovery cleanup: 56
- Temporal expressions before recovery cleanup: 3

Recovery cleanup was performed with the approved cleanup-delete scope and exact Phase A domain.

Recovery cleanup result:
- Deleted memories: 200
- Deleted memory edges: 56
- Deleted temporal expressions: 3
- Deleted feedback/snapshots/contradictions/context-graph/decision/self-model rows: 0
- Final Phase A domain count verified: 0

## Interpretation

This is an operational timeout, not retrieval-quality evidence.

The run did not produce complete Phase A retrieval artifacts and must not be treated as a passed or failed retrieval bridge evaluation. It likely reached ingestion and may not have reached retrieval/context calls, but because the parent process timed out before writing artifacts, reached surfaces beyond DB residue are not asserted here.

## Next valid rung

Do not rerun the 446-memory live path blindly.

Recommended next step:
1. Add progress-safe artifacting/checkpointing around live Phase A ingest/retrieval so timeout/failure preserves partial status without exposing secrets.
2. Add or use a smaller smoke rung for Phase A live plumbing, still no-answer/no-judge, before another full 25-question / 446-memory attempt.
3. Diagnose retain latency/background work on current server before another large ingest.
4. Keep cleanup DSN source as container-derived or otherwise server-effective, never repo `.env`-derived unless verified.

Any future live rerun still needs explicit approval for DB writes, runtime retrieval/context calls, cleanup deletes, and server action.
