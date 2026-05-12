# LongMemEval retrieval bridge Phase A smoke failure — 2026-05-12T22:36:27Z

## Scope

Explicitly approved small no-answer/no-judge Phase A live smoke rung using the current Memibrium server.

Approved side effects:

- DB ingest writes: yes
- Runtime retrieval/context calls: yes, but retrieval was not reached
- Cleanup deletes: yes
- Server action: use current server
- Smoke size: `--retrieval-bridge-smoke-max-questions 1`

Explicitly excluded:

- Answer model calls: no
- Judge calls: no
- Full LongMemEval `_s` / `_m`: no
- `/mcp/tools` inspection: no

## Preflight

Before launch, non-mutating checks showed:

```json
{
  "health_status": "ok",
  "health_engine": "memibrium",
  "phase_a_domain_count": 0,
  "dsn_printed": false
}
```

## Command shape

The smoke run used:

```bash
python3 docs/eval/results/run_longmemeval_oracle_canary.py \
  --run-retrieval-bridge-phase-a \
  --allow-db-writes \
  --allow-runtime-retrieval \
  --allow-cleanup-deletes \
  --memibrium-base-url http://localhost:9999 \
  --memibrium-db-dsn-source container \
  --memibrium-server-container memibrium-server \
  --memibrium-http-timeout 180 \
  --retrieval-bridge-smoke-max-questions 1 \
  --out-dir docs/eval/results/longmemeval_retrieval_bridge_phase_a_smoke_20260512T223627Z
```

The command did not include answer or judge flags.

## Result

The smoke run failed during `/mcp/retain` before retrieval/context calls.

Error class/messages:

```text
RuntimeError: memibrium_http_call_failed:/mcp/retain:timed out
MemibriumIngestError: memibrium_ingest_partial_failure
```

Progress artifact:

- `progress_checkpoint.json` was written.
- Stage: `cleanup_complete_after_failure`
- Selected question count: 1
- Selected question id: `031748ae_abs`
- Planned memory count: 24
- Created memory ids captured before timeout: 22
- Retrieval completed count: 0

Cleanup artifact from the smoke run:

- `cleanup_report.json` was written.
- Scoped cleanup deleted 22 created memories and 10 memory edges.
- Final domain count after scoped cleanup was 1, so cleanup status was `verification_failed`.

## Recovery cleanup

Because cleanup deletes were approved and the smoke run left one Phase A-domain memory, an immediate domain-wide recovery cleanup was run with the existing Phase A cleanup adapter and container-derived DB credentials. No DSN/password/secret values were printed.

Recovery result:

```json
{
  "cleanup_recovery": {
    "deleted_memory_count": 1,
    "final_domain_count_verified": 0,
    "linked_rows_deleted": {
      "user_feedback": 0,
      "memory_snapshots": 0,
      "memory_edges": 0,
      "contradictions": 0,
      "temporal_expressions": 0,
      "context_graph_edges": 0,
      "decision_traces": 0,
      "self_model_observations": 0
    }
  },
  "dsn_printed": false
}
```

Final independent domain verification:

```json
{
  "phase_a_domain_memory_count": 0,
  "dsn_printed": false
}
```

## Runner follow-up fix

The smoke run exposed a second cleanup-safety gap: when `/mcp/retain` times out after creating rows that are not returned in `created_ids`, scoped cleanup can delete the returned ids but still leave Phase A-domain residue.

Runner fix applied after the smoke attempt:

- If a failure occurred and scoped cleanup verifies a nonzero final domain count, the runner performs an automatic approved domain-wide recovery cleanup with `memory_ids=[]`.
- The cleanup report includes the recovery cleanup result.
- Tests cover this path.

## Verification after runner fix

- `python3 -m unittest test_longmemeval_oracle_canary -v` passed: 49 tests.
- `python3 -m unittest discover -v` passed: 198 tests.
- `git ls-files '*.py' | xargs python3 -m py_compile` passed.
- `git diff --check` passed.

## Interpretation

This is operational evidence only:

- The one-question smoke still timed out during retain.
- Retrieval/context calls were not reached.
- No answer model calls occurred.
- No judge calls occurred.
- No full LongMemEval `_s` / `_m` occurred.
- No `/mcp/tools` inspection occurred.

This is not retrieval-quality evidence and not benchmark/product evidence.

## Next valid gate

Do not run another full Phase A attempt, and do not proceed to answer/judge generation.

Recommended next work:

1. Diagnose `/mcp/retain` latency on the current server with a minimal single-memory retain probe in the exact Phase A domain, paired with cleanup deletes.
2. Inspect server logs/metrics with secret redaction only.
3. Consider restart/rebuild only after latency diagnosis identifies stale background workers, blocked queueing, or server runtime drift.
4. After retain latency is fixed, rerun the same one-question no-answer/no-judge smoke rung before any larger Phase A run.
