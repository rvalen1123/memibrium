# DATE NORMALIZATION COMPLETE

## FINAL RESULT
- Baseline: **61.37% temporal**, **61.96% overall**
- Normalized: **70.87% temporal**, **63.62% overall**
- Temporal delta: **+9.50 pp**
- Overall delta: **+1.66 pp**
- Measured fix-rate: **43.98%** (`(70.87 - 61.37) / 21.6`)
- Pre-registered prediction: **70.9% point**, **68.4%–73.6% range**
- Verdict: **calibrated**
- Commit hash (substrate): **aee3bc7**

## PROTOCOL-COMPARABLE 4-CATEGORY RESULT
- LoCoMo peer comparisons should exclude category 5 (adversarial).
- Baseline 4-category overall: **~72.32%**
- Normalized 4-category overall: **~75.04%**
- 4-category delta: **+2.72 pp**
- Use **75.04%**, not 63.62%, for any external peer comparison.

## INTERPRETATION
- The intervention landed essentially on the point estimate.
- Measured fix-rate (43.98%) is close to the assumed 40% and within the pre-registered 30–50% band.
- This validates both:
  1. the normalization intervention estimate
  2. the N=50 failure-mode bucketing method with spot-check correction
- Cross-category behavior:
  - multi-hop: 48.96% → 51.56% (+2.60 pp)
  - single-hop: 63.83% → 64.36% (+0.53 pp)
  - unanswerable: 81.99% → 82.76% (+0.77 pp)
  - cat-5: 26.23% → 24.44% (-1.79 pp)
- Read per pre-registration: temporal in-range + multi-hop also up = validated normalization win with possible composition-adjacent side effect worth future investigation.

## METHODOLOGY / RUN NOTES
- Full run completed with 1986/1986 questions scored.
- Resume seeding preserved the initial 6-conversation partial without duplicating conv-47 entries (`conv-47` count = 190, expected).
- Azure content filter falsely tripped in the judge path on a family-term example; mitigated by narrow sanitize-and-retry fallback in `judge_answer()`.
- Benchmark script now fails closed on Azure chat errors instead of silently returning `"I don't know"`.
- Benchmark preflight now validates both MCP recall reachability and benchmark LLM reachability before ingest.

## IMPORTANT SCRIPT IMPROVEMENTS MADE
- `llm_call()` now raises on Azure/auth/schema failures instead of silently returning `"I don't know"`.
- Added preflight check before benchmark ingest.
- Added richer Azure error logging including response body.
- Added resume-safe seeding for `--start-conv` runs.
- Added narrow content-filter retry in `judge_answer()` for family-term false positives.

## FILES
- Analysis: `docs/eval/failure_mode_analysis.md`
- Baseline results: `docs/eval/locomo_results.json`
- Partial/final normalized results on disk: `/tmp/locomo_results_normalized.json`
- Benchmark log: `/tmp/locomo_normalized_resume.log`

## NEXT STEPS
1. Update benchmark skill/documentation with the auth + preflight + resume + content-filter lessons.
2. Review git diff carefully before committing.
3. If doing a citable rerun later, consider:
   - judge-specific preflight probe
   - explicit `answer_refusal` flag in `results_log`
   - note judge-model bias / peer-score methodology caveat
4. Optional follow-up: inspect whether the multi-hop gain is concentrated on temporally anchored multi-hop questions.
