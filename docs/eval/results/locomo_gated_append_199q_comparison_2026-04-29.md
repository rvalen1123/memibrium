# LOCOMO Gated Append 199Q Comparison — 2026-04-29

Pre-registration: `docs/eval/locomo_gated_append_preregistration_2026-04-29.md`
Commit: `b04c339`
Slice: full LOCOMO conv-26, same-model, cleaned + normalized + query-expansion baseline vs gated append.
Protocol note: LOCOMO state was cleared before baseline and again before gated append because the smoke showed cumulative same-domain re-ingest (`49 -> 98`) without clearing.

## Result

| Metric | Query expansion baseline | Gated append | Delta |
|---|---:|---:|---:|
| Questions | 199 | 199 | — |
| Overall score | 47.49% | 47.49% | +0.00 pp |
| Avg query latency | 3285 ms | 2133 ms | -1152 ms |
| p50 query latency | 2439 ms | 2052 ms | -387 ms |
| p95 query latency | 8473 ms | 3159 ms | -5314 ms |
| Expansion fallback | 57/199 (28.64%) | 61/199 (30.65%) | — |

## Paired buckets

| Bucket | Count |
|---|---:|
| unchanged-correct | 70 |
| same-partial | 7 |
| rescued | 16 |
| unchanged-wrong | 79 |
| harmed-from-fully-correct | 15 |
| partial-changed | 12 |

## Category deltas

| Category | n | Avg delta |
|---|---:|---:|
| adversarial | 47 | -3.19 pp |
| multi-hop | 13 | -7.69 pp |
| single-hop | 32 | +1.56 pp |
| temporal | 37 | -4.05 pp |
| unanswerable | 70 | +5.00 pp |

## Pre-registered decision

Decision rules from §4:

- Accuracy delta must be >= +1.5pp: observed +0.00 pp.
- Harmed-from-fully-correct must be 0: observed 15.
- Per-question latency delta must be <= ~45ms/Q: observed -5.79 ms/Q.
- Slice size must be >= 50: observed 199.

Verdict: **HOLD/REJECT**.

Reason(s): accuracy_delta_below_+1.5pp, harmed_from_fully_correct_nonzero.

Interpretation: gated append is not promoted from this run. The full-slice accuracy delta was effectively zero and the hard safety criterion failed because previously fully-correct baseline answers were harmed.


## Post-run score audit

The exact baseline/gated score match was verified from the raw per-question credits, not just the rounded `overall_score` fields.

| Audit item | Query expansion baseline | Gated append | Delta |
|---|---:|---:|---:|
| Total credit | 94.5 / 199 | 94.5 / 199 | 0.0 |
| Raw percentage | 47.487437185930% | 47.487437185930% | +0.000000 pp |
| Rounded percentage | 47.49% | 47.49% | +0.00 pp |

Score-transition accounting explains the exact cancellation:

| Baseline score -> gated score | Count | Total credit delta |
|---|---:|---:|
| 0 -> 0 | 79 | +0.0 |
| 0 -> 0.5 | 6 | +3.0 |
| 0 -> 1 | 10 | +10.0 |
| 0.5 -> 0 | 6 | -3.0 |
| 0.5 -> 0.5 | 7 | +0.0 |
| 0.5 -> 1 | 6 | +3.0 |
| 1 -> 0 | 11 | -11.0 |
| 1 -> 0.5 | 4 | -2.0 |
| 1 -> 1 | 70 | +0.0 |

Net credit delta: `0.0`, so the `+0.00 pp` headline is exact for this scoring scheme.

## Post-run methodological notes

- The negative decision should remain visible. This was a pre-registered null/negative result: gated append failed the accuracy threshold and failed the hard safety criterion despite favorable latency.
- The latency reversal is a separate hypothesis, not a promotion argument for gated append. The 25Q canary showed gated append slower, while the full 199Q run showed lower average and p95 latency. Before treating this as a real finding, run a separate latency-focused pre-registration that controls arm ordering, warm-up/cache state, fallback behavior, and tail-query composition.
- The category shape is diagnostic: gated append helped single-hop and unanswerable questions but hurt temporal and multi-hop. That is the wrong shape for Memibrium's target use case. If this mechanism is revisited, start by testing whether the gate fires before multi-hop evidence assembly has completed.
- The approximately 30% query-expansion fallback rate is the next LOCOMO quality blocker. This paired comparison remains valid for the pre-registered gated-vs-baseline decision because both arms had similar fallback rates, but future absolute LOCOMO quality work should diagnose expansion/fallback before tuning gated append further.
