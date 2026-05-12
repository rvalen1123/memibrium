# LongMemEval oracle canary category-contract preregistration — 2026-05-08

Status: preregistration and preparation only. This document does not authorize answer generation, judge calls, a fresh score, a full LongMemEval `_s`/`_m` run, retrieval ingestion, DB/Docker/runtime mutation, or prompt retuning after seeing a new score.

## Motivation

The first scored 25-row oracle canary (`20260508T040926Z`) showed baseline `18/25` and the locked LOCOMO-derived answer-shape treatment `14/25`. The artifact-only failure review found:

- treatment regressions from over-abstention or partial enumeration on rows baseline solved;
- `single-session-preference` failed `0/4` in both arms because the existing factual/insufficient prompt is structurally mismatched to LongMemEval's rubric-style personalized recommendation rows;
- `knowledge-update` needs latest-matching-fact behavior while preserving abstention for absent entities;
- temporal/multi-session arithmetic/list synthesis should not inherit the broad LOCOMO answer-shape directive globally.

## Frozen source artifacts

Use the already committed and validated 25-row oracle canary slice only:

- Dataset: `longmemeval_oracle.json` from `xiaowu0162/longmemeval-cleaned` revision `98d7416c24c778c2fee6e6f3006e7a073259d48f`.
- Dataset SHA256: `821a2034d219ab45846873dd14c14f12cfe7776e73527a483f9dac095d38620c`.
- Selection artifact: `docs/eval/results/longmemeval_oracle_canary_25_selection_20260508.json`.
- Selection artifact SHA256: `8bd4ae95fbd768866b0af05f2cb91a6bc998d5210221e5201b007bb879ecf6b8`.
- Scored baseline/treatment result: `docs/eval/results/longmemeval_oracle_canary_result_scored_20260508T040926Z.md`.
- Failure review: `docs/eval/results/longmemeval_oracle_canary_failure_review_20260508T040926Z.md`.

## Proposed intervention: `category_contract_v1`

Create a new optional prompt condition that keeps oracle evidence identity unchanged and changes only answer instructions by LongMemEval question type:

1. `single-session-preference`: switch from factual QA to a recommender/advisor mode. The answer should provide useful personalized suggestions grounded in the oracle evidence. It should not say “insufficient” merely because no concrete local events/accessories/venues are present; it may offer preference-shaped recommendations and explicitly ground them in remembered preferences.
2. `knowledge-update`: use a latest-matching-fact contract. If the asked entity/attribute is present with stale and newer values, answer with the latest matching value. If the asked entity is absent and only adjacent entities appear, abstain rather than substituting the adjacent entity.
3. `multi-session`: preserve baseline behavior by default, with a minimal synthesis reminder only for numeric/list questions: combine all relevant evidence items and avoid partial subsets.
4. `temporal-reasoning`: preserve baseline behavior by default, with a minimal date/arithmetic reminder: use dates in evidence and show or return the computed duration/activity when evidence supports it.
5. Other types: preserve the baseline oracle prompt except for condition metadata.

## Primary comparison

If a future explicit launch is authorized, compare three arms on the same 25 rows:

- `baseline`: current baseline oracle prompt;
- `locked_answer_shape`: already scored LOCOMO-derived treatment, retained for historical comparison;
- `category_contract_v1`: new category-aware condition.

Do not overwrite the prior scored artifacts. A fresh launch must write a new timestamped output directory with prompt metadata, prediction JSONL, judge JSONL, summary JSON, and artifact hashes.

## Stop/go gates before any model calls

Before launch, the preparation harness must demonstrate without model calls:

- selection proof still validates dataset SHA, seed, row hashes, counts, groups, question types, and abstention flags;
- baseline and `category_contract_v1` prompts have identical evidence hashes for every row;
- `single-session-preference` prompts contain recommender/advisor wording and do not contain the baseline-only default of refusing personalized advice solely because event/item specifics are missing;
- `knowledge-update` prompts contain both latest-matching-fact and absent-entity-abstention wording;
- `multi-session` and `temporal-reasoning` prompts use narrower synthesis reminders than the old global answer-shape treatment;
- no answer-generation or judge code path is invoked in prep mode.

## Success criteria for a future launch

Because this is a 25-row oracle canary, treat results as diagnostic only:

- Strong go: `category_contract_v1 >= 18/25` and no category below the baseline count by more than one row.
- Mechanistic go: preference rows improve from `0/4` to at least `2/4` while knowledge-update does not regress below `4/5`.
- Stop: any abstention row that baseline solved by abstaining is converted to an adjacent-entity answer, or treatment drops below `14/25`.

## Guardrails

- No full LongMemEval `_s`/`_m` run from this preregistration.
- No retrieval-quality claim from oracle evidence.
- No DB/Docker/runtime mutation.
- No direct `/mcp/tools` inspection.
- No prompt retuning on a new score without a subsequent preregistration.
