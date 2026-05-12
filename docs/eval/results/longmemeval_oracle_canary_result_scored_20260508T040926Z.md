# LongMemEval oracle canary scored run — 2026-05-08

Scope: first 25-row oracle canary on the preregistered LongMemEval cleaned oracle slice. This run used oracle evidence only; it does not measure Memibrium retrieval quality and is not a full LongMemEval `_s` or `_m` run. No DB/Docker/runtime mutation occurred.

## Run identity

- Run directory: `docs/eval/results/longmemeval_oracle_canary_scored_20260508T040926Z/`
- Dataset: `longmemeval_oracle.json` from `xiaowu0162/longmemeval-cleaned` revision `98d7416c24c778c2fee6e6f3006e7a073259d48f`.
- Dataset SHA256: `821a2034d219ab45846873dd14c14f12cfe7776e73527a483f9dac095d38620c`.
- Selection artifact: `docs/eval/results/longmemeval_oracle_canary_25_selection_20260508.json`.
- Selection artifact SHA256: `8bd4ae95fbd768866b0af05f2cb91a6bc998d5210221e5201b007bb879ecf6b8`.
- Answer model: Azure AI Foundry `gpt-4o`, temperature 0.
- Judge model: Azure AI Foundry `gpt-4o` version `2024-11-20`, temperature 0.
- Judge prompt: copied verbatim from upstream `get_anscheck_prompt()` at LongMemEval commit `982fbd7045c9977e9119b5424cab0d7790d19413`.
- Explicitly authorized model calls: yes, via user “okay proceed”.

## Scores

- Baseline: `18/25` = `72.00%`.
- Treatment: `14/25` = `56.00%`.
- Net treatment delta: `-4` correct rows (`-16.00%`).
- Paired outcome counts: `{'regressed': 5, 'same_correct': 13, 'same_wrong': 6, 'recovered': 1}`.

## Scores by question type

| question_type | baseline | treatment | delta |
|---|---:|---:|---:|
| `knowledge-update` | 4/5 (80%) | 2/5 (40%) | -2 |
| `multi-session` | 4/4 (100%) | 2/4 (50%) | -2 |
| `single-session-assistant` | 4/4 (100%) | 4/4 (100%) | +0 |
| `single-session-preference` | 0/4 (0%) | 0/4 (0%) | +0 |
| `single-session-user` | 4/4 (100%) | 4/4 (100%) | +0 |
| `temporal-reasoning` | 2/4 (50%) | 2/4 (50%) | +0 |

## Paired row outcomes

| # | question_id | question_type | abstention | baseline | treatment | paired outcome |
|---:|---|---|---|---:|---:|---|
| 1 | `0ddfec37_abs` | `knowledge-update` | yes | 1 | 0 | `regressed` |
| 2 | `a1eacc2a` | `knowledge-update` | no | 1 | 1 | `same_correct` |
| 3 | `852ce960` | `knowledge-update` | no | 0 | 0 | `same_wrong` |
| 4 | `eace081b` | `knowledge-update` | no | 1 | 0 | `regressed` |
| 5 | `09ba9854_abs` | `multi-session` | yes | 1 | 1 | `same_correct` |
| 6 | `b3c15d39` | `multi-session` | no | 1 | 1 | `same_correct` |
| 7 | `3c1045c8` | `multi-session` | no | 1 | 0 | `regressed` |
| 8 | `gpt4_731e37d7` | `multi-session` | no | 1 | 0 | `regressed` |
| 9 | `dc439ea3` | `single-session-assistant` | no | 1 | 1 | `same_correct` |
| 10 | `58470ed2` | `single-session-assistant` | no | 1 | 1 | `same_correct` |
| 11 | `71a3fd6b` | `single-session-assistant` | no | 1 | 1 | `same_correct` |
| 12 | `fca762bc` | `single-session-assistant` | no | 1 | 1 | `same_correct` |
| 13 | `35a27287` | `single-session-preference` | no | 0 | 0 | `same_wrong` |
| 14 | `06878be2` | `single-session-preference` | no | 0 | 0 | `same_wrong` |
| 15 | `a89d7624` | `single-session-preference` | no | 0 | 0 | `same_wrong` |
| 16 | `d6233ab6` | `single-session-preference` | no | 0 | 0 | `same_wrong` |
| 17 | `29f2956b_abs` | `single-session-user` | yes | 1 | 1 | `same_correct` |
| 18 | `3f1e9474` | `single-session-user` | no | 1 | 1 | `same_correct` |
| 19 | `af8d2e46` | `single-session-user` | no | 1 | 1 | `same_correct` |
| 20 | `6f9b354f` | `single-session-user` | no | 1 | 1 | `same_correct` |
| 21 | `gpt4_fe651585_abs` | `temporal-reasoning` | yes | 1 | 1 | `same_correct` |
| 22 | `0db4c65d` | `temporal-reasoning` | no | 0 | 0 | `same_wrong` |
| 23 | `b9cfe692` | `temporal-reasoning` | no | 1 | 0 | `regressed` |
| 24 | `gpt4_68e94288` | `temporal-reasoning` | no | 0 | 1 | `recovered` |
| 25 | `45dc21b6` | `knowledge-update` | no | 1 | 1 | `same_correct` |

## Artifact hashes

| file | bytes | sha256 |
|---|---:|---|
| `longmemeval_oracle_canary_baseline_eval_results.jsonl` | 6410 | `62e5037489ce360ce3b20542ec314f19616d9e94d952ef7c6f1d81e17d639031` |
| `longmemeval_oracle_canary_baseline_predictions.jsonl` | 3860 | `d01227dedd793858bb581ec10613a3a611f5e203989f3c129f7a33c48167f6d9` |
| `longmemeval_oracle_canary_scored_metadata.json` | 1259393 | `e4381cce2f247f03be0512f21d0b0ddbd40a24ad50e6b35027b14e3208c1f4aa` |
| `longmemeval_oracle_canary_scored_summary.json` | 1807 | `67a46d50a6cfc79666099c76f4b1e03561335af268c359bb774b8c9293c8ac27` |
| `longmemeval_oracle_canary_treatment_eval_results.jsonl` | 6193 | `6ec5ae050cbdf540f28549983c8d190e940997ddd8675c4db60bf6cf26dce5c7` |
| `longmemeval_oracle_canary_treatment_predictions.jsonl` | 3643 | `b1491346cd38835211fe3269f10140bfd62ccc9d68221f3057667934ccb67d86` |

## Initial interpretation

- The locked answer-shape treatment hurt this LongMemEval oracle slice: `56%` vs `72%` baseline.
- The regression concentrates in `knowledge-update` and `multi-session`; `single-session-preference` remains 0/4 for both arms, suggesting the current oracle prompt does not satisfy rubric-style personalized-response judging even with evidence present.
- This is answer-side evidence only. It should not be quoted as a Memibrium retrieval result or compared directly to prior LOCOMO scores.
- Next diagnostic should be artifact-only failure review before changing prompts: inspect whether failures are answer-generation misses, judge/rubric mismatch, or prompt over-directiveness. Do not retune on the slice without preregistering the next intervention.

## Guardrails observed

- No full LongMemEval `_s` / `_m` run.
- No full LOCOMO run.
- No DB/Docker/runtime mutation.
- No direct `/mcp/tools` inspection.
- Secrets were not printed or stored; run artifacts contain endpoint metadata only (scheme/host/path), not API keys.

