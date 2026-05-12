# LOCOMO Context Packet Fixed-Row Canary Result

Run ID: `20260504T154709Z`

Scope: tiny fixed-row A/B canary only; not a 199Q LOCOMO benchmark.

## Gates
- Input row identity: `True`
- Paired row identity: `True`
- Condition metadata: `True`
- Context packet telemetry: `True`
- Score non-regression: `baseline=60.0`, `treatment=74.0`, `delta_pp=14.0`, `gate=True`
- Gold-evidence hit rates: `baseline=0.6957`, `treatment=0.8261`, `delta=0.1304`, `gate=True`
- Packet append attribution: `{'rows_with_packet_append': 3, 'rows_without_packet_append': 22, 'score_delta_when_packet_appended': 0.3333, 'score_delta_when_no_packet_appended': 0.1136, 'changed_when_packet_appended': 2, 'changed_when_no_packet_appended': 8}`
- Category regression gates: `{'cat-adversarial': {'baseline': 50.0, 'treatment': 50.0, 'delta': 0.0, 'severe_regression': False}, 'cat-multi-hop': {'baseline': 30.0, 'treatment': 90.0, 'delta': 60.0, 'severe_regression': False}, 'cat-single-hop': {'baseline': 60.0, 'treatment': 60.0, 'delta': 0.0, 'severe_regression': False}, 'cat-temporal': {'baseline': 90.0, 'treatment': 100.0, 'delta': 10.0, 'severe_regression': False}, 'cat-unanswerable': {'baseline': 70.0, 'treatment': 70.0, 'delta': 0.0, 'severe_regression': False}, 'no_severe_category_collapse': True, 'minimum_category_delta': 0.0, 'severe_drop_pp': 20.0}`
- Frozen baseline context hash match: `rate=1.0`, `by_row=[True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True]`
- Row 183 role-attribution diagnostic: `{'present': True, 'one_based_index': 183, 'role_attribution_regression': True, 'role_attribution_regression_absent': False, 'baseline_mentions_melanie': True, 'treatment_mentions_caroline': True, 'treatment_mentions_melanie': True, 'baseline_predicted': 'Melanie did not mention finding anything in her neighborhood during her walk; it was Caroline who found a vibrant rainbow sidewalk for Pride Month during her walk.', 'treatment_predicted': 'Melanie did not mention finding anything in her neighborhood during a walk; it was Caroline who found a vibrant rainbow sidewalk for Pride Month during her walk.', 'baseline_gold_hits': 1, 'treatment_gold_hits': 1, 'packet_appended': False, 'score_delta': -1.0}`
- Prompt context changed by row: `[True, False, False, True, True, False, False, True, True, False, False, True, False, True, False, False, False, False, False, False, False, False, False, False, True]`
- Final cleanup: `True`

## Artifacts
- baseline: `/home/zaddy/src/Memibrium/docs/eval/results/locomo_context_packet_canary_baseline_20260504T154709Z.json`
- treatment: `/home/zaddy/src/Memibrium/docs/eval/results/locomo_context_packet_canary_treatment_merge_refgate_frozen_shaped_multihop_20260504T154709Z.json`
- summary: `/home/zaddy/src/Memibrium/docs/eval/results/locomo_context_packet_canary_summary_merge_refgate_frozen_shaped_multihop_20260504T154709Z.json`
- markdown: `/home/zaddy/src/Memibrium/docs/eval/results/locomo_context_packet_canary_result_merge_refgate_frozen_shaped_multihop_20260504T154709Z.md`
