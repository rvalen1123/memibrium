# LOCOMO Prefix-Rerank Harm Audit

Generated: `2026-04-26T13:05:40.860585+00:00`

## Scope

Audited paired cases where prior query expansion scored `1.0` and prefix-preserving rerank scored `<1.0`.

Harmed cases audited: `23`
LOCOMO memories ingested for replay: `49`
Expansion fallback during audit: `0`

## Primary mechanism counts

| Mechanism | Count |
|---|---:|
| evidence_dropped_by_context_budget | 13 |
| evidence_loss_or_demoted_to_idk | 10 |

## Category counts

| Category | Count |
|---|---:|
| 5 | 4 |
| multi-hop | 1 |
| single-hop | 3 |
| temporal | 3 |
| unanswerable | 12 |

## Key aggregate diagnostics

- Cases with any original context item dropped by prefix-rerank top-k fill: `23`
- Cases where answer became I-don't-know: `10`
- Cases with identical context IDs but worse answer: `0`
- Prefix preservation invariant failures: `0`

## Per-case audit

### 1. 5 — evidence_loss_or_demoted_to_idk

Question: How did Caroline feel about her family after the accident?

Ground truth: They are important and mean the world to her

Prior correct answer: Caroline felt that family is everything and emphasized how important loved ones are, appreciating their strength and support after the accident.

Prefix-rerank answer (score 0.0): I don't know.

Reasons: `context_changed_by_topk_fill, candidate_evidence_dropped, answer_became_idk`

Dropped original-context items: `4`; gained reranked items: `4`; candidate count: `23`

Dropped items with lexical overlap:
- overlap=5 id=mem_2e2f33d3e1ad: [1:36 pm on 3 July, 2023] Caroline: Since we last spoke, some big things have happened. the week of 26 June 2023 I went to an LGBTQ+ pride parade. Everyone was
- overlap=7 id=mem_88530bc8052a: [4:33 pm on 12 July, 2023] Caroline: Hey Mel, great to chat with you again! So much has happened since we last spoke - I went to an LGBTQ conference two days ag
- overlap=2 id=mem_d59c5bfdd76f: [4:33 pm on 12 July, 2023] Caroline: Wow! What got you into running? | Melanie: I've been running farther to de-stress, which has been great for my headspace. |
- overlap=8 id=mem_1fff4a1d5d5f: [1:51 pm on 15 July, 2023] Caroline: Hey Mel, what's up? Been a busy week since we talked. | Melanie: Hey Caroline, it's been super busy here. So much since we

### 2. 5 — evidence_loss_or_demoted_to_idk

Question: How did Caroline's children handle the accident?

Ground truth: They were scared but resilient

Prior correct answer: Caroline's children were scared but were reassured and told their brother would be okay; they are described as tough kids.

Prefix-rerank answer (score 0.0): I don't know.

Reasons: `context_changed_by_topk_fill, candidate_evidence_dropped, answer_became_idk`

Dropped original-context items: `4`; gained reranked items: `4`; candidate count: `24`

Dropped items with lexical overlap:
- overlap=4 id=mem_154237055da5: [1:14 pm on 25 May, 2023] Melanie: Hey Caroline, since we last chatted, I've had a lot of things happening to me. I ran a charity race for mental health 20 May
- overlap=2 id=mem_e63f2dbe0c2d: [10:37 am on 27 June, 2023] Caroline: Hey Melanie! Long time no talk! A lot's been going on in my life! Take a look at this. | Melanie: Hey, Caroline! Nice to h
- overlap=4 id=mem_736359d9be60: [10:37 am on 27 June, 2023] Caroline: Lately, I've been looking into counseling and mental health as a career. I want to help people who have gone through the s
- overlap=1 id=mem_96b225aa4bef: [1:36 pm on 3 July, 2023] Caroline: Wow, Mel, I'm so stoked for you that art is helping you express yourself and bring you joy! Keep it up! | Melanie: Thanks, C

### 3. 5 — evidence_dropped_by_context_budget

Question: What does Caroline do to keep herself busy during her pottery break?

Ground truth: Read a book and paint.

Prior correct answer: During her pottery break, Caroline keeps busy by painting and reading a book recommended by Melanie.

Prefix-rerank answer (score 0.0): Caroline keeps herself busy during her pottery break by learning the piano.

Reasons: `context_changed_by_topk_fill, candidate_evidence_dropped`

Dropped original-context items: `2`; gained reranked items: `2`; candidate count: `21`

