# LOCOMO Conv-26 Prefix-Preserving Rerank Canary — 2026-04-26

## Condition

Command:

```bash
python3 benchmark_scripts/locomo_bench_v2.py --cleaned --normalize-dates --query-expansion --context-rerank --max-convs 1
```

Implementation under test: opt-in context rerank with original retriever prefix preservation (`RERANK_PRESERVE_PREFIX_K = 2`) plus lexical fill for remaining answer-context slots.

Metadata verified in artifact:

```json
{
  "cleaned": true,
  "normalize_dates": true,
  "query_expansion": true,
  "context_rerank": true
}
```

Expansion fallback: `0/199` (`0.00%`).

## Artifact files

- Prefix-preserving rerank canary:
  - `docs/eval/results/locomo_conv26_query_expansion_prefix_rerank_2026-04-26.json`
- Machine-readable comparison:
  - `docs/eval/results/locomo_prefix_rerank_comparison_2026-04-26.json`

## Important run hygiene note

A first attempt was interrupted at 120/199 questions during process inspection. Before rerunning, LOCOMO domains were cleared from the DB:

- `temporal_expressions`: 797 rows deleted
- `memories`: 797 rows deleted
- verification query returned 0 `locomo-%` rows

The final artifact above is from the clean rerun after that cleanup.

## Headline result

Prefix-preserving rerank improved slightly over pure lexical rerank, but did **not** recover most of the quality lost versus the prior query-expansion canary.

| Condition | Full 5-cat | Protocol 4-cat | Avg query latency |
|---|---:|---:|---:|
| Query expansion prior canary | 68.09% | 79.93% | 8026ms |
| Pure lexical rerank | 59.30% | 70.39% | 3979ms |
| Prefix-preserving rerank | 60.55% | 72.37% | 3810ms |

## Category scores

| Category | Query expansion | Pure lexical rerank | Prefix-preserving rerank |
|---|---:|---:|---:|
| adversarial / cat-5 | 29.79% | 23.40% | 22.34% |
| multi-hop | 50.00% | 34.62% | 38.46% |
| single-hop | 64.06% | 64.06% | 64.06% |
| temporal | 86.49% | 87.84% | 86.49% |
| unanswerable | 89.29% | 70.71% | 75.00% |

## Paired comparison: query expansion -> prefix-preserving rerank

Common paired questions: 199

| Class | Count |
|---|---:|
| rescued | 11 |
| harmed | 23 |
| unchanged correct | 93 |
| unchanged wrong | 35 |
| partial changed | 17 |
| same partial | 20 |

Category deltas versus query expansion:

| Category | Delta |
|---|---:|
| adversarial / cat-5 | -7.45 pp |
| multi-hop | -11.54 pp |
| single-hop | 0.00 pp |
| temporal | 0.00 pp |
| unanswerable | -14.29 pp |

I-don't-know / insufficient-answer rate increased:

- query expansion: 13.57%
- prefix-preserving rerank: 23.12%

## Paired comparison: pure lexical rerank -> prefix-preserving rerank

Common paired questions: 199

| Class | Count |
|---|---:|
| rescued | 13 |
| harmed | 10 |
| unchanged correct | 91 |
| unchanged wrong | 50 |
| partial changed | 15 |
| same partial | 20 |

Category deltas versus pure lexical rerank:

| Category | Delta |
|---|---:|
| adversarial / cat-5 | -1.06 pp |
| multi-hop | +3.85 pp |
| single-hop | 0.00 pp |
| temporal | -1.35 pp |
| unanswerable | +4.29 pp |

## Interpretation

Prefix preservation is directionally better than pure lexical rerank for multi-hop and unanswerable, but the recovery is too small:

- 4-cat score only recovers `+1.98 pp` of the `-9.54 pp` pure-rerank loss.
- Full 5-cat score only recovers `+1.25 pp` of the `-8.79 pp` pure-rerank loss.
- Harm remains concentrated in multi-hop and unanswerable.
- Increased I-don't-know rate suggests the reranked answer context is still losing or demoting evidence needed for answerability/composition.

Decision: do **not** promote prefix-preserving lexical rerank as currently implemented. Keep context rerank opt-in.

## Recommended next step

Stop blanket lexical rerank experiments for now. The next useful pass should be diagnostic, not another broad reranker:

1. Inspect the 23 query-expansion-correct -> prefix-rerank-harmed questions.
2. For each, compare the answer-context memories before vs after rerank.
3. Classify harm mechanism:
   - lost original evidence due to top-k budget overflow
   - evidence preserved but moved too low
   - negative/abstention evidence demoted
   - answer-model variance despite equivalent context
4. Only then choose a narrower policy, likely one of:
   - disable rerank for unanswerable/multi-hop-like queries
   - rerank only temporal/single-hop candidates
   - use lexical rerank as diversity fill, not ordering
   - increase preserve prefix from 2 only if evidence-loss audit supports it
