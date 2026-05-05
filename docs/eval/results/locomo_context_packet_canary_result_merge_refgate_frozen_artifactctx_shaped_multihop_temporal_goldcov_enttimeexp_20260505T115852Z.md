# LOCOMO Context Packet Fixed-Row Canary Result

Run ID: `20260505T115852Z`

Scope: tiny fixed-row A/B canary only; not a 199Q LOCOMO benchmark.

## Gates
- Input row identity: `True`
- Paired row identity: `True`
- Condition metadata: `True`
- Context packet telemetry: `True`
- Score non-regression: `baseline=54.0`, `treatment=64.0`, `delta_pp=10.0`, `gate=True`
- Gold-evidence hit rates: `baseline=0.7826`, `treatment=0.7826`, `delta=0.0`, `gate=True`
- Packet append attribution: `{'rows_with_packet_append': 0, 'rows_without_packet_append': 25, 'score_delta_when_packet_appended': None, 'score_delta_when_no_packet_appended': 0.1, 'changed_when_packet_appended': 0, 'changed_when_no_packet_appended': 13}`
- Category regression gates: `{'cat-adversarial': {'baseline': 40.0, 'treatment': 20.0, 'delta': -20.0, 'severe_regression': False}, 'cat-multi-hop': {'baseline': 30.0, 'treatment': 100.0, 'delta': 70.0, 'severe_regression': False}, 'cat-single-hop': {'baseline': 70.0, 'treatment': 70.0, 'delta': 0.0, 'severe_regression': False}, 'cat-temporal': {'baseline': 60.0, 'treatment': 60.0, 'delta': 0.0, 'severe_regression': False}, 'cat-unanswerable': {'baseline': 70.0, 'treatment': 70.0, 'delta': 0.0, 'severe_regression': False}, 'no_severe_category_collapse': True, 'minimum_category_delta': -20.0, 'severe_drop_pp': 20.0}`
- Frozen baseline context hash match: `rate=1.0`, `by_row=[True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True]`
- Row 183 role-attribution diagnostic: `{'present': True, 'one_based_index': 183, 'role_attribution_regression': False, 'role_attribution_regression_absent': True, 'baseline_mentions_melanie': False, 'treatment_mentions_caroline': False, 'treatment_mentions_melanie': False, 'baseline_predicted': "I don't know.", 'treatment_predicted': "I don't know.", 'baseline_gold_hits': 0, 'treatment_gold_hits': 0, 'packet_appended': False, 'score_delta': 0.0}`
- Prompt context changed by row: `[True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, False, True, False, False, True, False, True, False, False, False]`
- Final cleanup: `True`

## Artifacts
- baseline: `/home/zaddy/src/Memibrium/docs/eval/results/locomo_context_packet_canary_baseline_20260505T115852Z.json`
- treatment: `/home/zaddy/src/Memibrium/docs/eval/results/locomo_context_packet_canary_treatment_merge_refgate_frozen_artifactctx_shaped_multihop_temporal_goldcov_enttimeexp_20260505T115852Z.json`
- summary: `/home/zaddy/src/Memibrium/docs/eval/results/locomo_context_packet_canary_summary_merge_refgate_frozen_artifactctx_shaped_multihop_temporal_goldcov_enttimeexp_20260505T115852Z.json`
- markdown: `/home/zaddy/src/Memibrium/docs/eval/results/locomo_context_packet_canary_result_merge_refgate_frozen_artifactctx_shaped_multihop_temporal_goldcov_enttimeexp_20260505T115852Z.md`
