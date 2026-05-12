# LongMemEval oracle canary — category_contract_v1 second-slice artifact review

Date: 2026-05-08

## Scope

- Scored commit: `cfbf8d4 eval: score LongMemEval second oracle slice`
- Slice: `longmemeval_oracle_canary_25_second_slice_20260508`
- Dataset SHA256: `821a2034d219ab45846873dd14c14f12cfe7776e73527a483f9dac095d38620c`
- Selection artifact: `docs/eval/results/longmemeval_oracle_canary_25_second_slice_selection_20260508.json`
- Selection SHA256: `9cd322852a4e947730f811e6913012270e3bac9cc569b3394ee49e5b1d80edbb`
- Run directory: `docs/eval/results/longmemeval_oracle_canary_category_contract_second_slice_scored_20260508T132616Z`
- Artifact audit JSON: `docs/eval/results/longmemeval_oracle_canary_category_contract_second_slice_scored_20260508T132616Z/longmemeval_oracle_canary_second_slice_artifact_audit.json`

This review is artifact-only. It uses the existing scored predictions, existing eval JSONL, gate report, and pinned cleaned dataset evidence. It does not add model calls, judge calls, retrieval ingestion, DB/Docker/runtime mutation, or prompt retuning.

## Scored result recap

- Baseline: `16/25`
- Treatment, unchanged `category_contract_v1`: `19/25`
- Delta: `+3`
- Paired outcomes: `15` same-correct, `5` same-wrong, `4` recovered, `1` regressed
- Gate verdict: `PASS`

Correct framing:

> On a second preregistered 25-row LongMemEval oracle-evidence canary, unchanged `category_contract_v1` improved answer-side scoring from `16/25` to `19/25`, with all preregistered replication gates passing. The main mechanism signal again came from single-session preference recovery, `0/4 -> 4/4`. This is mechanism evidence only; retrieval remains untested.

## Mechanism summary

The second slice replicates the first-slice mechanism rather than broadening the claim:

1. All four moved wins are `single-session-preference` rows where the baseline abstained and `category_contract_v1` produced a personalized, rubric-aligned recommendation.
2. Knowledge-update did not regress in aggregate (`3/5 -> 3/5`), satisfying the preregistered hard watchpoint.
3. The one regressed row is temporal-reasoning, and artifact review suggests a fragile temporal/judge-answer issue rather than a preference-contract failure.
4. The remaining same-wrong rows split into shared temporal grounding failures, shared knowledge-update/premise-validation failures, and one assistant-turn extraction miss.

## Moved wins: preference recovery rows

| Row | Category | Outcome | Mechanism classification | Artifact interpretation |
| --- | --- | --- | --- | --- |
| `1da05512` | single-session-preference | recovered | personalized recommendation | Baseline abstained on whether to buy a NAS. Treatment used storage/security/external-drive context and gave a concrete NAS recommendation, matching the rubric's request for decision guidance grounded in current storage issues. |
| `1c0ddc50` | single-session-preference | recovered | activity-shape + negative constraint | Baseline abstained. Treatment suggested commute-safe audio activities and personalized toward history/science/podcasts rather than visually demanding activities. |
| `32260d93` | single-session-preference | recovered | platform/genre/storytelling constraint | Baseline abstained. Treatment recommended a Netflix stand-up/storytelling special, matching the rubric's platform and genre preference. |
| `06f04340` | single-session-preference | recovered | ingredient-grounded suggestion | Baseline abstained. Treatment used the homegrown cherry tomatoes, basil, and mint to propose dishes centered on those ingredients. |

Interpretation: this is the same answer-contract mechanism as the first slice. The contract converts preference questions from over-abstention to grounded, personalized recommendations. This is answer-side mechanism evidence only because the oracle prompt already includes the relevant evidence.

## Same-wrong and regressed rows

