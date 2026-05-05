# LOCOMO Entity/Time Expansion Precision Audit — 20260505T115852Z

Mode: artifact-only; no DB/Docker/runtime mutation; no benchmark rerun.

## Inputs
- Treatment artifact: `locomo_context_packet_canary_treatment_merge_refgate_frozen_artifactctx_shaped_multihop_temporal_goldcov_enttimeexp_20260505T115852Z.json`
- Baseline artifact: `locomo_context_packet_canary_baseline_20260505T115852Z.json`
- Summary artifact: `locomo_context_packet_canary_summary_merge_refgate_frozen_artifactctx_shaped_multihop_temporal_goldcov_enttimeexp_20260505T115852Z.json`

## Headline

- Added candidates: `19` across `14` rows.
- Coverage-class changes: `0`.
- Previously missing gold atoms recovered by added candidates: `0`.
- Main diagnosis: current gate is mechanically valid but too weak semantically; entity-name + nearby-turn admits topic-neighbor noise.
- Row 163 note: no candidates were added; its failure is role/subject attribution despite all gold atoms present, not expansion addition harm.

## Added-candidate classification counts
- `irrelevant_or_wrong_temporal_neighbor`: 8
- `irrelevant_topic_noise`: 6
- `supportive_inference_not_gold_literal`: 2
- `supportive_context_not_answer_object`: 1
- `mixed_related_extra_beach_context`: 1
- `neutral_no_gold_or_conflict`: 1

## Row-level audit

| Row | Cat | Score | Added | Coverage before→after | Classification | Question |
|---:|---|---:|---:|---|---|---|
| 5 | single-hop | 1.0 | 1 | no_atoms_present→no_atoms_present | irrelevant_topic_noise:1 | What is Caroline's identity? |
| 24 | single-hop | 0.5 | 2 | partial_atoms_present→partial_atoms_present | irrelevant_topic_noise:2 | What books has Melanie read? |
| 31 | multi-hop | 1.0 | 1 | no_atoms_present→no_atoms_present | supportive_context_not_answer_object:1 | Would Melanie be considered a member of the LGBTQ community? |
| 39 | single-hop | 0.5 | 2 | partial_atoms_present→partial_atoms_present | irrelevant_topic_noise:2 | What activities has Melanie done with her family? |
| 40 | single-hop | 1.0 | 1 | partial_atoms_present→partial_atoms_present | irrelevant_topic_noise:1 | In what ways is Caroline participating in the LGBTQ community? |
| 41 | single-hop | 0.5 | 1 | all_atoms_present→all_atoms_present | mixed_related_extra_beach_context:1 | How many times has Melanie gone to the beach in 2023? |
| 51 | multi-hop | 1.0 | 2 | no_atoms_present→no_atoms_present | supportive_inference_not_gold_literal:2 | What would Caroline's political leaning likely be? |
| 55 | temporal | 1.0 | 1 | no_atoms_present→no_atoms_present | neutral_no_gold_or_conflict:1 | When did Caroline draw a self-portrait? |
| 74 | temporal | 1.0 | 1 | all_atoms_present→all_atoms_present | irrelevant_or_wrong_temporal_neighbor:1 | When did Melanie get hurt? |
| 78 | multi-hop | 1.0 | 1 | no_atoms_present→no_atoms_present | irrelevant_or_wrong_temporal_neighbor:1 | Would Melanie go on another roadtrip soon? |
| 80 | temporal | 0.0 | 2 | no_atoms_present→no_atoms_present | irrelevant_or_wrong_temporal_neighbor:2 | When did Caroline pass the adoption interview? |
| 113 | unanswerable | 0.0 | 1 | no_atoms_present_conflicting_context→no_atoms_present_conflicting_context | irrelevant_or_wrong_temporal_neighbor:1 | What did Mel and her kids paint in their latest project in July 2023? |
| 123 | unanswerable | 0.5 | 0 | no_atoms_present_conflicting_context→no_atoms_present_conflicting_context | no_addition | Why did Melanie choose to use colors and patterns in her pottery project? |
| 128 | unanswerable | 1.0 | 1 | all_atoms_present→all_atoms_present | irrelevant_or_wrong_temporal_neighbor:1 | What did Caroline make for a local church? |
| 163 | adversarial | 0.0 | 0 | all_atoms_present→all_atoms_present | no_addition | What did Caroline and her family do while camping? |
| 172 | adversarial | 0.0 | 2 | no_atoms_present→no_atoms_present | irrelevant_or_wrong_temporal_neighbor:2 | What did Melanie see at the council meeting for adoption? |
| 185 | adversarial | 0.0 | 0 | all_atoms_present_with_conflicts→all_atoms_present_with_conflicts | no_addition | What type of instrument does Caroline play? |

