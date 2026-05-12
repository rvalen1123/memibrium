# LOCOMO Opt-In Retrieval Modes Summary — 2026-04-26

## PR framing

This work adds opt-in retrieval modes and includes the LOCOMO evaluation that determined they should not become defaults.

Default experimental quality baseline remains the query-expansion condition. Runtime query expansion is still opt-in by flag/env; context rerank and append-only context expansion are also opt-in and available for controlled experiments only.

## What changed

Source / implementation:

- `hybrid_retrieval.py`
  - Reconstructed/validated hybrid retrieval path for ruvector/pgvector vector casts.
  - Applies domain/state filters consistently in semantic and lexical paths.
- `benchmark_scripts/locomo_bench_v2.py`
  - Adds opt-in context rerank mode.
  - Adds opt-in append-only context expansion mode.
  - Adds condition-specific result suffixes/output paths and payload metadata.
  - Rejects simultaneous context rerank and append-only context expansion.
- Tests:
  - `test_hybrid_retrieval_ruvector.py`
  - `test_locomo_query_expansion.py`
- Audit script:
  - `scripts/audit_locomo_rerank_harms.py`

## Verdict first

Do not promote either new retrieval mode to default.

| Condition | Full 5-cat | Protocol 4-cat | Avg query latency | Verdict |
|---|---:|---:|---:|---|
| Query expansion canary | 68.09% | 79.93% | 8026ms | Keep as quality baseline |
| Pure lexical rerank | 59.30% | 70.39% | 3979ms | Not promotable |
| Prefix-preserving rerank | 60.55% | 72.37% | 3810ms | Not promotable |
| Append-only context expansion | 61.81% | 74.01% | 3073ms | Faster/safer than rerank, still not promotable |

## Key artifacts

Committed summary artifacts:

- `docs/eval/results/locomo_retrieval_modes_summary_2026-04-26.md`
- `docs/eval/results/locomo_append_context_analysis_2026-04-26.md`
- `docs/eval/results/locomo_prefix_rerank_analysis_2026-04-26.md`
- `docs/eval/results/locomo_rerank_harmed_rescued_analysis_2026-04-26.md`
- `docs/eval/results/locomo_prefix_rerank_harm_audit_2026-04-26.md`
- `docs/eval/results/locomo_append_context_comparison_2026-04-26.json`
- `docs/eval/results/locomo_prefix_rerank_comparison_2026-04-26.json`
- `docs/eval/results/locomo_query_expansion_overlap_2026-04-24.json`
- `docs/eval/results/locomo_conv26_query_expansion_2026-04-24.json`
- `docs/eval/results/locomo_conv26_query_expansion_reranked_2026-04-26.json`
- `docs/eval/results/locomo_conv26_query_expansion_prefix_rerank_2026-04-26.json`
- `docs/eval/results/locomo_conv26_query_expansion_appended_2026-04-26.json`

Not committed intentionally:

- `.hermes/` agent state.
- Large full 1,986-question raw benchmark JSONs for every run.
- Raw/interrupted/superseded artifacts such as `locomo_conv26_query_expansion_reranked_raw_2026-04-26.json`.

## Rerank harm audit conclusion

Rerank harm was caused by context replacement/top-k budget displacement, not answer-model variance.

Audit results:

- Harmed cases audited: 23
- Cases with context drops: 23
- Cases with equivalent context IDs but worse answer: 0
- Prefix preservation invariant failures: 0
- Cases where answer became IDK: 10
- Mean dropped original-context memories: 4.8

Primary mechanisms:

- `evidence_dropped_by_context_budget`: 13
- `evidence_loss_or_demoted_to_idk`: 10

## Append-only conclusion

Append-only context expansion recovered some quality relative to replacement rerank variants and was fastest, but still lost too much quality vs query expansion.

Paired comparison vs query expansion:

- Common questions: 199
- Rescued: 10
- Harmed: 21
- Unchanged correct: 95
- Unchanged wrong: 36
- Partial changed: 14
- Same partial: 23

Category deltas vs query expansion:

- cat-5/adversarial: -7.45 pp
- multi-hop: -11.54 pp
- single-hop: +4.69 pp
- temporal: 0.00 pp
- unanswerable: -12.86 pp

Interpretation: preserving original evidence is necessary but not sufficient. Extra context/noise can still hurt the answer model.

## Normalization measurement status

The original larger goal was to measure date-normalization impact on temporal accuracy. That full normalization measurement did not complete cleanly because a later benchmark attempt hung during integration work.

This branch ships the completed retrieval-mode implementation/evaluation work and defers normalization measurement to a follow-up.

## Next experiment

Start signals-only gated append-only context expansion:

- Require high lexical overlap for append extras.
- Require weak/low-confidence base context before appending.
- Do not use benchmark labels as production gates.
- Avoid question-classification gates initially; add them only if signals-only is insufficient and the latency cost is justified.
- Run conv-26 canary before any broader benchmark.
- Clean `locomo-%` DB data after every canary/audit.
