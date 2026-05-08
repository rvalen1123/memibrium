# LongMemEval oracle canary — category_contract_v1 second-slice scored result

Date: 2026-05-08

## Scope

- Slice: `longmemeval_oracle_canary_25_second_slice_20260508`
- Dataset SHA256: `821a2034d219ab45846873dd14c14f12cfe7776e73527a483f9dac095d38620c`
- Selection artifact: `docs/eval/results/longmemeval_oracle_canary_25_second_slice_selection_20260508.json`
- Selection SHA256: `9cd322852a4e947730f811e6913012270e3bac9cc569b3394ee49e5b1d80edbb`
- Condition: unchanged `category_contract_v1`
- Run directory: `docs/eval/results/longmemeval_oracle_canary_category_contract_second_slice_scored_20260508T132616Z`

This is an oracle-evidence answer-side canary only. It does not test retrieval and must not be framed as a product/retrieval benchmark claim.

## Result

- Baseline: `16/25`
- Treatment: `19/25`
- Delta: `+3`
- Paired outcomes: `15` same-correct, `5` same-wrong, `4` recovered, `1` regressed
- Preference recovery: `4/4` baseline-wrong preference rows recovered

## Gate verdict

Overall gate: `PASS`

| Gate | Result | Evidence |
| --- | --- | --- |
| total score treatment >= baseline | `PASS` | 16 -> 19 |
| knowledge-update >= baseline | `PASS` | 3 -> 3 |
| preference recovery >= 50% | `PASS` | 4/4 = 1.00 |
| moved rows >= 3 and recovered/regressed >= 2:1 | `PASS` | moved=5, recovered=4, regressed=1 |
| no non-watch category drop > 1 | `PASS` | drops={} |

## By category

| Question type | Baseline | Treatment | Delta |
| --- | ---: | ---: | ---: |
| knowledge-update | 3/5 | 3/5 | +0 |
| multi-session | 4/4 | 4/4 | +0 |
| single-session-assistant | 3/4 | 3/4 | +0 |
| single-session-preference | 0/4 | 4/4 | +4 |
| single-session-user | 4/4 | 4/4 | +0 |
| temporal-reasoning | 2/4 | 1/4 | -1 |

## Artifacts

- `docs/eval/results/longmemeval_oracle_canary_category_contract_second_slice_scored_20260508T132616Z/longmemeval_oracle_canary_baseline_predictions.jsonl`
- `docs/eval/results/longmemeval_oracle_canary_category_contract_second_slice_scored_20260508T132616Z/longmemeval_oracle_canary_treatment_predictions.jsonl`
- `docs/eval/results/longmemeval_oracle_canary_category_contract_second_slice_scored_20260508T132616Z/longmemeval_oracle_canary_baseline_eval_results.jsonl`
- `docs/eval/results/longmemeval_oracle_canary_category_contract_second_slice_scored_20260508T132616Z/longmemeval_oracle_canary_treatment_eval_results.jsonl`
- `docs/eval/results/longmemeval_oracle_canary_category_contract_second_slice_scored_20260508T132616Z/longmemeval_oracle_canary_scored_summary.json`
- `docs/eval/results/longmemeval_oracle_canary_category_contract_second_slice_scored_20260508T132616Z/longmemeval_oracle_canary_scored_metadata.json`
- `docs/eval/results/longmemeval_oracle_canary_category_contract_second_slice_scored_20260508T132616Z/longmemeval_oracle_canary_second_slice_gate_report.json`

## Correct framing

On a second preregistered 25-row LongMemEval oracle-evidence canary, unchanged `category_contract_v1` improved answer-side scoring from `16/25` to `19/25`, with all preregistered replication gates passing. The main mechanism signal again came from single-session preference recovery, `0/4 -> 4/4`. This is mechanism evidence only; retrieval remains untested.
