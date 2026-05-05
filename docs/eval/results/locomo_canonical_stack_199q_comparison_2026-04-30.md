# LOCOMO Canonical Stack 199Q Comparison — 2026-04-30
## Verdict
**FAILED REPRODUCTION**
- Threshold driver: score outside ±5pp: 62.06% vs 68.09% (delta -6.03pp)
- Locked rules: strong = score within ±2pp of 68.09 and fallback ≤2/199; partial = score within ±5pp and fallback ≤5/199; failed = outside ±5pp or fallback >5/199.
- Latency is recorded below but is out of scope as a reproduction gate.

## Score summary
| Artifact | Score | Fallback | Avg query latency | Questions |
|---|---:|---:|---:|---:|
| 04-24 reference | 68.09% | 0/199 | 8026ms | 199 |
| 04-30 canonical forced | 62.06% | 0/199 | 4212ms | 199 |
| Delta | -6.03pp | +0 | -3814ms | — |

## Inference stack identity
- endpoint: `https://sector-7.services.ai.azure.com/models`
- answer_model: `gpt-4.1-mini`
- judge_model: `gpt-4.1-mini`
- query_expansion_model: `gpt-4.1-mini`
- azure_chat_deployment: `gpt-4.1-mini`
- azure_openai_deployment: `gpt-4.1-mini`
- openai_base_url: `<unset>`
- azure_openai_endpoint: `<unset>`
- temperature: `0`
- decoding_params: `{'temperature': 0, 'max_tokens': 'path-dependent in locomo_bench_v2.py'}`
- run_commit: `d3925d52eb09962c89298161b11b3f1f0d960c33`
- branch: `query-expansion`

## Current condition metadata
- cleaned: `True`
- normalize_dates: `True`
- query_expansion: `True`
- context_rerank: `False`
- append_context_expansion: `False`
- gated_append_context_expansion: `False`
- no_expansion_arm_b: `False`

## Category comparison
| Category | Reference | Current | Delta | Count |
|---|---:|---:|---:|---:|
| adversarial | 29.79% | 24.47% | -5.32pp | 47 |
| multi-hop | 50.00% | 42.31% | -7.69pp | 13 |
| single-hop | 64.06% | 65.62% | +1.56pp | 32 |
| temporal | 86.49% | 82.43% | -4.05pp | 37 |
| unanswerable | 89.29% | 78.57% | -10.71pp | 70 |

## Paired overlap
- rescued: 14
- harmed: 23
- unchanged_correct: 93
- unchanged_wrong: 32
- partial_changed: 18
- same_partial: 19

## Hygiene / provenance
- hygiene_status: `PASS`
- launch_time_utc: `2026-04-30T07:30:00Z`
- repo_path: `/home/zaddy/src/Memibrium`
- branch: `query-expansion`
- head: `d3925d52eb09962c89298161b11b3f1f0d960c33`
- origin_head: `d3925d52eb09962c89298161b11b3f1f0d960c33`
- working_tree_short_status_count: `0`
- container_toggles: `ENABLE_BACKGROUND_SCORING=false;ENABLE_CONTRADICTION_DETECTION=false;ENABLE_HIERARCHY_PROCESSING=false`
- locomo_db_count: `0`
- tests: `test_locomo_query_expansion 51 OK; test_hybrid_retrieval_ruvector 6 OK; test_temporal_memory 10 OK`

## Notes
- Decision rules applied verbatim from locked pre-registration; latency recorded only as observation.
- Initial launch without .env credential hydration failed preflight with Azure 401 before ingest; no benchmark data was produced. Formal run sourced .env for credentials while preserving locked endpoint/model overrides.
- Run started with unrelated non-LOCOMO starting memories=19 after LOCOMO-domain count verified 0; benchmark domains remained locomo-specific.
- Paired comparison normalizes reference category label `5` and current label `adversarial` to the same adversarial bucket.

## Artifacts
- Current JSON: `docs/eval/results/locomo_conv26_canonical_stack_199q_2026-04-30.json`
- Current log: `docs/eval/results/locomo_conv26_canonical_stack_199q_2026-04-30.log`
- Comparison JSON: `docs/eval/results/locomo_canonical_stack_199q_comparison_2026-04-30.json`
