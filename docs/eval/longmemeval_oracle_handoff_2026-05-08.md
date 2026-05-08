# LongMemEval oracle canary handoff — 2026-05-08

This is a copy-paste handoff for the current LongMemEval oracle canary state on branch `query-expansion`.

## Repo state

- Repo: `/home/zaddy/src/Memibrium`
- Branch: `query-expansion`
- Current pushed HEAD at time of handoff doc creation: `93eb0e1 docs: record LongMemEval category contract gates`
- Remote branch: `origin/query-expansion`
- GitHub push warning is known and non-blocking: repository moved to `https://github.com/rvalen1123/memibrium.git`; pushes still succeeded.
- Known intentionally untracked noise remains:
  - `docs/reference/`
  - older generated `docs/eval/results/locomo_context_packet_canary_*` artifacts

## Hard guardrails

Do not proceed to any of these without explicit approval:

- New model/answer calls
- New judge calls
- Full LongMemEval `_s` or `_m`
- DB/Docker/runtime mutation
- Retrieval ingestion
- Direct `/mcp/tools` curl inspection
- Product/retrieval benchmark claims from oracle results

Continue to redact secrets/tokens/API keys/env credentials from logs and artifacts.

## Dataset and evaluator pins

- Cleaned dataset: `xiaowu0162/longmemeval-cleaned`
- Dataset revision: `98d7416c24c778c2fee6e6f3006e7a073259d48f`
- Oracle file: `/tmp/longmemeval-cleaned-pin/longmemeval_oracle.json`
- Oracle SHA256: `821a2034d219ab45846873dd14c14f12cfe7776e73527a483f9dac095d38620c`
- Upstream LongMemEval commit: `982fbd7045c9977e9119b5424cab0d7790d19413`
- Upstream judge script SHA256: `ecce9c4c79dc89d99534ac17b383a5cbb5b9f0c69ee98adaf0684742e3d95251`
- Judge prompt: upstream `get_anscheck_prompt()` at the pinned commit
- Answer model for scored runs: Azure AI Foundry `gpt-4o`, temperature 0
- Judge model for scored runs: Azure AI Foundry `gpt-4o`, version `2024-11-20`, temperature 0

## Selection and harness

Selection artifact:

- `docs/eval/results/longmemeval_oracle_canary_25_selection_20260508.json`
- Selection SHA256: `8bd4ae95fbd768866b0af05f2cb91a6bc998d5210221e5201b007bb879ecf6b8`
- Seed: `memibrium-longmemeval-oracle-canary-2026-05-08-v1`
- Shape: 25 oracle rows, 4 per LongMemEval question type, 1 extra knowledge-update row, 4 reserved abstention rows

Harness:

- `docs/eval/results/run_longmemeval_oracle_canary.py`
- Tests: `test_longmemeval_oracle_canary.py`
- Validates dataset SHA, selection artifact identity, selection seed, per-row selection hashes, counts, question types, abstention flags, and selection groups
- Supports prep-only placeholder output and explicit scored launch with `--allow-answer-generation`
- Supports `--condition locked_answer_shape` and `--condition category_contract_v1`

## Commit sequence

Relevant pushed commits on `query-expansion`:

- `05391a3 docs: preregister LongMemEval oracle canary slice`
- `4e5f1ae eval: add LongMemEval oracle canary prep harness`
- `b97f097 test: harden LongMemEval oracle canary proof`
- `20fc448 eval: run LongMemEval oracle canary`
- `f41c0c9 docs: audit LongMemEval oracle canary failures`
- `7ab243b eval: preregister LongMemEval category contract`
- `2c11b4a eval: run LongMemEval category contract canary`
- `93eb0e1 docs: record LongMemEval category contract gates`

## First scored oracle canary: locked answer-shape treatment

Run directory:

- `docs/eval/results/longmemeval_oracle_canary_scored_20260508T040926Z/`

Report:

- `docs/eval/results/longmemeval_oracle_canary_result_scored_20260508T040926Z.md`

Result:

- Baseline: `18/25` (`72%`)
- Locked treatment: `14/25` (`56%`)
- Net: `-4` rows / `-16` points
- Paired outcomes: `13` same-correct, `6` same-wrong, `1` recovered, `5` regressed

Interpretation:

- Locked answer-shape treatment regressed.
- Regression concentrated in `knowledge-update` and `multi-session`.
- `single-session-preference` remained `0/4` in both arms.
- Artifact-only review concluded the treatment over-abstained / partial-enumerated rows baseline solved and failed to add a preference/recommender mechanism.

Failure review:

- `docs/eval/results/longmemeval_oracle_canary_failure_review_20260508T040926Z.md`
- `docs/eval/results/longmemeval_oracle_canary_failure_review_20260508T040926Z.json`

## Category-contract preregistration and prep

Preregistration:

- `docs/eval/longmemeval_oracle_canary_category_contract_preregistration_2026-05-08.md`

Prep artifact:

- `docs/eval/results/longmemeval_oracle_canary_category_contract_prepare_20260508T050000Z/`

Condition:

- `category_contract_v1`

Contract intent:

- `single-session-preference`: recommender/advisor mode for stable user attributes and personalized suggestions
- `knowledge-update`: latest matching fact, with absent-entity abstention protection
- `multi-session`: all-relevant-items/list/numeric synthesis reminder
- `temporal-reasoning`: narrow date/arithmetic reminder

