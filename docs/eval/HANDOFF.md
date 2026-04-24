# QUERY EXPANSION COMPLETE

## FINAL RESULT
- Intervention: recall-time query expansion on top of normalized benchmark
- Full 5-category overall: **65.06%**
- Protocol-comparable 4-category overall: **77.48%**
- Normalized-only 4-category baseline: **75.04%**
- 4-category delta: **+2.44 pp**
- Query expansion fallback: **1/1986 = 0.05%**
- Runtime: **18,206s (~5.06h)**
- Avg query latency: **8,982ms**

## PRE-REGISTERED READ
- Predicted 4-category overall: **79% point**, **78–80% range**
- Actual 4-category overall: **77.48%**
- Verdict: **directional confirmation, magnitude miss**
- Miss size: **0.52 pp below the pre-registered lower bound**

## CATEGORY DELTAS VS NORMALIZED-ONLY BASELINE
- temporal: **70.87% → 75.08%** (**+4.21 pp**)
- single-hop: **64.36% → 68.26%** (**+3.90 pp**)
- multi-hop: **51.56% → 53.65%** (**+2.09 pp**)
- open-domain / unanswerable: **82.76% → 84.24%** (**+1.48 pp**)
- cat-5: **24.44% → 22.09%** (**-2.35 pp**)

## WHERE THE PREDICTION MISS CAME FROM
Weighted contribution to the expected 4-category gain:
- temporal: predicted **+1.13 pp**, actual **+0.88 pp**
- open-domain: predicted **+2.35 pp**, actual **+0.79 pp**
- single-hop: predicted **+0.29 pp**, actual **+0.72 pp**
- multi-hop: predicted **+0.24 pp**, actual **+0.13 pp**

Read:
- The main miss came from **open-domain not generalizing from the conv-26 canary**.
- Single-hop beat prediction.
- Temporal improved strongly and remained the largest realized gain.
- Multi-hop improved modestly, but did not become the main story.

## METHOD / INTERPRETATION LESSONS
- Query expansion helped directionally, but less than predicted at full-run scale.
- The honest mechanism story is **broader retrieval coverage**, not "fixes multi-hop."
- Single-conversation canary extrapolation was unreliable for a **high-weight category** (open-domain).
- Aggregate directional predictions appear more stable than per-category extrapolations from one conversation.
- Cat-5 declined slightly; worth follow-up to test whether expansion sometimes turns refusals into hallucinated answers on adversarial questions.

## A/B CANARY RESULT THAT JUSTIFIED THE FULL RUN
Conv-26 clean A/B:
- no expansion: **65.6%** overall
- expansion: **68.1%** overall
- delta: **+2.5 pp**
- expansion fallback: **0/199**

That was enough to justify the full run, but it overstated open-domain generalization.

## OPERATIONAL READ
- `USE_QUERY_EXPANSION=1` should remain **evaluation-only**, not a production default.
- Latency increased from roughly **2.6s/query** (conv-26 no-exp canary) to roughly **8.0–9.0s/query** with expansion.
- This is acceptable for benchmark exploration, not for live product retrieval.

## FILES
- Full run JSON: `docs/eval/locomo_results_expansion_full.json`
- Full normalized-only baseline: `docs/eval/locomo_results.json`
- Conv-26 no-exp canary JSON: `docs/eval/locomo_results_conv26_noexp.json`
- Conv-26 expansion canary JSON: `docs/eval/locomo_results_conv26_exp.json`
- Prediction log: `docs/eval/benchmark_prediction.md`
- Calibration record: `docs/eval/prediction_tracking.md`

## NEXT STEPS
1. Run entry-by-entry A/B diff (wrong→right, right→wrong) on conv-26 and/or full-run subsets.
2. Check category-5 specifically for refusal→hallucination flips under expansion.
3. Do **not** spend more time tuning expansion yet; higher-leverage next interventions are answer-model / judge-model upgrades and multi-run variance estimation.
