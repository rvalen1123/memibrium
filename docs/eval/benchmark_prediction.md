# Benchmark Prediction: Query Expansion Intervention

## Intervention
- Add recall-time multi-query fusion in `benchmark_scripts/locomo_bench_v2.py`.
- For each question, generate up to 3 diverse reformulations focused on entities, time, and relationships.
- Run one `recall` call per query, fuse results by memory id, deduplicate, and cap the answer context at 15 memories.
- This run is intentionally stacked on top of the already-validated date normalization intervention.

## Baseline anchor for this intervention
Use the normalized benchmark as the comparison point, not the original pre-normalization run.

- Normalized temporal: **70.87%**
- Normalized full overall: **63.62%**
- Normalized protocol-comparable 4-category overall: **75.04%**

This benchmark measures the marginal contribution of query expansion on top of date normalization.

## Main prediction
- Expected protocol-comparable **4-category overall: 78–80%**
- Point estimate: **79%**
- Predicted delta from normalized-only 4-category baseline (**75.04%**): **+3 to +5 pp**
- Updated expected mechanism: broader retrieval coverage, with biggest gains on **temporal** and **open-domain** rather than specifically on multi-hop

## Category-level directional expectations
- temporal: **~+5 pp** (full-run point expectation: ~76%)
- open-domain / unanswerable: **~+4 pp** (full-run point expectation: ~87%)
- single-hop: **~+1 to +2 pp** (full-run point expectation: ~66%)
- multi-hop: **~+3 to +4 pp** (full-run point expectation: ~55%)

## Mechanism note
The clean conv-26 A/B canary suggests query expansion is not primarily rescuing multi-step reasoning. The observed pattern is more consistent with **broader semantic coverage across retrieval**, especially for temporally keyed and wider open-domain questions.
Do not frame this intervention as "fixing multi-hop" unless the full-run evidence shows that clearly.

## Operational note
`USE_QUERY_EXPANSION=1` is currently an **evaluation-only** setting, not a production default.
In the conv-26 A/B canary it increased average query latency from ~2.6s to ~8.0s. That is acceptable for benchmark exploration, but not for live user-facing recall.

## Expansion fallback behavior rule
Expansion failures should fail open, not fail closed.

Rule:
- If query expansion errors or returns unusable output, fall back to `[question]` only.
- Count each fallback in `expand_query.fail_count`.
- Report fallback count and fallback rate at end of run and in saved results.

Interpretation threshold:
- **<5% fallback rate**: treat as noise; result is still valid
- **>5% fallback rate**: signal is contaminated; fix and rerun before interpreting as the expansion condition

Rationale:
- Answer/judge failures create false-zero scores and must fail closed.
- Expansion failures only reduce the number of retrieval passes, producing degraded but still valid retrieval.
- The real methodological risk is mixing expanded and non-expanded behavior across too much of the run.

## Answer-path content filter criterion
The answer path is methodologically distinct from the judge path.

Rule:
- Do not sanitize retrieved context or question text to work around answer-path filtering, because that changes the evidence used to answer.
- First-line mitigation is a neutral analytical answer system prompt.
- If answer-path `content_filter` still occurs and must be fail-opened as `"I don't know"`, count those events explicitly.

Validity threshold:
- **<=3% answer-path content_filter rate**: run may be usable with caveat
- **>3% answer-path content_filter rate**: benchmark is contaminated; fix deployment/filter settings or prompting and rerun

## Interpretation bands

| 4-cat overall | Read |
|---|---|
| 78–80% | Prediction validated. |
| 75–78% | Marginal gain. Expansion is doing some work; consider wider candidate set or answer-model bump. |
| <75% | Expansion is not helping. Check fallback rate, paraphrase diversity, and whether fusion/cap is suppressing useful candidates. |
| >80% | Stronger than expected. Check whether CE reranking is effectively double-dipping across similar paraphrases. |

## Canary before full run
Run a 1-conversation canary first:

```bash
python3 benchmark_scripts/locomo_bench_v2.py --max-convs 1 --normalize-dates
```

Purpose:
- catch integration bugs in the expansion path
- confirm fallback rate is sane
- detect pathological latency or collapsed scoring before spending ~2 hours on the full run
- surface answer-path content-filter failures before the main run

Canary success criteria:
- run completes successfully
- results look non-degenerate (not all zeros, not obvious failure)
- expansion fallback rate remains below 5%
- answer-path content-filter rate remains at or below 3%
- latency remains within a plausible expansion-cost envelope

If canary is sane, proceed directly to full run.

## Pre-registered before run
Date: 2026-04-24
Condition: date normalization + recall-time query expansion
Baseline anchor: normalized run (**75.04% 4-cat**, **70.87% temporal**)
Predicted 4-category overall: **78–80%** (point estimate **79%**)
Expansion fallback validity threshold: **<=5%**
Answer-path content-filter validity threshold: **<=3%**

## Outcome
- Actual 4-category overall: **77.48%**
- Actual full 5-category overall: **65.06%**
- Actual fallback rate: **1/1986 = 0.05%**
- Verdict: **directional confirmation, magnitude miss**
- Pre-registered range miss: **0.52 pp below lower bound**

## Outcome notes
- The intervention helped, but less than predicted at full-run scale.
- The main miss came from open-domain gain not generalizing from conv-26.
- Strongest full-run gains were temporal and single-hop, not multi-hop.
- `USE_QUERY_EXPANSION=1` remains benchmark-only due to latency cost (~9s/query).
