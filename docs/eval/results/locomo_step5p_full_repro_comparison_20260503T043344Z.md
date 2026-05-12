# LOCOMO Step 5p full-repro execution result

Run ID: `20260503T043344Z`
Date: 2026-05-03T04:44:11Z
Repo: `/home/zaddy/src/Memibrium`
Preregistration: `docs/eval/locomo_step5p_full_repro_preregistration_2026-05-03.md`

## Labels

- `full_repro_execution_complete_valid`
- `5j_v2_exec_bimodality_does_not_reproduce`
- `score_drifts_significantly`
- `no_go_phase_c_still_blocked`

## Scope

- Executed authorized Step 5p_exec full 199Q telemetry-off corrected-slice reproduction.
- No Phase C intervention was selected or implemented.
- No Docker rebuild/restart was performed.
- Retrieval shape remains the primary comparability axis; score is secondary.

## Results

- 5-cat overall: `54.77`
- Protocol 4-cat overall: `64.8`
- Fallback: `0` / `199`
- Mean n_memories: `14.6181`
- n_memories distribution: `{10: 1, 11: 3, 12: 8, 13: 9, 14: 17, 15: 161}`
- n=15: `161/199`
- adversarial mean n_memories: `14.6809`, n<=4 `0/47`
- non-adversarial mean n_memories: `14.5987`, n=15 `123/152`

## Comparison to Step 5j_v2_exec target

Step 5j_v2_exec target:

- 5-cat overall: `55.28%` ±2pp
- Protocol 4-cat overall: `70.07%` ±2pp
- Mean n_memories: `11.9296`
- n_memories distribution: `{4: 51, 12: 6, 13: 10, 14: 12, 15: 120}`
- n=15: `120/199`
- adversarial mean n_memories: `4.0`
- fallback: `0/199`

Step 5p_exec observed:

- 5-cat overall: `54.77%` — within the 5-cat score window.
- Protocol 4-cat overall: `64.8%` — outside the protocol 4-cat score window.
- Mean n_memories: `14.6181` — high-context, not the Step 5j_v2_exec third-regime shape.
- n_memories distribution: `{10: 1, 11: 3, 12: 8, 13: 9, 14: 17, 15: 161}`.
- n=15: `161/199`, close to the rejected Regime B telemetry retry shape (`162/199`) and far from Step 5j_v2_exec (`120/199`).
- adversarial mean n_memories: `14.6809`; adversarial low-context split did not reproduce (`n<=4` was `0/47`).
- fallback: `0/199`.

## Interpretation

Step 5j_v2_exec did not reproduce at the retrieval-shape gate and did not reproduce at the protocol 4-cat score gate, although the 5-cat score alone remained within tolerance. The observed retrieval shape is Regime-B-like high-context rather than the Step 5j_v2_exec bimodal third regime. No single-run baseline is canonical. Phase C remains blocked pending substrate nondeterminism audit.

## Cleanup

Cleanup hygiene: `{'memories': 0, 'temporal_expressions': 0, 'memory_snapshots': 0, 'user_feedback': 0, 'contradictions': 0, 'memory_edges': 0, 'ok': True}`

## Artifacts

- runner: `docs/eval/results/run_locomo_step5p_full_repro.py`
- prelaunch_snapshot: `/home/zaddy/src/Memibrium/docs/eval/results/locomo_step5p_full_repro_prelaunch_snapshot_20260503T043344Z.json`
- guard_summary: `/home/zaddy/src/Memibrium/docs/eval/results/locomo_step5p_full_repro_guard_summary_20260503T043344Z.json`
- raw_result: `/home/zaddy/src/Memibrium/docs/eval/results/locomo_step5p_full_repro_raw_20260503T043344Z.json`
- run_log: `/home/zaddy/src/Memibrium/docs/eval/results/locomo_step5p_full_repro_log_20260503T043344Z.log`
- validation: `/home/zaddy/src/Memibrium/docs/eval/results/locomo_step5p_full_repro_validation_20260503T043344Z.json`
- labels: `/home/zaddy/src/Memibrium/docs/eval/results/locomo_step5p_full_repro_labels_20260503T043344Z.json`
- postrun_snapshot: `/home/zaddy/src/Memibrium/docs/eval/results/locomo_step5p_full_repro_postrun_snapshot_20260503T043344Z.json`
- cleanup: `/home/zaddy/src/Memibrium/docs/eval/results/locomo_step5p_full_repro_cleanup_20260503T043344Z.json`
- comparison: `/home/zaddy/src/Memibrium/docs/eval/results/locomo_step5p_full_repro_comparison_20260503T043344Z.md`
- post_execution_verification: `/home/zaddy/src/Memibrium/docs/eval/results/locomo_step5p_full_repro_post_execution_verification_20260503T043344Z.json`
