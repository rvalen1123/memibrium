# LongMemEval oracle canary failure review — 2026-05-08

Scope: artifact-only review of scored run `20260508T040926Z`. No model calls, no prompt retuning, no new benchmark, no DB/Docker/runtime mutation.

## Executive conclusion

- Baseline beat treatment: `18/25` (`72%`) vs treatment `14/25` (`56%`).
- The treatment failure is not a broad LongMemEval blocker; it is a prompt-transfer failure from LOCOMO answer-shape rules into LongMemEval oracle mode.
- Main harmful mechanism: treatment increased abstention or partial enumeration on rows baseline already solved.
- Main shared blocker: `single-session-preference` uses rubric-style personalized recommendation judging; the current factual/insufficient oracle prompt is structurally mismatched and gets `0/4` in both arms.
- Knowledge-update needs a distinct stale/new conflict contract that preserves abstention for wrong-entity unanswerables; the current latest-fact directive can invert abstention.

## Outcome and mechanism counts

| bucket | count |
|---|---:|
| `both_wrong` | 6 |
| `same_correct` | 13 |
| `treatment_recovery` | 1 |
| `treatment_regression` | 5 |

| mechanism | count |
|---|---:|
| `abstention_inverted_by_latest-fact_directive` | 1 |
| `answer_shape_helped_exact_activity_date` | 1 |
| `calculation_abstention_after_correct_baseline` | 1 |
| `overcautious_insufficient_after_correct_baseline` | 1 |
| `partial_enumeration_missing_cost_item` | 1 |
| `preference_rubric_prompt_mismatch` | 4 |
| `stale_fact_selected_over_updated_fact` | 1 |
| `temporal_evidence_linking_miss` | 1 |
| `temporal_synthesis_abstention_after_correct_baseline` | 1 |

## Row-level failure classification

| # | qid | type | B | T | outcome | mechanism | rationale |
|---:|---|---|---:|---:|---|---|---|
| 1 | `0ddfec37_abs` | `knowledge-update` | 1 | 0 | `treatment_regression` | `abstention_inverted_by_latest-fact_directive` | Treatment converted an unanswerable football question into a baseball answer. Baseline correctly said insufficient. Mechanism: knowledge-update/treatment directive overrode abstention behavior; answer contains adjacent-but-wrong entity. |
| 3 | `852ce960` | `knowledge-update` | 0 | 0 | `both_wrong` | `stale_fact_selected_over_updated_fact` | Both arms answered $350,000 while ground truth is $400,000. This is a knowledge-update failure: stale evidence dominated over later update. |
| 4 | `eace081b` | `knowledge-update` | 1 | 0 | `treatment_regression` | `overcautious_insufficient_after_correct_baseline` | Baseline found Oahu; treatment said insufficient. Mechanism: treatment prompt likely increased abstention/precision threshold and suppressed usable evidence. |
| 7 | `3c1045c8` | `multi-session` | 1 | 0 | `treatment_regression` | `calculation_abstention_after_correct_baseline` | Baseline computed 2.5 years; treatment said insufficient. Mechanism: answer-shape directive did not help numeric synthesis and induced abstention. |
| 8 | `gpt4_731e37d7` | `multi-session` | 1 | 0 | `treatment_regression` | `partial_enumeration_missing_cost_item` | Baseline included $500 digital marketing workshop and reached $720; treatment omitted/misclassified that paid workshop and answered $220. Mechanism: list/count forcing caused partial enumeration/conflict with cost evidence. |
| 13 | `35a27287` | `single-session-preference` | 0 | 0 | `both_wrong` | `preference_rubric_prompt_mismatch` | Both arms said insufficient, but LongMemEval preference rows expect personalized recommendations using preferences. Mechanism: oracle prompt instructs direct factual answer/insufficient, mismatched to rubric-style generative personalization. |
| 14 | `06878be2` | `single-session-preference` | 0 | 0 | `both_wrong` | `preference_rubric_prompt_mismatch` | Both arms said insufficient for photography accessories, but rubric expects Sony/high-quality accessory suggestions from preference evidence. Mechanism: prompt mismatch, not retrieval. |
| 15 | `a89d7624` | `single-session-preference` | 0 | 0 | `both_wrong` | `preference_rubric_prompt_mismatch` | Both arms said insufficient for Denver suggestions, while rubric expects live-music/Brandon Flowers-aware recommendations. Mechanism: prompt mismatch to preference recommendation task. |
| 16 | `d6233ab6` | `single-session-preference` | 0 | 0 | `both_wrong` | `preference_rubric_prompt_mismatch` | Both arms said insufficient for reunion advice, while rubric expects advice grounded in positive high-school memories. Mechanism: prompt mismatch to personalized advice task. |
| 22 | `0db4c65d` | `temporal-reasoning` | 0 | 0 | `both_wrong` | `temporal_evidence_linking_miss` | Both arms said insufficient for days elapsed. Mechanism: temporal link across finish date and event date failed despite oracle evidence being available. |
| 23 | `b9cfe692` | `temporal-reasoning` | 1 | 0 | `treatment_regression` | `temporal_synthesis_abstention_after_correct_baseline` | Baseline computed 5.5 weeks; treatment said insufficient. Mechanism: answer-shape treatment increased abstention on temporal synthesis. |
| 24 | `gpt4_68e94288` | `temporal-reasoning` | 0 | 1 | `treatment_recovery` | `answer_shape_helped_exact_activity_date` | Baseline said insufficient; treatment answered #PlankChallenge with date and was judged correct. Mechanism: exact item/date directive helped one temporal row. |

