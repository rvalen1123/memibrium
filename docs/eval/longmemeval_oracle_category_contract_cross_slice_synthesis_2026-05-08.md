# LongMemEval oracle canary — category_contract_v1 cross-slice synthesis

Date: 2026-05-08

## Scope

This is a documentation-only synthesis across the two preregistered 25-row LongMemEval oracle-evidence canaries for unchanged `category_contract_v1`.

Inputs:

- First-slice scored run: `docs/eval/results/longmemeval_oracle_canary_category_contract_scored_20260508T050507Z/`
- First-slice scored report: `docs/eval/results/longmemeval_oracle_canary_category_contract_result_scored_20260508T050507Z.md`
- First-slice artifact review: `memibrium-operations` reference `references/longmemeval-category-contract-artifact-review-2026-05-08.md`
- Second-slice scored run: `docs/eval/results/longmemeval_oracle_canary_category_contract_second_slice_scored_20260508T132616Z/`
- Second-slice result doc: `docs/eval/longmemeval_oracle_canary_category_contract_second_slice_result_2026-05-08.md`
- Second-slice artifact review: `docs/eval/longmemeval_oracle_canary_category_contract_second_slice_artifact_review_2026-05-08.md`

No new model calls, judge calls, retrieval ingestion, DB/Docker/runtime mutation, full LongMemEval `_s`/`_m`, or prompt retuning were performed for this synthesis.

## Communication boundary

These are oracle-evidence answer-side canaries. The relevant evidence is already supplied to the answer model. These runs do not measure retrieval quality, memory ingestion, ranking, recall, or product benchmark performance.

Do not phrase the result as:

- "Memibrium scores 84% on LongMemEval."
- "Memibrium scores 76% on LongMemEval."
- "Retrieval improved LongMemEval."

Defensible phrasing:

> Across two preregistered 25-row LongMemEval oracle-evidence canaries, unchanged `category_contract_v1` improved answer-side scoring from `18/25` to `21/25` on the first slice and from `16/25` to `19/25` on the second slice. The replicated mechanism was single-session preference recovery: `0/4 -> 3/4` on slice 1 and `0/4 -> 4/4` on slice 2. This is answer-side mechanism evidence only; retrieval remains untested.

## Cross-slice scoreboard

| Slice | Selection | Baseline | `category_contract_v1` | Delta | Paired outcomes | Preference movement | Knowledge-update movement | Gate read |
| --- | --- | ---: | ---: | ---: | --- | --- | --- | --- |
| Slice 1 | `8bd4ae95fbd768866b0af05f2cb91a6bc998d5210221e5201b007bb879ecf6b8` | 18/25 | 21/25 | +3 | 17 same-correct, 3 same-wrong, 4 recovered, 1 regressed | 0/4 -> 3/4 | 4/5 -> 3/5 | Passed original strong go gate; KU watchpoint |
| Slice 2 | `9cd322852a4e947730f811e6913012270e3bac9cc569b3394ee49e5b1d80edbb` | 16/25 | 19/25 | +3 | 15 same-correct, 5 same-wrong, 4 recovered, 1 regressed | 0/4 -> 4/4 | 3/5 -> 3/5 | Passed all preregistered replication gates |
| Combined descriptive total | 50 rows | 34/50 | 40/50 | +6 | 32 same-correct, 8 same-wrong, 8 recovered, 2 regressed | 0/8 -> 7/8 | 7/10 -> 6/10 | Descriptive only; not a preregistered combined benchmark |

Important: the combined row is descriptive. The valid evidentiary units are the preregistered per-slice outcomes and gates.

## Replicated mechanism

The stable signal is not aggregate accuracy. It is category-local paired movement:

1. Baseline scored `0/4` on `single-session-preference` in both independent slices.
2. `category_contract_v1` recovered `3/4` on slice 1 and `4/4` on slice 2.
3. Across the two slices, 7 of 8 preference rows became correct under the unchanged contract.
4. The recovered rows shared the same mechanism: convert over-abstention into grounded, personalized recommendation/advisor answers when oracle evidence contains user preferences or stable context.

Mechanistic examples:

- Slice 1: preference rows recovered from abstention to concrete personalized advice, while one row (`35a27287`) moved directionally but remained too generic for the rubric.
- Slice 2: all four preference recoveries were rubric-aligned personalized recommendations:
  - `1da05512`: NAS-buying decision grounded in storage/security context.
  - `1c0ddc50`: commute activities constrained toward audio/history/science rather than visual tasks.
  - `32260d93`: Netflix stand-up/storytelling recommendation.
  - `06f04340`: dinner suggestions centered on homegrown cherry tomatoes, basil, and mint.

This supports promoting the answer-side idea that LongMemEval preference questions need a category-aware recommender/advisor answer contract rather than a generic "not enough information" posture.

## Watchpoints and non-replicated failures

### Knowledge-update

Knowledge-update is not cleanly solved by `category_contract_v1`:

- Slice 1: `4/5 -> 3/5`, with one treatment-introduced regression.
- Slice 2: `3/5 -> 3/5`, satisfying the preregistered non-regression gate but retaining shared misses.

Artifact interpretation:

- `eace081b` from slice 1 was not stale-recency suppression. Evidence contained the newer Oahu fact; the contract over-abstained because the adjacent-entity/attribute guard was too strict for casual "where am I staying" language. A future v2 could relax type-compatible location answers, but this should be done only after separating it from the already-replicated preference mechanism.
- `852ce960` from slice 1 is the true stale-recency failure: both arms chose older `$350,000` instead of newer `$400,000`, likely because the newer fact appears in a move/cable-services context rather than a dense mortgage context.
- `031748ae_abs` from slice 2 is a premise-validation trap: evidence says Senior Software Engineer while the question asks Software Engineer Manager.
- `a2f3aa27` from slice 2 is shared under-answering on an approximate current count: newer evidence says close to 1300 after older 1250, but both arms abstained.

Conclusion: knowledge-update needs separate premise/recency/conflict calibration. It should not be patched by blindly retuning the preference contract.

### Temporal-reasoning

Temporal-reasoning remains a separate weak layer:

- Slice 1: `2/4 -> 3/4`, with one temporal recovery.
- Slice 2: `2/4 -> 1/4`, with a labeled regression and shared temporal misses.

Artifact interpretation:

- `0db4c65d` from slice 1: both arms missed event-date extraction and date arithmetic; relevant dates were `2022/12/28` and `2023/01/15`.
- `gpt4_61e13b3c` from slice 2: both arms abstained despite event dates implying 3 weeks.
- `gpt4_2487a7cb` from slice 2: both arms mishandled relative-date ordering; `two months ago` should precede `last Saturday` from the question date.
- `gpt4_78cf46a3` from slice 2: labeled as treatment regression, but artifact review found both answers chose the wrong final event while stating date facts that imply the gold. Treat as temporal/judge-answer consistency fragility, not a preference-contract failure.

Conclusion: temporal failures are upstream of `category_contract_v1` and should be handled by timestamp grounding / temporal-link extraction / final-choice consistency work, not by preference prompt retuning.

### Assistant-turn extraction

The second slice added a clear assistant-turn extraction miss:

- `cc539528`: the gold list `Ruby, Python, or PHP` appears in an assistant turn marked `has_answer`; both arms abstained.

Conclusion: assistant-authored recommendation/list extraction is another separate answer-side gap. It is not retrieval and not the same mechanism as preference recovery.

## Decision recommendation

Do not retune `category_contract_v1` as an immediate next step.

Reason:

- The intended mechanism has replicated across two independent preregistered oracle slices.
- The remaining errors are heterogeneous and mostly outside the preference mechanism:
  - knowledge-update premise/recency/confidence,
  - temporal grounding/date arithmetic/final-choice consistency,
  - assistant-turn list extraction,
  - one open-ended preference specificity limitation.
- A broad prompt retune now risks overfitting and could damage the stable preference recovery.

Clean next options:

1. Preregister a retrieval-coupled oracle-to-product bridge.
   - Goal: test whether Memibrium retrieval supplies the evidence that the oracle answer contract can use.
   - Keep answer contract unchanged for the first retrieval-coupled rung.
   - Separate retrieval hit/coverage gates from answer-side scoring gates.
   - Do not claim product performance until retrieval ingestion, recall/ranking, and answer synthesis are all in the loop.

2. Preregister a narrow answer-side v2 only after freezing the v1 conclusion.
   - Candidate v2 components should be separate toggles, not a broad rewrite:
     - type-compatible location acceptance for casual knowledge-update questions,
     - temporal timestamp grounding / final-choice consistency,
     - assistant-turn list extraction,
     - concrete-event recommendation shape for open-ended preference rows.
   - Run each as a separately preregistered canary rather than stacking all fixes.

3. Write a public/internal narrative note.
   - Use the defensible phrasing above.
   - Lead with the mechanism: preference questions require recommender/advisor answer shape.
   - Put retrieval boundary and limitations in the first paragraph, not a footnote.

## Recommended next rung

The cleanest next engineering rung is retrieval-coupled preregistration, not another oracle run and not prompt retuning.

Minimum preregistration contents:

- Dataset/slice: choose either one of the existing oracle slices as a frozen answer-side target or preregister a new retrieval-coupled 25-row slice before inspecting outcomes.
- Retrieval condition: define how memories are ingested and recalled, with DB/Docker/runtime mutation requiring a separately approved window.
- Evidence coverage gates: track whether gold-supporting facts appear in retrieved context before answer generation.
- Answer gates: keep `category_contract_v1` unchanged for the first bridge rung and score only after evidence coverage is measured.
- Stop conditions: if retrieval coverage is missing, do not tune the answer contract to compensate.
- Communication boundary: retrieval-coupled canary is still not full LongMemEval `_s`/`_m` unless the exact upstream mode is run and reported as such.

## Artifact hashes

| Artifact | SHA256 |
| --- | --- |
| First-slice summary JSON | `8d653842b0ea0dd8f716b1b4cfcb0adeabbb82f9cf047c51928549eb2e0633e2` |
| Second-slice summary JSON | `21a96540561ef4efeeb289acc93c23a49206833a6f5a26d77aade0e8e02c834c` |
| Second-slice gate report JSON | `8d399652ed190cfe83b37dc9e5d91ba79c41623cc7fe4bc54533dfa77c96ea5a` |

## Final claim boundary

After two preregistered oracle slices, `category_contract_v1` has replicated answer-side mechanism evidence for preference recovery. It has not established retrieval performance, full LongMemEval performance, or a general answer-quality improvement outside the oracle-evidence setup.