Dropped items with lexical overlap:
- overlap=2 id=mem_2529911f8d3c: [7:55 pm on 9 June, 2023] Caroline: Sounds great, Mel! Glad you had a great time. Cherish the moments - they're the best! | Melanie: Absolutely, Caroline! I che
- overlap=2 id=mem_e63f2dbe0c2d: [10:37 am on 27 June, 2023] Caroline: Hey Melanie! Long time no talk! A lot's been going on in my life! Take a look at this. | Melanie: Hey, Caroline! Nice to h

### 4. 5 — evidence_loss_or_demoted_to_idk

Question: Which classical musicians does Caroline enjoy listening to?

Ground truth: Bach and Mozart

Prior correct answer: Caroline enjoys listening to classical musicians Bach and Mozart.

Prefix-rerank answer (score 0.0): I don't know.

Reasons: `context_changed_by_topk_fill, answer_became_idk`

Dropped original-context items: `8`; gained reranked items: `8`; candidate count: `37`

Dropped items with lexical overlap:
- overlap=1 id=mem_c172656a67b0: [7:55 pm on 9 June, 2023] Caroline: Hey Melanie! How's it going? I wanted to tell you about my school event the week of 02 June 2023. It was awesome! I talked a
- overlap=1 id=mem_d709c57af80c: [7:55 pm on 9 June, 2023] Caroline: Thanks, Mel! My friends, family and mentors are my rocks – they motivate me and give me the strength to push on. Here's a pi
- overlap=1 id=mem_e63f2dbe0c2d: [10:37 am on 27 June, 2023] Caroline: Hey Melanie! Long time no talk! A lot's been going on in my life! Take a look at this. | Melanie: Hey, Caroline! Nice to h
- overlap=1 id=mem_736359d9be60: [10:37 am on 27 June, 2023] Caroline: Lately, I've been looking into counseling and mental health as a career. I want to help people who have gone through the s
- overlap=1 id=mem_96b225aa4bef: [1:36 pm on 3 July, 2023] Caroline: Wow, Mel, I'm so stoked for you that art is helping you express yourself and bring you joy! Keep it up! | Melanie: Thanks, C

### 5. multi-hop — evidence_loss_or_demoted_to_idk

Question: Would Caroline likely have Dr. Seuss books on her bookshelf?

Ground truth: Yes, since she collects classic children's books

Prior correct answer: Yes, Caroline likely has Dr. Seuss books on her bookshelf as she mentioned having lots of kids' books including classics.

Prefix-rerank answer (score 0.0): I don't know.

Reasons: `context_changed_by_topk_fill, candidate_evidence_dropped, answer_became_idk, sensitive_category`

Dropped original-context items: `4`; gained reranked items: `4`; candidate count: `27`

Dropped items with lexical overlap:
- overlap=1 id=mem_843845841fff: [1:33 pm on 25 August, 2023] Caroline: Wow, Mel! Any more paintings coming up? | Melanie: I'm feeling inspired by autumn so I'm planning a few. You got any cool
- overlap=1 id=mem_2f5ddacb2b80: [10:31 am on 13 October, 2023] Caroline: The room was electric with energy and support! The posters were amazing, so much pride and strength! It inspired me to
- overlap=2 id=mem_66f2ae02d53b: [3:31 pm on 23 August, 2023] Caroline: Painting's great for expressing myself. I love creating art! Here's a recent self-portrait I made the week of 16 August 2
- overlap=1 id=mem_01bf237aa233: [1:33 pm on 25 August, 2023] Caroline: Thanks, Mel! Glad you like it. It's a symbol of togetherness, to celebrate differences and be that much closer. I'd love

### 6. single-hop — evidence_dropped_by_context_budget

Question: How many children does Melanie have?

Ground truth: 3

Prior correct answer: Melanie has three children.

Prefix-rerank answer (score 0.5): Melanie has multiple children, but the exact number is not specified.

Reasons: `context_changed_by_topk_fill, candidate_evidence_dropped`

Dropped original-context items: `5`; gained reranked items: `5`; candidate count: `28`

Dropped items with lexical overlap:
- overlap=2 id=mem_d59c5bfdd76f: [4:33 pm on 12 July, 2023] Caroline: Wow! What got you into running? | Melanie: I've been running farther to de-stress, which has been great for my headspace. |
- overlap=1 id=mem_d7ab1626d98b: [2:31 pm on 17 July, 2023] Melanie: Hey Caroline, hope all's good! I had a quiet weekend after we went camping with my fam the weekend of 08 July 2023. It was g
- overlap=1 id=mem_3cde9e6bbf55: [2:24 pm on 14 August, 2023] Melanie: Your art's amazing, Caroline. I love how you use it to tell your stories and teach people about trans folks. I'd love to s
- overlap=1 id=mem_e63f2dbe0c2d: [10:37 am on 27 June, 2023] Caroline: Hey Melanie! Long time no talk! A lot's been going on in my life! Take a look at this. | Melanie: Hey, Caroline! Nice to h
- overlap=1 id=mem_339f23536898: [1:56 pm on 8 May, 2023] Caroline: I'm keen on counseling or working in mental health - I'd love to support those with similar issues. | Melanie: You'd be a gre