## Added candidates

### Row 5 — irrelevant_topic_noise — mem_61d9a85cc27d
Question: What is Caroline's identity?
GT: Transgender woman
Pred: Caroline is a transgender woman.
Adds missing atoms: []; mentions atoms: []; conflicts: []
Refs: session=5 turns=0-9 nearest_base_turn_distance=1
Snippet: [3:31 pm on 23 August, 2023] Caroline: Hi Melanie! Hope you're doing good. Guess what I did this week? I took the first step towards becoming a mom - I applied to adoption agencies! It's a big decision, but I think I'm ready to give all my love to a child. I got lots of help from this adoption advice/assistance group I attended. It was great! | Melanie: Caroline, congrats! So proud of you for taking this step. How does it feel? Also, do you have any pets? | Caroline: Thanks, Mel! Exciting but ki

### Row 24 — irrelevant_topic_noise — mem_9e8127a47935
Question: What books has Melanie read?
GT: "Nothing is Impossible", "Charlotte's Web"
Pred: Melanie loved reading "Charlotte's Web" as a child.
Adds missing atoms: []; mentions atoms: []; conflicts: []
Refs: session=11 turns=0-9 nearest_base_turn_distance=1
Snippet: [9:55 am on 22 October, 2023] Caroline: Woohoo Melanie! I passed the adoption agency interviews last Friday! I'm so excited and thankful. This is a big move towards my goal of having a family. | Melanie: Congrats, Caroline! Adoption sounds awesome. I'm so happy for you. These figurines I bought yesterday remind me of family love. Tell me, what's your vision for the future? | Caroline: Thanks so much, Melanie! It's beautiful! It really brings home how much love's in families - both blood and the 

### Row 24 — irrelevant_topic_noise — mem_035231f14925
Question: What books has Melanie read?
GT: "Nothing is Impossible", "Charlotte's Web"
Pred: Melanie loved reading "Charlotte's Web" as a child.
Adds missing atoms: []; mentions atoms: []; conflicts: []
Refs: session=2 turns=0-9 nearest_base_turn_distance=1
Snippet: [8:56 pm on 20 July, 2023] Caroline: Hey Melanie! Just wanted to say hi! | Melanie: Hey Caroline! Good to talk to you again. What's up? Anything new since last time? | Caroline: Hey Mel! A lot's happened since we last chatted - I just joined a new LGBTQ activist group last Tues. I'm meeting so many cool people who are as passionate as I am about rights and community support. I'm giving my voice and making a real difference, plus it's fulfilling in so many ways. It's just great, you know? | Melan

### Row 31 — supportive_context_not_answer_object — mem_562b1c73b337
Question: Would Melanie be considered a member of the LGBTQ community?
GT: Likely no, she does not refer to herself as part of it
Pred: Likely no; the context shows Melanie supports Caroline, who is transgender and active in LGBTQ advocacy, but there is no indication Melanie identifies as LGBTQ herself.
Adds missing atoms: []; mentions atoms: []; conflicts: []
Refs: session=12 turns=10-16 nearest_base_turn_distance=1
Snippet: [1:14 pm on 25 May, 2023] Melanie: Wow, that agency looks great! What made you pick it? | Caroline: I chose them 'cause they help LGBTQ+ folks with adoption. Their inclusivity and support really spoke to me. | Melanie: That's great, Caroline! Loving the inclusivity and support. Anything you're excited for in the adoption process? | Caroline: I'm thrilled to make a family for kids who need one. It'll be tough as a single parent, but I'm up for the challenge! | Melanie: You're doing something amaz

### Row 39 — irrelevant_topic_noise — mem_9e8127a47935
Question: What activities has Melanie done with her family?
GT: Pottery, painting, camping, museum, swimming, hiking
Pred: Melanie has gone camping with her family, roasting marshmallows, telling stories around the campfire, watching the Perseid meteor shower, and spending time at the beach with her kids.
Adds missing atoms: []; mentions atoms: []; conflicts: []
Refs: session=11 turns=0-9 nearest_base_turn_distance=1
Snippet: [9:55 am on 22 October, 2023] Caroline: Woohoo Melanie! I passed the adoption agency interviews last Friday! I'm so excited and thankful. This is a big move towards my goal of having a family. | Melanie: Congrats, Caroline! Adoption sounds awesome. I'm so happy for you. These figurines I bought yesterday remind me of family love. Tell me, what's your vision for the future? | Caroline: Thanks so much, Melanie! It's beautiful! It really brings home how much love's in families - both blood and the 

