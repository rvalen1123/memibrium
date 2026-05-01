# LOCOMO hybrid-active failure-mode audit — 2026-05-01

Repo: `/home/zaddy/src/Memibrium`  
Branch: `query-expansion`  
Audit preregistration: `docs/eval/locomo_hybrid_active_failure_mode_audit_preregistration_2026-05-01.md`  
Baseline result: `docs/eval/results/locomo_conv26_hybrid_active_substrate_baseline_2026-05-01.json`  
Support labels: `docs/eval/results/locomo_hybrid_active_failure_mode_audit_labels_2026-05-01.json`

## Executive conclusion

Scoped conclusion only: this active hybrid configuration, at this commit and canonical substrate, is under-retrieving for LOCOMO conv-26. Do not generalize to all hybrid retrieval, all Memibrium configs, other substrates, other commits, or full LOCOMO.

The dominant measured signature is under-context / recall-volume collapse. The baseline returns `n<=3` memories for 167/199 questions (83.92%), and that bucket scores 5.39%. The high-context buckets remain much stronger: `n=11-14` scores 55.00% and `n=15` scores 68.18%. Zero-score rows have mean `n_memories=3.16`; full-score rows have mean `n_memories=12.20`.

However, the committed baseline artifact does not preserve returned memory text, pre-threshold candidates, per-stream semantic/lexical hits, RRF scores, threshold decisions, or answer-context transfer traces. Therefore the audit can identify recall starvation at the final-context level but cannot distinguish candidate-fetch starvation from threshold/fusion cutoff or output-cap/context-transfer loss. Per preregistered decision rule, the stop/go decision is:

`go_telemetry_preregistration`

Recommendation confidence: moderate for “retrieval/context-volume problem exists”; insufficient evidence for selecting a specific retrieval implementation change before telemetry.

## Inputs and side-effect status

Read-only inputs used:

- committed baseline JSON/log and comparison writeup;
- committed source code: `benchmark_scripts/locomo_bench_v2.py` and `hybrid_retrieval.py`;
- pinned dial481/Penfield Labs artifacts under `docs/eval/phase_b_artifacts/locomo_audit_9493fb4b4af4256ed17a18e8fd0b3cfdeec29539/`;
- local LOCOMO dataset copy `/tmp/locomo/data/locomo10.json` only to map committed questions to static evidence refs/text.

No benchmark, smoke benchmark, retain/recall probe, DB write, cleanup, env edit, container restart/rebuild, schema mutation, or Phase C implementation was run.

## Baseline facts preserved

- 5-category overall: 14.82%
- Protocol 4-category overall: 19.41%
- Questions: 199
- Query expansion fallback: 0/199
- Avg query latency: 2478 ms
- Mean `n_memories`: 4.5327
- `n_memories == 15`: 22/199 (11.06%)
- Recovered stale-live-path floor: 66.08%, mean `n_memories=13.1608`, `n=15` saturation 31.16%

## Overall n_memories distribution

|n_memories|count|score|zero|partial|full|abstentions|mean latency ms|
|---|---:|---:|---:|---:|---:|---:|---:|
|2|57|4.39%|54|1|2|52|2238|
|3|110|5.91%|99|9|2|94|2361|
|11|1|50.00%|0|1|0|0|2895|
|12|3|50.00%|1|1|1|1|2967|
|13|3|50.00%|1|1|1|1|2896|
|14|3|66.67%|0|2|1|0|3245|
|15|22|68.18%|5|4|13|4|3435|


## n_memories buckets

|bucket|count|score|zero|partial|full|abstentions|mean latency ms|
|---|---:|---:|---:|---:|---:|---:|---:|
|n<=3|167|5.39%|153|10|4|146|2319|
|n=11-14|10|55.00%|2|5|3|2|3022|
|n=15|22|68.18%|5|4|13|4|3435|


Interpretation: there are no rows in the middle `n=4-10` bucket. The system mostly returns either 2-3 memories or near-cap context. This makes the score gradient unusually sharp and supports a final-context recall-volume diagnosis.

## Per-category score, n_memories, saturation, zero-score, abstention

|category|count|score|mean n|median n|n=15 saturation|zero-score|abstentions|
|---|---:|---:|---:|---:|---:|---:|---:|
|adversarial|47|0.00%|2.62|3|0 (0.00%)|47 (100.00%)|47|
|multi-hop|13|30.77%|7.23|3|4 (30.77%)|8 (61.54%)|8|
|single-hop|32|26.56%|6.22|3.0|5 (15.62%)|18 (56.25%)|15|
|temporal|37|39.19%|8.14|3|13 (35.14%)|21 (56.76%)|19|
|unanswerable|70|3.57%|2.64|3.0|0 (0.00%)|66 (94.29%)|63|


