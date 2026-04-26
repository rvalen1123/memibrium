# LOCOMO conv-26 query-expansion + lexical-rerank harmed/rescued analysis

Date: 2026-04-26

## Compared artifacts
- Prior query-expansion canary: `locomo_conv26_query_expansion_2026-04-24.json`
- Lexical-rerank canary: `locomo_conv26_query_expansion_reranked_2026-04-26.json`

## Aggregate
- Common paired questions: 199
- rescued: 10
- harmed: 25
- unchanged_correct: 91
- unchanged_wrong: 36
- partial_changed: 13
- same_partial: 24
- Full 5-cat: 68.09% -> 59.30%
- Protocol 4-cat: 79.93% -> 70.39%
- Avg query latency: 8026ms -> 3979ms

## By category
| Category | N | Avg delta pp | Rescued | Harmed | Unchanged correct | Unchanged wrong | Partial changed | Same partial | Avg latency delta ms | Avg n_mem delta |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| adversarial | 47 | -6.38 | 1 | 4 | 7 | 26 | 6 | 3 | -2701 | 1.7 |
| multi-hop | 13 | -15.38 | 0 | 1 | 4 | 5 | 2 | 1 | -3806 | 4.1 |
| single-hop | 32 | 0.00 | 4 | 4 | 7 | 1 | 1 | 15 | -4435 | 4.0 |
| temporal | 37 | 1.35 | 4 | 3 | 28 | 1 | 0 | 1 | -4919 | 4.2 |
| unanswerable | 70 | -18.57 | 1 | 13 | 45 | 3 | 4 | 4 | -4356 | 3.6 |

## Harm signals
Rerank damage concentrates where lexical overlap can demote negative/compositional evidence.

- adversarial: harmed=4, harmed answers with abstention/insufficient-evidence language=3, empty=0
- multi-hop: harmed=1, harmed answers with abstention/insufficient-evidence language=1, empty=0
- single-hop: harmed=4, harmed answers with abstention/insufficient-evidence language=0, empty=0
- temporal: harmed=3, harmed answers with abstention/insufficient-evidence language=1, empty=0
- unanswerable: harmed=13, harmed answers with abstention/insufficient-evidence language=7, empty=0

## Interpretation
- Pure lexical reranking should remain opt-in and should not be promoted.
- The canary improved latency but damaged paired quality: more harmed than rescued.
- Temporal was the only category with a positive average delta; multi-hop/unanswerable/cat-5 regressed.
- The safer next rerank policy should preserve diversity/original-order evidence and avoid blanket lexical filtering.
- Recommended policy test: keep a fixed prefix of original retrieval order, then fill remaining context with lexical-ranked candidates. This can preserve negative and compositional evidence while still improving precision in later slots.

## Example harmed cases
1. `conv-26` cat=adversarial score 1 -> 0
   - Q: How did Caroline feel about her family after the accident?
   - Gold: They are important and mean the world to her
   - QE answer: Caroline felt that family is everything and emphasized how important loved ones are, appreciating their strength and support after the accident.
   - Rerank answer: I don't know.
2. `conv-26` cat=adversarial score 1 -> 0
   - Q: How did Caroline's children handle the accident?
   - Gold: They were scared but resilient
   - QE answer: Caroline's children were scared but were reassured and told their brother would be okay; they are described as tough kids.
   - Rerank answer: I don't know.
3. `conv-26` cat=adversarial score 1 -> 0
   - Q: What does Caroline do to keep herself busy during her pottery break?
   - Gold: Read a book and paint.
   - QE answer: During her pottery break, Caroline keeps busy by painting and reading a book recommended by Melanie.
   - Rerank answer: Caroline keeps herself busy during her pottery break by learning to play the piano.
4. `conv-26` cat=adversarial score 1 -> 0
   - Q: What kind of place does Melanie want to create for people?
   - Gold: a safe and inviting place for people to grow
   - QE answer: Melanie wants to create a safe space for people to grow.
   - Rerank answer: I don't know.
5. `conv-26` cat=multi-hop score 1 -> 0
   - Q: Would Caroline likely have Dr. Seuss books on her bookshelf?
   - Gold: Yes, since she collects classic children's books
   - QE answer: Yes, Caroline likely has Dr. Seuss books on her bookshelf as she mentioned having lots of kids' books including classics.
   - Rerank answer: I don't know.
6. `conv-26` cat=single-hop score 1 -> 0.5
   - Q: How many children does Melanie have?
   - Gold: 3
   - QE answer: Melanie has three children.
   - Rerank answer: Melanie has multiple children, but the exact number is not specified.