## Detailed failure notes

### 1. `0ddfec37_abs` — `knowledge-update` — `treatment_regression`

- Mechanism: `abstention_inverted_by_latest-fact_directive`
- Question: How many autographed football have I added to my collection in the first three months of collection?
- Ground truth/rubric: The information provided is not enough. You mentioned collecting autographed baseball but not football.
- Baseline (correct): The information provided is not enough to determine how many autographed footballs you added to your collection in the first three months of collecting.
- Treatment (wrong): The evidence indicates that you added 15 autographed baseballs to your collection in the first three months of collecting.
- Rationale: Treatment converted an unanswerable football question into a baseball answer. Baseline correctly said insufficient. Mechanism: knowledge-update/treatment directive overrode abstention behavior; answer contains adjacent-but-wrong entity.

### 3. `852ce960` — `knowledge-update` — `both_wrong`

- Mechanism: `stale_fact_selected_over_updated_fact`
- Question: What was the amount I was pre-approved for when I got my mortgage from Wells Fargo?
- Ground truth/rubric: $400,000
- Baseline (wrong): The information provided indicates that you were pre-approved for $350,000 from Wells Fargo when you got your mortgage.
- Treatment (wrong): The amount you were pre-approved for when you got your mortgage from Wells Fargo was **$350,000**, as stated in the evidence from 2023/08/11.
- Rationale: Both arms answered $350,000 while ground truth is $400,000. This is a knowledge-update failure: stale evidence dominated over later update.

### 4. `eace081b` — `knowledge-update` — `treatment_regression`

- Mechanism: `overcautious_insufficient_after_correct_baseline`
- Question: Where am I planning to stay for my birthday trip to Hawaii?
- Ground truth/rubric: Oahu
- Baseline (correct): The information provided indicates that you are planning to stay on Oahu for your birthday trip to Hawaii.
- Treatment (wrong): The information provided is not enough to determine where you are planning to stay for your birthday trip to Hawaii.
- Rationale: Baseline found Oahu; treatment said insufficient. Mechanism: treatment prompt likely increased abstention/precision threshold and suppressed usable evidence.

### 7. `3c1045c8` — `multi-session` — `treatment_regression`

- Mechanism: `calculation_abstention_after_correct_baseline`
- Question: How much older am I than the average age of employees in my department?
- Ground truth/rubric: 2.5 years
- Baseline (correct): You are 2.5 years older than the average age of employees in your department.
- Treatment (wrong): The information provided is not enough.
- Rationale: Baseline computed 2.5 years; treatment said insufficient. Mechanism: answer-shape directive did not help numeric synthesis and induced abstention.

