# LOCOMO answer-side ablation and off-slice diagnostic — 2026-05-08

Scope: diagnostic/canary evidence only. These runs are default-off/eval-only frozen answer-prompt diagnostics on 25-row slices. They are not a full 199Q benchmark, not cumulative, and not quote-worthy performance claims.

## Preconditions and guardrails

- Branch: `query-expansion`.
- Latest pre-run pushed commit: `3e564d1 eval: record LOCOMO answer-side canary`.
- Full 199Q and cumulative LOCOMO remain blocked without separate explicit approval.
- DB/Docker/runtime mutation remained blocked; the canary runner performed its normal cleanup probe and final hygiene was clean.
- `docs/reference/` was intentionally untouched.
- Secrets/env credentials in emitted summaries were redacted by the runner.

## Same-slice lever ablation

Fixed rows: `docs/eval/results/locomo_context_packet_merge_prereg_25rows_2026-05-03.json`.

Baseline substrate: artifact-pinned full-context replay from `docs/eval/results/locomo_context_packet_canary_treatment_merge_refgate_frozen_shaped_multihop_temporal_goldcov_20260506T103203Z.json`.

All rows preserved baseline prefix and matched frozen context hashes (`25/25`). Gold-evidence hit rate stayed flat at `0.8696 -> 0.8696` in every ablation, so this block isolates answer-prompt sensitivity, not retrieval improvement.

| Run | Condition | Score | Delta | Main category movement | Improved rows | Regressed rows |
| --- | --- | ---: | ---: | --- | --- | --- |
| `20260508T015408Z` | shape-only | `54.0 -> 68.0` | `+14.0 pp` | multi-hop +70 | 31, 51, 70, 78 | none |
| `20260508T015541Z` | mmmeta-only | `54.0 -> 58.0` | `+4.0 pp` | unanswerable +20 | 113 | none |
| `20260508T015715Z` | subject-guard-only | `54.0 -> 58.0` | `+4.0 pp` | adversarial +20 | 172 | none |
| `20260508T015232Z` | shape+mmmeta | `54.0 -> 72.0` | `+18.0 pp` | multi-hop +70, unanswerable +20 | 31, 51, 70, 78, 113 | none |


Interpretation:

- Answer-shape directive is the dominant same-slice lever: shape-only moved `54.0 -> 68.0` and recovered rows 31, 51, 70, and 78, all multi-hop.
- Multimodal metadata projection is real but narrow: mmmeta-only moved `54.0 -> 58.0` by recovering row 113, the image/object failure.
- Subject guard is weak/narrow: subject-guard-only moved `54.0 -> 58.0` by partially recovering row 172, but row 185 remained a persistent failure in the earlier stacked run despite the target being surfaced.
- Shape+mmmeta without subject guard matched the prior stacked score (`54.0 -> 72.0`), showing the subject guard is not needed for the same-slice aggregate. The stacked run’s attribution was therefore confounded; this ablation separates most observed movement into shape and mmmeta.

## Off-slice preregistration

Created a new fixed 25-row off-slice file before looking at off-slice scores:

- `docs/eval/results/locomo_answer_side_offslice_prereg_25rows_2026-05-08.json`

Selection rule: deterministic hash-stratified read-only selection from `conv-26`, excluding the original 2026-05-03 fixed rows, using `sha256(conv-26:index:question)` and taking the first five rows per normalized category. No score-aware tuning.

Selected one-based row indexes:

`44, 53, 72, 57, 16, 36, 1, 27, 42, 7, 15, 43, 23, 60, 65, 111, 83, 144, 117, 140, 175, 188, 176, 192, 193`

Category counts: single-hop 5, temporal 5, multi-hop 5, unanswerable 5, adversarial 5.

Identity-only verification passed:

```bash
python3 docs/eval/results/run_locomo_context_packet_canary.py \
  --identity-only \
  --fixed-rows-path docs/eval/results/locomo_answer_side_offslice_prereg_25rows_2026-05-08.json \
  --min-prereg-rows 20 \
  --max-prereg-rows 30
```

## Off-slice frozen canary

Candidate run after same-slice ablation: shape directive for `multi-hop,temporal` plus multimodal metadata projection for `single-hop,unanswerable`; subject guard omitted because same-slice ablation showed it was not needed for aggregate movement and remains weak on the key adversarial failure.

Run ID: `20260508T020734Z`

Command shape:

```bash
python3 docs/eval/results/run_locomo_context_packet_canary.py \
  --fixed-rows-path docs/eval/results/locomo_answer_side_offslice_prereg_25rows_2026-05-08.json \
  --min-prereg-rows 20 \
  --max-prereg-rows 30 \
  --merge-treatment \
  --merge-ref-gate \
  --frozen-context-replay \
  --frozen-baseline-artifact docs/eval/results/locomo_context_packet_canary_baseline_20260508T020434Z.json \
  --frozen-baseline-artifact-final-context-replay \
  --frozen-answer-shape-directive \
  --frozen-answer-shape-directive-categories multi-hop,temporal \
  --frozen-multimodal-metadata-projection \
  --frozen-multimodal-metadata-projection-categories single-hop,unanswerable
```

Result summary:

- Score: `46.0 -> 56.0` (`+10.0 pp`).
- Gold-evidence hit rate: `0.68 -> 0.68` (flat).
- Frozen context hash match: `100.0%`.
- Baseline prefix preserved: `100.0%`.
- Packet append rows: `0/25`; this off-slice replay is again answer-prompt sensitivity over the frozen final-context substrate.
- No severe category collapse: `true`; minimum category delta `+0.0 pp`.
- Improved rows: `16, 15, 23, 111`.
- Regressed rows: `53`.

Category movement:

- adversarial: `+0.0 pp`
- multi-hop: `+40.0 pp`
- single-hop: `+0.0 pp`
- temporal: `+0.0 pp`
- unanswerable: `+10.0 pp`


Off-slice interpretation:

- The cleaned candidate survived directionally off-slice (`+10 pp`) without changing gold-hit rate. This is encouraging diagnostic evidence for answer-side shape sensitivity, especially multi-hop.
- It is still not quote-worthy: n=25, same conversation (`conv-26`), one off-slice deterministic sample, flat gold-hit rate, and at least one regression.
- The regression row is 53: baseline included `Luna, Oliver, and Bailey`; treatment dropped `Bailey` and scored lower. This is a precision/list-completeness failure to preserve before any broader run.
- The strongest repeated mechanism is answer-shape for multi-hop. Multimodal metadata remains promising for image/object rows but was not the main off-slice driver.
- Adversarial remains unsolved (`+0 pp` off-slice; row 185 was still a failure in the earlier same-slice diagnostic), so subject/conflict handling should not be promoted as a solved mechanism.

## Artifacts to preserve

Same-slice ablation artifact sets preserved for the four claims in the table above: baseline JSON, treatment JSON, summary JSON, and result markdown for run IDs `20260508T015408Z`, `20260508T015541Z`, `20260508T015715Z`, and `20260508T015232Z`.

Off-slice preregistration and final replay artifacts preserved:

- `docs/eval/results/locomo_answer_side_offslice_prereg_25rows_2026-05-08.json`
- `docs/eval/results/locomo_context_packet_canary_baseline_20260508T020434Z.json` (off-slice frozen baseline artifact used by final replay)
- `docs/eval/results/locomo_context_packet_canary_baseline_20260508T020734Z.json`
- `docs/eval/results/locomo_context_packet_canary_treatment_merge_refgate_frozen_artifactctx_shaped_multihop_temporal_mmmeta_singlehop_unanswerable_20260508T020734Z.json`
- `docs/eval/results/locomo_context_packet_canary_summary_merge_refgate_frozen_artifactctx_shaped_multihop_temporal_mmmeta_singlehop_unanswerable_20260508T020734Z.json`
- `docs/eval/results/locomo_context_packet_canary_result_merge_refgate_frozen_artifactctx_shaped_multihop_temporal_mmmeta_singlehop_unanswerable_20260508T020734Z.md`

Exploratory side-combination artifacts not referenced by this document were intentionally not preserved.

## Remaining caveats before 199Q

This evidence now supports a defensible mechanism story, but not a stable size/scope claim.

What the evidence supports:

- Shape directive is a real generation-side mechanism, not just retrieval movement: standalone same-slice `+14 pp`, off-slice same-conversation `+10 pp`, with flat gold-hit rates.
- Multimodal metadata projection is narrow image/object support, approximately a `+4 pp` same-slice mechanism in this slice, not a broad answer-side intervention.
- Subject guard should be excluded from the locked candidate for now: its standalone movement was narrow, it did not add orthogonal aggregate signal beyond shape+mmmeta, and row 185 remained unresolved.
- The same-slice additivity check passed: shape (`+14`) + mmmeta (`+4`) matched shape+mmmeta (`+18`), with no obvious hidden interaction in this slice.

What the evidence still does not support:

- Cross-conversation generalization. Both fixed slices are `conv-26`; the off-slice is different rows, not a different conversation/discourse style.
- Stable magnitude. The off-slice `+10 pp` is still n=25, roughly 2-3 questions of movement.
- Harmlessness on list-completion questions. Row 53 regressed by dropping `Bailey`, a direct example of concise-shape pressure under-listing a required list.
- Solved adversarial/conflict handling. Adversarial was flat off-slice, and row 185 remains a key failure.

## Recommended next gate

Before any full 199Q quote run, add one more diagnostic gate:

1. Select a second off-slice 25-row sample from a different conversation ID using the same deterministic hash-stratified procedure, before scoring.
2. Run the same locked cleaned candidate: answer-shape for `multi-hop,temporal`, multimodal metadata for `single-hop,unanswerable`, no subject guard.
3. Do not tune after seeing the cross-conversation result.
4. Predeclare 199Q thresholds before promotion. Candidate thresholds:
   - multi-hop shape benefit must be at least `+6 pp` on 199Q multi-hop or an equivalent preregistered category metric;
   - list-completion regressions should be no worse than `-1 pp`, or more than two row-53-class under-listing regressions should trigger rollback/no-claim;
   - adversarial/conflict handling must not be framed as improved unless separately tested.

## Recommendation

Do not run or quote a full 199Q yet by default. The evidence now supports a narrow hypothesis: answer-shape directives improve multi-hop synthesis on frozen context and show same-conversation off-slice directionality. The missing gating step is cross-conversation off-slice validation plus preregistered effect-size/rollback thresholds. If promotion is later approved, use one locked candidate: shape+mmmeta, excluding subject guard unless separately fixed/tested.
