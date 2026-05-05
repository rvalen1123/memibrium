# LOCOMO Artifact-Pinned Row-Level Failure Audit — 2026-05-05

## Scope

- Artifact-only audit over existing 25-row preregistered conv-26 canary artifacts.
- No new benchmark launch, no full 199Q LOCOMO, no DB/runtime mutation.
- Compared two artifact-pinned frozen full-final-context runs:
  - `20260504T182630Z` multi-hop+temporal answer-shape, `60 -> 80`, gold-hit `0.8261 -> 0.8261`, frozen hash `25/25`.
  - `20260505T094418Z` single-hop-only answer-shape, `62 -> 68`, gold-hit `0.8261 -> 0.8261`, frozen hash `25/25`.

## Aggregate Finding

Best available treatment score per row across the two artifact-pinned runs:

- `19/25` rows reached full credit in at least one targeted answer-shape run.
- `6/25` rows remained partial or failed after the best available targeted transform.
- Remaining failures split mostly into retrieval/context misses, not generic answer-shape gaps.

This means the 25-row slice is no longer primarily a prompt-shape problem. The next clean work should target evidence coverage/entity-time substrate and answer contracts, not more broad prompt stacking.

## Remaining Non-Full Rows

| Row | Category | Best score | Ground truth | Best/representative prediction | Refined class | Evidence note |
|---:|---|---:|---|---|---|---|
| 24 | single-hop | 0.5 | "Nothing is Impossible", "Charlotte's Web" | Melanie has read "Charlotte's Web" as a favorite childhood book and a book Caroline recommended that inspires pursuing dreams. | `retrieval_context_miss_partial_evidence` | Only Charlotte's Web found in pinned context; Nothing is Impossible absent. Shape cannot recover missing book. |
| 41 | single-hop | 0.0 | 2 | I don't know. | `retrieval_context_miss` | Gold count is 2; beach term absent from pinned context; answer abstains. |
| 113 | unanswerable | 0.0 | a sunset with a palm tree | Mel and her kids painted a nature-inspired painting featuring lovely flowers in their latest project in July 2023. | `retrieval_context_miss_wrong_near_neighbor` | Context contains latest nature/flowers painting, but gold sunset with palm tree absent; likely stale/near-neighbor retrieval. |
| 123 | unanswerable | 0.5 | She wanted to catch the eye and make people smile. | Melanie used colors and patterns in her pottery project to express emotions, creativity, and self-expression. | `retrieval_context_miss_or_wrong_evidence` | Gold phrase catch the eye / make people smile absent; retrieved context has generic colors/smile unrelated. |
| 163 | adversarial | 0.5 | explored nature, roasted marshmallows, and went on a hike | They roasted marshmallows and shared stories around the campfire. | `retrieval_context_miss_partial_evidence` | Context has marshmallows/nature/camping but no hike; partial answer reflects missing event detail. |
| 185 | adversarial | 0.0 | clarinet and violin | Caroline plays acoustic guitar. | `entity_role_attribution_or_judge_mismatch` | Context contains Caroline acoustic guitar and Melanie clarinet/violin; gold says Caroline clarinet+violin, suggesting benchmark/entity ambiguity or conflict needing source audit. |

## Detailed Row Notes

### Row 24 — single-hop

- Question: `What books has Melanie read?`
- Ground truth: `"Nothing is Impossible", "Charlotte's Web"`
- Best score: `0.5` from `multi_temporal`
- Prediction: `Melanie has read "Charlotte's Web" as a favorite childhood book and a book Caroline recommended that inspires pursuing dreams.`
- Class: `retrieval_context_miss_partial_evidence`
- Term scan in pinned context: `Charlotte:1`
- Interpretation: Only Charlotte's Web found in pinned context; Nothing is Impossible absent. Shape cannot recover missing book.

### Row 41 — single-hop

- Question: `How many times has Melanie gone to the beach in 2023?`
- Ground truth: `2`
- Best score: `0.0` from `multi_temporal`
- Prediction: `I don't know.`
- Class: `retrieval_context_miss`
- Term scan in pinned context: `none`
- Interpretation: Gold count is 2; beach term absent from pinned context; answer abstains.

