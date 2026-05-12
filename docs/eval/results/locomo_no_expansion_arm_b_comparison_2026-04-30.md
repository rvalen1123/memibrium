# LOCOMO No-Expansion Arm B Comparison — 2026-04-30

Pre-registration: `docs/eval/locomo_no_expansion_arm_b_preregistration_2026-04-30.md`
Run commit: `1de8250`
Arm B behavioral commit: `18d9b54`
Parser hygiene commit: `ddb0aa8`
Slice: full LOCOMO conv-26, 199Q, cleaned + normalized.
Arm A reference is not re-run; Arm B is original-query-only with expansion disabled.

## Result

| Metric | Arm A: query expansion reference | Arm B: no expansion | Delta |
|---|---:|---:|---:|
| Questions | 199 | 199 | — |
| Raw credit | 94.5 / 199 | 87.5 / 199 | -7.0 |
| Full 5-cat accuracy | 47.487437% | 43.969849% | -3.517588 pp |
| Protocol 4-cat accuracy | 57.89% | 52.96% | -4.93 pp |
| Avg query latency | 3285 ms | 904 ms | -2381 ms |
| p50 query latency | 2439 ms | 860 ms | -1579 ms |
| p95 query latency | 8473 ms | 1236 ms | -7237 ms |
| Avg latency reduction | — | — | -72.48% |
| p95 latency reduction | — | — | -85.41% |
| Accuracy cost of no-expansion | — | — | -3.517588 pp |
| Expansion fallback | 57/199 (28.64%) | 0/199 (0.00%) | — |

## Category deltas (B vs A)

| Category | n | Arm A acc | Arm B acc | Delta |
|---|---:|---:|---:|---:|
| adversarial | 47 | 13.83% | 14.89% | +1.06 pp |
| multi-hop | 13 | 61.54% | 50.00% | -11.54 pp |
| single-hop | 32 | 43.75% | 39.06% | -4.69 pp |
| temporal | 37 | 60.81% | 60.81% | +0.00 pp |
| unanswerable | 70 | 62.14% | 55.71% | -6.43 pp |

## Paired buckets

| Bucket | Count |
|---|---:|
| unchanged_correct | 64 |
| unchanged_wrong | 81 |
| same_partial | 8 |
| rescued | 14 |
| harmed_from_fully_correct | 21 |
| partial_changed | 11 |

## Pre-registered decision (§5)

Outcome triggered: **Outcome 3**.
Verdict: **expansion_was_helping_no_config_change**.

Reasons:
- B_minus_A_le_-1.5pp

Arm B − Arm A = -3.517588 pp, which is ≤ −1.5pp. Under §5 Outcome 3, expansion was actually helping relative to original-query-only retrieval. Arm B is a research finding, not a config change. Arm C becomes a candidate next pre-registration, and the original diagnosis should get a follow-up/superseding doc rather than an inline edit.

The same result is also accepted as a quantified latency/accuracy tradeoff data point. Disabling expansion is rejected as a default-config change, but it establishes one endpoint of the production curve: query expansion costs about 2.4s average latency and about 7.2s at p95, while buying about +3.5pp full 5-category accuracy and +4.9pp protocol 4-category accuracy on this substrate. This latency finding was pre-registered only as a sanity check, so it should not be over-interpreted as a promotion rule, but its magnitude is operationally important.

## Mechanism sanity check (§6)

Prediction: adversarial and unanswerable should improve most; single-hop could be neutral/slightly worse; multi-hop/temporal uncertain but directionally better.

Observed:

- adversarial: +1.06 pp
- unanswerable: -6.43 pp
- single-hop: -4.69 pp
- multi-hop: -11.54 pp
- temporal: +0.00 pp

Assessment: **mechanism not confirmed**. Mechanistic prediction failed: adversarial improved slightly, but unanswerable and multi-hop worsened materially; single-hop worsened as allowed; temporal was neutral.

Methodology lesson: the fallback-vs-non-fallback diagnostic measured the wrong counterfactual for a full-population config change. The fallback subpopulation was selected by the mechanism under test: the expansion LLM failed or refused to emit usable JSON on those questions. That selected population can outperform the expansion-success population without implying that disabling expansion for every question will help. In this run, the unanswerable fallback subpopulation had looked better in diagnosis, but full-population no-expansion made unanswerable worse by -6.43pp. Future diagnostics should treat mechanism-defined subpopulation comparisons as hypothesis generators, not as estimates of full-population intervention effects.


## Cross-run multi-hop sensitivity

Multi-hop was the largest Arm B category loss: -11.54pp (about -1.5 credits on n=13). The category is thin, so the exact magnitude should not be overweighted, but the direction now matches another independent retrieval/context intervention: the 2026-04-29 gated-append full run also hurt multi-hop by -7.69pp.

Cross-run pattern: changes to retrieval expansion/context mechanics are disproportionately risky for multi-hop. That is plausible because multi-hop questions depend on assembling multiple evidence fragments and are most sensitive to evidence displacement, missing expansion terms, and noisy context. Since multi-hop is also the category Memibrium should be positioned to win, future expansion/latency work should preserve or separately audit multi-hop behavior rather than optimizing only aggregate score or latency.

## Integrity notes

- Smoke run completed with `--no-expansion-arm-b --max-convs 1 --max-questions 3`; log grep found no expansion activity.
- Full run log grep also found no expansion activity.
- Arm B artifact records `condition.no_expansion_arm_b=true` and `condition.query_expansion=false`.
- Arm B fallback count is 0/199; expansion path was disabled rather than failing open.
- Comparison distinguishes run commit from behavioral commits for attribution clarity.
