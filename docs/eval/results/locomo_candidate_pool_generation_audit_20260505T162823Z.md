# LOCOMO Candidate-Pool Generation Audit — 20260505T162823Z

Scope: artifact-only/read-only audit of preserved context-packet candidate pools from `20260505T115852Z`. No live recall, no DB/Docker mutation, no full/cumulative LOCOMO run.

## Summary

- Focus rows: 16 (5, 24, 31, 39, 40, 41, 51, 55, 74, 78, 80, 113, 128, 163, 172, 185)
- Rows with missing coverage atoms: 11
- Rows where candidate pool contains any literal missing atom: 0
- Rows where final context contains any literal missing atom: 0
- Rows where candidate pool overlaps gold evidence refs: 7
- Rows where final context overlaps gold evidence refs: 13

Absence-mode counts:
- `gold_evidence_turn_not_in_candidate_pool`: 5
- `evidence_in_pool_but_literal_missing_atom_absent_or_coverage_granularity_mismatch`: 5
- `coverage_satisfied_not_candidate_pool_problem`: 4
- `no_gold_evidence_refs_in_dataset_inference_or_negative_answer`: 1
- `answer_conflict_selection_not_pool_absence`: 1

## Main finding

The new coverage-aware expansion gate is not the bottleneck. For the rows it would need to rescue, the preserved packet candidate pool usually does not contain the literal missing gold atoms. Some raw LOCOMO gold evidence turns exist in conv-26 but are absent from the preserved candidate pool, so the next substrate question is upstream candidate generation/query selection/recall, not the entity/time post-filter.

## Row-level audit

| row | cat | score | coverage | missing | pool literal hits | evidence refs in pool | mode |
|---:|---|---:|---|---|---:|---:|---|
| 5 | single-hop | 1.0 | no_atoms_present | Transgender woman | 0 | 0 | `gold_evidence_turn_not_in_candidate_pool` |
| 24 | single-hop | 0.5 | partial_atoms_present | Nothing is Impossible | 0 | 1 | `evidence_in_pool_but_literal_missing_atom_absent_or_coverage_granularity_mismatch` |
| 31 | multi-hop | 1.0 | no_atoms_present | Likely no, she does not refer to herself as part of it | 0 | 0 | `no_gold_evidence_refs_in_dataset_inference_or_negative_answer` |
| 39 | single-hop | 0.5 | partial_atoms_present | museum, hiking | 0 | 0 | `gold_evidence_turn_not_in_candidate_pool` |
| 40 | single-hop | 1.0 | partial_atoms_present | Joining activist group, going to pride parades, participating in an art show | 0 | 2 | `evidence_in_pool_but_literal_missing_atom_absent_or_coverage_granularity_mismatch` |
| 41 | single-hop | 0.5 | all_atoms_present | — | 0 | 1 | `coverage_satisfied_not_candidate_pool_problem` |
| 51 | multi-hop | 1.0 | no_atoms_present | Liberal | 0 | 1 | `evidence_in_pool_but_literal_missing_atom_absent_or_coverage_granularity_mismatch` |
| 55 | temporal | 1.0 | no_atoms_present | The week before 23 August 2023 | 0 | 1 | `evidence_in_pool_but_literal_missing_atom_absent_or_coverage_granularity_mismatch` |
| 74 | temporal | 1.0 | all_atoms_present | — | 0 | 0 | `coverage_satisfied_not_candidate_pool_problem` |
| 78 | multi-hop | 1.0 | no_atoms_present | Likely no, since this one went badly | 0 | 0 | `gold_evidence_turn_not_in_candidate_pool` |
| 80 | temporal | 0.0 | no_atoms_present | The Friday before 22 October 2023 | 0 | 0 | `gold_evidence_turn_not_in_candidate_pool` |
| 113 | unanswerable | 0.0 | no_atoms_present_conflicting_context | sunset, palm tree | 0 | 1 | `evidence_in_pool_but_literal_missing_atom_absent_or_coverage_granularity_mismatch` |
| 128 | unanswerable | 1.0 | all_atoms_present | — | 0 | 1 | `coverage_satisfied_not_candidate_pool_problem` |
| 163 | adversarial | 0.0 | all_atoms_present | — | 0 | 0 | `coverage_satisfied_not_candidate_pool_problem` |
| 172 | adversarial | 0.0 | no_atoms_present | many people wanting to create loving homes for children in need | 0 | 0 | `gold_evidence_turn_not_in_candidate_pool` |
| 185 | adversarial | 0.0 | all_atoms_present_with_conflicts | — | 0 | 0 | `answer_conflict_selection_not_pool_absence` |

## Raw evidence examples for key residual rows

### Row 24: What books has Melanie read?
- GT: "Nothing is Impossible", "Charlotte's Web"
- Coverage: `partial_atoms_present`; missing=['Nothing is Impossible']; conflicts=[]
- Candidate pool literal missing-atom hits: {'Nothing is Impossible': []}
- Gold evidence refs in pool: 1; in final context: 2
  - D7:8 (session 7 / lex 17, turn 7): Caroline, so glad you got the support! Your experience really brought you to where you need to be. You're gonna make a huge difference! This book I read last year reminds me to always pursue my dreams, just like you are doing!🌟
    image_query=painted canvas follow your dreams; blip_caption=a photography of a book cover with a gold coin on it
  - D6:10 (session 6 / lex 16, turn 9): I loved reading "Charlotte's Web" as a kid. It was so cool seeing how friendship and compassion can make a difference.
    image_query=charlotte's web book; blip_caption=a photo of a book cover with a picture of a girl and a cat

