# LOCOMO one-last-go full-domain-context spike (20260503T054413Z)

## Intent
Give the conv-26 corrected slice one final opt-in try by bypassing retrieval/context selection and feeding the answer model the full ingested conversation-domain context in chronological chunk order. This is a spike, not a canonical baseline or Phase C authorization.

## Condition
- Command: `python3 benchmark_scripts/locomo_bench_v2.py --max-convs 1 --query-expansion --full-domain-context`
- Query expansion: on
- Full-domain context: on
- Context rerank / append / legacy: off

## Result
- Valid shape: True
- Full 5-cat overall: 69.1%
- Protocol 4-cat overall: 77.63%
- Category scores: `{"cat-adversarial": 41.49, "cat-multi-hop": 38.46, "cat-single-hop": 64.06, "cat-temporal": 79.73, "cat-unanswerable": 90.0}`
- Mean n_memories: 49
- n_memories distribution: `{"49": 199}`
- Query-expansion fallback count: 0

## Interpretation boundary
If this improves materially, the ceiling is mostly context selection/retrieval under the LOCOMO harness. If it does not, LOCOMO is not worth further score-chasing here. Phase C remains blocked either way.

## Artifacts
- Raw: `/home/zaddy/src/Memibrium/docs/eval/results/locomo_last_go_full_domain_context_raw_20260503T054413Z.json`
- Summary: `/home/zaddy/src/Memibrium/docs/eval/results/locomo_last_go_full_domain_context_summary_20260503T054413Z.json`
- Log: `/home/zaddy/src/Memibrium/docs/eval/results/locomo_last_go_full_domain_context_log_20260503T054413Z.txt`
