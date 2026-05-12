# LOCOMO Context-Packet Source Attribution Audit — 20260506T103203Z

Scope: 25-row conv-26 canary/audit only. Not a 199Q LOCOMO benchmark claim. Source attribution was opt-in/default-off.

## Inputs
- treatment: `/home/zaddy/src/Memibrium/docs/eval/results/locomo_context_packet_canary_treatment_merge_refgate_frozen_shaped_multihop_temporal_goldcov_20260506T103203Z.json`
- baseline: `/home/zaddy/src/Memibrium/docs/eval/results/locomo_context_packet_canary_baseline_20260506T103203Z.json`
- summary: `/home/zaddy/src/Memibrium/docs/eval/results/locomo_context_packet_canary_summary_merge_refgate_frozen_shaped_multihop_temporal_goldcov_20260506T103203Z.json`
- raw_locomo: `/tmp/locomo/data/locomo10.json`

## Canary metrics
- baseline -> treatment: `52.0 -> 68.0` (`+16.0` pp)
- treatment category scores: `{'cat-single-hop': 70.0, 'cat-temporal': 100.0, 'cat-multi-hop': 100.0, 'cat-unanswerable': 70.0, 'cat-adversarial': 0.0}`
- gold-ref hit rate: `{'baseline': 0.8261, 'treatment': 0.8696}`
- final hygiene ok: `True`

## Source attribution summary
- rows: `25`
- source_attr_present: `25`
- source_any_gold_ref: `11`
- source_all_gold_refs: `9`
- pool_any_gold_ref: `11`
- pool_all_gold_refs: `9`
- final_any_gold_ref: `20`
- final_all_gold_refs: `19`
- packet_added_rows: `3`
- missing_atom_rows: `16`
- class_passed_in_canary: `15`
- nonfull_rows: `10`
- class_gold_ref_present_but_atom_missing_or_multimodal_metadata: `3`
- class_answer_synthesis_shape_or_subject_error: `2`
- class_answer_conflict_selection: `2`
- class_baseline_has_ref_context_packet_query_missed_ref: `1`
- class_retrieval_absence_all_paths: `2`

## Focus rows
| row | cat | score | class | source refs | final refs | missing/conflict | note |
|---:|---|---:|---|---:|---:|---|---|
| 24 | single-hop | 0.5 | gold_ref_present_but_atom_missing_or_multimodal_metadata | 1/2 | 2/2 | Nothing is Impossible | D7:8 retrieved, title atom missing from text/metadata; D6:10 only in final. |
| 41 | single-hop | 0.5 | answer_synthesis_shape_or_subject_error | 1/2 | 1/2 |  | All atom present but count answer hedges once/twice; missing D6:16 source/final ref. |
| 80 | temporal | 1.0 | passed_in_canary | 0/1 | 1/1 |  | Passed; final has D19:1, source recall missed it. |
| 113 | unanswerable | 0.0 | gold_ref_present_but_atom_missing_or_multimodal_metadata | 1/1 | 1/1 | sunset, palm tree, flowers, nature-inspired | Gold ref retrieved, but answer object is in blip/image metadata; text says nature/flowers. |
| 163 | adversarial | 0.0 | answer_synthesis_shape_or_subject_error | 0/1 | 1/1 |  | Final has D4:8/all atoms; answer says I don’t know; subject/adversarial synthesis issue. |
| 172 | adversarial | 0.0 | baseline_has_ref_context_packet_query_missed_ref | 0/1 | 1/1 | many people wanting to create loving homes for children in need | Final has D8:9 but source query missed; adversarial subject wording conflicts with gold. |
| 185 | adversarial | 0.0 | answer_conflict_selection | 1/1 | 1/1 | acoustic guitar, guitar | Gold ref retrieved/final rank1, but guitar conflict wins over clarinet/violin. |

## Non-full rows
- row 24 `gold_ref_present_but_atom_missing_or_multimodal_metadata` score=0.5 cov=partial_atoms_present source_refs=1/2 final_refs=2/2: Melanie has read "Charlotte's Web" and a book Caroline recommended to her last year that inspires pursuing dreams.
- row 39 `gold_ref_present_but_atom_missing_or_multimodal_metadata` score=0.5 cov=partial_atoms_present source_refs=1/6 final_refs=2/6: Melanie has gone camping at the beach, camping in the mountains, hiking in the mountains and forests, roasting marshmallows around a campfire, playing games, eating good food, going on a road trip including visiting the Grand Canyon, and swimming with her kids.
- row 41 `answer_synthesis_shape_or_subject_error` score=0.5 cov=all_atoms_present source_refs=1/2 final_refs=1/2: Melanie has gone to the beach once or twice in 2023.
- row 113 `gold_ref_present_but_atom_missing_or_multimodal_metadata` score=0.0 cov=no_atoms_present_conflicting_context source_refs=1/1 final_refs=1/1: Mel and her kids painted a nature-inspired painting featuring lovely flowers in their latest project in July 2023.
- row 123 `answer_conflict_selection` score=0.5 cov=all_atoms_present_with_conflicts source_refs=1/1 final_refs=1/1: Melanie chose the colors and patterns in her pottery project to catch the eye, make people smile, and to express her feelings and creativity, with each stroke carrying a part of her.
- row 163 `answer_synthesis_shape_or_subject_error` score=0.0 cov=all_atoms_present source_refs=0/1 final_refs=1/1: I don't know.
- row 172 `baseline_has_ref_context_packet_query_missed_ref` score=0.0 cov=no_atoms_present source_refs=0/1 final_refs=1/1: Melanie did not attend the council meeting for adoption; Caroline did and found it inspiring and emotional.
- row 183 `retrieval_absence_all_paths` score=0.0 cov=no_atoms_present source_refs=0/1 final_refs=0/1: I don't know.
- row 185 `answer_conflict_selection` score=0.0 cov=all_atoms_present_with_conflicts source_refs=1/1 final_refs=1/1: Caroline plays acoustic guitar.
- row 195 `retrieval_absence_all_paths` score=0.0 cov=no_atoms_present source_refs=0/1 final_refs=0/1: I don't know.

## Conclusions
- Source attribution emitted for all 25 rows and preserved candidate-pool/source evidence linkage.
- Context-packet source recall overlapped any gold evidence ref on 11/25 rows and all gold refs on 9/25; final context overlapped any gold ref on 20/25 and all refs on 19/25.
- Most remaining non-full rows are not solved by entity/time post-filtering: either answer synthesis/conflict selection fails despite final gold refs, or the source context-packet query misses a ref already present in baseline final context.
- Rows 183 and 195 remain true retrieval absence cases in this canary: no source/pool/final gold ref hits.

## Recommended next step
- Do not run full 199Q yet. Implement/evaluate a default-off answer-side conflict/subject contract for adversarial rows and a multimodal metadata/object projection for image-query/blip atoms; then rerun the same 25-row canary or artifact-pinned replay.
