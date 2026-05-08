# LongMemEval category-contract preparation — 20260508T050000Z

Scope: preparation-only artifact for preregistered `category_contract_v1` prompt condition. No answer generation, no judge calls, no benchmark score, no DB/Docker/runtime mutation.

Files:

- `longmemeval_oracle_canary_baseline_placeholder.jsonl` — upstream-shaped baseline placeholder predictions with empty hypotheses.
- `longmemeval_oracle_canary_category_contract_v1_placeholder.jsonl` — upstream-shaped category-contract placeholder predictions with empty hypotheses.
- `longmemeval_oracle_canary_preparation_metadata.json` — selection proof plus baseline/category prompt metadata.

Verification summary:

- mode: `preparation_only_no_answer_generation`
- condition: `category_contract_v1`
- rows: `25`
- baseline/category evidence hash identity: `25/25`
- preference prompts with recommender/advisor directive: `4/4`
- knowledge-update prompts with latest-matching-fact and absent-entity-abstention directive: `5/5`

This artifact is not a scored run and should not be compared as a benchmark result.