## Per-category score-by-n sensitivity

|category|n bucket|count|score|zero|partial|full|abstentions|
|---|---:|---:|---:|---:|---:|---:|---:|
|adversarial|n<=3|47|0.00%|47|0|0|47|
|multi-hop|n<=3|8|31.25%|5|1|2|5|
|multi-hop|n=11-14|1|0.00%|1|0|0|1|
|multi-hop|n=15|4|37.50%|2|1|1|2|
|single-hop|n<=3|22|11.36%|17|5|0|14|
|single-hop|n=11-14|5|50.00%|1|3|1|1|
|single-hop|n=15|5|70.00%|0|3|2|0|
|temporal|n<=3|20|7.50%|18|1|1|17|
|temporal|n=11-14|4|75.00%|0|2|2|0|
|temporal|n=15|13|76.92%|3|0|10|2|
|unanswerable|n<=3|70|3.57%|66|3|1|63|


Category-specific observations:

- temporal: improves from 7.50% at `n<=3` to 75.00% at `n=11-14` and 76.92% at `n=15`; this is the strongest recall-volume sensitivity.
- single-hop: improves from 11.36% at `n<=3` to 50.00% at `n=11-14` and 70.00% at `n=15`.
- multi-hop: mixed because the bucket is small; `n<=3` includes a few successes, while high-n has unresolved abstentions and negative-inference failures.
- unanswerable: all 70 rows are `n<=3`; this artifact cannot test whether more context helps or harms unanswerable.
- adversarial: all 47 rows are `n<=3`, all abstain, all score 0; this artifact cannot separate adversarial handling from missing context or evaluator/category mismatch.

## Query latency by score and n bucket

|score bucket|count|mean latency ms|median latency ms|
|---|---:|---:|---:|
|zero|160|2346|2228.5|
|partial|19|2873|2800|
|full|20|3154|3199.5|


Latency rises with score and with high `n_memories`, likely because successful rows traverse and synthesize larger contexts. This is descriptive only, not a causal performance diagnosis.

## Abstentions / “I don't know”

Total abstentions: 152/199.

Abstentions by category:

|category|abstentions|count|abstention rate|score among abstentions|
|---|---:|---:|---:|---:|
|adversarial|47|47|100.00%|0.00%|
|multi-hop|8|13|61.54%|0.00%|
|single-hop|15|32|46.88%|0.00%|
|temporal|19|37|51.35%|0.00%|
|unanswerable|63|70|90.00%|0.00%|


Every abstention scored 0 in this baseline. Abstention is highly coupled to low final-context volume: 144/152 abstentions occur at `n<=3`.

## High-n zero-score cases: exhaustive labels

All zero-score rows with `n_memories >= 12` are listed below. This is the key diagnostic bucket for deciding whether recall recovery alone is sufficient.

|#|cat|n|score|Q|GT|Pred|primary label|
|---|---:|---:|---:|---:|---:|---:|---:|
|6|temporal|15|0.0|When did Melanie run a charity race?|The sunday before 25 May 2023|Melanie ran a charity race for mental health on Saturday, 20 May 2023.|adversarial_or_unanswerable_evaluator_format_mismatch|
|8|single-hop|13|0.0|What is Caroline's relationship status?|Single|I don't know.|insufficient_evidence_from_artifacts|
|15|multi-hop|12|0.0|Would Caroline still want to pursue counseling as a career if she h...|Likely no|I don't know.|insufficient_evidence_from_artifacts|
|22|temporal|15|0.0|When did Caroline have a picnic?|The week before 6 July 2023|I don't know.|insufficient_evidence_from_artifacts|
|27|temporal|15|0.0|When did Melanie read the book "nothing is impossible"?|2022|I don't know.|adversarial_or_unanswerable_evaluator_format_mismatch|
|28|multi-hop|15|0.0|Would Caroline pursue writing as a career option?|LIkely no; though she likes reading, she w...|I don't know.|insufficient_evidence_from_artifacts|
|31|multi-hop|15|0.0|Would Melanie be considered a member of the LGBTQ community?|Likely no, she does not refer to herself a...|I don't know.|adversarial_or_unanswerable_evaluator_format_mismatch|


High-n zero notes:

- #6 When did Melanie run a charity race?: adversarial_or_unanswerable_evaluator_format_mismatch; Prediction says Saturday 20 May 2023. Pinned errors.json says gold Sunday is wrong; correct answer is Saturday before 25 May. Current baseline score 0 is evaluator/gold mismatch, not retrieval failure.
- #8 What is Caroline's relationship status?: insufficient_evidence_from_artifacts; source evidence is known from static LOCOMO refs, but returned-context text/pre-threshold traces are absent. With n=13 and abstention, the exact layer is unresolved.
- #15 Would Caroline still want to pursue counseling as a career if she hadn't received support growing up?: insufficient_evidence_from_artifacts; gold requires combining D4:15 and D3:5, but returned-context text is not preserved. Cannot distinguish missing context from synthesis failure.
- #22 When did Caroline have a picnic?: insufficient_evidence_from_artifacts; source evidence D6:11 says picnic last week, but absent context traces prevent distinguishing missing evidence from temporal synthesis failure.
- #27 When did Melanie read the book "nothing is impossible"?: adversarial_or_unanswerable_evaluator_format_mismatch; Pinned errors.json says the title is fabricated; 2022 is inferable for an unnamed book, but the question premise is flawed. Abstention at n=15 is plausibly defensible under corrected interpretation.
- #28 Would Caroline pursue writing as a career option?: insufficient_evidence_from_artifacts; source evidence requires contrasting career intent (D7:5) with love of reading (D7:9), but returned-context text is unavailable, so retrieval vs synthesis cannot be classified.
- #31 Would Melanie be considered a member of the LGBTQ community?: adversarial_or_unanswerable_evaluator_format_mismatch; Gold is a negative inference from absence of self-identification; no explicit evidence refs. Abstention may be semantically appropriate, but current judge scores 0 against “Likely no”.