### 7. single-hop — evidence_dropped_by_context_budget

Question: What activities has Melanie done with her family?

Ground truth: Pottery, painting, camping, museum, swimming, hiking

Prior correct answer: Melanie has done camping trips, hiking, roasting marshmallows around campfires, pottery workshops, painting nature-inspired art, beach outings, museum visits, and family games and meals together.

Prefix-rerank answer (score 0.5): Melanie has done camping trips, hiking in mountains and forests, roasting marshmallows around campfires, exploring nature, going to the beach, visiting museums (like a dinosaur exhibit), and spending time at parks with her kids.

Reasons: `context_changed_by_topk_fill, candidate_evidence_dropped`

Dropped original-context items: `4`; gained reranked items: `4`; candidate count: `29`

Dropped items with lexical overlap:
- overlap=3 id=mem_339f23536898: [1:56 pm on 8 May, 2023] Caroline: I'm keen on counseling or working in mental health - I'd love to support those with similar issues. | Melanie: You'd be a gre
- overlap=0 id=mem_4b4c956b5f6e: [1:50 pm on 17 August, 2023] Caroline: Yeah, Mel! Life's all about creating memories. Can't wait for the trip!
- overlap=3 id=mem_b4a29e2f59a1: [1:51 pm on 15 July, 2023] Caroline: Thanks Melanie - love the blue vase in the pic! Blue's my fave, it makes me feel relaxed. Sunflowers mean warmth and happin
- overlap=3 id=mem_a914c3f66867: [8:56 pm on 20 July, 2023] Caroline: Hey Melanie! Just wanted to say hi! | Melanie: Hey Caroline! Good to talk to you again. What's up? Anything new since last

### 8. single-hop — evidence_dropped_by_context_budget

Question: What musical artists/bands has Melanie seen?

Ground truth: Summer Sounds, Matt Patterson

Prior correct answer: Melanie has seen the band "Summer Sounds" and the artist Matt Patterson.

Prefix-rerank answer (score 0.5): Melanie has seen the band "Summer Sounds."

Reasons: `context_changed_by_topk_fill, candidate_evidence_dropped`

Dropped original-context items: `5`; gained reranked items: `5`; candidate count: `39`

Dropped items with lexical overlap:
- overlap=6 id=mem_e9ea623a4cbe: [2:24 pm on 14 August, 2023] Melanie: Hey Caroline! 13 August 2023 was amazing! We celebrated my daughter's birthday with a concert surrounded by music, joy and
- overlap=2 id=mem_66c230080489: [3:31 pm on 23 August, 2023] Caroline: Hi Melanie! Hope you're doing good. Guess what I did the week of 23 August 2023? I took the first step towards becoming a
- overlap=1 id=mem_d709c57af80c: [7:55 pm on 9 June, 2023] Caroline: Thanks, Mel! My friends, family and mentors are my rocks – they motivate me and give me the strength to push on. Here's a pi
- overlap=2 id=mem_77e1ef776d15: [9:55 am on 22 October, 2023] Caroline: Woohoo Melanie! I passed the adoption agency interviews 20 October 2023! I'm so excited and thankful. This is a big move
- overlap=2 id=mem_e13e379de221: [3:19 pm on 28 August, 2023] Caroline: Hey Melanie, great to hear from you. What's been up since we talked? | Melanie: Hey Caroline! Since we last spoke, I took

### 9. temporal — evidence_dropped_by_context_budget

Question: When did Caroline apply to adoption agencies?

Ground truth: The week of 23 August 2023

Prior correct answer: Caroline applied to adoption agencies the week of 23 August 2023.

Prefix-rerank answer (score 0.0): Caroline was researching and looking into adoption agencies around late May 2023.

Reasons: `context_changed_by_topk_fill, candidate_evidence_dropped`

Dropped original-context items: `3`; gained reranked items: `3`; candidate count: `21`