| Row | Category | Outcome | Gold | Baseline | Treatment | Classification |
| --- | --- | --- | --- | --- | --- | --- |
| `031748ae_abs` | knowledge-update | same-wrong | not enough information, because the role mentioned was Senior Software Engineer, not Software Engineer Manager | `5 engineers` | `5 engineers` | Shared benchmark-schema/premise-validation trap. Both arms answered adjacent Senior Software Engineer team-size facts for a question asking Software Engineer Manager. Not treatment-introduced. |
| `cc539528` | single-session-assistant | same-wrong | `Ruby, Python, or PHP` | abstained | abstained | Assistant-turn extraction/list recall miss. The gold appears in an assistant turn marked `has_answer`; both arms failed to extract it from oracle evidence. |
| `gpt4_61e13b3c` | temporal-reasoning | same-wrong | `3 weeks` | abstained | abstained | Temporal-link extraction/date arithmetic not triggered. Evidence dates are Farmers' Market `2023/02/26` and Spring Fling Market on `2023/03/20` via a `2023/03/21` yesterday reference. |
| `gpt4_2487a7cb` | temporal-reasoning | same-wrong | Data Analysis using Python webinar | Effective Time Management first | Effective Time Management first | Relative-date anchoring error. Question date is `2023/05/28`; webinar `two months ago` precedes workshop `last Saturday`. Treatment made the wrong anchoring explicit rather than correcting it. |
| `gpt4_78cf46a3` | temporal-reasoning | regressed | Receiving the new phone case | final choice says charger first, but includes the correct rationale that phone case about a month ago precedes charger loss two weeks ago; judge marked Yes | final choice says charger first with same date facts; judge marked No | Fragile temporal/judge-answer inconsistency. The row is counted as a regression by labels, but both final answers choose the wrong event despite stating date facts that imply the gold. Treat as temporal watchpoint, not a preference-contract failure. |
| `a2f3aa27` | knowledge-update | same-wrong | `1300` | abstained | abstained | Shared knowledge-update recency/confidence failure. Newer evidence says the user is close to 1300 after older 1250; both arms abstained. Not treatment-introduced. |

## Watchpoints

### Temporal-reasoning remains weak

Temporal-reasoning moved from `2/4` to `1/4`. The one labeled regression, `gpt4_78cf46a3`, is artifact-fragile because both answers state that the phone case was about a month ago and the charger loss about two weeks ago, yet both final choices say charger first. Still, the category-level drop is real in the scored artifact and should remain a watchpoint.

Do not fix this by retuning `category_contract_v1`. The failure layer is temporal-link extraction / relative-date grounding / final-choice consistency, not the preference contract.

### Knowledge-update passed the second-slice gate but still has shared failures

Knowledge-update was stable (`3/5 -> 3/5`), so the first-slice Oahu-style over-abstention did not repeat as an aggregate regression. However:

- `031748ae_abs` shows a premise-validation trap: role title changed from Senior Software Engineer evidence to Software Engineer Manager question wording.
- `a2f3aa27` shows under-answering on an approximate/current count where newer evidence implies `1300` after older `1250`.

These are not treatment-introduced regressions. They should be handled as separate knowledge-update/premise/recency calibration issues after the answer-contract replication summary is written up.

### Assistant-turn extraction is a separate gap

`cc539528` shows that both arms can miss a gold list from an assistant turn even in oracle evidence. That is not a retrieval failure and not specific to category_contract_v1. It points to extraction from assistant-authored recommendations/lists.

## Updated mechanism map

| Failure / signal | Layer | Treatment-introduced? | Contract can fix? | Notes |
| --- | --- | --- | --- | --- |
| Preference recoveries `1da05512`, `1c0ddc50`, `32260d93`, `06f04340` | Answer contract | Positive treatment effect | Already fixed by v1 on this slice | Replicates first-slice preference mechanism. |
| `031748ae_abs` role-title trap | Premise validation / knowledge-update | No | Maybe, but not a v1 retune target | Needs careful handling of question premise vs adjacent evidence. |
| `a2f3aa27` follower count abstention | Knowledge-update recency/confidence | No | Maybe | Shared under-answering on approximate current count. |
| `cc539528` assistant language list miss | Oracle-evidence extraction | No | Possibly via list extraction, but separate from preference contract | Gold is in assistant turn; both arms abstained. |
| `gpt4_61e13b3c` weeks between events | Temporal grounding | No | No | Date arithmetic/linking failure. |
| `gpt4_2487a7cb` event ordering | Temporal grounding | No | No | Relative-date anchoring failure. |
| `gpt4_78cf46a3` phone-case/charger regression | Temporal grounding + answer consistency + judge fragility | Labeled yes, mechanistically ambiguous | No | Treat as temporal watchpoint, not contract failure. |

## Recommendation

Do not retune `category_contract_v1` yet. The answer-contract mechanism has now replicated across two independent preregistered 25-row oracle-evidence slices:

- First slice: `18/25 -> 21/25`, preference `0/4 -> 3/4`
- Second slice: `16/25 -> 19/25`, preference `0/4 -> 4/4`, all preregistered gates passed

The next clean step should be a synthesis/writeup or a preregistered retrieval-coupled rung, not prompt tweaks. If moving beyond oracle evidence, preregister the retrieval-coupled design separately and keep oracle conclusions scoped as answer-side mechanism evidence only.