### Row 41: How many times has Melanie gone to the beach in 2023?
- GT: 2
- Coverage: `all_atoms_present`; missing=[]; conflicts=[]
- Candidate pool literal missing-atom hits: {}
- Gold evidence refs in pool: 1; in final context: 1
  - D10:8 (session 10 / lex 2, turn 7): Wow, fantastic, Caroline! Bet the atmosphere was incredible. Oh yeah, we went to the beach recently. It was awesome! The kids had such a blast.
    image_query=beach family playing frisbee sandy shore; blip_caption=a photo of three children playing on the beach with a kite
  - D6:16 (session 6 / lex 16, turn 15): Glad you have support, Caroline! Unconditional love is so important. Here's a pic of my family camping at the beach. We love it, it brings us closer!
    image_query=family campfire; blip_caption=a photo of a family sitting around a campfire on the beach

### Row 113: What did Mel and her kids paint in their latest project in July 2023?
- GT: a sunset with a palm tree
- Coverage: `no_atoms_present_conflicting_context`; missing=['sunset', 'palm tree']; conflicts=['flowers', 'nature-inspired']
- Candidate pool literal missing-atom hits: {'sunset': [], 'palm tree': []}
- Gold evidence refs in pool: 1; in final context: 1
  - D8:6 (session 8 / lex 18, turn 5): We love painting together lately, especially nature-inspired ones. Here's our latest work from last weekend.
    image_query=painting vibrant flowers sunset sky; blip_caption=a photo of a painting of a sunset with a palm tree

### Row 163: What did Caroline and her family do while camping?
- GT: explored nature, roasted marshmallows, and went on a hike
- Coverage: `all_atoms_present`; missing=[]; conflicts=[]
- Candidate pool literal missing-atom hits: {}
- Gold evidence refs in pool: 0; in final context: 1
  - D4:8 (session 4 / lex 14, turn 7): It was an awesome time, Caroline! We explored nature, roasted marshmallows around the campfire and even went on a hike. The view from the top was amazing! The 2 younger kids love nature. It was so special having these moments together as a family - I'll never forget it!

### Row 185: What type of instrument does Caroline play?
- GT: clarinet and violin
- Coverage: `all_atoms_present_with_conflicts`; missing=[]; conflicts=['acoustic guitar', 'guitar']
- Candidate pool literal missing-atom hits: {}
- Gold evidence refs in pool: 0; in final context: 1
  - D15:26 (session 15 / lex 7, turn 25): Yeah, I play clarinet! Started when I was young and it's been great. Expression of myself and a way to relax.
    image_query=None; blip_caption=a photo of a sheet music with notes and a pencil

### Row 80: When did Caroline pass the adoption interview?
- GT: The Friday before 22 October 2023
- Coverage: `no_atoms_present`; missing=['The Friday before 22 October 2023']; conflicts=[]
- Candidate pool literal missing-atom hits: {'The Friday before 22 October 2023': []}
- Gold evidence refs in pool: 0; in final context: 0
  - D19:1 (session 19 / lex 11, turn 0): Woohoo Melanie! I passed the adoption agency interviews last Friday! I'm so excited and thankful. This is a big move towards my goal of having a family.

### Row 172: What did Melanie see at the council meeting for adoption?
- GT: many people wanting to create loving homes for children in need
- Coverage: `no_atoms_present`; missing=['many people wanting to create loving homes for children in need']; conflicts=[]
- Candidate pool literal missing-atom hits: {'many people wanting to create loving homes for children in need': []}
- Gold evidence refs in pool: 0; in final context: 1
  - D8:9 (session 8 / lex 18, turn 8): That photo is stunning! So glad you bonded over our love of nature. Last Friday I went to a council meeting for adoption. It was inspiring and emotional - so many people wanted to create loving homes for children in need. It made me even more determined to adopt.

## Candidate-generation telemetry limitation

The `20260505T115852Z` frozen artifact preserves `context_packet_candidate_pool`, but not per-query context-packet recall provenance. In artifact replay, `expanded_queries` is just the user question and `per_query_recall` is empty by design. The context-packet projection keeps counts/query type but not the query text/result IDs that formed the pool.

So this audit can prove whether missing atoms/evidence refs are present in the preserved pool, but it cannot yet attribute absence to one of:

- query wording / query decomposition,
- vector recall ranking,
- context-packet top-k cap,
- ref-gate / merge cap behavior, or
- multimodal evidence being present only in `blip_caption` / `query` metadata rather than dialogue text.

Next diagnostic should therefore be telemetry-only: preserve context-packet source queries and pre/post-cap candidate IDs/refs/scores in artifacts. Keep it default-off and artifact-only before any new canary.

## Interpretation

- Candidate-pool preservation is mechanically useful, but the current pool is often missing the actual gold-evidence turn or the literal answer object.
- Rows 163 and 185 should not be treated as candidate-pool absence: 163 has all gold atoms but subject attribution fails; 185 has clarinet evidence plus guitar conflict and needs conflict/benchmark handling.
- Rows like 31/51/78 have inference-style gold answers; literal missing-atom matching is expected to undercount them and they need structured answer contracts/evidence reasoning rather than blind expansion.
- Next best technical step is a read-only query/candidate-source attribution audit: compare context_packet query inputs, per-query recall candidates, and raw evidence refs for missing rows; then decide whether to alter query generation or packet candidate selection.