Dropped items with lexical overlap:
- overlap=2 id=mem_736359d9be60: [10:37 am on 27 June, 2023] Caroline: Lately, I've been looking into counseling and mental health as a career. I want to help people who have gone through the s
- overlap=3 id=mem_4022869f5920: [8:18 pm on 6 July, 2023] Caroline: Wow, that's great! It sure shows how important friendship and compassion are. It's made me appreciate how lucky I am to have
- overlap=2 id=mem_88530bc8052a: [4:33 pm on 12 July, 2023] Caroline: Hey Mel, great to chat with you again! So much has happened since we last spoke - I went to an LGBTQ conference two days ag

### 10. temporal — evidence_dropped_by_context_budget

Question: When did Caroline go to the LGBTQ conference?

Ground truth: 10 July 2023

Prior correct answer: Caroline went to the LGBTQ conference on 10 July 2023 (two days before 12 July 2023).

Prefix-rerank answer (score 0.5): Caroline went to the LGBTQ conference in early July 2023, specifically mentioned around 3 July 2023 and again referenced on 12 July 2023.

Reasons: `context_changed_by_topk_fill, candidate_evidence_dropped`

Dropped original-context items: `7`; gained reranked items: `7`; candidate count: `35`

Dropped items with lexical overlap:
- overlap=2 id=mem_154237055da5: [1:14 pm on 25 May, 2023] Melanie: Hey Caroline, since we last chatted, I've had a lot of things happening to me. I ran a charity race for mental health 20 May
- overlap=2 id=mem_d709c57af80c: [7:55 pm on 9 June, 2023] Caroline: Thanks, Mel! My friends, family and mentors are my rocks – they motivate me and give me the strength to push on. Here's a pi
- overlap=2 id=mem_2529911f8d3c: [7:55 pm on 9 June, 2023] Caroline: Sounds great, Mel! Glad you had a great time. Cherish the moments - they're the best! | Melanie: Absolutely, Caroline! I che
- overlap=3 id=mem_e63f2dbe0c2d: [10:37 am on 27 June, 2023] Caroline: Hey Melanie! Long time no talk! A lot's been going on in my life! Take a look at this. | Melanie: Hey, Caroline! Nice to h
- overlap=3 id=mem_29c7d073359c: [8:18 pm on 6 July, 2023] Caroline: Hey Mel! Long time no talk. Lots has been going on since then! | Melanie: Hey Caroline! Missed you. Anything new? Spill the

### 11. temporal — evidence_dropped_by_context_budget

Question: When did Caroline join a mentorship program?

Ground truth: The weekend before 17 July 2023

Prior correct answer: Caroline joined a mentorship program for LGBTQ youth the weekend of 15 July 2023.

Prefix-rerank answer (score 0.5): Caroline joined a mentorship program for LGBTQ youth the week of 15 July 2023.

Reasons: `context_changed_by_topk_fill, candidate_evidence_dropped`

Dropped original-context items: `5`; gained reranked items: `5`; candidate count: `20`

Dropped items with lexical overlap:
- overlap=2 id=mem_d709c57af80c: [7:55 pm on 9 June, 2023] Caroline: Thanks, Mel! My friends, family and mentors are my rocks – they motivate me and give me the strength to push on. Here's a pi
- overlap=2 id=mem_2529911f8d3c: [7:55 pm on 9 June, 2023] Caroline: Sounds great, Mel! Glad you had a great time. Cherish the moments - they're the best! | Melanie: Absolutely, Caroline! I che
- overlap=3 id=mem_96b225aa4bef: [1:36 pm on 3 July, 2023] Caroline: Wow, Mel, I'm so stoked for you that art is helping you express yourself and bring you joy! Keep it up! | Melanie: Thanks, C
- overlap=3 id=mem_98f3ec8b4eb5: [4:33 pm on 12 July, 2023] Caroline: I loved "Becoming Nicole" by Amy Ellis Nutt. It's a real inspiring true story about a trans girl and her family. It made me
- overlap=3 id=mem_d59c5bfdd76f: [4:33 pm on 12 July, 2023] Caroline: Wow! What got you into running? | Melanie: I've been running farther to de-stress, which has been great for my headspace. |

### 12. unanswerable — evidence_loss_or_demoted_to_idk

Question: How did Melanie feel about her family after the accident?

Ground truth: They are important and mean the world to her

Prior correct answer: Melanie felt very thankful and realized how precious life and family are; her family means the world to her and they are her biggest motivation and support.

Prefix-rerank answer (score 0.0): I don't know.

Reasons: `context_changed_by_topk_fill, candidate_evidence_dropped, answer_became_idk, sensitive_category`

Dropped original-context items: `4`; gained reranked items: `4`; candidate count: `23`

