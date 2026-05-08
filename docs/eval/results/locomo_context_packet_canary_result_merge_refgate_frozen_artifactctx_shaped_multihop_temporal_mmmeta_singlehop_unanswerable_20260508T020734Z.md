# LOCOMO Context Packet Fixed-Row Canary Result

Run ID: `20260508T020734Z`

Scope: tiny fixed-row A/B canary only; not a 199Q LOCOMO benchmark.

## Gates
- Input row identity: `True`
- Paired row identity: `True`
- Condition metadata: `True`
- Context packet telemetry: `True`
- Score non-regression: `baseline=46.0`, `treatment=56.0`, `delta_pp=10.0`, `gate=True`
- Gold-evidence hit rates: `baseline=0.68`, `treatment=0.68`, `delta=0.0`, `gate=True`
- Packet append attribution: `{'rows_with_packet_append': 0, 'rows_without_packet_append': 25, 'score_delta_when_packet_appended': None, 'score_delta_when_no_packet_appended': 0.1, 'changed_when_packet_appended': 0, 'changed_when_no_packet_appended': 16}`
- Category regression gates: `{'cat-adversarial': {'baseline': 10.0, 'treatment': 10.0, 'delta': 0.0, 'severe_regression': False}, 'cat-multi-hop': {'baseline': 40.0, 'treatment': 80.0, 'delta': 40.0, 'severe_regression': False}, 'cat-single-hop': {'baseline': 40.0, 'treatment': 40.0, 'delta': 0.0, 'severe_regression': False}, 'cat-temporal': {'baseline': 70.0, 'treatment': 70.0, 'delta': 0.0, 'severe_regression': False}, 'cat-unanswerable': {'baseline': 70.0, 'treatment': 80.0, 'delta': 10.0, 'severe_regression': False}, 'no_severe_category_collapse': True, 'minimum_category_delta': 0.0, 'severe_drop_pp': 20.0}`
- Frozen baseline context hash match: `rate=1.0`, `by_row=[True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True]`
- Row 183 role-attribution diagnostic: `{'present': False, 'role_attribution_regression': False, 'role_attribution_regression_absent': True}`
- Prompt context changed by row: `[True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, False, False, False, False, False]`
- Final cleanup: `True`

## Artifacts
- baseline: `/home/zaddy/src/Memibrium/docs/eval/results/locomo_context_packet_canary_baseline_20260508T020734Z.json`
- treatment: `/home/zaddy/src/Memibrium/docs/eval/results/locomo_context_packet_canary_treatment_merge_refgate_frozen_artifactctx_shaped_multihop_temporal_mmmeta_singlehop_unanswerable_20260508T020734Z.json`
- summary: `/home/zaddy/src/Memibrium/docs/eval/results/locomo_context_packet_canary_summary_merge_refgate_frozen_artifactctx_shaped_multihop_temporal_mmmeta_singlehop_unanswerable_20260508T020734Z.json`
- markdown: `/home/zaddy/src/Memibrium/docs/eval/results/locomo_context_packet_canary_result_merge_refgate_frozen_artifactctx_shaped_multihop_temporal_mmmeta_singlehop_unanswerable_20260508T020734Z.md`
