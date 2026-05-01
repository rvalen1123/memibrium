# LOCOMO hybrid-active failure-mode audit pre-registration — 2026-05-01

Repo: `/home/zaddy/src/Memibrium`
Branch: `query-expansion`
Baseline commit: `f2466c9`
Baseline class: no-intervention, canonical-substrate, hybrid-active conv-26 baseline.

## Purpose

This document pre-registers a read-only diagnostic audit against the first committed canonical-substrate hybrid-active LOCOMO baseline:

- Result JSON: `docs/eval/results/locomo_conv26_hybrid_active_substrate_baseline_2026-05-01.json`
- Run log: `docs/eval/results/locomo_conv26_hybrid_active_substrate_baseline_2026-05-01.log`
- Prelaunch evidence: `docs/eval/results/locomo_hybrid_active_substrate_baseline_prelaunch_2026-05-01.json`
- Comparison note: `docs/eval/results/locomo_hybrid_active_substrate_baseline_199q_comparison_2026-05-01.md`

The baseline measured this exact scope only:

> This active hybrid configuration, at this commit and canonical substrate, is under-retrieving for LOCOMO conv-26.

Do not generalize this audit to all hybrid retrieval, all Memibrium configs, other substrates, other commits, or full LOCOMO without separate evidence.

## Hard scope and side-effect policy

Allowed:

- Read committed result artifacts.
- Read committed source code to understand retrieval layers and evaluator behavior.
- Read pinned LOCOMO audit artifacts copied under `docs/eval/phase_b_artifacts/locomo_audit_9493fb4b4af4256ed17a18e8fd0b3cfdeec29539/`.
- Compute summaries, stratifications, sample sets, and labels from existing files.
- Create new markdown/JSON audit artifacts under `docs/eval/results/`.

Not allowed in this audit:

- No LOCOMO benchmark launch.
- No smoke benchmark launch.
- No retain/recall probe against the running server.
- No DB writes, cleanup, restart, rebuild, env edit, container mutation, schema mutation, or API calls that mutate state.
- No Phase C intervention implementation.
- No tuning after inspecting failures.

If any needed question cannot be answered from committed artifacts/source/pinned audit files, the audit result must say `insufficient evidence` and propose a separately pre-registered follow-up. It must not silently mutate runtime or run a benchmark to fill the gap.

## Baseline facts to preserve

Hybrid-active canonical baseline:

- Overall 5-category score: `14.82%`
- Protocol 4-category score: `19.41%`
- Total questions: `199`
- Query expansion fallback: `0/199`
- Avg query latency: `2478 ms`
- Mean `n_memories`: `4.5327`
- `n_memories == 15` saturation: `22/199 (11.06%)`
- Distribution: `2:57, 3:110, 11:1, 12:3, 13:3, 14:3, 15:22`

Recovered stale-live-path floor:

- Overall reference floor: `66.08%`
- Query expansion fallback: `0/199`
- Mean `n_memories`: `13.1608`
- `n=15` saturation: `31.16%`

Initial n-memory sensitivity observed from the committed baseline JSON:

- `n=2`: 57 questions, `4.39%`
- `n=3`: 110 questions, `5.91%`
- `n=11-14`: 10 questions, approximately `55%`
- `n=15`: 22 questions, `68.18%`
- zero-score questions: 160/199, mean `n_memories=3.16`
- partial-score questions: 19/199, mean `n_memories=8.05`
- full-score questions: 20/199, mean `n_memories=12.2`

These are priors to be checked/reported, not a substitute for the audit.

## Audit questions

The audit must answer, with evidence:

1. Is the dominant failure signature retrieval starvation, scoring/threshold cutoff, wrong evidence, synthesis failure, category/evaluator mismatch, or mixed?
2. Does more returned context correlate with better score overall and within each category?
3. Are high-`n_memories` zero-score cases explainable by missing evidence, present-but-unused evidence, entity/temporal mismatch, or evaluator/format mismatch?
4. Is the adversarial `0/47` primarily a Memibrium retrieval/synthesis failure, an evaluator/format mismatch, or mixed?
5. Is unanswerable `3.57%` helped or harmed by larger `n_memories`?
6. Which Phase C intervention family is justified by the audit, if any?

## Failure categories

Label sampled failed questions using these categories. Multiple labels are allowed, but every sampled failure must have one primary label.

1. `retrieval_starvation_candidate_fetch`
   - Too few memories are returned to plausibly answer.
   - Evidence cannot be assessed as present from the returned answer context because the model clearly lacked support or answered `I don't know` with low `n_memories`.
   - Intervention family if dominant: increase candidate fetch breadth or recall top-k before scoring.

