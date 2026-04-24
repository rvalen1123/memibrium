# Benchmark Prediction: Date Normalization Intervention

## Current Baseline (barely-cleaned dataset, 7 gold-label fixes applied)
- Condition 4 (temporal): 37.7% (121/321 correct)
- Overall LOCOMO: ~46.2%

## Failure-mode breakdown (eyeball-corrected, N=50)
- Relative-date failures: ~54% of failure pool (33.6 pp absolute)
- Gold-label errors: ~26% of failure pool (16.2 pp absolute) — UNFIXABLE by system
- True retrieval misses: ~12% of failure pool (7.5 pp absolute)
- Composition failures: ~8% of failure pool (5.0 pp absolute)

## Explicit fix-rate prediction

**Assumption:** Date normalization captures 40% of relative-date failures.
- Rationale: Normalization makes dates explicit in memory text, improving retrieval match
  and giving the model concrete dates to reason with. But the model still needs to:
  (a) retrieve the normalized memory, (b) connect it to the question, (c) reason correctly.
  40% is moderate — not all relative-date failures are rescued by text normalization alone.

**Math:**
- Baseline: 37.7%
- Gain from normalization: 33.6 pp × 0.40 = 13.4 pp
- Predicted condition-4 score: **51.1%**
- Prediction range: **45–55%** (fix-rate uncertainty: 30–50%)

## Interpretation bands

| Result | Interpretation |
|--------|---------------|
| < 40% | Normalization failed or hurt; investigate false positives / retrieval degradation |
| 40–45% | Marginal gain (~5 pp); normalization helps some cases but not enough to matter |
| 45–55% | **Expected range** — normalization captures meaningful fraction of relative-date bucket |
| 55–60% | Strong gain; normalization + retrieval synergy better than expected |
| > 60% | Surprisingly strong; may indicate label noise still present or overfitting to eval |

## Key caveat: "barely-cleaned" data

The `/tmp/locomo10_cleaned.json` dataset has only 7 confirmed gold-label fixes.
The eyeball scan suggests ~26% of all temporal failures are gold-label errors.
On the full 321-question temporal set, that's ~50 questions with label noise.

**This means:**
- The 37.7% baseline is understated (some failures are unfixable label errors)
- The effective ceiling on the current eval is ~74% (100% − 26% gold-label errors)
- A result of 51% on barely-cleaned data could mean:
  (a) normalization captured ~40% of fixable relative-date failures (real gain)
  (b) label noise distribution shifted favorably (noise)
  (c) both

**For clean measurement:** Full label cleanup should happen before the next major intervention.

## Label cleanup stop criterion

**Scope:** Classify all 107 retrieval-missing-bucket failures using the rubric in `/tmp/failure_mode_rubric.md`.
**Stop when:** All 107 have been classified, confirmed gold-label errors removed, everything else accepted as-is.
**Do not expand to:** Other buckets (relative-date, composition) or all 200 failures. Those are out of scope for this cleanup pass.
**Time budget:** 2 hours. If not done in 2 hours, document what's pending and proceed.

## Pre-pinned post-hoc formula

After both runs complete, compute measured fix-rate with:

```
measured_fix_rate = (normalization_score − baseline_score) / 33.6
```

Where 33.6 = absolute percentage points of relative-date failures in the pool (54% of 62.3% failure rate).

Interpretation:
- ~40%: prediction was well-calibrated
- >60%: the 54% relative-date estimate was right and normalization is more effective than expected
- <20%: either the relative-date estimate was wrong or normalization isn't capturing what was assumed

Note: 33.6 assumes the eyeball-corrected 54% share is accurate. The eyeball CI was wide, so measured_fix_rate is itself an estimate.

## Pre-registered before run

Date: 2026-04-23
Predicted condition-4 temporal accuracy on cleaned data with normalization: **45–55%**
Assumed fix-rate for relative-date failures: **40%**

Post-run analysis will compare actual fix-rate to assumed 40%.
