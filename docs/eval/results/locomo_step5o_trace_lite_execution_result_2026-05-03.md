# LOCOMO Step 5o bounded checkpoint / trace-lite execution result

Run ID: `20260503T005114Z`
Date: 2026-05-03 UTC
Repo: `/home/zaddy/src/Memibrium`
Preregistration: `docs/eval/locomo_step5o_bounded_checkpoint_trace_lite_preregistration_2026-05-02.md`

## Labels

Primary: `checkpoint_shows_no_static_boundary_effect`

Secondary:
- `no_go_phase_c_still_blocked`
- `supports_post_cb56559_high_context_path`
- `supports_effective_harness_mismatch`
- `requires_full_repro_prereg`

## Scope

- Executed authorized bounded Step 5o checkpoint / trace-lite only.
- No full 199Q benchmark was launched.
- No Phase C intervention was selected or implemented.
- Temporary uvicorn servers were used for checkpoint source execution; no Docker rebuild/restart was performed.
- Scores were not produced; retrieval-count path was primary.

## Guardrails

### A_f2466c9

- Checkpoint: `f2466c9`
- Status: `completed`
- Source hashes matched expected: `true`
- Input: `/tmp/locomo/data/locomo10.json` SHA256 `79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4`
- Slice: index 0 `conv-26`, speakers Caroline / Melanie, QA count 199
- Fixed-row identity proofs: `True`
- LOCOMO hygiene before: `{'memories': 0, 'temporal_expressions': 0, 'memory_snapshots': 0, 'user_feedback': 0, 'contradictions': 0, 'memory_edges': 0, 'ok': True}`
- LOCOMO hygiene after cleanup: `{'memories': 0, 'temporal_expressions': 0, 'memory_snapshots': 0, 'user_feedback': 0, 'contradictions': 0, 'memory_edges': 0, 'ok': True}`
- Server log: `docs/eval/results/locomo_step5o_A_f2466c9_server_20260503T005114Z.log`

### B_current

- Checkpoint: `8a0e421`
- Status: `completed`
- Source hashes matched expected: `true`
- Input: `/tmp/locomo/data/locomo10.json` SHA256 `79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4`
- Slice: index 0 `conv-26`, speakers Caroline / Melanie, QA count 199
- Fixed-row identity proofs: `True`
- LOCOMO hygiene before: `{'memories': 0, 'temporal_expressions': 0, 'memory_snapshots': 0, 'user_feedback': 0, 'contradictions': 0, 'memory_edges': 0, 'ok': True}`
- LOCOMO hygiene after cleanup: `{'memories': 0, 'temporal_expressions': 0, 'memory_snapshots': 0, 'user_feedback': 0, 'contradictions': 0, 'memory_edges': 0, 'ok': True}`
- Server log: `docs/eval/results/locomo_step5o_B_current_server_20260503T005114Z.log`

## Retrieval-count summary

### A_f2466c9

| Row label | expanded queries | per-query result counts | candidates before dedupe | candidates after dedupe | final context |
|---|---:|---|---:|---:|---:|
| `adversarial_split_early` | 4 | `[10, 10, 10, 10]` | 40 | 19 | 15 |
| `adversarial_split_late` | 4 | `[10, 10, 10, 10]` | 40 | 17 | 15 |
| `unanswerable_high_context` | 4 | `[3, 6, 7, 10]` | 26 | 19 | 15 |
| `unanswerable_c_low_exception` | 4 | `[10, 10, 10, 10]` | 40 | 22 | 15 |
| `temporal_high_context` | 4 | `[10, 10, 10, 10]` | 40 | 14 | 14 |
| `single_hop_high_context` | 4 | `[10, 10, 10, 10]` | 40 | 16 | 15 |
| `multi_hop_high_context` | 4 | `[10, 10, 10, 10]` | 40 | 26 | 15 |

### B_current

| Row label | expanded queries | per-query result counts | candidates before dedupe | candidates after dedupe | final context |
|---|---:|---|---:|---:|---:|
| `adversarial_split_early` | 4 | `[10, 10, 10, 10]` | 40 | 15 | 15 |
| `adversarial_split_late` | 4 | `[10, 10, 10, 10]` | 40 | 19 | 15 |
| `unanswerable_high_context` | 4 | `[10, 10, 10, 10]` | 40 | 22 | 15 |
| `unanswerable_c_low_exception` | 4 | `[10, 10, 10, 10]` | 40 | 17 | 15 |
| `temporal_high_context` | 4 | `[10, 10, 10, 10]` | 40 | 14 | 14 |
| `single_hop_high_context` | 4 | `[10, 10, 10, 10]` | 40 | 20 | 15 |
| `multi_hop_high_context` | 4 | `[10, 10, 10, 10]` | 40 | 23 | 15 |

## Interpretation

Arm A did not reproduce the preregistered f2466c9 low-context fixed-row family. Under the checkpoint source/runtime path exercised here, all seven fixed rows reached high or near-high context: six rows at final context 15 and one temporal row at 14.

Arm B/current reproduced the high-context trace mechanics on the same fixed rows: four expanded queries per row, mostly 40 pre-dedupe candidates, and final answer context 14-15. The expected current adversarial low-context split was not reproduced in this bounded run; adversarial fixed rows also reached 15.

This supports treating the historical 14.82% f2466c9 low-context artifact as noncanonical / effective-runtime-artifact pending any later preregistered full reproduction. Because Arm A and Arm B did not differ materially in retrieval-count shape, the primary Step 5o label is `checkpoint_shows_no_static_boundary_effect`, with `supports_post_cb56559_high_context_path` retained as secondary. Phase C remains blocked.

## Artifacts

- Summary JSON: `docs/eval/results/locomo_step5o_trace_lite_summary_20260503T005114Z.json`
- Arm A JSON: `docs/eval/results/locomo_step5o_A_f2466c9_trace_lite_20260503T005114Z.json`
- Arm B JSON: `docs/eval/results/locomo_step5o_B_current_trace_lite_20260503T005114Z.json`
- Arm A server log: `docs/eval/results/locomo_step5o_A_f2466c9_server_20260503T005114Z.log`
- Arm B server log: `docs/eval/results/locomo_step5o_B_current_server_20260503T005114Z.log`
- Harness: `docs/eval/results/run_locomo_step5o_trace_lite.py`