7. `conv-26` cat=single-hop score 1 -> 0.5
   - Q: What activities has Melanie done with her family?
   - Gold: Pottery, painting, camping, museum, swimming, hiking
   - QE answer: Melanie has done camping trips, hiking, roasting marshmallows around campfires, pottery workshops, painting nature-inspired art, beach outings, museum visits, and family games and meals together.
   - Rerank answer: Melanie has gone camping, roasted marshmallows around campfires, told stories, hiked in mountains and forests, explored nature, watched the Perseid meteor shower, and enjoyed family outings.
8. `conv-26` cat=single-hop score 1 -> 0.5
   - Q: Where has Melanie camped?
   - Gold: beach, mountains, forest
   - QE answer: Melanie has camped in the mountains, the forest, and on beach trips with her family.
   - Rerank answer: Melanie has camped in the forest, mountains, and with her family in nature.
9. `conv-26` cat=single-hop score 1 -> 0.5
   - Q: Who supports Caroline when she has a negative experience?
   - Gold: Her mentors, family, and friends
   - QE answer: Caroline is supported by her friends, family, mentors, and community during negative experiences.
   - Rerank answer: Caroline is supported by her friends, family, and people who accept and encourage her.
10. `conv-26` cat=temporal score 1 -> 0
   - Q: When did Caroline and Melanie go to a pride fesetival together?
   - Gold: 2022
   - QE answer: Caroline and Melanie went to a pride festival together in 2022.
   - Rerank answer: Caroline and Melanie went to an LGBTQ+ pride event together in June 2023.
11. `conv-26` cat=temporal score 1 -> 0
   - Q: When did Caroline apply to adoption agencies?
   - Gold: The week of 23 August 2023
   - QE answer: Caroline applied to adoption agencies the week of 23 August 2023.
   - Rerank answer: Caroline was researching adoption agencies and looking into the process around May 25, 2023.
12. `conv-26` cat=temporal score 1 -> 0
   - Q: When did Caroline join a mentorship program?
   - Gold: The weekend before 17 July 2023
   - QE answer: Caroline joined a mentorship program for LGBTQ youth the weekend of 15 July 2023.
   - Rerank answer: I don't know.

## Example rescued cases
1. `conv-26` cat=adversarial score 0 -> 1
   - Q: What is Melanie excited about in her adoption process?
   - Gold: creating a family for kids who need one
   - QE answer: I don't know.
   - Rerank answer: Melanie is excited about creating a family for kids who need one and is up for the challenge of being a single parent.
2. `conv-26` cat=single-hop score 0.5 -> 1
   - Q: How many times has Melanie gone to the beach in 2023?
   - Gold: 2
   - QE answer: Melanie went to the beach once in 2023.
   - Rerank answer: Melanie has gone to the beach at least twice in 2023.
3. `conv-26` cat=single-hop score 0.5 -> 1
   - Q: What are Melanie's pets' names?
   - Gold: Oliver, Luna, Bailey
   - QE answer: Melanie's pets' names are Luna and Oliver.
   - Rerank answer: Melanie's pets' names are Luna, Oliver, and Bailey.
4. `conv-26` cat=single-hop score 0.5 -> 1
   - Q: What did Caroline research?
   - Gold: Adoption agencies
   - QE answer: Caroline researched counseling, mental health careers, and adoption agencies.
   - Rerank answer: Caroline researched adoption agencies.
5. `conv-26` cat=single-hop score 0 -> 1
   - Q: When did Melanie go on a hike after the roadtrip?
   - Gold: 19 October 2023
   - QE answer: Melanie went on a hike during the family camping trip the week of 20 June 2023, before the road trip mentioned in October.
   - Rerank answer: Melanie went on a hike after the road trip on 19 October 2023.
6. `conv-26` cat=temporal score 0 -> 1
   - Q: When did Caroline go biking with friends?
   - Gold: The weekend before 13 September 2023
   - QE answer: I don't know.
   - Rerank answer: Caroline went biking with friends the weekend of 09 September 2023.
7. `conv-26` cat=temporal score 0 -> 1
   - Q: When did Caroline go to a pride parade during the summer?
   - Gold: The week before 3 July 2023
   - QE answer: Caroline went to a pride parade on 11 August 2023 during the summer.
   - Rerank answer: Caroline went to a pride parade the week of 26 June 2023.
8. `conv-26` cat=temporal score 0 -> 1
   - Q: When did Caroline have a picnic?
   - Gold: The week before 6 July 2023
   - QE answer: I don't know.
   - Rerank answer: Caroline had a picnic the week of 29 June 2023.
9. `conv-26` cat=temporal score 0.5 -> 1
   - Q: When is Melanie planning on going camping?
   - Gold: June 2023
   - QE answer: Melanie was planning a family outing or special trip with Caroline for summer 2023.
   - Rerank answer: Melanie was planning on going camping in June 2023.