### Row 39 — irrelevant_topic_noise — mem_035231f14925
Question: What activities has Melanie done with her family?
GT: Pottery, painting, camping, museum, swimming, hiking
Pred: Melanie has gone camping with her family, roasting marshmallows, telling stories around the campfire, watching the Perseid meteor shower, and spending time at the beach with her kids.
Adds missing atoms: []; mentions atoms: []; conflicts: []
Refs: session=2 turns=0-9 nearest_base_turn_distance=1
Snippet: [8:56 pm on 20 July, 2023] Caroline: Hey Melanie! Just wanted to say hi! | Melanie: Hey Caroline! Good to talk to you again. What's up? Anything new since last time? | Caroline: Hey Mel! A lot's happened since we last chatted - I just joined a new LGBTQ activist group last Tues. I'm meeting so many cool people who are as passionate as I am about rights and community support. I'm giving my voice and making a real difference, plus it's fulfilling in so many ways. It's just great, you know? | Melan

### Row 40 — irrelevant_topic_noise — mem_ab40259ed9db
Question: In what ways is Caroline participating in the LGBTQ community?
GT: Joining activist group, going to pride parades, participating in an art show, mentoring program
Pred: Caroline is participating in the LGBTQ community by joining an activist group, mentoring LGBTQ youth, speaking at school events about her transgender journey, attending pride parades, and being involved in support groups.
Adds missing atoms: []; mentions atoms: []; conflicts: []
Refs: session=2 turns=20-23 nearest_base_turn_distance=1
Snippet: [8:56 pm on 20 July, 2023] Caroline: Aw, that's sweet, Mel! Those milestones are great reminders of how special our bonds are. | Melanie: Yeah, they sure are. It's special moments like these that make me appreciate life and how lucky I am to be with my family and have our love. | Caroline: Wow, Melanie, what a beautiful moment! Lucky you to have such an awesome family! | Melanie: Thanks, Caroline! I'm really lucky to have my family; they bring so much joy and love.

### Row 41 — mixed_related_extra_beach_context — mem_824ed468a72a
Question: How many times has Melanie gone to the beach in 2023?
GT: 2
Pred: Melanie went to the beach once or twice in 2023.
Adds missing atoms: []; mentions atoms: ['beach']; conflicts: []
Refs: session=2 turns=10-19 nearest_base_turn_distance=1
Snippet: [8:56 pm on 20 July, 2023] Caroline: Sounds special, those beach trips! Do you have any other summer traditions you all do together? Create those memories! | Melanie: We always look forward to our family camping trip. We roast marshmallows, tell stories around the campfire and just enjoy each other's company. It's the highlight of our summer! | Caroline: Wow, Mel, that's awesome! What's your best camping memory? | Melanie: I'll always remember our camping trip last year when we saw the Perseid m

### Row 51 — supportive_inference_not_gold_literal — mem_8d80b22b2fb2
Question: What would Caroline's political leaning likely be?
GT: Liberal
Pred: Caroline's political leaning is likely progressive or left-leaning, as she is actively involved in LGBTQ activism, supports mental health awareness, advocates for LGBTQ rights, and promotes inclusivity and acceptance.
Adds missing atoms: []; mentions atoms: []; conflicts: []
Refs: session=1 turns=0-9 nearest_base_turn_distance=1
Snippet: [1:56 pm on 8 May, 2023] Caroline: Hey Mel! Good to see you! How have you been? | Melanie: Hey Caroline! Good to see you! I'm swamped with the kids & work. What's up with you? Anything new? | Caroline: I went to a LGBTQ support group yesterday and it was so powerful. | Melanie: Wow, that's cool, Caroline! What happened that was so awesome? Did you hear any inspiring stories? | Caroline: The transgender stories were so inspiring! I was so happy and thankful for all the support. | Melanie: Wow, lo

