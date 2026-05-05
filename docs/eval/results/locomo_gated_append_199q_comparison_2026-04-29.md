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


## Post-run churn interpretation

The zero aggregate delta should not be read as "no effect." Gated append changed a material minority of questions and the changes canceled exactly:

| Churn item | Count / credit |
|---|---:|
| Changed questions | 43 / 199 (21.61%) |
| Improved questions | 22 |
| Degraded questions | 21 |
| Unchanged questions | 156 |
| Improved total credit | +16.0 |
| Degraded total credit | -16.0 |
| Net total credit | 0.0 |

Interpretation: gated append was active but not aligned with correctness. This is methodologically different from a no-op/null mechanism; the gate perturbed answers on ~22% of the slice without improving net accuracy.

### Diagnostic full-to-zero failures

These 11 cases are the highest-signal failure set for any future revisit of gated context mechanisms: the query-expansion baseline received full credit, while gated append received zero.

| # | Category | Question | Ground truth | Baseline answer | Gated answer |
|---:|---|---|---|---|---|
| 1 | adversarial | Who is Caroline a fan of in terms of modern music? | Ed Sheeran | **Ed Sheeran ("Perfect").**  This is based on the conversation from 28 August 2023, where Melanie mentions being a fan of Ed Sheeran's "Perfect" as modern music, and Caroline responds positively without contradicting it.… | **Sara Bareilles and Ed Sheeran.**  From the conversation on 28 August 2023, Caroline said "Brave" by Sara Bareilles has deep personal meaning for her. Melanie mentioned being a fan of Ed Sheeran's "Perfect" in the same … |
| 2 | multi-hop | Would Melanie go on another roadtrip soon? | Likely no; since this one went badly | **No**, Melanie would not go on another roadtrip soon. The October 2023 roadtrip ended in a scary accident involving her son, which left the family traumatized. In the conversation right after, she emphasized cherishing … | **Yes**, Melanie would likely go on another roadtrip soon.  She enjoys family camping and nature trips (e.g., Grand Canyon in October 2023, multiple camping outings in 2023), views them positively for recharging and bond… |
| 3 | single-hop | What book did Melanie read from Caroline's suggestion? | "Becoming Nicole" | **"Becoming Nicole" by Amy Ellis Nutt.**  In the conversation on 12 July 2023, Caroline recommended this book to Melanie, describing it as an inspiring true story about a trans girl and her family. Later, on 13 October 2… | **I don't know.**  The provided conversation transcripts mention Caroline recommending a book that Melanie read in September 2023 after her pottery injury, but they do not specify the title. |
| 4 | single-hop | What instruments does Melanie play? | clarinet and violin | **Clarinet and violin.** | **Clarinet.** |
| 5 | single-hop | What subject have Caroline and Melanie both painted? | Sunsets | **Sunsets.**  Both have created paintings inspired by sunsets: Caroline painted one after visiting the beach (week of 18 August 2023), and Melanie painted one inspired by sunsets (week of 6 October 2023). This is support… | **Horses.**  Both have painted horses: Caroline created a horse painting for her August 2023 LGBTQ art show (inspired by an LGBTQ center, capturing unity and strength), and Melanie painted a horse, sharing a photo of it … |
| 6 | temporal | When did Caroline attend a pride parade in August? | The Friday before 14 August 2023 | **11 August 2023**  From the first retrieved memory (session 3, 14 August 2023), Caroline explicitly states she attended a pride parade on 11 August 2023. No other pride parades in August are mentioned across the provide… | **I don't know.**  No context mentions Caroline attending a pride parade in August 2023. The pride parades referenced occurred in June 2023, 11 August 2023, and the weekend of 15 July 2023. |
| 7 | temporal | When did Caroline go biking with friends? | The weekend before 13 September 2023 | **Weekend of 09 September 2023.**  This is from the conversation on 13 September 2023 (session 8), where Caroline says: "I had a wicked day out with the gang the weekend of 09 September 2023 - we went biking..." (The lat… | **the weekend of 09 September 2023**  This is from the conversation on 13 September 2023 (session 8, turns 0-9), where Caroline says: "I had a wicked day out with the gang the weekend of 09 September 2023 - we went bikin… |
| 8 | temporal | When did Melanie go camping in June? | The week before 27 June 2023 | **20 June 2023**  From the first memory (session 14, 27 June 2023), Melanie states she went camping with her family "the week of 20 June 2023". No other June camping trip is mentioned. | **June 2023 (week of 20 June 2023 and weekend of 8 July 2023, overlapping into late June).**  From the memories: - Session 14 (27 June 2023): Melanie mentions taking her family camping "the week of 20 June 2023." - Sessi… |
| 9 | unanswerable | What did Caroline find in her neighborhood during her walk? | a rainbow sidewalk | **A cool rainbow sidewalk for Pride Month.** | **I don't know.**  The provided conversation transcripts contain no mention of Caroline taking a walk in her neighborhood or finding anything during one. |
| 10 | unanswerable | What workshop did Caroline attend recently? | LGBTQ+ counseling workshop | **LGBTQ+ counseling workshop on 23 June 2023.** | **I don't know.**  The provided context mentions Caroline attending an LGBTQ support group (May 2023), pride parade (June 2023), transgender conference (July 2023), LGBTQ conference (July 2023), council meeting for adopt… |
| 11 | unanswerable | Whose birthday did Melanie celebrate recently? | Melanie's daughter | **Melanie's daughter's birthday.**  This is based on the conversation from 14 August 2023, where Melanie says: "13 August 2023 was amazing! We celebrated my daughter's birthday with a concert..." | **I don't know.**  The provided conversation transcripts mention Melanie celebrating family moments, her wedding (5 years prior), camping trips, and art projects, but none reference a recent birthday celebration for hers… |

## Post-run methodological notes

- The negative decision should remain visible. This was a pre-registered null/negative result: gated append failed the accuracy threshold and failed the hard safety criterion despite favorable latency.
- The latency reversal is a separate hypothesis, not a promotion argument for gated append. The 25Q canary showed gated append slower, while the full 199Q run showed lower average and p95 latency. Before treating this as a real finding, run a separate latency-focused pre-registration that controls arm ordering, warm-up/cache state, fallback behavior, and tail-query composition.
- The category shape is diagnostic: gated append helped single-hop and unanswerable questions but hurt temporal and multi-hop. That is the wrong shape for Memibrium's target use case. If this mechanism is revisited, start by testing whether the gate fires before multi-hop evidence assembly has completed.
- The approximately 30% query-expansion fallback rate is the next LOCOMO quality blocker. This paired comparison remains valid for the pre-registered gated-vs-baseline decision because both arms had similar fallback rates, but future absolute LOCOMO quality work should diagnose expansion/fallback before tuning gated append further.