10. `conv-26` cat=unanswerable score 0.5 -> 1
   - Q: How did Melanie feel after the accident?
   - Gold: Grateful and thankful for her family
   - QE answer: Melanie felt really scared after the accident but was thankful her son was okay and it reminded her to cherish her family.
   - Rerank answer: Melanie felt really scared during the accident but was thankful her son was okay, and the experience reminded her that life is precious and to cherish her family.

## Example partial_changed cases
1. `conv-26` cat=adversarial score 0.5 -> 0
   - Q: How did Caroline feel after the accident?
   - Gold: Grateful and thankful for her family
   - QE answer: Caroline felt sorry and concerned for Melanie and her family after the accident, recognizing it must have been traumatizing.
   - Rerank answer: Caroline felt sorry and empathetic about the accident, recognizing it must have been traumatizing for Melanie's family.
2. `conv-26` cat=adversarial score 0.5 -> 0
   - Q: What are Melanie's plans for the summer with respect to adoption?
   - Gold: researching adoption agencies
   - QE answer: Melanie is considering adoption and is starting to do research and prepare emotionally, but no specific summer plans related to adoption are mentioned.
   - Rerank answer: Melanie does not have any plans related to adoption for the summer mentioned in the context.
3. `conv-26` cat=adversarial score 0 -> 0.5
   - Q: What did Caroline and her family do while camping?
   - Gold: explored nature, roasted marshmallows, and went on a hike
   - QE answer: I don't know.
   - Rerank answer: Caroline and her family roasted marshmallows, told stories around the campfire, enjoyed each other's company, explored nature, went on hikes, and watched the Perseid meteor shower.
4. `conv-26` cat=adversarial score 0.5 -> 0
   - Q: What did Caroline and her family see during their camping trip last year?
   - Gold: Perseid meteor shower
   - QE answer: Caroline did not mention a camping trip last year; Melanie recalled seeing the Perseid meteor shower during their 2022 camping trip.
   - Rerank answer: I don't know.
5. `conv-26` cat=adversarial score 0 -> 0.5
   - Q: What inspired Caroline's sculpture for the art show?
   - Gold: visiting an LGBTQ center and wanting to capture unity and strength
   - QE answer: I don't know.
   - Rerank answer: Caroline's sculpture for the art show was inspired by her own journey as a transgender woman and the idea of accepting growth and change.
6. `conv-26` cat=adversarial score 0 -> 0.5
   - Q: Why did Caroline choose to use colors and patterns in her pottery project?
   - Gold: She wanted to catch the eye and make people smile.
   - QE answer: Caroline did not make a pottery project; Melanie did. Melanie chose colors and patterns to catch the eye, make people smile, and express her feelings and creativity.
   - Rerank answer: Caroline chose colors and patterns in her pottery project because they remind her of art and self-expression.
7. `conv-26` cat=multi-hop score 0.5 -> 0
   - Q: What personality traits might Melanie say Caroline has?
   - Gold: Thoughtful, authentic, driven
   - QE answer: Melanie might say Caroline is empathetic, understanding, creative, authentic, courageous, supportive, and passionate about helping others.
   - Rerank answer: Melanie might say Caroline is courageous, inspiring, passionate, supportive, creative, and dedicated to helping others.
8. `conv-26` cat=multi-hop score 0.5 -> 0
   - Q: Would Caroline be considered religious?
   - Gold: Somewhat, but not extremely religious
   - QE answer: No, Caroline would not be considered religious based on the provided context.
   - Rerank answer: I don't know.
9. `conv-26` cat=single-hop score 0.5 -> 0
   - Q: What is Caroline's relationship status?
   - Gold: Single
   - QE answer: Caroline had a tough breakup before June 2023; no current relationship status is mentioned.
   - Rerank answer: I don't know.
10. `conv-26` cat=unanswerable score 0.5 -> 0
   - Q: What did Melanie do after the road trip to relax?
   - Gold: Went on a nature walk or hike
   - QE answer: Melanie went camping with her family to relax after the road trip.
   - Rerank answer: Melanie went on a camping trip with her family on 19 October 2023 to relax after the road trip.
11. `conv-26` cat=unanswerable score 0.5 -> 0
   - Q: What painting did Melanie show to Caroline on October 13, 2023?
   - Gold: A painting inspired by sunsets with a pink sky.
   - QE answer: Melanie showed Caroline a painting inspired by sunsets with calming colors on October 13, 2023.
   - Rerank answer: I don't know.
12. `conv-26` cat=unanswerable score 0.5 -> 0
   - Q: What setback did Melanie face in October 2023?
   - Gold: She got hurt and had to take a break from pottery.
   - QE answer: In October 2023, Melanie got hurt in September and had to take a break from pottery.
   - Rerank answer: I don't know.