### Row 51 — supportive_inference_not_gold_literal — mem_035231f14925
Question: What would Caroline's political leaning likely be?
GT: Liberal
Pred: Caroline's political leaning is likely progressive or left-leaning, as she is actively involved in LGBTQ activism, supports mental health awareness, advocates for LGBTQ rights, and promotes inclusivity and acceptance.
Adds missing atoms: []; mentions atoms: []; conflicts: []
Refs: session=2 turns=0-9 nearest_base_turn_distance=1
Snippet: [8:56 pm on 20 July, 2023] Caroline: Hey Melanie! Just wanted to say hi! | Melanie: Hey Caroline! Good to talk to you again. What's up? Anything new since last time? | Caroline: Hey Mel! A lot's happened since we last chatted - I just joined a new LGBTQ activist group last Tues. I'm meeting so many cool people who are as passionate as I am about rights and community support. I'm giving my voice and making a real difference, plus it's fulfilling in so many ways. It's just great, you know? | Melan

### Row 55 — neutral_no_gold_or_conflict — mem_e048d7a36489
Question: When did Caroline draw a self-portrait?
GT: The week before 23 August 2023
Pred: Caroline drew a self-portrait last week before 23 August 2023.
Adds missing atoms: []; mentions atoms: []; conflicts: []
Refs: session=3 turns=0-9 nearest_base_turn_distance=1
Snippet: [2:24 pm on 14 August, 2023] Melanie: Hey Caroline! Last night was amazing! We celebrated my daughter's birthday with a concert surrounded by music, joy and the warm summer breeze. Seeing my kids' smiles was so awesome, and I'm so thankful for our special moments together. | Caroline: Wow, sounds wonderful! Your love for your kids is so awesome. What concert was it? The advocacy event was a cool experience - so much love and support, amazing! | Melanie: Thanks, Caroline! It was Matt Patterson, h

### Row 74 — irrelevant_or_wrong_temporal_neighbor — mem_8d80b22b2fb2
Question: When did Melanie get hurt?
GT: September 2023
Pred: Melanie got hurt last month before 13 October 2023.
Adds missing atoms: []; mentions atoms: []; conflicts: []
Refs: session=1 turns=0-9 nearest_base_turn_distance=1
Snippet: [1:56 pm on 8 May, 2023] Caroline: Hey Mel! Good to see you! How have you been? | Melanie: Hey Caroline! Good to see you! I'm swamped with the kids & work. What's up with you? Anything new? | Caroline: I went to a LGBTQ support group yesterday and it was so powerful. | Melanie: Wow, that's cool, Caroline! What happened that was so awesome? Did you hear any inspiring stories? | Caroline: The transgender stories were so inspiring! I was so happy and thankful for all the support. | Melanie: Wow, lo

### Row 78 — irrelevant_or_wrong_temporal_neighbor — mem_e048d7a36489
Question: Would Melanie go on another roadtrip soon?
GT: Likely no; since this one went badly
Pred: Likely no; Melanie said the roadtrip had a bad start with an accident that was a real scary experience.
Adds missing atoms: []; mentions atoms: []; conflicts: []
Refs: session=3 turns=0-9 nearest_base_turn_distance=1
Snippet: [2:24 pm on 14 August, 2023] Melanie: Hey Caroline! Last night was amazing! We celebrated my daughter's birthday with a concert surrounded by music, joy and the warm summer breeze. Seeing my kids' smiles was so awesome, and I'm so thankful for our special moments together. | Caroline: Wow, sounds wonderful! Your love for your kids is so awesome. What concert was it? The advocacy event was a cool experience - so much love and support, amazing! | Melanie: Thanks, Caroline! It was Matt Patterson, h

### Row 80 — irrelevant_or_wrong_temporal_neighbor — mem_035231f14925
Question: When did Caroline pass the adoption interview?
GT: The Friday before 22 October 2023
Pred: I don't know.
Adds missing atoms: []; mentions atoms: []; conflicts: []
Refs: session=2 turns=0-9 nearest_base_turn_distance=1
Snippet: [8:56 pm on 20 July, 2023] Caroline: Hey Melanie! Just wanted to say hi! | Melanie: Hey Caroline! Good to talk to you again. What's up? Anything new since last time? | Caroline: Hey Mel! A lot's happened since we last chatted - I just joined a new LGBTQ activist group last Tues. I'm meeting so many cool people who are as passionate as I am about rights and community support. I'm giving my voice and making a real difference, plus it's fulfilling in so many ways. It's just great, you know? | Melan

