# LongMemEval oracle category contract next gates — 2026-05-08

Scope: documentation-only interpretation and next-gate discipline after the preregistered `category_contract_v1` 25-row oracle canary. This is not approval to launch another run, retune the contract, mutate runtime state, ingest retrieval data, or run full LongMemEval `_s` / `_m`.

## Current scored oracle evidence

Run: `docs/eval/results/longmemeval_oracle_canary_category_contract_scored_20260508T050507Z/`.

Same-run result:

- Baseline: `18/25` (`72%`).
- `category_contract_v1`: `21/25` (`84%`).
- Net delta: `+3` rows / `+12` percentage points.
- Paired outcomes: `17` same-correct, `3` same-wrong, `4` recovered, `1` regressed.

By question type:

| question_type | baseline | category_contract_v1 | delta | read |
|---|---:|---:|---:|---|
| `knowledge-update` | 4/5 | 3/5 | -1 | watchpoint |
| `multi-session` | 4/4 | 4/4 | 0 | preserved |
| `single-session-assistant` | 4/4 | 4/4 | 0 | preserved |
| `single-session-preference` | 0/4 | 3/4 | +3 | primary mechanism gain |
| `single-session-user` | 4/4 | 4/4 | 0 | preserved |
| `temporal-reasoning` | 2/4 | 3/4 | +1 | secondary gain |

## Mechanism interpretation

The most informative result is not the aggregate `+12` points. It is the category movement:

- `single-session-preference` moved from `0/4` to `3/4`.
- This category asks for stable user attributes and personalized recommendations, not ordinary factual recall.
- A `0/4` baseline implies the prior answer shape was not handling that structural distinction.
- A `3/4` category-contract result is evidence that `category_contract_v1` added a missing answer-side mechanism.

The paired movement is the primary stability statistic for future oracle canaries:

- 20/25 rows were unchanged by correctness outcome.
- 5/25 rows moved.
- Moved-row win/loss ratio was `4:1` recovered/regressed.

Track this ratio directly across second-slice and replicate runs. Aggregate delta alone can hide a fragile intervention if the moved-row ratio shifts toward `3:2`, `2:3`, or worse.

## Knowledge-update watchpoint

`knowledge-update` moved from `4/5` to `3/5`. At `n=5`, this is not statistically decisive, but it is mechanistically important.

Knowledge-update is the LongMemEval category most aligned with Memibrium CT lifecycle behavior:

- latest fact vs stale fact,
- contradiction handling,
- delta-decay,
- freeze/revert semantics,
- willingness to override older crystallized facts when newer evidence supersedes them.

The one regressed knowledge-update row should be reviewed artifact-only before any further prompt changes. The review should answer:

1. Was the gold answer the latest fact while the candidate returned an earlier fact?
2. Did oracle evidence contain both old and new facts?
3. Did the contract structurally encourage commitment to the first-mentioned or stale fact?
4. Did the candidate fail because of over-abstention, wrong entity, stale fact selection, or judge/rubric mismatch?

If the contract encouraged stale/first-mentioned commitment, treat that as recency-suppression and fix it before any `_s` / `_m` scaling.

## Next gate discipline

Before promoting `category_contract_v1` into a broader answer contract:

1. Do artifact-only review of the one knowledge-update regression and the three same-wrong rows.
2. Preregister a second hash-stratified 25-row oracle slice with no further tuning.
3. Run only after explicit approval for model/judge calls.
4. Treat `knowledge-update` baseline-or-better as a hard threshold, not a soft watchpoint.
5. Keep paired outcomes as the primary stability metric.

Recommended second-slice gates:

- `category_contract_v1` total score must be `>= baseline`.
- `knowledge-update` must be `>= baseline` on the same slice.
- `single-session-preference` should reproduce a substantial recovery; preregister exact threshold after inspecting slice composition.
- Moved-row win/loss ratio should remain positive and should not drop below `1:1`.
- No severe category collapse: no non-watch category may drop by more than one row.

## Communication boundary

The correct external/internal framing is:

- This is an answer-side oracle mechanism canary.
- It isolates behavior when evidence is already supplied.
- It does not measure retrieval quality.
- It is not a full LongMemEval `_s` or `_m` benchmark.
- It should not be stated as "Memibrium scores 84% on LongMemEval."

The defensible phrasing is:

> On a preregistered 25-row LongMemEval oracle-evidence canary, a category-specific answer contract improved answer-side scoring from 18/25 to 21/25, primarily by recovering single-session preference questions from 0/4 to 3/4. This is mechanism evidence only; retrieval remains untested.

## Non-actions

This note does not authorize:

- another scored run,
- prompt retuning,
- full LongMemEval `_s` / `_m`,
- retrieval ingestion,
- DB/Docker/runtime mutation,
- product benchmark claims.