### 8. `gpt4_731e37d7` — `multi-session` — `treatment_regression`

- Mechanism: `partial_enumeration_missing_cost_item`
- Question: How much total money did I spend on attending workshops in the last four months?
- Ground truth/rubric: $720
- Baseline (correct): Based on the oracle evidence, you spent a total of **$720** on attending workshops in the last four months:

1. **Mindfulness workshop** (December 12): $20
2. **Writing workshop** (November): $200
3. **Digital marketing workshop** (March 15-16): $500

The photography workshop (February 22) was free, and no other paid workshops are mentioned.
- Treatment (wrong): The total money you spent on attending workshops in the last four months is **$220**. This includes:

1. **Mindfulness workshop** on December 12: $20  
2. **Writing workshop** in November: $200  

The other workshops mentioned (photography on February 22, digital marketing on March 15-16, and entrepreneurship in January) were free or no cost was specified.
- Rationale: Baseline included $500 digital marketing workshop and reached $720; treatment omitted/misclassified that paid workshop and answered $220. Mechanism: list/count forcing caused partial enumeration/conflict with cost evidence.

### 13. `35a27287` — `single-session-preference` — `both_wrong`

- Mechanism: `preference_rubric_prompt_mismatch`
- Question: Can you recommend some interesting cultural events happening around me this weekend?
- Ground truth/rubric: The user would prefer responses that suggest cultural events where they can practice their language skills, particularly Spanish and French. They would also appreciate if the event has a focus on language learning resources. They would not prefer events that do not provide opportunities for language practice or cultural exchange.
- Baseline (wrong): The information provided is not enough to recommend specific cultural events happening around you this weekend.
- Treatment (wrong): The information provided is not enough to recommend specific cultural events happening around you this weekend.
- Rationale: Both arms said insufficient, but LongMemEval preference rows expect personalized recommendations using preferences. Mechanism: oracle prompt instructs direct factual answer/insufficient, mismatched to rubric-style generative personalization.

### 14. `06878be2` — `single-session-preference` — `both_wrong`

- Mechanism: `preference_rubric_prompt_mismatch`
- Question: Can you suggest some accessories that would complement my current photography setup?
- Ground truth/rubric: The user would prefer suggestions of Sony-compatible accessories or high-quality photography gear that can enhance their photography experience. They may not prefer suggestions of other brands' equipment or low-quality gear.
- Baseline (wrong): The information provided is not enough to suggest accessories that would complement your current photography setup.
- Treatment (wrong): The information provided is not enough to suggest accessories that would complement your current photography setup.
- Rationale: Both arms said insufficient for photography accessories, but rubric expects Sony/high-quality accessory suggestions from preference evidence. Mechanism: prompt mismatch, not retrieval.

### 15. `a89d7624` — `single-session-preference` — `both_wrong`

- Mechanism: `preference_rubric_prompt_mismatch`
- Question: I'm planning a trip to Denver soon. Any suggestions on what to do there?
- Ground truth/rubric: The user would prefer responses that take into account their previous experience in Denver, specifically their interest in live music and memorable encounter with Brandon Flowers. They might appreciate suggestions that revisit or build upon this experience, such as revisiting the same bar or exploring similar music venues in the area. The user may not prefer general tourist recommendations or activities unrelated to their interest in live music.
- Baseline (wrong): The information provided is not enough.
- Treatment (wrong): The information provided is not enough.
- Rationale: Both arms said insufficient for Denver suggestions, while rubric expects live-music/Brandon Flowers-aware recommendations. Mechanism: prompt mismatch to preference recommendation task.

### 16. `d6233ab6` — `single-session-preference` — `both_wrong`

