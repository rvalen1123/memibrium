# LOCOMO telemetry-augmented hybrid-active baseline — blocked result, 2026-05-01

## Verdict

`telemetry_baseline_blocked_runtime_serialization_error`

Stop/go output: `no_go_insufficient_evidence_expand_telemetry`

This is not a valid comparable telemetry baseline. Do not use it to select or implement Phase C.

## Scope

Authorized Step 5 attempted the preregistered telemetry-augmented conv-26 LOCOMO observation only. No Phase C intervention was implemented. No retrieval parameter, prompt, judge, schema, env, rebuild, or container mutation was performed during this attempt.

## Prelaunch gates

Prelaunch gates passed and were preserved in:

- `/home/zaddy/src/Memibrium/docs/eval/results/locomo_hybrid_active_telemetry_baseline_prelaunch_2026-05-01.json`

Key prelaunch evidence from that artifact:

- Branch/head: `query-expansion` / `328da535f39c254d79f1fc17e3afd4402277203b`
- Git status: `''`
- Health: `{'json': {'engine': 'memibrium', 'status': 'ok'}, 'status': 200}`
- LOCOMO contamination before launch: `0`
- Embedding type: `USER-DEFINED:ruvector`
- RuVector type count / vector type count: `1` / `0`
- Instrumentation result present and go: `True` / `True`

## Launch outcome

The launch began with the locked condition:

- Dataset: `/tmp/locomo/data/locomo10.json`
- Conversation: first conversation only, `--max-convs 1` (`conv-26`)
- Query expansion: enabled
- Telemetry request path: enabled with `INCLUDE_RECALL_TELEMETRY=1`
- Answer/judge/chat model: `gpt-4.1-mini`
- Server embedding deployment: `text-embedding-3-small`

The benchmark aborted before completion. Last progress marker:

- `120` / `199` questions, running accuracy `72.1%`

Run-log failure:

```text
RuntimeError: MCP recall failed after 3 attempts: non-200 response; status=500; response=Internal Server Error
```

Server-side failure:

```text
TypeError: Object of type Decimal is not JSON serializable
```

The server traceback points to the opt-in telemetry response serialization path:

```text
/app/server.py", line 1957, in handle_recall
    return JSONResponse(_serialize_result({"results": result, "telemetry": response_telemetry}))
```

## Artifacts preserved

- Prelaunch: `/home/zaddy/src/Memibrium/docs/eval/results/locomo_hybrid_active_telemetry_baseline_prelaunch_2026-05-01.json`
- Main placeholder result: `/home/zaddy/src/Memibrium/docs/eval/results/locomo_conv26_hybrid_active_telemetry_baseline_2026-05-01.json`
- Trace placeholder result: `/home/zaddy/src/Memibrium/docs/eval/results/locomo_conv26_hybrid_active_telemetry_traces_2026-05-01.json`
- Failed run log: `/home/zaddy/src/Memibrium/docs/eval/results/locomo_conv26_hybrid_active_telemetry_baseline_2026-05-01.log`
- Server log excerpt/full tail: `/home/zaddy/src/Memibrium/docs/eval/results/locomo_hybrid_active_telemetry_baseline_failed_server_log_2026-05-01.log`
- Blocked structured evidence: `/home/zaddy/src/Memibrium/docs/eval/results/locomo_hybrid_active_telemetry_baseline_blocked_2026-05-01.json`

No complete 199-question result JSON exists. `/tmp/locomo_results_query_expansion_raw.json` was absent at preservation time.

## Cleanup requirement

Because the LOCOMO launch ingested rows before aborting, cleanup is mandatory. Pre-cleanup linked row counts were captured in the blocked JSON. Cleanup must remove `locomo-%` memories and linked rows, then verify:

```sql
SELECT count(id) FROM memories WHERE domain LIKE 'locomo-%';
```

returns `0`.

## Methodological interpretation

This blocked run provides evidence of an instrumentation serialization defect in the telemetry response path. It does not provide a comparable telemetry baseline, does not adjudicate candidate fetch starvation versus fusion/cutoff versus output-cap/context-transfer, and does not update the Phase C intervention prior.

Next valid step after cleanup and commit is a separately preregistered instrumentation-correction mutation window for Decimal-safe telemetry serialization, followed by a new authorized observation attempt only if behavior-preservation gates pass.

## Cleanup completed

Cleanup was executed after preserving failure evidence.

- Cleanup script: `scripts/clear_locomo_domains.sh`
- Cleanup log: `/home/zaddy/src/Memibrium/docs/eval/results/locomo_hybrid_active_telemetry_baseline_cleanup_2026-05-01.log`
- Post-cleanup LOCOMO `count(id)`: `0`
- Linked-row post-cleanup counts:

```text
temporal_expressions|0
memory_snapshots|0
user_feedback|0
contradictions|0
memory_edges|0
```

- Health after cleanup: `{"status":"ok","engine":"memibrium"}`