### Row 80 — irrelevant_or_wrong_temporal_neighbor — mem_ab40259ed9db
Question: When did Caroline pass the adoption interview?
GT: The Friday before 22 October 2023
Pred: I don't know.
Adds missing atoms: []; mentions atoms: []; conflicts: []
Refs: session=2 turns=20-23 nearest_base_turn_distance=1
Snippet: [8:56 pm on 20 July, 2023] Caroline: Aw, that's sweet, Mel! Those milestones are great reminders of how special our bonds are. | Melanie: Yeah, they sure are. It's special moments like these that make me appreciate life and how lucky I am to be with my family and have our love. | Caroline: Wow, Melanie, what a beautiful moment! Lucky you to have such an awesome family! | Melanie: Thanks, Caroline! I'm really lucky to have my family; they bring so much joy and love.

### Row 113 — irrelevant_or_wrong_temporal_neighbor — mem_9b079c82f34e
Question: What did Mel and her kids paint in their latest project in July 2023?
GT: a sunset with a palm tree
Pred: Mel and her kids painted a nature-inspired painting featuring lovely flowers in their latest project in July 2023.
Adds missing atoms: []; mentions atoms: []; conflicts: []
Refs: session=4 turns=20-20 nearest_base_turn_distance=1
Snippet: [1:50 pm on 17 August, 2023] Caroline: Yeah, Mel! Life's all about creating memories. Can't wait for the trip!

### Row 128 — irrelevant_or_wrong_temporal_neighbor — mem_946204d143a3
Question: What did Caroline make for a local church?
GT: a stained glass window
Pred: Caroline made a stained glass window for a local church.
Adds missing atoms: []; mentions atoms: []; conflicts: []
Refs: session=8 turns=10-19 nearest_base_turn_distance=1
Snippet: [12:09 am on 13 September, 2023] Caroline: I haven't done pottery yet, but I'm game for trying new art. I might try it sometime! Check out this piece I made! | Melanie: Wow, Caroline! This painting is awesome. Love the red and blue. What gave you the idea? | Caroline: Thanks, Melanie! I made this painting to show my path as a trans woman. The red and blue are for the binary gender system, and the mix of colors means smashing that rigid thinking. It's a reminder to love my authentic self - it's t

### Row 172 — irrelevant_or_wrong_temporal_neighbor — mem_035231f14925
Question: What did Melanie see at the council meeting for adoption?
GT: many people wanting to create loving homes for children in need
Pred: I don't know.
Adds missing atoms: []; mentions atoms: []; conflicts: []
Refs: session=2 turns=0-9 nearest_base_turn_distance=1
Snippet: [8:56 pm on 20 July, 2023] Caroline: Hey Melanie! Just wanted to say hi! | Melanie: Hey Caroline! Good to talk to you again. What's up? Anything new since last time? | Caroline: Hey Mel! A lot's happened since we last chatted - I just joined a new LGBTQ activist group last Tues. I'm meeting so many cool people who are as passionate as I am about rights and community support. I'm giving my voice and making a real difference, plus it's fulfilling in so many ways. It's just great, you know? | Melan

### Row 172 — irrelevant_or_wrong_temporal_neighbor — mem_ab40259ed9db
Question: What did Melanie see at the council meeting for adoption?
GT: many people wanting to create loving homes for children in need
Pred: I don't know.
Adds missing atoms: []; mentions atoms: []; conflicts: []
Refs: session=2 turns=20-23 nearest_base_turn_distance=1
Snippet: [8:56 pm on 20 July, 2023] Caroline: Aw, that's sweet, Mel! Those milestones are great reminders of how special our bonds are. | Melanie: Yeah, they sure are. It's special moments like these that make me appreciate life and how lucky I am to be with my family and have our love. | Caroline: Wow, Melanie, what a beautiful moment! Lucky you to have such an awesome family! | Melanie: Thanks, Caroline! I'm really lucky to have my family; they bring so much joy and love.

## Interpretation

The preservation fix should stay: artifact replay can now consume preserved non-duplicate candidate pools. But the current expansion rule should not be scaled as-is. It mostly picks same-speaker/name candidates near already retrieved context, without proving that the added content contains the missing object or resolves a conflict.

Recommended next intervention: default-off canary logic that only expands when coverage_before is missing atoms/conflicting, and ranks/filters candidates by expected-object lexical/semantic coverage or conflict reduction before entity/time proximity. Also separate adversarial subject-attribution handling for rows like 163/185; expansion alone is not the right tool there.