Interpretation: high-n zero cases are mixed. Three are clear or likely evaluator/gold-format/negative-inference issues (#6, #27, and #31). The remaining high-n abstentions show source evidence exists in static LOCOMO refs, but the baseline artifact does not show whether that evidence was in returned context. This argues against immediately implementing synthesis-only fixes, but also prevents choosing a precise retrieval-layer knob.

## n=15 complete table

|#|cat|n|score|Q|GT|Pred|primary label|
|---|---:|---:|---:|---:|---:|---:|---:|
|1|temporal|15|1.0|When did Caroline go to the LGBTQ support group?|7 May 2023|Caroline went to the LGBTQ support group on 7 May 2023 (the day bef...|success_control|
|2|temporal|15|1.0|When did Melanie paint a sunrise?|2022|Melanie painted a lake sunrise last year, as mentioned in the conve...|success_control|
|3|multi-hop|15|0.5|What fields would Caroline be likely to pursue in her educaton?|Psychology, counseling certification|Caroline is likely to pursue education in counseling or mental health.|success_control|
|4|single-hop|15|0.5|What did Caroline research?|Adoption agencies|Caroline researched adoption agencies and career options in counsel...|success_control|
|5|single-hop|15|1.0|What is Caroline's identity?|Transgender woman|Caroline is a transgender woman.|success_control|
|6|temporal|15|0.0|When did Melanie run a charity race?|The sunday before 25 May 2023|Melanie ran a charity race for mental health on Saturday, 20 May 2023.|adversarial_or_unanswerable_evaluator_format_mismatch|
|7|temporal|15|1.0|When is Melanie planning on going camping?|June 2023|Melanie is planning on going camping next month from 25 May, 2023, ...|success_control|
|9|temporal|15|1.0|When did Caroline give a speech at a school?|The week before 9 June 2023|Caroline gave a speech at a school in early June 2023, before 9 Jun...|success_control|
|13|temporal|15|1.0|How long ago was Caroline's 18th birthday?|10 years ago|Caroline's 18th birthday was ten years ago.|success_control|
|14|single-hop|15|1.0|What career path has Caroline decided to persue?|counseling or mental health for Transgende...|Caroline has decided to pursue a career in counseling or mental hea...|success_control|
|16|single-hop|15|0.5|What activities does Melanie partake in?|pottery, camping, painting, swimming|Melanie partakes in camping with her family, running, reading, play...|success_control|
|18|temporal|15|1.0|When is Caroline going to the transgender conference?|July 2023|Caroline is going to the transgender conference in July 2023.|success_control|
|20|single-hop|15|0.5|What do Melanie's kids like?|dinosaurs, nature|Melanie's kids like pottery, painting (especially nature-inspired a...|success_control|
|21|temporal|15|1.0|When did Melanie go to the museum?|5 July 2023|Melanie went to the museum on 5 July, 2023 (the day before 6 July, ...|success_control|
|22|temporal|15|0.0|When did Caroline have a picnic?|The week before 6 July 2023|I don't know.|insufficient_evidence_from_artifacts|
|23|multi-hop|15|1.0|Would Caroline likely have Dr. Seuss books on her bookshelf?|Yes, since she collects classic children's...|Yes, Caroline likely has Dr. Seuss books on her bookshelf as she me...|success_control|
|26|temporal|15|1.0|When did Caroline go to the LGBTQ conference?|10 July 2023|Caroline went to the LGBTQ conference on 10 July 2023 (two days bef...|success_control|
|27|temporal|15|0.0|When did Melanie read the book "nothing is impossible"?|2022|I don't know.|adversarial_or_unanswerable_evaluator_format_mismatch|
|28|multi-hop|15|0.0|Would Caroline pursue writing as a career option?|LIkely no; though she likes reading, she w...|I don't know.|insufficient_evidence_from_artifacts|
|29|temporal|15|1.0|When did Caroline go to the adoption meeting?|The friday before 15 July 2023|Caroline went to the adoption council meeting last Friday before 15...|success_control|
|30|temporal|15|1.0|When did Melanie go to the pottery workshop?|The Friday before 15 July 2023|Melanie went to the pottery workshop on 14 July 2023.|success_control|
|31|multi-hop|15|0.0|Would Melanie be considered a member of the LGBTQ community?|Likely no, she does not refer to herself a...|I don't know.|adversarial_or_unanswerable_evaluator_format_mismatch|


At `n=15`, score is high overall (68.18%) but not perfect: 5/22 are zero. This supports “more context is usually necessary and often sufficient,” not “more context alone guarantees success.”

## Low-n zero-score stratified sample

|#|cat|n|score|Q|GT|Pred|primary label|
|---|---:|---:|---:|---:|---:|---:|---:|
|36|temporal|3|0.0|When did Melanie go camping in July?|two weekends before 17 July 2023|I don't know.|retrieval_starvation_candidate_fetch|
|37|temporal|3|0.0|When did Caroline join a mentorship program?|The weekend before 17 July 2023|I don't know.|retrieval_starvation_candidate_fetch|
|45|temporal|2|0.0|When is Melanie's daughter's birthday?|13 August|I don't know.|retrieval_starvation_candidate_fetch|
|35|single-hop|3|0.0|What events has Caroline participated in to help children?|Mentoring program, school speech|I don't know.|retrieval_starvation_candidate_fetch|
|38|single-hop|3|0.0|What did Melanie paint recently?|sunset|I don't know.|retrieval_starvation_candidate_fetch|
|39|single-hop|2|0.0|What activities has Melanie done with her family?|Pottery, painting, camping, museum, swimmi...|Melanie has taken her kids to the beach once or twice a year, which...|evidence_present_synthesis_failed|
|43|multi-hop|3|0.0|Would Melanie be more interested in going to a national park or a t...|National park; she likes the outdoors|I don't know.|retrieval_starvation_candidate_fetch|
|60|multi-hop|3|0.0|Would Caroline be considered religious?|Somewhat, but not extremely religious|I don't know.|retrieval_starvation_candidate_fetch|
|65|multi-hop|2|0.0|Would Melanie likely enjoy the song "The Four Seasons" by Vivaldi?|Yes; it's classical music|I don't know.|retrieval_starvation_candidate_fetch|
|83|unanswerable|3|0.0|What did the charity race raise awareness for?|mental health|I don't know.|retrieval_starvation_candidate_fetch|
|84|unanswerable|2|0.0|What did Melanie realize after the charity race?|self-care is important|I don't know.|retrieval_starvation_candidate_fetch|
|85|unanswerable|2|0.0|How does Melanie prioritize self-care?|by carving out some me-time each day for a...|I don't know.|retrieval_starvation_candidate_fetch|
|153|adversarial|3|0.0|What did Caroline realize after her charity race?|self-care is important|I don't know.|retrieval_starvation_candidate_fetch|
|154|adversarial|2|0.0|What are Melanie's plans for the summer with respect to adoption?|researching adoption agencies|I don't know.|retrieval_starvation_candidate_fetch|
|155|adversarial|2|0.0|What type of individuals does the adoption agency Melanie is consid...|LGBTQ+ individuals|I don't know.|retrieval_starvation_candidate_fetch|


Low-n zero failures are mostly abstentions and are consistent with final-context retrieval starvation. Because low-n failures are numerous and predictable, they should not dominate Phase C design beyond justifying telemetry and recall calibration investigation.

## Unanswerable stratified sample

The unanswerable category is not actually “unanswerable” in the sense of lacking gold answers in the harness; rows have ground-truth answers and are judged against them. In this baseline, all unanswerable rows have `n<=3`, so the preregistered question “does more context help or hurt unanswerable?” cannot be answered from this artifact.

|#|cat|n|score|Q|GT|Pred|primary label|
|---|---:|---:|---:|---:|---:|---:|---:|
|98|unanswerable|3|0.5|What workshop did Caroline attend recently?|LGBTQ+ counseling workshop|Caroline attended an LGBTQ support group.|success_control|
|101|unanswerable|3|0.5|What kind of place does Caroline want to create for people?|a safe and inviting place for people to grow|Caroline wants to create a supportive and accepting place for peopl...|success_control|
|118|unanswerable|2|1.0|How often does Melanie go to the beach with her kids?|once or twice a year|Melanie goes to the beach with her kids usually only once or twice ...|success_control|
|143|unanswerable|3|0.5|How do Melanie and Caroline describe their journey through life tog...|An ongoing adventure of learning and growing.|Melanie and Caroline describe their journey through life together a...|success_control|
|86|unanswerable|3|0.0|What are Caroline's plans for the summer?|researching adoption agencies|Caroline plans to continue her education, explore career options, a...|genuine_adversarial_or_unanswerable_handling_failure|
|99|unanswerable|2|0.0|What was discussed in the LGBTQ+ counseling workshop?|therapeutic methods and how to best work w...|The workshop included inspiring transgender stories and provided su...|genuine_adversarial_or_unanswerable_handling_failure|
|152|unanswerable|3|0.0|What did Melanie do after the road trip to relax?|Went on a nature walk or hike|Melanie went to the beach with her kids to relax after the road trip.|genuine_adversarial_or_unanswerable_handling_failure|
|83|unanswerable|3|0.0|What did the charity race raise awareness for?|mental health|I don't know.|retrieval_starvation_candidate_fetch|
|84|unanswerable|2|0.0|What did Melanie realize after the charity race?|self-care is important|I don't know.|retrieval_starvation_candidate_fetch|
|85|unanswerable|2|0.0|How does Melanie prioritize self-care?|by carving out some me-time each day for a...|I don't know.|retrieval_starvation_candidate_fetch|
|87|unanswerable|3|0.0|What type of individuals does the adoption agency Caroline is consi...|LGBTQ+ individuals|I don't know.|retrieval_starvation_candidate_fetch|
|88|unanswerable|3|0.0|Why did Caroline choose the adoption agency?|because of their inclusivity and support f...|I don't know.|retrieval_starvation_candidate_fetch|
|89|unanswerable|3|0.0|What is Caroline excited about in the adoption process?|creating a family for kids who need one|I don't know.|retrieval_starvation_candidate_fetch|
|90|unanswerable|3|0.0|What does Melanie think about Caroline's decision to adopt?|she thinks Caroline is doing something ama...|I don't know.|retrieval_starvation_candidate_fetch|
|91|unanswerable|3|0.0|How long have Mel and her husband been married?|Mel and her husband have been married for ...|I don't know.|retrieval_starvation_candidate_fetch|


Unanswerable summary: 70/70 are `n<=3`; score is 3.57%; 63/70 abstain. Any global recall expansion should still be gated by telemetry because the artifact provides no high-context unanswerable counterfactual.

## Adversarial / evaluator-format sub-audit

Adversarial baseline result: 0/47, all `n<=3`, all abstentions.

Pinned artifact mapping:

- baseline exact matches in `answer_key.json`: 152/199
- baseline adversarial exact matches in `answer_key.json`: 0/47
- baseline exact matches in `errors.json`: 27/199
- baseline adversarial exact matches in `errors.json`: 0/47

The pinned Penfield/dial481 `answer_key.json` and scored reference artifacts contain categories 1-4 from the published/open-domain framing, not the harness-generated adversarial category-5 rows. Therefore this audit cannot map the 47 adversarial rows to corrected answer outcomes from pinned artifacts. The correct label for the adversarial subset is unresolved: it mixes final-context starvation (`n<=3` + abstention) with possible evaluator/category-format mismatch, but the existing pinned artifacts do not distinguish them.

Full adversarial table:

|#|n|score|abstain|question|ground truth|evidence refs|primary label|
|---|---:|---:|---:|---:|---:|---:|---:|
|153|3|0.0|Y|What did Caroline realize after her charity race?|self-care is important|D2:3|retrieval_starvation_candidate_fetch|
|154|2|0.0|Y|What are Melanie's plans for the summer with respect to adoption?|researching adoption agencies|D2:8|retrieval_starvation_candidate_fetch|
|155|2|0.0|Y|What type of individuals does the adoption agency Melanie is considering support|LGBTQ+ individuals|D2:12|retrieval_starvation_candidate_fetch|
|156|2|0.0|Y|Why did Melanie choose the adoption agency?|because of their inclusivity and support for LGBTQ|D2:12|retrieval_starvation_candidate_fetch|
|157|2|0.0|Y|What is Melanie excited about in her adoption process?|creating a family for kids who need one|D2:14|retrieval_starvation_candidate_fetch|
|158|2|0.0|Y|What does Melanie's necklace symbolize?|love, faith, and strength|D4:3|retrieval_starvation_candidate_fetch|
|159|2|0.0|Y|What country is Melanie's grandma from?|Sweden|D4:3|retrieval_starvation_candidate_fetch|
|160|2|0.0|Y|What was grandma's gift to Melanie?|necklace|D4:3|retrieval_starvation_candidate_fetch|
|161|3|0.0|Y|What was grandpa's gift to Caroline?|necklace|D4:3|retrieval_starvation_candidate_fetch|
|162|3|0.0|Y|What is Caroline's hand-painted bowl a reminder of?|art and self-expression|D4:5|retrieval_starvation_candidate_fetch|
|163|3|0.0|Y|What did Caroline and her family do while camping?|explored nature, roasted marshmallows, and went on|D4:8|retrieval_starvation_candidate_fetch|
|164|2|0.0|Y|What kind of counseling and mental health services is Melanie interested in purs|working with trans people, helping them accept the|D4:13|retrieval_starvation_candidate_fetch|
|165|2|0.0|Y|What kind of counseling workshop did Melanie attend recently?|LGBTQ+ counseling workshop|D4:13|retrieval_starvation_candidate_fetch|
|166|2|0.0|Y|What motivated Melanie to pursue counseling?|her own journey and the support she received, and |D4:15|retrieval_starvation_candidate_fetch|
|167|3|0.0|Y|What kind of place does Melanie want to create for people?|a safe and inviting place for people to grow|D4:15|retrieval_starvation_candidate_fetch|
|168|3|0.0|Y|Did Caroline make the black and white bowl in the photo?|No|D5:8|retrieval_starvation_candidate_fetch|
|169|3|0.0|Y|What are the new shoes that Caroline got used for?|Running|D7:19|retrieval_starvation_candidate_fetch|
|170|3|0.0|Y|What is Caroline's reason for getting into running?|To de-stress and clear her mind|D7:21|retrieval_starvation_candidate_fetch|
|171|3|0.0|Y|What does Caroline say running has been great for?|Her mental health|D7:24|retrieval_starvation_candidate_fetch|
|172|2|0.0|Y|What did Melanie see at the council meeting for adoption?|many people wanting to create loving homes for chi|D8:9|retrieval_starvation_candidate_fetch|
|173|2|0.0|Y|What inspired Melanie's painting for the art show?|visiting an LGBTQ center and wanting to capture un|D9:16|retrieval_starvation_candidate_fetch|
|174|3|0.0|Y|What inspired Caroline's sculpture for the art show?|visiting an LGBTQ center and wanting to capture un|D9:16|retrieval_starvation_candidate_fetch|
|175|3|0.0|Y|How often does Caroline go to the beach with her kids?|once or twice a year|D10:10|retrieval_starvation_candidate_fetch|
|176|3|0.0|Y|What did Caroline and her family see during their camping trip last year?|Perseid meteor shower|D10:14|retrieval_starvation_candidate_fetch|
|177|3|0.0|Y|How did Caroline feel while watching the meteor shower?|in awe of the universe|D10:18|retrieval_starvation_candidate_fetch|
|178|3|0.0|Y|Why did Caroline choose to use colors and patterns in her pottery project?|She wanted to catch the eye and make people smile.|D12:6|retrieval_starvation_candidate_fetch|
|179|2|0.0|Y|Is Oscar Melanie's pet?|No|D13:3|retrieval_starvation_candidate_fetch|
|180|2|0.0|Y|Where did Oscar hide his bone once?|In Melanie's slipper|D13:6|retrieval_starvation_candidate_fetch|
|181|2|0.0|Y|What activity did Melanie used to do with her dad?|Horseback riding|D13:7|retrieval_starvation_candidate_fetch|
|182|3|0.0|Y|What did Melanie make for a local church?|a stained glass window|D14:17|retrieval_starvation_candidate_fetch|
|183|2|0.0|Y|What did Melanie find in her neighborhood during her walk?|a rainbow sidewalk|D14:23|retrieval_starvation_candidate_fetch|
|184|2|0.0|Y|Which song motivates Melanie to be courageous?|Brave by Sara Bareilles|D15:23|retrieval_starvation_candidate_fetch|
|185|3|0.0|Y|What type of instrument does Caroline play?|clarinet and violin|D15:26|retrieval_starvation_candidate_fetch|
|186|3|0.0|Y|Which classical musicians does Caroline enjoy listening to?|Bach and Mozart|D15:28|retrieval_starvation_candidate_fetch|
|187|3|0.0|Y|Who is Caroline a fan of in terms of modern music?|Ed Sheeran|D15:28|retrieval_starvation_candidate_fetch|
|188|3|0.0|Y|What precautionary sign did Caroline see at the café?|A sign stating that someone is not being able to l|D16:16|retrieval_starvation_candidate_fetch|
|189|3|0.0|Y|What setback did Caroline face recently?|She got hurt and had to take a break from pottery.|D17:8|retrieval_starvation_candidate_fetch|
|190|3|0.0|Y|What does Caroline do to keep herself busy during her pottery break?|Read a book and paint.|D17:10|retrieval_starvation_candidate_fetch|
|191|2|0.0|Y|What was the poetry reading that Melanie attended about?|It was a transgender poetry reading where transgen|D17:18|retrieval_starvation_candidate_fetch|
|192|3|0.0|Y|What happened to Caroline's son on their road trip?|He got into an accident|D18:1|retrieval_starvation_candidate_fetch|
|193|3|0.0|Y|How did Caroline's son handle the accident?|He was scared but reassured by his family|D18:6,D18:7|retrieval_starvation_candidate_fetch|
|194|3|0.0|Y|How did Caroline feel about her family after the accident?|They are important and mean the world to her|D18:5|retrieval_starvation_candidate_fetch|
|195|3|0.0|Y|How did Caroline's children handle the accident?|They were scared but resilient|D18:7|retrieval_starvation_candidate_fetch|
|196|3|0.0|Y|How did Caroline feel after the accident?|Grateful and thankful for her family|D18:5|retrieval_starvation_candidate_fetch|
|197|3|0.0|Y|What was Caroline's reaction to her children enjoying the Grand Canyon?|She was happy and thankful|D18:5|retrieval_starvation_candidate_fetch|
|198|3|0.0|Y|What did Caroline do after the road trip to relax?|Went on a nature walk or hike|D18:17|retrieval_starvation_candidate_fetch|
|199|3|0.0|Y|What does Caroline love most about camping with her family?|Being present and bonding with her family|D18:21|retrieval_starvation_candidate_fetch|


Adversarial decision: do not use the 0/47 adversarial result alone to justify Memibrium retrieval or synthesis changes. A telemetry/corrected-reporting preregistration should include explicit adversarial evidence/context traces and, if possible, a corrected semantic evaluator for category-5 rows.

## Temporal high-n failures

Temporal zero-score rows with `n_memories >= 12`:

|#|cat|n|score|Q|GT|Pred|primary label|
|---|---:|---:|---:|---:|---:|---:|---:|
|6|temporal|15|0.0|When did Melanie run a charity race?|The sunday before 25 May 2023|Melanie ran a charity race for mental health on Saturday, 20 May 2023.|adversarial_or_unanswerable_evaluator_format_mismatch|
|22|temporal|15|0.0|When did Caroline have a picnic?|The week before 6 July 2023|I don't know.|insufficient_evidence_from_artifacts|
|27|temporal|15|0.0|When did Melanie read the book "nothing is impossible"?|2022|I don't know.|adversarial_or_unanswerable_evaluator_format_mismatch|


Temporal high-n interpretation:

- “When did Melanie run a charity race?” is a pinned gold/evaluator error: the model predicted Saturday 20 May 2023, and `errors.json` says the correct answer is Saturday before 25 May, not Sunday.
- “When did Caroline have a picnic?” and “When did Melanie read the book ...” are abstentions despite high n. The latter is pinned as a hallucinated book-title premise; the former requires returned-context telemetry to distinguish missing evidence from temporal synthesis failure.

## Success controls

|#|cat|n|score|Q|GT|Pred|primary label|
|---|---:|---:|---:|---:|---:|---:|---:|
|33|single-hop|3|0.5|What LGBTQ+ events has Caroline participated in?|Pride parade, school speech, support group|Caroline joined an LGBTQ activist group called "Connected LGBTQ Act...|success_control|
|34|temporal|3|0.5|When did Caroline go to a pride parade during the summer?|The week before 3 July 2023|Caroline mentioned the pride parade took place last weekend before ...|success_control|
|40|single-hop|3|0.5|In what ways is Caroline participating in the LGBTQ community?|Joining activist group, going to pride par...|Caroline is participating in the LGBTQ community by joining an acti...|success_control|
|41|single-hop|2|0.5|How many times has Melanie gone to the beach in 2023?|2|Melanie has gone to the beach once or twice in 2023.|success_control|
|42|temporal|3|1.0|When did Caroline join a new activist group?|The Tuesday before 20 July 2023|Caroline joined a new LGBTQ activist group in the week before 20 Ju...|success_control|
|47|multi-hop|2|1.0|Would Melanie be considered an ally to the transgender community?|Yes, she is supportive|Yes, Melanie would be considered an ally to the transgender community.|success_control|
|48|single-hop|3|0.5|Who supports Caroline when she has a negative experience?|Her mentors, family, and friends|Caroline receives support from the LGBTQ support group she attends.|success_control|
|51|multi-hop|3|1.0|What would Caroline's political leaning likely be?|Liberal|Caroline's political leaning is likely progressive or left-leaning,...|success_control|
|57|single-hop|3|0.5|What symbols are important to Caroline?|Rainbow flag, transgender symbol|Flags and signs celebrating love and diversity are important symbol...|success_control|
|70|multi-hop|3|0.5|What personality traits might Melanie say Caroline has?|Thoughtful, authentic, driven|Melanie might say Caroline is passionate, courageous, supportive, i...|success_control|


Success controls show that some low-n cases can succeed and many high-n cases do succeed. The audit therefore avoids the simplistic rule “low n always fails / high n always succeeds”; still, the aggregate gradient is strong enough to prioritize context-volume telemetry.

## Source-code retrieval-layer diagnosis

Relevant source observations:

- `benchmark_scripts/locomo_bench_v2.py` uses `RECALL_TOP_K = 10` and `ANSWER_CONTEXT_TOP_K = 15`.
- With query expansion enabled, it calls `/mcp/recall` for each expanded query with `top_k=10`, dedupes returned memories, and passes up to 15 memories to the answer prompt.
- The saved baseline artifact only records `len(memories)` after this assembly.
- `hybrid_retrieval.py` fetches `fetch_k = top_k * 2` per stream (semantic, lexical, optional temporal), applies RRF fusion, optional multihop/chronology sorting, and returns `final[:top_k]` to the caller.

Because only final `n_memories` is saved, the audit cannot determine whether low final context came from:

1. too few semantic/lexical candidates fetched;
2. lexical query parsing / tsquery failure or BM25 fallback weakness;
3. RRF/fusion ranking or score normalization excluding relevant evidence;
4. output cap/context-transfer after enough candidates existed;
5. query expansion producing duplicate or low-yield recall results.

Therefore, the retrieval-layer distinction required by the preregistration remains unresolved from existing artifacts.

## Failure-label aggregate

Primary labels in support JSON:

|primary label|count|
|---|---:|
|adversarial_or_unanswerable_evaluator_format_mismatch|3|
|evidence_present_synthesis_failed|4|
|genuine_adversarial_or_unanswerable_handling_failure|3|
|insufficient_evidence_from_artifacts|4|
|retrieval_starvation_candidate_fetch|146|
|success_control|39|


Caveat: for non-sampled low-n failures, labels are conservative heuristic labels based on score, final `n_memories`, abstention, and category. The high-n zero labels are the decisive manual labels.

## Intervention-family recommendation

Recommended next step: `go_telemetry_preregistration`.

Rationale:

- Evidence strongly supports final-context under-retrieval / under-context as the dominant measured failure signature.
- But existing artifacts cannot distinguish candidate fetch starvation from threshold/fusion cutoff or output-cap/context-transfer loss.
- High-n failures include evaluator/gold-format problems and unresolved abstentions, so a blind global recall expansion or synthesis-only intervention would be under-justified.
- Adversarial 0/47 cannot be interpreted because pinned correction artifacts do not map category-5 rows and all adversarial rows have low n + abstention.

Recommended telemetry preregistration should capture, per question and expanded query, without changing retrieval behavior:

- expanded query strings;
- semantic, lexical, and temporal candidate counts before fusion;
- candidate ids/refs, scores, and ranks by stream;
- RRF/fused ranks and cutoff reason;
- final answer-context ids/refs and text hashes/snippets;
- whether gold evidence refs are present in candidates, fused top-k, and final answer context;
- adversarial/category-5 evidence-ref coverage and corrected semantic scoring notes.

## Explicit non-recommendations

- Do not implement Phase C retrieval calibration yet: final-context recall is implicated, but the specific layer is unresolved.
- Do not implement precision/context-pruning first: the main observed problem is too little context, not too much context.
- Do not implement synthesis-only fixes first: high-n zero cases are too few and mixed with evaluator/gold-format issues; returned-context evidence is absent.
- Do not treat adversarial 0/47 as pure Memibrium failure: pinned correction artifacts do not cover the generated adversarial rows, and all adversarial rows are low-n abstentions.
- Do not compare future interventions only to the stale legacy floor; compare to the committed canonical hybrid-active baseline and preserve retrieval-shape diagnostics.

## Stop/go decision

`go_telemetry_preregistration`

Phase C remains blocked until a new telemetry preregistration is written, approved as needed, executed, and reviewed. This audit report itself implements no Phase C intervention.
