# LOCOMO Context Packet Fixed-Row Canary Result

Run ID: `20260508T023558Z`

Scope: tiny fixed-row A/B canary only; not a 199Q LOCOMO benchmark.

## Gates
- Input row identity: `True`
- Paired row identity: `True`
- Condition metadata: `True`
- Context packet telemetry: `True`
- Score non-regression: `baseline=23.08`, `treatment=38.46`, `delta_pp=15.38`, `gate=True`
- Gold-evidence hit rates: `baseline=0.6154`, `treatment=0.6154`, `delta=0.0`, `gate=True`
- Packet append attribution: `{'rows_with_packet_append': 0, 'rows_without_packet_append': 13, 'score_delta_when_packet_appended': None, 'score_delta_when_no_packet_appended': 0.1538, 'changed_when_packet_appended': 0, 'changed_when_no_packet_appended': 6}`
- Category regression gates: `{'cat-adversarial': {'baseline': 0.0, 'treatment': 0.0, 'delta': 0.0, 'severe_regression': False}, 'cat-multi-hop': {'baseline': 0.0, 'treatment': 33.33, 'delta': 33.33, 'severe_regression': False}, 'cat-single-hop': {'baseline': 66.67, 'treatment': 66.67, 'delta': 0.0, 'severe_regression': False}, 'cat-temporal': {'baseline': 50.0, 'treatment': 50.0, 'delta': 0.0, 'severe_regression': False}, 'cat-unanswerable': {'baseline': 0.0, 'treatment': 33.33, 'delta': 33.33, 'severe_regression': False}, 'no_severe_category_collapse': True, 'minimum_category_delta': 0.0, 'severe_drop_pp': 20.0}`
- Frozen baseline context hash match: `rate=1.0`, `by_row=[True, True, True, True, True, True, True, True, True, True, True, True, True]`
- Row 183 role-attribution diagnostic: `{'present': False, 'role_attribution_regression': False, 'role_attribution_regression_absent': True}`
- Prompt context changed by row: `[True, True, True, True, True, True, True, True, True, True, True, False, False]`
- Final cleanup: `True`

## Artifacts
- baseline: `/home/zaddy/src/Memibrium/docs/eval/results/locomo_context_packet_canary_baseline_20260508T023558Z.json`
- treatment: `/home/zaddy/src/Memibrium/docs/eval/results/locomo_context_packet_canary_treatment_merge_refgate_frozen_artifactctx_shaped_multihop_temporal_mmmeta_singlehop_unanswerable_20260508T023558Z.json`
- summary: `/home/zaddy/src/Memibrium/docs/eval/results/locomo_context_packet_canary_summary_merge_refgate_frozen_artifactctx_shaped_multihop_temporal_mmmeta_singlehop_unanswerable_20260508T023558Z.json`
- markdown: `/home/zaddy/src/Memibrium/docs/eval/results/locomo_context_packet_canary_result_merge_refgate_frozen_artifactctx_shaped_multihop_temporal_mmmeta_singlehop_unanswerable_20260508T023558Z.md`