Prep run made no model calls, no judge calls, no score, and no DB/Docker/runtime mutation.

## Scored category_contract_v1 canary

Run directory:

- `docs/eval/results/longmemeval_oracle_canary_category_contract_scored_20260508T050507Z/`

Report:

- `docs/eval/results/longmemeval_oracle_canary_category_contract_result_scored_20260508T050507Z.md`

Result:

- Baseline: `18/25` (`72%`)
- `category_contract_v1`: `21/25` (`84%`)
- Net: `+3` rows / `+12` points
- Paired outcomes: `17` same-correct, `3` same-wrong, `4` recovered, `1` regressed
- Moved-row win/loss ratio: `4:1`

By question type:

- `knowledge-update`: `4/5 -> 3/5`, delta `-1`
- `multi-session`: `4/4 -> 4/4`, delta `0`
- `single-session-assistant`: `4/4 -> 4/4`, delta `0`
- `single-session-preference`: `0/4 -> 3/4`, delta `+3`
- `single-session-user`: `4/4 -> 4/4`, delta `0`
- `temporal-reasoning`: `2/4 -> 3/4`, delta `+1`

Gate read:

- Strong go gate passed: `21/25 >= 18/25`, no category dropped below baseline by more than one row.
- Main mechanism signal: preference recovery `0/4 -> 3/4`.
- Main watchpoint: knowledge-update regression `4/5 -> 3/5`.

Do not headline this as “Memibrium scores 84% on LongMemEval.” Correct framing:

> On a preregistered 25-row LongMemEval oracle-evidence canary, a category-specific answer contract improved answer-side scoring from 18/25 to 21/25, primarily by recovering single-session preference questions from 0/4 to 3/4. This is mechanism evidence only; retrieval remains untested.

## Next gate doc

Read before proceeding:

- `docs/eval/longmemeval_oracle_category_contract_next_gates_2026-05-08.md`

Key next-gate rules:

1. Do artifact-only review of the one knowledge-update regression (`eace081b`) and the three same-wrong rows.
2. Preregister a second hash-stratified 25-row oracle slice with no further tuning.
3. Run only after explicit approval for model/judge calls.
4. Treat `knowledge-update` baseline-or-better as a hard threshold, not a soft watchpoint.
5. Track paired outcomes as the primary stability metric.

Recommended second-slice gates:

- `category_contract_v1` total score must be `>= baseline`.
- `knowledge-update` must be `>= baseline` on the same slice.
- `single-session-preference` should reproduce a substantial recovery; preregister the exact threshold after inspecting slice composition.
- Moved-row win/loss ratio should remain positive and should not drop below `1:1`.
- No severe category collapse: no non-watch category may drop by more than one row.

## Immediate next work

The clean next action is artifact-only review, not another run and not retuning.

Focus rows from `category_contract_v1` scored report:

- `eace081b`: knowledge-update regression; question “Where am I planning to stay for my birthday trip to Hawaii?”; gold `Oahu`; baseline correct; category contract answered insufficient info.
- `852ce960`: knowledge-update same-wrong; mortgage pre-approval amount; gold `$400,000`; both answered `$350,000`.
- `35a27287`: single-session-preference same-wrong; cultural event recommendation; baseline abstained; category contract gave generic platforms rather than concrete/rubric-aligned preference response.
- `0db4c65d`: temporal-reasoning same-wrong; days between reading completion and library event; gold `18` or `19`; both abstained.

For `eace081b`, answer these from artifacts only:

1. Was the gold answer the latest fact and did the candidate return an earlier fact or abstain?
2. Did oracle evidence contain both old and new Hawaii lodging facts?
3. Did the contract directive structurally encourage stale/first-mentioned commitment or over-abstention?
4. Should the next preregistration adjust knowledge-update handling, or should `category_contract_v1` be replicated unchanged on a second slice first?

## Verification history

Most recent scored run verification included:

- Preflight passed with endpoint metadata only; no secrets printed.
- JSON summary/metadata parsed with `python3 -m json.tool`.
- Secret-pattern scan on run artifacts/report: no hits.
- `python3 -m py_compile docs/eval/results/run_longmemeval_oracle_canary.py test_longmemeval_oracle_canary.py` passed.
- `python3 -m unittest test_longmemeval_oracle_canary.py test_locomo_context_packet_canary.py` passed with 57 tests.
- `git diff --check` passed.
- Process list was clean.

## Suggested copy-paste prompt for next session

Continue from `/home/zaddy/src/Memibrium` on branch `query-expansion`. Load the `memibrium-operations` skill and read `docs/eval/longmemeval_oracle_handoff_2026-05-08.md` plus `docs/eval/longmemeval_oracle_category_contract_next_gates_2026-05-08.md`. Do not run model/judge calls, do not mutate DB/Docker/runtime, and do not retune prompts. First do artifact-only failure review of the `category_contract_v1` scored canary, focusing on `eace081b` knowledge-update regression and same-wrong rows `852ce960`, `35a27287`, and `0db4c65d`. Determine whether `eace081b` is recency suppression, over-abstention, evidence ambiguity, or judge/rubric mismatch. Preserve the oracle-only communication boundary: do not frame `21/25` or `84%` as a product/retrieval LongMemEval score. If new code or docs are needed, use TDD/verification discipline, commit selectively, and leave `docs/reference/` plus old LOCOMO generated artifacts untouched.
