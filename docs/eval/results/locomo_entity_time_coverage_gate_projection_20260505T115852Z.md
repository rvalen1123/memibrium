# LOCOMO Coverage-Aware Entity/Time Expansion Projection — 20260505T115852Z

Mode: artifact-only projection using local code; no DB/Docker/runtime mutation; no benchmark rerun.

- Source artifact: `locomo_context_packet_canary_treatment_merge_refgate_frozen_artifactctx_shaped_multihop_temporal_goldcov_enttimeexp_20260505T115852Z.json`
- Prior rule added: `19` candidates
- Coverage-aware projected additions: `0` candidates

Interpretation: the new rule blocks the previously observed noisy additions, but this preserved candidate pool does not contain missing gold atoms under current telemetry. So coverage-aware entity/time expansion should not be expected to improve this artifact-pinned 25-row slice by itself.

| Row | Cat | Old added | Projected added | Coverage | Missing before | Question |
|---:|---|---:|---:|---|---|---|
| 5 | single-hop | 1 | 0 | no_atoms_present→no_atoms_present | Transgender woman | What is Caroline's identity? |
| 24 | single-hop | 2 | 0 | partial_atoms_present→partial_atoms_present | Nothing is Impossible | What books has Melanie read? |
| 31 | multi-hop | 1 | 0 | no_atoms_present→no_atoms_present | Likely no, she does not refer to herself as part of it | Would Melanie be considered a member of the LGBTQ community? |
| 39 | single-hop | 2 | 0 | partial_atoms_present→partial_atoms_present | museum, hiking | What activities has Melanie done with her family? |
| 40 | single-hop | 1 | 0 | partial_atoms_present→partial_atoms_present | Joining activist group, going to pride parades, participating in an art show | In what ways is Caroline participating in the LGBTQ community? |
| 41 | single-hop | 1 | 0 | all_atoms_present→all_atoms_present |  | How many times has Melanie gone to the beach in 2023? |
| 51 | multi-hop | 2 | 0 | no_atoms_present→no_atoms_present | Liberal | What would Caroline's political leaning likely be? |
| 55 | temporal | 1 | 0 | no_atoms_present→no_atoms_present | The week before 23 August 2023 | When did Caroline draw a self-portrait? |
| 74 | temporal | 1 | 0 | all_atoms_present→all_atoms_present |  | When did Melanie get hurt? |
| 78 | multi-hop | 1 | 0 | no_atoms_present→no_atoms_present | Likely no, since this one went badly | Would Melanie go on another roadtrip soon? |
| 80 | temporal | 2 | 0 | no_atoms_present→no_atoms_present | The Friday before 22 October 2023 | When did Caroline pass the adoption interview? |
| 113 | unanswerable | 1 | 0 | no_atoms_present_conflicting_context→no_atoms_present_conflicting_context | sunset, palm tree | What did Mel and her kids paint in their latest project in July 2023? |
| 128 | unanswerable | 1 | 0 | all_atoms_present→all_atoms_present |  | What did Caroline make for a local church? |
| 163 | adversarial | 0 | 0 | all_atoms_present→all_atoms_present |  | What did Caroline and her family do while camping? |
| 172 | adversarial | 2 | 0 | no_atoms_present→no_atoms_present | many people wanting to create loving homes for children in need | What did Melanie see at the council meeting for adoption? |
| 185 | adversarial | 0 | 0 | all_atoms_present_with_conflicts→all_atoms_present_with_conflicts |  | What type of instrument does Caroline play? |
