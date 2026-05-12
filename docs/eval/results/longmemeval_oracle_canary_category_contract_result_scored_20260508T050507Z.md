# LongMemEval oracle canary category-contract scored run — 2026-05-08

Scope: 25-row oracle canary of preregistered `category_contract_v1`. This is answer-side oracle evidence only; it does not measure Memibrium retrieval quality and is not a full LongMemEval `_s`/`_m` run. No DB/Docker/runtime mutation occurred.

## Run identity

- Run directory: `docs/eval/results/longmemeval_oracle_canary_category_contract_scored_20260508T050507Z/`
- Preregistration: `docs/eval/longmemeval_oracle_canary_category_contract_preregistration_2026-05-08.md`.
- Dataset SHA256: `821a2034d219ab45846873dd14c14f12cfe7776e73527a483f9dac095d38620c`.
- Selection SHA256: `8bd4ae95fbd768866b0af05f2cb91a6bc998d5210221e5201b007bb879ecf6b8`.
- Condition: `category_contract_v1`.
- Answer model: Azure AI Foundry `gpt-4o`, temperature 0.
- Judge model: Azure AI Foundry `gpt-4o` version `2024-11-20`, temperature 0.
- Preflight passed with endpoint metadata only; no secrets printed.

## Scores

- Baseline: `18/25` = `72.00%`.
- Category contract: `21/25` = `84.00%`.
- Net delta: `+3` rows (`+12.00%`).
- Paired outcomes: `{'same_correct': 17, 'same_wrong': 3, 'recovered': 4, 'regressed': 1}`.

## Scores by question type

| question_type | baseline | category_contract_v1 | delta |
|---|---:|---:|---:|
| `knowledge-update` | 4/5 (80%) | 3/5 (60%) | -1 |
| `multi-session` | 4/4 (100%) | 4/4 (100%) | +0 |
| `single-session-assistant` | 4/4 (100%) | 4/4 (100%) | +0 |
| `single-session-preference` | 0/4 (0%) | 3/4 (75%) | +3 |
| `single-session-user` | 4/4 (100%) | 4/4 (100%) | +0 |
| `temporal-reasoning` | 2/4 (50%) | 3/4 (75%) | +1 |

## Paired row outcomes

| # | question_id | question_type | abstention | baseline | category_contract_v1 | paired outcome |
|---:|---|---|---|---:|---:|---|
| 1 | `0ddfec37_abs` | `knowledge-update` | yes | 1 | 1 | `same_correct` |
| 2 | `a1eacc2a` | `knowledge-update` | no | 1 | 1 | `same_correct` |
| 3 | `852ce960` | `knowledge-update` | no | 0 | 0 | `same_wrong` |
| 4 | `eace081b` | `knowledge-update` | no | 1 | 0 | `regressed` |
| 5 | `09ba9854_abs` | `multi-session` | yes | 1 | 1 | `same_correct` |
| 6 | `b3c15d39` | `multi-session` | no | 1 | 1 | `same_correct` |
| 7 | `3c1045c8` | `multi-session` | no | 1 | 1 | `same_correct` |
| 8 | `gpt4_731e37d7` | `multi-session` | no | 1 | 1 | `same_correct` |
| 9 | `dc439ea3` | `single-session-assistant` | no | 1 | 1 | `same_correct` |
| 10 | `58470ed2` | `single-session-assistant` | no | 1 | 1 | `same_correct` |
| 11 | `71a3fd6b` | `single-session-assistant` | no | 1 | 1 | `same_correct` |
| 12 | `fca762bc` | `single-session-assistant` | no | 1 | 1 | `same_correct` |
| 13 | `35a27287` | `single-session-preference` | no | 0 | 0 | `same_wrong` |
| 14 | `06878be2` | `single-session-preference` | no | 0 | 1 | `recovered` |
| 15 | `a89d7624` | `single-session-preference` | no | 0 | 1 | `recovered` |
| 16 | `d6233ab6` | `single-session-preference` | no | 0 | 1 | `recovered` |
| 17 | `29f2956b_abs` | `single-session-user` | yes | 1 | 1 | `same_correct` |
| 18 | `3f1e9474` | `single-session-user` | no | 1 | 1 | `same_correct` |
| 19 | `af8d2e46` | `single-session-user` | no | 1 | 1 | `same_correct` |
| 20 | `6f9b354f` | `single-session-user` | no | 1 | 1 | `same_correct` |
| 21 | `gpt4_fe651585_abs` | `temporal-reasoning` | yes | 1 | 1 | `same_correct` |
| 22 | `0db4c65d` | `temporal-reasoning` | no | 0 | 0 | `same_wrong` |
| 23 | `b9cfe692` | `temporal-reasoning` | no | 1 | 1 | `same_correct` |
| 24 | `gpt4_68e94288` | `temporal-reasoning` | no | 0 | 1 | `recovered` |
| 25 | `45dc21b6` | `knowledge-update` | no | 1 | 1 | `same_correct` |

