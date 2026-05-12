# LOCOMO hybrid-active telemetry baseline retry comparison — 2026-05-02

## Verdict

`telemetry_baseline_rejected_noncomparable`

The telemetry-augmented conv-26 retry completed all 199 questions with telemetry enabled and no Decimal serialization/runtime 500 failure. Phase C remains blocked pending review/failure-mode audit.

## Primary metrics

- 5-category overall: `58.29%`
- Protocol 4-category overall: `69.41%`
- Questions: `199`
- Query expansion fallback: `0/199`
- Avg query latency: `3272 ms`
- Mean n_memories: `14.6231`
- n_memories == 15: `162/199` (81.41%)

## Category scores

- `adversarial`: `22.34%` (47 questions, mean_n=14.6809)
- `multi-hop`: `42.31%` (13 questions, mean_n=14.5385)
- `single-hop`: `64.06%` (32 questions, mean_n=14.6875)
- `temporal`: `68.92%` (37 questions, mean_n=14.4054)
- `unanswerable`: `77.14%` (70 questions, mean_n=14.6857)

## Retrieval-shape comparability against f2466c9 14.82% baseline

- Locked baseline n distribution: `2:57, 3:110, 11:1, 12:3, 13:3, 14:3, 15:22`
- Retry n distribution: `11:3, 12:6, 13:17, 14:11, 15:162`
- Mean gate ±0.25 around 4.5327: `False` (14.6231)
- n=15 saturation gate ±5 around 22: `False` (162)
- Dominant bucket gate: `False`
- High-n bucket gate: `False`
- No hybrid fallback strings: `True`
- Overall comparable: `False`

## Serialization/runtime evidence

- `contains_decimal_not_json_serializable`: `False`
- `contains_type_error`: `False`
- `contains_hybrid_retrieval_failed`: `False`
- `contains_type_vector_missing`: `False`
- `contains_internal_server_error`: `False`

## Telemetry artifact inventory

- `/home/zaddy/src/Memibrium/docs/eval/results/locomo_conv26_hybrid_active_telemetry_baseline_retry_2026-05-02.json`
- `/home/zaddy/src/Memibrium/docs/eval/results/locomo_conv26_hybrid_active_telemetry_traces_retry_2026-05-02.json`
- `/home/zaddy/src/Memibrium/docs/eval/results/locomo_conv26_hybrid_active_telemetry_baseline_retry_2026-05-02.log`
- `/home/zaddy/src/Memibrium/docs/eval/results/locomo_hybrid_active_telemetry_summary_retry_2026-05-02.json`
- `/home/zaddy/src/Memibrium/docs/eval/results/locomo_hybrid_active_telemetry_baseline_retry_server_log_2026-05-02.log`
- `/home/zaddy/src/Memibrium/docs/eval/results/locomo_hybrid_active_telemetry_baseline_retry_199q_comparison_2026-05-02.md`

## Interpretation boundary

This artifact records the completed retry observation and comparability status. It does not implement or authorize Phase C. Use the telemetry artifacts in a separate failure-mode audit before selecting an intervention family.

## Cleanup and final state

- Cleanup executed after the LOCOMO launch.
- LOCOMO contamination count after cleanup: `0`
- Linked cleanup counts after cleanup: `temporal_expressions|0, memory_snapshots|0, user_feedback|0, contradictions|0, memory_edges|0`
- Health after cleanup: `{"status":"ok","engine":"memibrium"}`

## Structured result

- `/home/zaddy/src/Memibrium/docs/eval/results/locomo_hybrid_active_telemetry_baseline_retry_noncomparable_2026-05-02.json`

## Stop/go

`telemetry_baseline_rejected_noncomparable`

The Decimal serialization blocker is resolved, but the retry is rejected as a comparable telemetry baseline because retrieval shape drifted from the locked 14.82% structural regime (mean n_memories `4.5327`, n=15 `22/199`) to a high-context regime (mean n_memories `14.6231`, n=15 `162/199`). Do not use this run to choose Phase C.
