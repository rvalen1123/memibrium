# LOCOMO Context Packet Fixed-Row Canary Result

Run ID: `20260504T071410Z`

Scope: tiny fixed-row A/B canary only; not a 199Q LOCOMO benchmark.

## Gates
- Input row identity: `True`
- Paired row identity: `True`
- Condition metadata: `True`
- Context packet telemetry: `True`
- Gold-evidence hit rates: `baseline=0.6522`, `treatment=0.7826`, `delta=0.1304`
- Packet append attribution: `{'rows_with_packet_append': 9, 'rows_without_packet_append': 16, 'score_delta_when_packet_appended': 0.0556, 'score_delta_when_no_packet_appended': -0.0938, 'changed_when_packet_appended': 7, 'changed_when_no_packet_appended': 12}`
- Category regression gates: `{'cat-adversarial': {'baseline': 30.0, 'treatment': 20.0, 'delta': -10.0, 'severe_regression': False}, 'cat-multi-hop': {'baseline': 50.0, 'treatment': 50.0, 'delta': 0.0, 'severe_regression': False}, 'cat-single-hop': {'baseline': 60.0, 'treatment': 70.0, 'delta': 10.0, 'severe_regression': False}, 'cat-temporal': {'baseline': 80.0, 'treatment': 80.0, 'delta': 0.0, 'severe_regression': False}, 'cat-unanswerable': {'baseline': 80.0, 'treatment': 60.0, 'delta': -20.0, 'severe_regression': False}, 'no_severe_category_collapse': True, 'minimum_category_delta': -20.0, 'severe_drop_pp': 20.0}`
- Prompt context changed by row: `[True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True]`
- Final cleanup: `True`

## Artifacts
- baseline: `/home/zaddy/src/Memibrium/docs/eval/results/locomo_context_packet_canary_baseline_20260504T071410Z.json`
- treatment: `/home/zaddy/src/Memibrium/docs/eval/results/locomo_context_packet_canary_treatment_merge_refgate_20260504T071410Z.json`
- summary: `/home/zaddy/src/Memibrium/docs/eval/results/locomo_context_packet_canary_summary_merge_refgate_20260504T071410Z.json`
- markdown: `/home/zaddy/src/Memibrium/docs/eval/results/locomo_context_packet_canary_result_merge_refgate_20260504T071410Z.md`
