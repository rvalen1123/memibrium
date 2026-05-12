# LOCOMO Append-Only Context Expansion Canary

Generated: 2026-04-26T14:01:29.438802+00:00

## Condition
`--cleaned --normalize-dates --query-expansion --append-context-expansion --max-convs 1`

Policy: preserve original top-15 answer context exactly, then append up to 5 non-duplicate lexical/ranked extra memories below it. No original evidence is displaced.

## Headline scores

| Condition | Full 5-cat | Protocol 4-cat | Avg query latency | Fallbacks |
|---|---:|---:|---:|---:|
| Query expansion baseline | 68.09% | 79.93% | 8026ms | 0 |
| Pure lexical rerank | 59.30% | 70.39% | 3979ms | 0 |
| Prefix-preserving rerank | 60.55% | 72.37% | 3810ms | 0 |
| Append-only context expansion | 61.81% | 74.01% | 3073ms | 0 |

## Paired movement vs query expansion baseline

- common: 199
- rescued: 10
- harmed: 21
- unchanged_correct: 95
- unchanged_wrong: 36
- partial_changed: 14
- same_partial: 23

Category deltas vs query expansion baseline:
- 5: -7.45 pp
- multi-hop: -11.54 pp
- single-hop: +4.69 pp
- temporal: +0.00 pp
- unanswerable: -12.86 pp

## Paired movement vs rerank variants

Vs pure lexical rerank: rescued 14, harmed 10, protocol delta +3.62 pp
Vs prefix-preserving rerank: rescued 14, harmed 13, protocol delta +1.64 pp

## Interpretation

Append-only context expansion is faster than the query-expansion baseline (3073ms vs 8026ms), and safer than replacement rerank variants, but it still underperforms the query-expansion quality baseline by -5.92 pp protocol / -6.28 pp full.

Decision: do not promote append-only context expansion yet. It is useful as a safer canary relative to reranking, but the answer model appears sensitive to extra context/noise even when original evidence is preserved. Next precision work should test selective append gating or leave query expansion as the quality baseline.

## Artifacts

- Append result: `/home/zaddy/src/Memibrium/docs/eval/results/locomo_conv26_query_expansion_appended_2026-04-26.json`
- Comparison JSON: `/home/zaddy/src/Memibrium/docs/eval/results/locomo_append_context_comparison_2026-04-26.json`
