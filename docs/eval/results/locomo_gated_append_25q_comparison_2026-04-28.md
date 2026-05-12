# LOCOMO gated append 25Q comparison — 2026-04-28

Target: `docs/eval/results/locomo_conv26_gated_append_25q_2026-04-28.json`
Same-model baseline: `docs/eval/results/locomo_conv26_query_expansion_25q_2026-04-28.json`

## Same-model query-expansion-only 25Q baseline
- Overall / protocol-4: 80.0%
- Questions: 25
- Avg query latency: 3301ms
- Expansion fallback: 0/25 (0.00%)
- Categories: `{"cat-multi-hop": 50.0, "cat-single-hop": 65.0, "cat-temporal": 100.0}`

## Gated append 25Q result
- Overall / protocol-4: 82.0%
- Questions: 25
- Avg query latency: 4048ms
- Expansion fallback: 0/25 (0.00%)
- Categories: `{"cat-multi-hop": 50.0, "cat-single-hop": 70.0, "cat-temporal": 100.0}`

## Primary paired comparison: gated append vs same-model query expansion
- Common questions: 25
- Query-expansion avg on common: 80.0%
- Gated avg on common: 82.0%
- Delta: 2.0 pp
- Latency delta: 747.2ms (baseline 3300.3ms -> gated 4047.6ms)
- Buckets: `{"rescued": 1, "same_partial": 5, "unchanged_correct": 17, "unchanged_wrong": 2}`
- Category deltas:
  - multi-hop: 50.0% -> 50.0% (0.0 pp), n=3, rescued=0, harmed=0, partial=0
  - single-hop: 65.0% -> 70.0% (5.0 pp), n=10, rescued=1, harmed=0, partial=0
  - temporal: 100.0% -> 100.0% (0.0 pp), n=12, rescued=0, harmed=0, partial=0

## Historical comparisons
These compare against older full-run artifacts and are retained for continuity only; the same-model 25Q baseline above is the clean comparison.

### vs query_expansion_full
- Common questions: 25
- Baseline avg on common: 76.0%
- Gated avg on common: 82.0%
- Delta: 6.0 pp
- Latency delta: -3729.9ms (baseline 7777.4ms -> gated 4047.6ms)
- Buckets: `{"partial_changed": 1, "rescued": 3, "same_partial": 5, "unchanged_correct": 15, "unchanged_wrong": 1}`

### vs append_full
- Common questions: 25
- Baseline avg on common: 70.0%
- Gated avg on common: 82.0%
- Delta: 12.0 pp
- Latency delta: 1082.2ms (baseline 2965.4ms -> gated 4047.6ms)
- Buckets: `{"rescued": 4, "same_partial": 5, "unchanged_correct": 14, "unchanged_wrong": 2}`

### vs prefix_rerank_full
- Common questions: 25
- Baseline avg on common: 76.0%
- Gated avg on common: 82.0%
- Delta: 6.0 pp
- Latency delta: 1229.2ms (baseline 2818.3ms -> gated 4047.6ms)
- Buckets: `{"partial_changed": 1, "rescued": 1, "same_partial": 4, "unchanged_correct": 17, "unchanged_wrong": 2}`

### vs rerank_full
- Common questions: 25
- Baseline avg on common: 76.0%
- Gated avg on common: 82.0%
- Delta: 6.0 pp
- Latency delta: 213.9ms (baseline 3833.7ms -> gated 4047.6ms)
- Buckets: `{"rescued": 2, "same_partial": 5, "unchanged_correct": 16, "unchanged_wrong": 2}`

## Interpretation
- The same-model/same-slice query-expansion-only 25Q baseline now exists and is the primary comparison.
- On the first 25 conv-26 questions, gated append is +2.0 pp over same-model query expansion (82.0% vs 80.0%) with no fully-correct answers harmed, but one partial answer regressed to wrong.
- This remains canary-level evidence; run a larger same-model slice or full conv-26 before promoting gated append.
- Next methodologically clean step: run a larger same-model slice (for example first 50 or full 199Q conv-26) before attempting any default/promotion decision.