Dropped items with lexical overlap:
- overlap=5 id=mem_2e2f33d3e1ad: [1:36 pm on 3 July, 2023] Caroline: Since we last spoke, some big things have happened. the week of 26 June 2023 I went to an LGBTQ+ pride parade. Everyone was
- overlap=3 id=mem_29c7d073359c: [8:18 pm on 6 July, 2023] Caroline: Hey Mel! Long time no talk. Lots has been going on since then! | Melanie: Hey Caroline! Missed you. Anything new? Spill the
- overlap=2 id=mem_d59c5bfdd76f: [4:33 pm on 12 July, 2023] Caroline: Wow! What got you into running? | Melanie: I've been running farther to de-stress, which has been great for my headspace. |
- overlap=4 id=mem_1fff4a1d5d5f: [1:51 pm on 15 July, 2023] Caroline: Hey Mel, what's up? Been a busy week since we talked. | Melanie: Hey Caroline, it's been super busy here. So much since we

### 13. unanswerable — evidence_loss_or_demoted_to_idk

Question: How did Melanie's children handle the accident?

Ground truth: They were scared but resilient

Prior correct answer: Melanie's children were scared but were reassured and explained that their brother would be okay; they are described as tough kids.

Prefix-rerank answer (score 0.0): I don't know.

Reasons: `context_changed_by_topk_fill, candidate_evidence_dropped, answer_became_idk, sensitive_category`

Dropped original-context items: `5`; gained reranked items: `5`; candidate count: `21`

Dropped items with lexical overlap:
- overlap=5 id=mem_154237055da5: [1:14 pm on 25 May, 2023] Melanie: Hey Caroline, since we last chatted, I've had a lot of things happening to me. I ran a charity race for mental health 20 May
- overlap=2 id=mem_2529911f8d3c: [7:55 pm on 9 June, 2023] Caroline: Sounds great, Mel! Glad you had a great time. Cherish the moments - they're the best! | Melanie: Absolutely, Caroline! I che
- overlap=3 id=mem_e63f2dbe0c2d: [10:37 am on 27 June, 2023] Caroline: Hey Melanie! Long time no talk! A lot's been going on in my life! Take a look at this. | Melanie: Hey, Caroline! Nice to h
- overlap=4 id=mem_736359d9be60: [10:37 am on 27 June, 2023] Caroline: Lately, I've been looking into counseling and mental health as a career. I want to help people who have gone through the s
- overlap=1 id=mem_d59c5bfdd76f: [4:33 pm on 12 July, 2023] Caroline: Wow! What got you into running? | Melanie: I've been running farther to de-stress, which has been great for my headspace. |

### 14. unanswerable — evidence_loss_or_demoted_to_idk

Question: How did Melanie's son handle the accident?

Ground truth: He was scared but reassured by his family

Prior correct answer: Melanie's son was scared but okay after the accident; the family reassured the other kids that he would be fine.

Prefix-rerank answer (score 0.0): I don't know.

Reasons: `context_changed_by_topk_fill, candidate_evidence_dropped, answer_became_idk, sensitive_category`

Dropped original-context items: `5`; gained reranked items: `5`; candidate count: `21`

Dropped items with lexical overlap:
- overlap=6 id=mem_154237055da5: [1:14 pm on 25 May, 2023] Melanie: Hey Caroline, since we last chatted, I've had a lot of things happening to me. I ran a charity race for mental health 20 May
- overlap=3 id=mem_736359d9be60: [10:37 am on 27 June, 2023] Caroline: Lately, I've been looking into counseling and mental health as a career. I want to help people who have gone through the s
- overlap=3 id=mem_4022869f5920: [8:18 pm on 6 July, 2023] Caroline: Wow, that's great! It sure shows how important friendship and compassion are. It's made me appreciate how lucky I am to have
- overlap=3 id=mem_98f3ec8b4eb5: [4:33 pm on 12 July, 2023] Caroline: I loved "Becoming Nicole" by Amy Ellis Nutt. It's a real inspiring true story about a trans girl and her family. It made me
- overlap=1 id=mem_d59c5bfdd76f: [4:33 pm on 12 July, 2023] Caroline: Wow! What got you into running? | Melanie: I've been running farther to de-stress, which has been great for my headspace. |

### 15. unanswerable — evidence_dropped_by_context_budget

Question: How do Melanie and Caroline describe their journey through life together?

Ground truth: An ongoing adventure of learning and growing.

Prior correct answer: Melanie and Caroline describe their journey through life together as one of mutual support, learning, growth, and shared adventures. They emphasize the importance of friendship, family, community, and being true to themselves, finding strength and inspiration in each other along the way.