## Remaining misses / regressions

### 3. `852ce960` — `knowledge-update` — `same_wrong`
- Question: What was the amount I was pre-approved for when I got my mortgage from Wells Fargo?
- Ground truth/rubric: $400,000
- Baseline (wrong): The information provided indicates that you were pre-approved for $350,000 from Wells Fargo when you got your mortgage.
- Category contract (wrong): The evidence indicates that you were pre-approved for $350,000 from Wells Fargo for your mortgage.

### 4. `eace081b` — `knowledge-update` — `regressed`
- Question: Where am I planning to stay for my birthday trip to Hawaii?
- Ground truth/rubric: Oahu
- Baseline (correct): You are planning to stay on Oahu for your birthday trip to Hawaii.
- Category contract (wrong): The information provided is not enough.

### 13. `35a27287` — `single-session-preference` — `same_wrong`
- Question: Can you recommend some interesting cultural events happening around me this weekend?
- Ground truth/rubric: The user would prefer responses that suggest cultural events where they can practice their language skills, particularly Spanish and French. They would also appreciate if the event has a focus on language learning resources. They would not prefer events that do not provide opportunities for language practice or cultural exchange.
- Baseline (wrong): The information provided is not enough to recommend specific cultural events happening around you this weekend.
- Category contract (wrong): The information provided does not include specific cultural events happening this weekend. However, based on your interest in language diversity and cultural exchange, I recommend exploring platforms like **Eventbrite**, **Meetup**, or local cultural centers and embassies for events that align with your preferences. Look for language exchange meetups, international festivals, or cultural celebrations that focus on French and Spanish languages. You might also enjoy checking out local universities or language schools, as they often host relevant events.

### 22. `0db4c65d` — `temporal-reasoning` — `same_wrong`
- Question: How many days had passed since I finished reading 'The Seven Husbands of Evelyn Hugo' when I attended the book reading event at the local library, where the author of 'The Silent Patient' is discussing her latest thriller novel?
- Ground truth/rubric: 18 days. 19 days (including the last day) is also acceptable.
- Baseline (wrong): The information provided is not enough to determine how many days had passed between finishing "The Seven Husbands of Evelyn Hugo" and attending the book reading event.
- Category contract (wrong): The information provided is not enough to determine how many days had passed between finishing "The Seven Husbands of Evelyn Hugo" and attending the book reading event.

## Artifact hashes

| file | bytes | sha256 |
|---|---:|---|
| `longmemeval_oracle_canary_baseline_eval_results.jsonl` | 6343 | `8b956605b79852e86e67d63eee281cb1888e5509f1ec7af6cce7252c923d1f0c` |
| `longmemeval_oracle_canary_baseline_predictions.jsonl` | 3793 | `870de9acacee4c717200f3c8bc32c575d3e6d8e856a558e89f6b4278f27f8c7e` |
| `longmemeval_oracle_canary_scored_metadata.json` | 1262937 | `c8e298c96f2d671b10071f43e521e2af7c4bb2702deb2e3550ed0779cdb8ff9a` |
| `longmemeval_oracle_canary_scored_summary.json` | 1848 | `8d653842b0ea0dd8f716b1b4cfcb0adeabbb82f9cf047c51928549eb2e0633e2` |
| `longmemeval_oracle_canary_treatment_eval_results.jsonl` | 9706 | `bfdf74d37f3b0cffe547179a8e36d2943e2fee1d9b6bd7e2c52089d415590551` |
| `longmemeval_oracle_canary_treatment_predictions.jsonl` | 7156 | `2bca77cac198c1a991ed11e7d5dff0d908f42701e3d885253fda3b52621dff0b` |

## Interpretation

- `category_contract_v1` passed the preregistered strong go gate: `21/25` is >= `18/25`, and no category drops below baseline by more than one row.
- Mechanistic target also moved: preference rows improved from `0/4` to `3/4`, while knowledge-update ended `3/5`, below the desired `4/5` mechanism gate.
- The only observed regression versus same-run baseline is `eace081b` (`Oahu`) in knowledge-update; remaining shared misses are one stale mortgage update, one preference recommendation, and one temporal-linking row.
- Treat as a diagnostic oracle canary, not retrieval/product benchmark evidence. Next step should be artifact-only failure review or a preregistered robustness/replicate plan before promoting the prompt contract.

## Guardrails observed

- No full LongMemEval `_s` / `_m` run.
- No retrieval ingestion.
- No DB/Docker/runtime mutation.
- No direct `/mcp/tools` inspection.
- Secrets were not printed or stored; artifacts contain endpoint metadata only.