1a. `retrieval_threshold_cutoff_or_fusion_miss`
   - The relevant evidence plausibly exists in ingested LOCOMO chunks or pre-threshold candidates but is absent after hybrid scoring/fusion/thresholding.
   - Distinct from candidate-fetch starvation because intervention targets thresholds, score normalization, RRF/fusion weights, or post-score cutoff rather than initial candidate generation.
   - If committed artifacts lack pre-threshold candidate traces, mark as `unresolved_requires_telemetry` rather than guessing.

2. `evidence_absent_from_returned_context`
   - Enough context is returned, but the gold-supporting evidence is not visible in what the answerer likely saw.
   - Intervention family if dominant: retrieval calibration/fusion/candidate expansion.

3. `evidence_present_synthesis_failed`
   - Gold-supporting evidence appears to have been available, but the generated answer is wrong, incomplete, or `I don't know`.
   - Intervention family if dominant: synthesis prompt, answer extraction, evidence selector, or reasoning layer.

4. `wrong_entity_or_attribution_confusion`
   - Returned/used evidence is about the wrong person, wrong relationship, or wrong entity.
   - Intervention family if dominant: entity attribution guard or entity-aware retrieval.

5. `temporal_normalization_or_date_mismatch`
   - Evidence exists but date normalization, relative date resolution, or temporal granularity causes mismatch.
   - Intervention family if dominant: temporal normalization or judge/date scoring correction.

6. `adversarial_or_unanswerable_evaluator_format_mismatch`
   - Prediction may be semantically compatible with gold/corrected answer, but evaluator or adversarial formatting likely rejects it.
   - Intervention family if dominant: evaluator correction / Penfield Labs correction reporting, not Memibrium retrieval code.

7. `genuine_adversarial_or_unanswerable_handling_failure`
   - The system is semantically wrong on adversarial/unanswerable even under corrected interpretation.
   - Intervention family depends on whether the local cause is retrieval starvation, over-context hallucination, or answer policy.

8. `insufficient_evidence_from_artifacts`
   - Existing committed artifacts do not expose enough candidate/context detail to classify.
   - Output must recommend a separately pre-registered telemetry audit rather than choosing a Phase C implementation.

## Required quantitative analyses

The audit must compute and report:

1. Overall `n_memories` distribution and score by `n_memories` bucket.
2. Per-category score, mean/median `n_memories`, saturation rate, and zero-score rate.
3. Per-category score-by-`n_memories` sensitivity:
   - Does score improve with more context for temporal, single-hop, multi-hop, unanswerable, adversarial?
   - Does unanswerable get better, worse, or stay flat as context increases?
   - Does adversarial remain zero independent of context?
4. Query latency by score bucket and by `n_memories` bucket, only as descriptive evidence.
5. Count of `I don't know` or equivalent abstentions by category, score bucket, and `n_memories` bucket.
6. High-`n_memories` zero-score subset size and labels.
7. Low-`n_memories` zero-score subset size and labels.

## Sampling policy

The audit should be asymmetric: exhaustive where the bucket is small and highly diagnostic, sampled where the bucket is large and predictable.

Required sample sets:

1. `high_n_zero_score_exhaustive`
   - Include all zero-score questions with `n_memories >= 12`.
   - This bucket distinguishes `recall recovery is sufficient` from `recall is necessary but not sufficient`.

2. `n15_all_or_exhaustive_summary`
   - Include all `n_memories == 15` questions, or at minimum a complete table with score/category/question and failure label for every zero-score item in the bucket.

3. `low_n_zero_score_sample`
   - Sample 10-15 zero-score questions with `n_memories <= 3`.
   - Stratify across categories where possible.
   - This bucket is expected-failure evidence; do not over-sample it at the expense of high-diagnostic buckets.

4. `adversarial_exhaustive_or_full_table`
   - Include all 47 adversarial questions in a structured table with prediction, gold, score, `n_memories`, and preliminary semantic/evaluator mismatch label.
   - If full manual labeling is too large, provide full table plus manually label at least 15, prioritizing any non-`I don't know`/non-obvious cases.

5. `unanswerable_stratified_sample`
   - Sample at least 15 unanswerable questions, stratified by `n_memories` and by score/abstention pattern.
   - Explicitly test whether more context helps or hurts this category.

6. `temporal_high_n_failures`
   - Include all temporal zero-score questions with `n_memories >= 12`.
   - Distinguish true temporal normalization mismatch from missing evidence/synthesis failure.

7. `success_controls`
   - Include at least 10 successful/partial questions, emphasizing `n_memories <= 3` successes and `n_memories >= 12` successes.
   - Purpose: avoid labeling every low-n case as impossible and every high-n case as sufficient.