Prefix-rerank answer (score 0.5): Melanie and Caroline describe their journey through life together as a supportive, inspiring friendship where they motivate and help each other, share experiences, and spread love, acceptance, and understanding.

Reasons: `context_changed_by_topk_fill, candidate_evidence_dropped, sensitive_category`

Dropped original-context items: `7`; gained reranked items: `7`; candidate count: `34`

Dropped items with lexical overlap:
- overlap=7 id=mem_154237055da5: [1:14 pm on 25 May, 2023] Melanie: Hey Caroline, since we last chatted, I've had a lot of things happening to me. I ran a charity race for mental health 20 May
- overlap=7 id=mem_2e2f33d3e1ad: [1:36 pm on 3 July, 2023] Caroline: Since we last spoke, some big things have happened. the week of 26 June 2023 I went to an LGBTQ+ pride parade. Everyone was
- overlap=4 id=mem_96b225aa4bef: [1:36 pm on 3 July, 2023] Caroline: Wow, Mel, I'm so stoked for you that art is helping you express yourself and bring you joy! Keep it up! | Melanie: Thanks, C
- overlap=7 id=mem_29c7d073359c: [8:18 pm on 6 July, 2023] Caroline: Hey Mel! Long time no talk. Lots has been going on since then! | Melanie: Hey Caroline! Missed you. Anything new? Spill the
- overlap=10 id=mem_98f3ec8b4eb5: [4:33 pm on 12 July, 2023] Caroline: I loved "Becoming Nicole" by Amy Ellis Nutt. It's a real inspiring true story about a trans girl and her family. It made me

### 16. unanswerable — evidence_dropped_by_context_budget

Question: How does Melanie prioritize self-care?

Ground truth: by carving out some me-time each day for activities like running, reading, or playing the violin

Prior correct answer: Melanie prioritizes self-care by carving out daily "me-time" for activities like running, reading, and playing her violin to refresh herself and stay present for her family.

Prefix-rerank answer (score 0.5): Melanie prioritizes self-care by carving out daily "me-time" for activities like running, reading, playing her violin, painting, and pottery, which help her de-stress, express herself, and stay present for her family.

Reasons: `context_changed_by_topk_fill, candidate_evidence_dropped, sensitive_category`

Dropped original-context items: `7`; gained reranked items: `7`; candidate count: `31`

Dropped items with lexical overlap:
- overlap=2 id=mem_70d0f7298224: [1:14 pm on 25 May, 2023] Melanie: Wow, that agency looks great! What made you pick it? | Caroline: I chose them 'cause they help LGBTQ+ folks with adoption. Th
- overlap=5 id=mem_c172656a67b0: [7:55 pm on 9 June, 2023] Caroline: Hey Melanie! How's it going? I wanted to tell you about my school event the week of 02 June 2023. It was awesome! I talked a
- overlap=6 id=mem_d709c57af80c: [7:55 pm on 9 June, 2023] Caroline: Thanks, Mel! My friends, family and mentors are my rocks – they motivate me and give me the strength to push on. Here's a pi
- overlap=4 id=mem_2e2f33d3e1ad: [1:36 pm on 3 July, 2023] Caroline: Since we last spoke, some big things have happened. the week of 26 June 2023 I went to an LGBTQ+ pride parade. Everyone was
- overlap=3 id=mem_96b225aa4bef: [1:36 pm on 3 July, 2023] Caroline: Wow, Mel, I'm so stoked for you that art is helping you express yourself and bring you joy! Keep it up! | Melanie: Thanks, C

### 17. unanswerable — evidence_loss_or_demoted_to_idk

Question: How often does Melanie go to the beach with her kids?

Ground truth: once or twice a year

Prior correct answer: Melanie goes to the beach with her kids usually only once or twice a year.

Prefix-rerank answer (score 0.0): I don't know.

Reasons: `context_changed_by_topk_fill, answer_became_idk, sensitive_category`

Dropped original-context items: `5`; gained reranked items: `5`; candidate count: `23`