- Mechanism: `preference_rubric_prompt_mismatch`
- Question: I've been feeling nostalgic lately. Do you think it would be a good idea to attend my high school reunion?
- Ground truth/rubric: The user would prefer responses that draw upon their personal experiences and memories, specifically their positive high school experiences such as being part of the debate team and taking advanced placement courses. They would prefer suggestions that highlight the potential benefits of attending the reunion, such as reconnecting with old friends and revisiting favorite subjects like history and economics. The user might not prefer generic or vague responses that do not take into account their individual experiences and interests.
- Baseline (wrong): The information provided is not enough to determine whether attending your high school reunion would be a good idea.
- Treatment (wrong): The information provided is not enough to determine whether attending your high school reunion would be a good idea.
- Rationale: Both arms said insufficient for reunion advice, while rubric expects advice grounded in positive high-school memories. Mechanism: prompt mismatch to personalized advice task.

### 22. `0db4c65d` — `temporal-reasoning` — `both_wrong`

- Mechanism: `temporal_evidence_linking_miss`
- Question: How many days had passed since I finished reading 'The Seven Husbands of Evelyn Hugo' when I attended the book reading event at the local library, where the author of 'The Silent Patient' is discussing her latest thriller novel?
- Ground truth/rubric: 18 days. 19 days (including the last day) is also acceptable.
- Baseline (wrong): The information provided is not enough to determine how many days had passed between finishing "The Seven Husbands of Evelyn Hugo" and attending the book reading event.
- Treatment (wrong): The information provided is not enough to determine how many days had passed between finishing "The Seven Husbands of Evelyn Hugo" and attending the book reading event.
- Rationale: Both arms said insufficient for days elapsed. Mechanism: temporal link across finish date and event date failed despite oracle evidence being available.

### 23. `b9cfe692` — `temporal-reasoning` — `treatment_regression`

- Mechanism: `temporal_synthesis_abstention_after_correct_baseline`
- Question: How long did I take to finish 'The Seven Husbands of Evelyn Hugo' and 'The Nightingale' combined?
- Ground truth/rubric: 5.5 weeks
- Baseline (correct): You took a total of 5.5 weeks to finish "The Seven Husbands of Evelyn Hugo" (2.5 weeks) and "The Nightingale" (3 weeks) combined.
- Treatment (wrong): The information provided is not enough.
- Rationale: Baseline computed 5.5 weeks; treatment said insufficient. Mechanism: answer-shape treatment increased abstention on temporal synthesis.

### 24. `gpt4_68e94288` — `temporal-reasoning` — `treatment_recovery`

- Mechanism: `answer_shape_helped_exact_activity_date`
- Question: What was the social media activity I participated 5 days ago?
- Ground truth/rubric: You participated in a social media challenge called #PlankChallenge.
- Baseline (wrong): The information provided is not enough to determine the social media activity you participated in 5 days ago.
- Treatment (correct): #PlankChallenge on 2023/03/15 (Wed).
- Rationale: Baseline said insufficient; treatment answered #PlankChallenge with date and was judged correct. Mechanism: exact item/date directive helped one temporal row.

## Next preregistered intervention candidates

Do not retune directly on this score without preregistration. If continuing, split interventions by LongMemEval category rather than applying one LOCOMO-derived answer-shape globally:

1. `single-session-preference`: new preference-response mode that answers as a helpful recommender/advisor using personal evidence, not “insufficient” unless evidence truly lacks preferences.
2. `knowledge-update`: conflict contract that explicitly chooses latest matching entity/fact but keeps abstention when the asked entity is absent (e.g., football vs baseball).
3. `multi-session` / `temporal-reasoning`: avoid the current treatment’s over-abstention; preserve baseline prompt or use minimal arithmetic/list-completion support only when evidence is present.
4. Confirm with an artifact-pinned rerun or fresh same-slice baseline only after preregistering stochasticity handling; do not treat one 25-row score as a stable external claim.

## Guardrails

- Artifact-only: read existing dataset/artifacts only.
- No model calls or judge calls.
- No full LongMemEval `_s`/`_m` run.
- No DB/Docker/runtime mutation.
- No direct `/mcp/tools` inspection.

JSON companion artifact: `docs/eval/results/longmemeval_oracle_canary_failure_review_20260508T040926Z.json`.