If a required sample bucket is smaller than the target, include it exhaustively and state the bucket size.

## Adversarial / Penfield Labs correction sub-audit

Pinned dependency:

- Repo: `https://github.com/dial481/locomo-audit.git`
- Commit: `9493fb4b4af4256ed17a18e8fd0b3cfdeec29539`
- Local pinned artifacts: `docs/eval/phase_b_artifacts/locomo_audit_9493fb4b4af4256ed17a18e8fd0b3cfdeec29539/`

The audit must cross-reference the pinned audit artifacts where applicable, especially:

- `answer_key.json`
- `errors.json`
- `ap_v1_specific_wrong_scored_reference.json`
- `ap_v2_vague_topical_scored_reference.json`
- probe/reference JSON files copied in the pinned directory.

Adversarial audit requirements:

1. Identify whether each adversarial baseline row maps to an audited/corrected item when possible.
2. Flag predictions that may be semantically correct under corrected answer interpretation but scored zero by the current evaluator.
3. Separate evaluator/format mismatch from genuine adversarial-handling failure.
4. Report adversarial results under three labels where possible:
   - current evaluator score;
   - likely corrected semantic outcome;
   - unresolved.
5. If the pinned artifacts are insufficient to map adversarial items, say so and do not invent corrected labels.

Rationale: Penfield Labs audit noted that published LoCoMo results do not evaluate the adversarial subset and that the original multiple-choice formatter is broken for many items. A `0/47` adversarial result may therefore mix Memibrium failure with evaluation-format mismatch. The Phase C intervention family differs completely depending on which is dominant.

## Retrieval-layer distinction to preserve

If retrieval is implicated, the audit must distinguish these layers as far as artifacts allow:

1. Candidate fetch breadth:
   - Too few memories ever enter scoring.
   - Candidate intervention: increase initial semantic/lexical fetch count, add query expansion breadth, or adjust domain/session coverage.

2. Scoring/fusion/threshold cutoff:
   - Candidate set exists but relevant evidence is downweighted or cut off.
   - Candidate intervention: relax threshold, change RRF/fusion weights, normalize scores, expose more post-score candidates.

3. Output cap / answer-context transfer:
   - Enough scored candidates exist but too few reach the answerer due to cap or selection.
   - Candidate intervention: adaptive output top-k, evidence-aware context packing, or category-sensitive cap.

If the baseline artifacts only contain final `n_memories` and not pre-threshold candidates/scores, the audit must state that layer 1 vs 2 vs 3 cannot be resolved without a separately pre-registered telemetry run.

## Output deliverables

Primary output:

- `docs/eval/results/locomo_hybrid_active_failure_mode_audit_2026-05-01.md`

Optional machine-readable support file:

- `docs/eval/results/locomo_hybrid_active_failure_mode_audit_labels_2026-05-01.json`

The markdown report must include:

1. Executive conclusion scoped to this baseline only.
2. Quantitative tables from the required analyses.
3. Sampling tables and labels.
4. Adversarial/evaluator-format sub-audit.
5. Retrieval-layer diagnosis with explicit uncertainty.
6. Intervention-family recommendation with confidence:
   - `high`, `moderate`, `low`, or `insufficient evidence`.
7. Explicit non-recommendations: intervention families ruled out or deferred and why.
8. Stop/go decision for Phase C:
   - `go_retrieval_calibration_preregistration`
   - `go_evaluator_correction_reporting`
   - `go_telemetry_preregistration`
   - `go_category_specific_intervention_preregistration`
   - `no_go_insufficient_evidence_expand_audit`

## Decision rules

- If low-n failures dominate and high-n successes remain strong, recommend retrieval calibration only if high-n zero failures do not show a separate dominant synthesis/evaluator problem.
- If high-n zero failures frequently contain correct evidence but wrong answers, retrieval calibration alone is insufficient; recommend synthesis/evidence-selection audit or combined staged plan.
- If adversarial zeros are mostly evaluator/format mismatch, do not recommend Memibrium retrieval code changes for that subset before corrected reporting.
- If unanswerable performance worsens with more context, avoid global recall expansion; recommend category-sensitive or confidence-gated retrieval instead.
- If artifacts cannot distinguish candidate fetch from threshold/fusion cutoff, recommend telemetry preregistration before implementing retrieval changes.
- If findings conflict or sample support is too small, output `insufficient evidence` rather than forcing a Phase C intervention.

## Phase C boundary

This audit may recommend an intervention family. It must not implement one.

Any Phase C intervention requires a new pre-registration after this audit is complete and committed. The Phase C preregistration must cite the committed audit report and must not tune against the full 199Q result beyond the failure-mode family justified here.