Dropped items with lexical overlap:
- overlap=1 id=mem_c172656a67b0: [7:55 pm on 9 June, 2023] Caroline: Hey Melanie! How's it going? I wanted to tell you about my school event the week of 02 June 2023. It was awesome! I talked a
- overlap=1 id=mem_2529911f8d3c: [7:55 pm on 9 June, 2023] Caroline: Sounds great, Mel! Glad you had a great time. Cherish the moments - they're the best! | Melanie: Absolutely, Caroline! I che
- overlap=1 id=mem_2e2f33d3e1ad: [1:36 pm on 3 July, 2023] Caroline: Since we last spoke, some big things have happened. the week of 26 June 2023 I went to an LGBTQ+ pride parade. Everyone was
- overlap=1 id=mem_88530bc8052a: [4:33 pm on 12 July, 2023] Caroline: Hey Mel, great to chat with you again! So much has happened since we last spoke - I went to an LGBTQ conference two days ag
- overlap=1 id=mem_d59c5bfdd76f: [4:33 pm on 12 July, 2023] Caroline: Wow! What got you into running? | Melanie: I've been running farther to de-stress, which has been great for my headspace. |

### 18. unanswerable — evidence_dropped_by_context_budget

Question: What did Melanie and her family see during their camping trip last year?

Ground truth: Perseid meteor shower

Prior correct answer: Melanie and her family saw the Perseid meteor shower during their camping trip in 2022.

Prefix-rerank answer (score 0.0): Melanie and her family explored nature, roasted marshmallows around the campfire, went on a hike, and saw an amazing view from the top.

Reasons: `context_changed_by_topk_fill, candidate_evidence_dropped, sensitive_category`

Dropped original-context items: `5`; gained reranked items: `5`; candidate count: `22`

Dropped items with lexical overlap:
- overlap=3 id=mem_70d0f7298224: [1:14 pm on 25 May, 2023] Melanie: Wow, that agency looks great! What made you pick it? | Caroline: I chose them 'cause they help LGBTQ+ folks with adoption. Th
- overlap=3 id=mem_d709c57af80c: [7:55 pm on 9 June, 2023] Caroline: Thanks, Mel! My friends, family and mentors are my rocks – they motivate me and give me the strength to push on. Here's a pi
- overlap=2 id=mem_2529911f8d3c: [7:55 pm on 9 June, 2023] Caroline: Sounds great, Mel! Glad you had a great time. Cherish the moments - they're the best! | Melanie: Absolutely, Caroline! I che
- overlap=3 id=mem_2e2f33d3e1ad: [1:36 pm on 3 July, 2023] Caroline: Since we last spoke, some big things have happened. the week of 26 June 2023 I went to an LGBTQ+ pride parade. Everyone was
- overlap=2 id=mem_96b225aa4bef: [1:36 pm on 3 July, 2023] Caroline: Wow, Mel, I'm so stoked for you that art is helping you express yourself and bring you joy! Keep it up! | Melanie: Thanks, C

### 19. unanswerable — evidence_dropped_by_context_budget

Question: What does Caroline's necklace symbolize?

Ground truth: love, faith, and strength

Prior correct answer: Caroline's necklace symbolizes love, faith, and strength.

Prefix-rerank answer (score 0.5): Caroline's necklace symbolizes love, faith, strength, and serves as a reminder of her roots and family support.

Reasons: `context_changed_by_topk_fill, candidate_evidence_dropped, sensitive_category`

Dropped original-context items: `3`; gained reranked items: `3`; candidate count: `33`

Dropped items with lexical overlap:
- overlap=2 id=mem_88530bc8052a: [4:33 pm on 12 July, 2023] Caroline: Hey Mel, great to chat with you again! So much has happened since we last spoke - I went to an LGBTQ conference two days ag
- overlap=2 id=mem_7cc1542c0259: [1:56 pm on 8 May, 2023] Caroline: Hey Mel! Good to see you! How have you been? | Melanie: Hey Caroline! Good to see you! I'm swamped with the kids & work. What
- overlap=2 id=mem_22cbbf8fa32c: [2:31 pm on 17 July, 2023] Melanie: Wow, Caroline! They must have felt so appreciated. It's awesome to see the difference we can make in each other's lives. Any

### 20. unanswerable — evidence_dropped_by_context_budget

Question: What does Melanie do to keep herself busy during her pottery break?

Ground truth: Read a book and paint.

Prior correct answer: During her pottery break, Melanie keeps busy by reading a book Caroline recommended and painting.

Prefix-rerank answer (score 0.5): Melanie paints, runs, reads, and plays her violin to keep busy during her pottery break.

Reasons: `context_changed_by_topk_fill, candidate_evidence_dropped, sensitive_category`

Dropped original-context items: `2`; gained reranked items: `2`; candidate count: `21`

