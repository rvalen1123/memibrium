# Failure-Mode Analysis: Temporal (Condition 4) — N=50 Sample

**Date:** 2026-04-24
**Baseline:** 61.37% temporal accuracy (197/321)
**Sample:** N=50 from 97 score=0 failures, seed=42
**Commit hash (substrate):** aee3bc7

---

## Distribution (N=50)

| Category | Count | % | Description |
|----------|-------|---|-------------|
| A. Relative-Date | 28 | 56.0% | Evidence exists with unresolved relative date |
| B. Retrieval-Miss | 6 | 12.0% | Evidence exists but model failed to retrieve |
| C. Gold-Label | 10 | 20.0% | GT contradicts or lacks evidence |
| D. Composition | 6 | 12.0% | Requires combining multiple pieces |

**Spot-check corrections (3/50 = 6% error rate):**
- [0] conv-49 Sam Dec 4: C → A ("yesterday" on Dec 5 = Dec 4)
- [8] conv-50 Calvin August city: B → C (both Tokyo and Miami in August)
- [11] conv-49 Sam Canadian woman: C → B (model retrieved wrong event)

**Classifier uncertainty:** ~6% error rate from spot-check (N=5). Errors are bidirectional between gold-label and fixable categories (A↔C, B↔C), consistent with documented LLM classifier confusability. Bucket shares have ±3 pp uncertainty from classification alone, before sampling error. The 68.4–73.6% range accommodates this.

**Comparison to previous N=50:**
- Relative-date: 54% → 56% (stable, within noise)
- Gold-label: 26% → 20% (decrease)
- Retrieval-miss: 12% → 12% (stable)
- Composition: 8% → 12% (increase)

---

## Fixable by Date Normalization

**Directly fixable (Category A):** 56% of score=0 failures = 21.6 pp absolute
- Examples: "yesterday" on Aug 5 → Aug 4, "last week" on Oct 13 → week before Oct 13
- Many are "yesterday", "last week", "last Friday" type expressions

**Not fixable:**
- B (retrieval-miss): 12% = 4.6 pp — embedding/retrieval issue
- C (gold-label): 20% = 7.7 pp — dataset error or unanswerable

**Composition (Category D):** 12% = 4.6 pp
- Some involve date arithmetic (duration between events)
- Conservative: 20% of D failures rescued by better date context = +0.9 pp
- Included in combined estimate below

---

## Prediction

### Framework
- Failure pool: 38.6 pp absolute (100% - 61.37%)
- Relative-date share: 21.6 pp absolute (56% of failure pool)
- Fix rate: 40% (consistent with prior sessions)
  - Rationale: model still needs to retrieve, connect, and reason correctly even with normalized dates
  - Some relative dates are vague ("recently", "a while ago") and not resolvable
- Composition contribution: +0.9 pp (20% of D failures)

### Point Estimate
- Gain = 21.6 × 0.40 + 0.9 = 9.5 pp
- **Projected temporal accuracy: 70.9%**

### Range (fix-rate 30–50%)
- Low (30% A + 10% D): 61.4 + 6.5 + 0.5 = **68.4%**
- High (50% A + 30% D): 61.4 + 10.8 + 1.4 = **73.6%**
- **Prediction interval: 68.4% — 73.6%**

### Theoretical Maximum
- 100% capture of relative-date failures: 61.4 + 21.6 = **83.0%**
- Anything above 73.6% suggests normalization captures more than direct date resolution

### Environment comparability note
- Baseline is pinned to commit `aee3bc7`.
- Rerun assumes the same benchmark environment (same endpoint/model family) and is re-validated with recall + LLM preflight before ingest.
- If preflight fails or the endpoint/model changes, the baseline-to-normalized comparison is invalid and must be re-derived.

---

## Post-Run Formula

```text
measured_fix_rate = (normalization_score - 61.37) / 21.6
```

Interpretation:
- Near 40%: prediction calibrated, normalization works as expected
- Much higher (>60%): easier failures in pool than assumed, or method captures more
- Much lower (<20%): residual failures are harder than expected

### Pre-registered interpretation table

