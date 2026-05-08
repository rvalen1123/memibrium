# LongMemEval oracle canary category-contract second-slice preregistration — 2026-05-08

Status: preregistration and preparation only. This document does not authorize answer generation, judge calls, a fresh score, a full LongMemEval `_s`/`_m` run, retrieval ingestion, DB/Docker/runtime mutation, or prompt retuning.

## Motivation

The first `category_contract_v1` oracle-evidence canary improved answer-side scoring from `18/25` to `21/25`, primarily by recovering `single-session-preference` rows from `0/4` to `3/4`. Artifact review found one treatment-introduced knowledge-update regression (`eace081b`) caused by over-abstention from adjacent-entity/attribute strictness, not stale-recency suppression.

The next clean gate is a second hash-stratified 25-row oracle slice with `category_contract_v1` unchanged. This is a replication/stability gate, not a retuning gate.

## Frozen source artifacts

Use the pinned oracle dataset and evaluator lineage:

- Dataset: `xiaowu0162/longmemeval-cleaned`.
- Dataset revision: `98d7416c24c778c2fee6e6f3006e7a073259d48f`.
- Oracle SHA256: `821a2034d219ab45846873dd14c14f12cfe7776e73527a483f9dac095d38620c`.
- Upstream LongMemEval commit: `982fbd7045c9977e9119b5424cab0d7790d19413`.
- Judge script SHA256: `ecce9c4c79dc89d99534ac17b383a5cbb5b9f0c69ee98adaf0684742e3d95251`.

Prior first-slice artifact, excluded from second-slice selection:

- `docs/eval/results/longmemeval_oracle_canary_25_selection_20260508.json`.
- SHA256: `8bd4ae95fbd768866b0af05f2cb91a6bc998d5210221e5201b007bb879ecf6b8`.

Second-slice selection artifact:

- `docs/eval/results/longmemeval_oracle_canary_25_second_slice_selection_20260508.json`.
- SHA256: `999cf9ae1fb40960502b7d6ec5c86b186cb4528d7e7613f656273401721c0398`.
- Seed: `memibrium-longmemeval-oracle-canary-2026-05-08-v2`.
- Shape: 25 oracle rows, 4 per LongMemEval question type, 1 extra non-abstention knowledge-update row, 4 reserved abstention rows.
- Prior-slice overlap: `0` question IDs.

Preparation artifact:

- `docs/eval/results/longmemeval_oracle_canary_category_contract_second_slice_prepare_20260508T054716Z/`.
- Mode: `preparation_only_no_answer_generation`.
- Condition: `category_contract_v1`.

## Selection rule

Second hash-stratified 25-row oracle slice:

1. Exclude all question IDs from `docs/eval/results/longmemeval_oracle_canary_25_selection_20260508.json`.
2. For each LongMemEval `question_type`, sort remaining rows by `sha256(seed:question_id:question)` using seed `memibrium-longmemeval-oracle-canary-2026-05-08-v2`.
3. If the question type has remaining abstention rows, reserve one slot for the lowest-hash `_abs` row and fill the other three slots with the lowest-hash non-abstention rows.
4. If the question type has no abstention rows, fill all four slots by lowest hash.
5. Add one extra lowest-hash not-yet-selected non-abstention `knowledge-update` row as a product-telemetry oversample.
6. Commit question IDs before answer generation or judging.

## Intervention freeze

Use `category_contract_v1` unchanged from the first scored canary. Do not retune based on `eace081b`, `852ce960`, `35a27287`, or `0db4c65d` until this second-slice replication gate is scored and reviewed under a separate approval.

The unchanged contract intent is:

- `single-session-preference`: recommender/advisor mode grounded in stable user attributes and personalized suggestions.
- `knowledge-update`: latest matching fact, with absent-entity/adjacent-entity abstention protection.
- `multi-session`: narrow numeric/list synthesis reminder.
- `temporal-reasoning`: narrow date/arithmetic reminder.

## Preregistered scoring gates for a future explicit launch

If, and only if, a future explicit launch is approved for model and judge calls, compare baseline vs `category_contract_v1` on this same second slice. The gates are:

1. Total score: `category_contract_v1 >= baseline` on the same slice.
2. Knowledge-update: `knowledge-update >= baseline` on the same slice. This is a hard threshold.
3. Preference mechanism: `preference_recovered / preference_baseline_wrong >= 50%`.
4. Moved-row stability: `recovered/regressed >= 2:1`. A `1:1` moved-row ratio does not pass.
5. Category collapse: no non-watch category drops by more than one row.

## Communication boundary

This remains an oracle-evidence answer-side canary. It isolates answer behavior when evidence is already supplied. It does not measure retrieval quality and must not be framed as a product LongMemEval score.

Defensible phrasing remains:

> On a preregistered 25-row LongMemEval oracle-evidence canary, a category-specific answer contract improved answer-side scoring from 18/25 to 21/25, primarily by recovering single-session preference questions from 0/4 to 3/4. This is mechanism evidence only; retrieval remains untested.

## Non-actions

This preregistration and prep artifact do not authorize:

- answer generation,
- judge calls,
- prompt retuning,
- full LongMemEval `_s` / `_m`,
- retrieval ingestion,
- DB/Docker/runtime mutation,
- direct `/mcp/tools` inspection,
- product/retrieval benchmark claims.