Dropped items with lexical overlap:
- overlap=2 id=mem_70d0f7298224: [1:14 pm on 25 May, 2023] Melanie: Wow, that agency looks great! What made you pick it? | Caroline: I chose them 'cause they help LGBTQ+ folks with adoption. Th
- overlap=2 id=mem_e63f2dbe0c2d: [10:37 am on 27 June, 2023] Caroline: Hey Melanie! Long time no talk! A lot's been going on in my life! Take a look at this. | Melanie: Hey, Caroline! Nice to h

### 21. unanswerable — evidence_loss_or_demoted_to_idk

Question: What was Melanie's reaction to her children enjoying the Grand Canyon?

Ground truth: She was happy and thankful

Prior correct answer: Melanie was thankful and happy that her children enjoyed the Grand Canyon despite the accident scare.

Prefix-rerank answer (score 0.0): I don't know.

Reasons: `context_changed_by_topk_fill, candidate_evidence_dropped, answer_became_idk, sensitive_category`

Dropped original-context items: `11`; gained reranked items: `11`; candidate count: `34`

Dropped items with lexical overlap:
- overlap=2 id=mem_154237055da5: [1:14 pm on 25 May, 2023] Melanie: Hey Caroline, since we last chatted, I've had a lot of things happening to me. I ran a charity race for mental health 20 May
- overlap=2 id=mem_70d0f7298224: [1:14 pm on 25 May, 2023] Melanie: Wow, that agency looks great! What made you pick it? | Caroline: I chose them 'cause they help LGBTQ+ folks with adoption. Th
- overlap=3 id=mem_c172656a67b0: [7:55 pm on 9 June, 2023] Caroline: Hey Melanie! How's it going? I wanted to tell you about my school event the week of 02 June 2023. It was awesome! I talked a
- overlap=4 id=mem_d709c57af80c: [7:55 pm on 9 June, 2023] Caroline: Thanks, Mel! My friends, family and mentors are my rocks – they motivate me and give me the strength to push on. Here's a pi
- overlap=3 id=mem_2529911f8d3c: [7:55 pm on 9 June, 2023] Caroline: Sounds great, Mel! Glad you had a great time. Cherish the moments - they're the best! | Melanie: Absolutely, Caroline! I che

### 22. unanswerable — evidence_dropped_by_context_budget

Question: What workshop did Caroline attend recently?

Ground truth: LGBTQ+ counseling workshop

Prior correct answer: Caroline recently attended an LGBTQ+ counseling workshop on 23 June 2023.

Prefix-rerank answer (score 0.0): Caroline recently attended an adoption advice/assistance group workshop.

Reasons: `context_changed_by_topk_fill, candidate_evidence_dropped, sensitive_category`

Dropped original-context items: `2`; gained reranked items: `2`; candidate count: `27`

Dropped items with lexical overlap:
- overlap=2 id=mem_339f8808f421: [8:56 pm on 20 July, 2023] Caroline: Sounds special, those beach trips! Do you have any other summer traditions you all do together? Create those memories! | Me
- overlap=2 id=mem_ad5c824974f2: [1:51 pm on 15 July, 2023] Caroline: I felt so proud and grateful - the vibes were amazing and it was comforting to know I'm not alone and have a great communit

### 23. unanswerable — evidence_loss_or_demoted_to_idk

Question: Which song motivates Caroline to be courageous?

Ground truth: Brave by Sara Bareilles

Prior correct answer: "Brave" by Sara Bareilles motivates Caroline to be courageous.

Prefix-rerank answer (score 0.0): I don't know.

Reasons: `context_changed_by_topk_fill, answer_became_idk, sensitive_category`

Dropped original-context items: `3`; gained reranked items: `3`; candidate count: `20`

Dropped items with lexical overlap:
- overlap=1 id=mem_29c7d073359c: [8:18 pm on 6 July, 2023] Caroline: Hey Mel! Long time no talk. Lots has been going on since then! | Melanie: Hey Caroline! Missed you. Anything new? Spill the
- overlap=1 id=mem_98f3ec8b4eb5: [4:33 pm on 12 July, 2023] Caroline: I loved "Becoming Nicole" by Amy Ellis Nutt. It's a real inspiring true story about a trans girl and her family. It made me
- overlap=1 id=mem_1fff4a1d5d5f: [1:51 pm on 15 July, 2023] Caroline: Hey Mel, what's up? Been a busy week since we talked. | Melanie: Hey Caroline, it's been super busy here. So much since we

## Interpretation

Most harms coincide with context-set changes from lexical fill/top-k budgeting. The reranker is not merely reordering equivalent evidence; it changes which memories reach the answer model. Do not broaden lexical rerank. Next policy should either disable rerank for sensitive categories/query types or treat lexical scoring only as a diagnostic/diversity feature while preserving a much larger original-order context.