### Row 113 — unanswerable

- Question: `What did Mel and her kids paint in their latest project in July 2023?`
- Ground truth: `a sunset with a palm tree`
- Best score: `0.0` from `multi_temporal`
- Prediction: `Mel and her kids painted a nature-inspired painting featuring lovely flowers in their latest project in July 2023.`
- Class: `retrieval_context_miss_wrong_near_neighbor`
- Term scan in pinned context: `flower:1, latest:1`
- Interpretation: Context contains latest nature/flowers painting, but gold sunset with palm tree absent; likely stale/near-neighbor retrieval.

### Row 123 — unanswerable

- Question: `Why did Melanie choose to use colors and patterns in her pottery project?`
- Ground truth: `She wanted to catch the eye and make people smile.`
- Best score: `0.5` from `multi_temporal`
- Prediction: `Melanie used colors and patterns in her pottery project to express emotions, creativity, and self-expression.`
- Class: `retrieval_context_miss_or_wrong_evidence`
- Term scan in pinned context: `smile:1, colors:4`
- Interpretation: Gold phrase catch the eye / make people smile absent; retrieved context has generic colors/smile unrelated.

### Row 163 — adversarial

- Question: `What did Caroline and her family do while camping?`
- Ground truth: `explored nature, roasted marshmallows, and went on a hike`
- Best score: `0.5` from `multi_temporal`
- Prediction: `They roasted marshmallows and shared stories around the campfire.`
- Class: `retrieval_context_miss_partial_evidence`
- Term scan in pinned context: `marshmallows:1, nature:5, camping:5`
- Interpretation: Context has marshmallows/nature/camping but no hike; partial answer reflects missing event detail.

### Row 185 — adversarial

- Question: `What type of instrument does Caroline play?`
- Ground truth: `clarinet and violin`
- Best score: `0.0` from `multi_temporal`
- Prediction: `Caroline plays acoustic guitar.`
- Class: `entity_role_attribution_or_judge_mismatch`
- Term scan in pinned context: `clarinet:1, violin:1, guitar:4`
- Interpretation: Context contains Caroline acoustic guitar and Melanie clarinet/violin; gold says Caroline clarinet+violin, suggesting benchmark/entity ambiguity or conflict needing source audit.

## Intervention Map

Immediate default-off/eval-only candidates:

1. `retrieval_context_miss` / `partial_evidence` rows `24, 41, 113, 123, 163`
   - Need evidence coverage improvements, not more generic answer-shape prompting.
   - Candidate substrate work: canonical entities, event/time anchors, query-time entity/event expansion, expected-answer object coverage telemetry.
   - Add diagnostics that explicitly report missing gold object terms in pinned/final context where gold answers are known.

2. Row `185` entity/role ambiguity
   - Context supports Caroline acoustic guitar and Melanie clarinet/violin, while gold says Caroline clarinet+violin.
   - Treat as entity/role attribution or benchmark/source ambiguity until source dialogue is manually verified.
   - Do not tune against this row blindly; first audit source refs and expected-answer provenance.

3. Structured answer contract v0
   - Still justified by rows that recovered from shape (`39`, multi-hop/temporal rows in `20260504T182630Z`).
   - Should expose `answer_intent`, `answer_value`, extracted facts, entities, dates/counts/lists, provenance, abstention, conflicts, and confidence/source state.
   - This should be versioned/default-off for clients, not silently replacing prose behavior.

## Next Clean Diagnostic

Before any full LOCOMO or cumulative mode:

- Create an artifact-only `gold_object_coverage` diagnostic over the pinned 25-row artifacts.
- For each row, extract expected answer atoms from gold, scan final_context, and classify:
  - all atoms present
  - partial atoms present
  - no atoms present
  - contradictory/entity-conflicting atoms present
- Then select one default-off retrieval substrate intervention for rows with absent/partial atoms.

This keeps the next step comparable, cheap, and aligned with the Hippocampus architecture signal without overclaiming external benchmark comparability.