| Temporal outcome | Other categories | Read |
|---|---|---|
| In [68.4, 73.6] | ~flat (±2 pp) | Prediction validated. Clean win. |
| In [68.4, 73.6] | multi-hop also up | Composition-adjacent gain. Note it, but do not claim it as the primary intervention effect. |
| In [68.4, 73.6] | single-hop down | Normalization may be hurting non-temporal retrieval (token drift / retrieval trade-off). Investigate before rollout claims. |
| >73.6 | anything | Above expected range suggests label noise, bucket-share miscalibration, or broader side effects. Investigate before claiming a stronger method. |
| <68.4 | any pattern | Prediction miss. Report measured fix-rate and investigate residual failures; do not move the goalposts. |

### Implementation notes for next iteration
- Current preflight validates recall and generic LLM reachability. A judge-specific probe (numeric response, low `max_tokens`) would make the benchmark more robust to model-behavior drift.
- Consider adding `answer_refusal = predicted.strip().lower().startswith("i don't know")` to `results_log` so post-run analysis can separate model refusals from judge-scored wrong answers.

---

## Date Normalization Intervention Result

- Baseline (healthy DB, barely-cleaned, no normalization): **61.37% temporal**, **61.96% overall**
- Normalized (healthy DB, barely-cleaned, with normalization): **70.87% temporal**, **63.62% overall**
- Temporal delta: **+9.50 pp**
- Overall delta: **+1.66 pp**
- Measured fix-rate: **43.98%** (`(70.87 - 61.37) / 21.6`)
- Pre-registered prediction: **70.9% point**, **68.4%–73.6% range**
- Verdict: **calibrated**
- Commit hash (substrate): **aee3bc7**

### Interpretation
- The intervention landed essentially on the point estimate (70.87% vs 70.9%).
- Measured fix-rate (43.98%) is close to the assumed 40% and well within the pre-registered 30–50% band.
- This validates not only the intervention estimate but also the failure-mode bucketing methodology (N=50 + spot-check) that produced the 56% relative-date share estimate.
- Cross-category behavior: multi-hop improved from **48.96% → 51.56%** (+2.60 pp), single-hop was effectively flat (**63.83% → 64.36%**), unanswerable was flat-to-slightly-up (**81.99% → 82.76%**), and cat-5 declined (**26.23% → 24.44%**).
- Applying the pre-registered interpretation table: temporal is in-range and multi-hop is also up, so this is a validated normalization win with a possible composition-adjacent side effect worth future investigation, not a primary claim.

### Protocol-comparable overall score (categories 1–4 only)
- LoCoMo protocol comparisons should exclude category 5 (adversarial).
- Baseline 4-category overall: **~72.32%**
- Normalized 4-category overall: **~75.04%**
- 4-category delta: **+2.72 pp**
- This is the correct aggregate number to compare against protocol-compliant peer reports.

### Peer-comparison caution
- The previously reported **63.62% overall** includes category 5 and is **not comparable** to peer results that follow the published 4-category protocol.
- Published peer numbers are methodology-sensitive and sometimes contested:
  - Zep's public 84% claim was audited down to 58.44% after correcting category inclusion.
  - Mem0 self-reports are materially higher than some independent replications.
  - The Remembra 94.2 figure is not currently sourceable from its public repo.
- For external comparison, prefer protocol-comparable anchors with documented methodology (for example MemMachine v0.2 and independent Memobase/Mem0 evaluations) and disclose judge-model coupling caveats.

### Run notes
- Full run completed with 1986/1986 questions scored.
- Resume seeding preserved the initial 6-conversation partial without duplicating conv-47 entries (`conv-47` count = 190, expected).
- A judge-path Azure content-filter false positive on a family-term example was mitigated by a narrow sanitize-and-retry fallback in `judge_answer()`.
- Benchmark script now fails closed on Azure chat errors instead of silently returning `"I don't know"`.
- Preflight now validates both MCP recall reachability and benchmark LLM reachability before ingest.

## Files
- Raw analysis: `/tmp/failure_analysis_raw.json` (ephemeral local output, not committed as a reproducible artifact)
- Classification (corrected): `/tmp/failure_classification_corrected.json` (ephemeral local output, not committed as a reproducible artifact)
