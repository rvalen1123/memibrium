# LOCOMO Gold-Object Coverage Audit — 2026-05-05

Scope: artifact-only diagnostic over pinned 25-row canary artifacts; no live benchmark, no DB/runtime mutation.

## Inputs

- `multi_temporal`: `docs/eval/results/locomo_context_packet_canary_treatment_merge_refgate_frozen_artifactctx_shaped_multihop_temporal_20260504T182630Z.json`
- `singlehop`: `docs/eval/results/locomo_context_packet_canary_treatment_merge_refgate_frozen_artifactctx_shaped_singlehop_20260505T094418Z.json`

## Best-Row Coverage Summary

- Rows audited: `25`
- `all_atoms_present`: `8`
- `all_atoms_present_with_conflicts`: `1`
- `no_atoms_present`: `9`
- `no_atoms_present_conflicting_context`: `1`
- `partial_atoms_present`: `5`
- `partial_atoms_present_with_conflicts`: `1`

## Rows With Missing or Conflicting Gold Objects

| Row | Cat | Score | Coverage | Present atoms | Missing atoms | Conflicts |
|---:|---|---:|---|---|---|---|
| 24 | single-hop | 0.5 | `partial_atoms_present` | Charlotte's Web | Nothing is Impossible | — |
| 30 | temporal | 1.0 | `no_atoms_present` | — | The Friday before 15 July 2023 | — |
| 31 | multi-hop | 1.0 | `no_atoms_present` | — | Likely no, she does not refer to herself as part of it | — |
| 39 | single-hop | 1.0 | `partial_atoms_present` | Pottery, painting, camping | museum, swimming, hiking | — |
| 40 | single-hop | 1.0 | `partial_atoms_present` | mentoring program | Joining activist group, going to pride parades, participating in an art show | — |
| 41 | single-hop | 0.0 | `no_atoms_present` | — | beach | — |
| 51 | multi-hop | 1.0 | `no_atoms_present` | — | Liberal | — |
| 55 | temporal | 1.0 | `no_atoms_present` | — | The week before 23 August 2023 | — |
| 69 | temporal | 1.0 | `no_atoms_present` | — | Since 2016 | — |
| 70 | multi-hop | 1.0 | `partial_atoms_present` | Thoughtful, authentic | driven | — |
| 74 | temporal | 1.0 | `no_atoms_present` | — | September 2023 | — |
| 78 | multi-hop | 1.0 | `no_atoms_present` | — | Likely no, since this one went badly | — |
| 113 | unanswerable | 0.0 | `no_atoms_present_conflicting_context` | — | sunset, palm tree | flowers, nature-inspired |
| 121 | unanswerable | 1.0 | `no_atoms_present` | — | Melanie's daughter | — |
| 123 | unanswerable | 0.5 | `partial_atoms_present_with_conflicts` | make people smile | catch the eye | express emotions, self-expression, relax |
| 163 | adversarial | 0.5 | `partial_atoms_present` | nature, roasted marshmallows | hike | — |
| 185 | adversarial | 0.0 | `all_atoms_present_with_conflicts` | clarinet, violin | — | acoustic guitar, guitar |

## Interpretation

- `all_atoms_present` rows are primarily synthesis/judge/answer-contract candidates if they still score below full credit.
- `partial_atoms_present` rows need targeted retrieval expansion or evidence-completion before more answer shaping.
- `no_atoms_present` rows are retrieval/context misses under the pinned final_context substrate.
- `*_with_conflicts` rows need entity/role/source-provenance audit before tuning.

## Next Step

Use this audit to drive a default-off evidence coverage intervention: entity/time anchored expansion with explicit expected-object coverage telemetry on the preregistered 25-row slice only.
