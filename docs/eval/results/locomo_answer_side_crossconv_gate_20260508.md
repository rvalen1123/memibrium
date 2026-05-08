# LOCOMO answer-side cross-conversation gate — 2026-05-08

Scope: diagnostic/canary evidence only. This is a 25-row cross-conversation gate split across two non-conv-26 conversations. It is not a full 199Q LOCOMO benchmark, not cumulative, and not a quote-worthy benchmark result.

## Preconditions and guardrails

- Branch: `query-expansion`.
- Latest pre-run pushed commit: `f23fcc5 docs: tighten LOCOMO answer-side promotion gates`.
- Full 199Q/cumulative LOCOMO remained blocked; this run did not execute either.
- The locked candidate was not retuned after same-conversation evidence: answer-shape directive for `multi-hop,temporal`; multimodal metadata projection for `single-hop,unanswerable`; no subject guard.
- Conversation selection and row selection were predeclared by hash before scoring.
- `docs/reference/` was not touched.
- Secrets/env credentials in emitted summaries are redacted by the runner.

## Predeclared selection

Preregistration file: `docs/eval/results/locomo_answer_side_crossconv_prereg_25rows_2026-05-08.json`.

Conversation pool: all LOCOMO conversations in `/tmp/locomo/data/locomo10.json` except `conv-26`, requiring enough rows per normalized category. Selection seed:

`memibrium-locomo-answer-side-crossconv-gate-2026-05-08-v1`

Conversation method: rank eligible conversations by `sha256(seed + ':conv:' + sample_id)`, select the first two, and split n as 13/12 before scoring. Selected conversations: `conv-44` (13 rows) and `conv-41` (12 rows).

Row method: within each selected conversation/category, rank rows by `sha256(seed + ':row:' + sample_id + ':' + one_based_index + ':' + question)` and take predeclared category quotas. Overall category counts: 5 each for single-hop, temporal, multi-hop, unanswerable, adversarial.

Selected row indexes:

- `conv-44`: `4, 29, 16, 59, 9, 21, 45, 44, 65, 90, 118, 126, 132`
- `conv-41`: `7, 31, 62, 23, 35, 15, 40, 66, 112, 158, 168, 154`

## Predeclared thresholds/watchpoints

- Cross-conversation gate for 199Q consideration: multi-hop absolute delta must be at least `+6pp`. If it comes in below `+6pp`, do not relax the threshold post hoc.
- Row-53-class under-listing definition: list-type questions where the gold answer contains at least two enumerated entities and the treatment answer returns a strict subset of the gold list, especially if the omitted entity was present in the baseline answer or directly supported by the frozen context.
- Under-listing rollback watchpoint: more than 2 row-53-class failures on this 25-row gate blocks 199Q promotion. For any later 199Q preregistration, keep the budget at <=2 row-53-class failures and about <= -1pp aggregate list-completion impact.
- No adversarial/conflict improvement claim unless separately tested.

## Runner change

The canary runner previously hard-coded the first LOCOMO record as `conv-26`. For this gate only, it was generalized with `--sample-id` and `--expected-qa-count` while preserving the historical defaults (`conv-26`, 199 QA). Unit coverage was added for selecting a non-`conv-26` sample. No benchmark-scoring defaults were changed.

Identity/preflight commands:

```bash
python3 docs/eval/results/run_locomo_context_packet_canary.py --identity-only --sample-id conv-44 --expected-qa-count 158 --fixed-rows-path docs/eval/results/locomo_answer_side_crossconv_prereg_conv-44_2026-05-08.json --min-prereg-rows 10 --max-prereg-rows 15
python3 docs/eval/results/run_locomo_context_packet_canary.py --identity-only --sample-id conv-41 --expected-qa-count 193 --fixed-rows-path docs/eval/results/locomo_answer_side_crossconv_prereg_conv-41_2026-05-08.json --min-prereg-rows 10 --max-prereg-rows 15
python3 -m unittest -q test_locomo_context_packet_canary.py
python3 -m py_compile docs/eval/results/run_locomo_context_packet_canary.py test_locomo_context_packet_canary.py benchmark_scripts/locomo_bench_v2.py
git diff --check
```

## Frozen final-context runs

Fresh baseline+frozen runs were first launched to capture cross-conversation substrates. The scored final artifact-pinned runs used those baseline artifacts with `--frozen-baseline-artifact-final-context-replay`, so packet append rows were `0` and the final scored deltas isolate answer-side prompt changes over fixed final context.

Final command shape per conversation:

```bash
python3 docs/eval/results/run_locomo_context_packet_canary.py \
  --sample-id <conv-44-or-conv-41> \
  --expected-qa-count <158-or-193> \
  --fixed-rows-path docs/eval/results/locomo_answer_side_crossconv_prereg_<sample>_2026-05-08.json \
  --min-prereg-rows 10 \
  --max-prereg-rows 15 \
  --merge-treatment \
  --merge-ref-gate \
  --frozen-context-replay \
  --frozen-baseline-artifact <matching baseline artifact> \
  --frozen-baseline-artifact-final-context-replay \
  --frozen-answer-shape-directive \
  --frozen-answer-shape-directive-categories multi-hop,temporal \
  --frozen-multimodal-metadata-projection \
  --frozen-multimodal-metadata-projection-categories single-hop,unanswerable
```

## Results

Per-conversation final artifact-pinned results:

| Conversation | Run ID | n | Score | Delta | Gold-hit | Packet appended | Category movement |
| --- | --- | ---: | ---: | ---: | --- | ---: | --- |
| `conv-44` | `20260508T023558Z` | 13 | `23.08 -> 38.46` | `15.38pp` | `0.6154 -> 0.6154` | 0 | single-hop 66.67->66.67; temporal 50.00->50.00; multi-hop 0.00->33.33; unanswerable 0.00->33.33; adversarial 0.00->0.00 |
| `conv-41` | `20260508T023704Z` | 12 | `54.17 -> 54.17` | `0.0pp` | `0.6667 -> 0.6667` | 0 | single-hop 75.00->75.00; temporal 66.67->66.67; multi-hop 50.00->50.00; unanswerable 50.00->50.00; adversarial 33.33->33.33 |

Combined 25-row aggregate across the two preselected conversations:

- Overall: `38.0 -> 46.0` (`8.0pp`, n=25).
- adversarial: `20.0 -> 20.0` (`0.0pp`, n=5).
- multi-hop: `20.0 -> 40.0` (`20.0pp`, n=5).
- single-hop: `70.0 -> 70.0` (`0.0pp`, n=5).
- temporal: `60.0 -> 60.0` (`0.0pp`, n=5).
- unanswerable: `20.0 -> 40.0` (`20.0pp`, n=5).

Improved rows:
- `conv-44` row 21 (multi-hop): `0.0 -> 1.0`; baseline `I don't know.`; treatment `Chicken (as in Chicken Pot Pie)`.
- `conv-44` row 65 (unanswerable): `0.0 -> 1.0`; baseline `I don't know.`; treatment `Audrey has a tattoo of sunflowers.`.
- Regressed rows: none by judge score.

Under-listing audit:

- `conv-44` row 4 (single-hop): list-type places; treatment changed list but no score drop and not a strict subset of baseline/gold by manual screen.
- `conv-44` row 90 (unanswerable): gold list; both baseline/treatment I don't know in final artifact run.
- `conv-44` row 132 (adversarial): gold list; both baseline/treatment I don't know.
- `conv-41` row 7 (single-hop): gold list; both baseline/treatment returned homeless shelter only, no treatment-induced under-listing.
- `conv-41` row 31 (single-hop): gold list; both returned homeless shelter and dog shelter.
- `conv-41` row 66 (unanswerable): two-part answer; no treatment-induced under-listing.
- `conv-41` row 168 (adversarial): gold list; both returned salads, sandwiches, homemade desserts.
- Row-53-class under-listing failures by the predeclared definition: `0`.

## Interpretation

This gate is mixed, and it should be treated as a diagnostic result only.

What it supports:

- The locked answer-side candidate had positive combined movement on a hash-selected cross-conversation 25-row gate: `38.0 -> 46.0` (+8pp).
- The predeclared multi-hop threshold passed on this gate: multi-hop `20.0 -> 40.0` (+20pp), above the +6pp absolute threshold.
- The row-53-class under-listing watchpoint did not fire: no score regressions and 0 mechanical under-listing failures.
- Packet append was 0/25 in the final artifact-pinned runs, so these final scored deltas are answer-side over fixed context, not retrieval expansion.

What it does not support:

- Do not call this quote-worthy. It is n=25 across two conversations, not 199Q/cumulative.
- Do not claim retrieval improvement. Gold-hit was flat in the final artifact-pinned runs (`conv-44` 0.6154 -> 0.6154; `conv-41` 0.6667 -> 0.6667).
- Do not claim broad category robustness. The combined gain comes from `conv-44` multi-hop/unanswerable movement; `conv-41` final artifact-pinned run was flat overall and flat on multi-hop.
- Do not claim adversarial/conflict improvement. Adversarial stayed `20.0 -> 20.0` combined.

Bottom line: the cross-conversation gate clears the predeclared multi-hop and under-listing gates, but the effect is heterogeneous and still diagnostic. It justifies preparing a preregistered 199Q candidate if desired; it does not itself justify quoting a benchmark result.

## Artifacts preserved

- `docs/eval/results/locomo_context_packet_canary_baseline_20260508T023558Z.json`
- `docs/eval/results/locomo_context_packet_canary_treatment_merge_refgate_frozen_artifactctx_shaped_multihop_temporal_mmmeta_singlehop_unanswerable_20260508T023558Z.json`
- `docs/eval/results/locomo_context_packet_canary_summary_merge_refgate_frozen_artifactctx_shaped_multihop_temporal_mmmeta_singlehop_unanswerable_20260508T023558Z.json`
- `docs/eval/results/locomo_context_packet_canary_result_merge_refgate_frozen_artifactctx_shaped_multihop_temporal_mmmeta_singlehop_unanswerable_20260508T023558Z.md`
- `docs/eval/results/locomo_context_packet_canary_baseline_20260508T023704Z.json`
- `docs/eval/results/locomo_context_packet_canary_treatment_merge_refgate_frozen_artifactctx_shaped_multihop_temporal_mmmeta_singlehop_unanswerable_20260508T023704Z.json`
- `docs/eval/results/locomo_context_packet_canary_summary_merge_refgate_frozen_artifactctx_shaped_multihop_temporal_mmmeta_singlehop_unanswerable_20260508T023704Z.json`
- `docs/eval/results/locomo_context_packet_canary_result_merge_refgate_frozen_artifactctx_shaped_multihop_temporal_mmmeta_singlehop_unanswerable_20260508T023704Z.md`

Additional preregistration files:

- `docs/eval/results/locomo_answer_side_crossconv_prereg_25rows_2026-05-08.json`
- `docs/eval/results/locomo_answer_side_crossconv_prereg_conv-44_2026-05-08.json`
- `docs/eval/results/locomo_answer_side_crossconv_prereg_conv-41_2026-05-08.json`

## Handoff closeout

Repository state at closeout:

- Branch: `query-expansion`.
- Latest pushed result commit before this handoff note: `a804547 eval: add LOCOMO cross-conversation answer gate`.
- The cross-conversation gate doc, preregistration files, runner/test changes, and final `20260508T023558Z` / `20260508T023704Z` artifacts were committed and pushed in `a804547`.
- Verification for that commit passed: `python3 -m unittest -q test_locomo_context_packet_canary.py` (`48` tests OK), `py_compile` for runner/tests/benchmark, `git diff --check`, per-conversation identity preflights, and redaction sanity over final summaries.
- Current intentionally untracked items remain outside the evidence package: `docs/reference/` plus older/exploratory canary artifacts, including `20260505T111609Z`, `20260508T014920Z`, `20260508T015059Z`, `20260508T020434Z`, `20260508T023155Z`, and `20260508T023359Z` artifact families.

Current locked candidate for any future preregistered 199Q preparation:

- answer-shape directive scoped to `multi-hop,temporal`;
- multimodal metadata projection scoped to `single-hop,unanswerable`;
- no subject guard;
- preserve frozen/artifact-pinned comparability where possible;
- predeclare thresholds and rollback criteria before execution.

Blocked without separate explicit approval:

- full 199Q LOCOMO;
- cumulative benchmark;
- DB/Docker/runtime mutation;
- direct `/mcp/tools` curl inspection;
- touching or committing `docs/reference/`.

Copy/paste bottom line:

> On frozen 25-row diagnostics, answer-shape directives show generation-side sensitivity with flat gold-hit, same-conversation off-slice support, and a hash-selected cross-conversation gate that cleared the multi-hop watchpoint but was heterogeneous. This supports preparing a preregistered 199Q candidate if explicitly approved; it is not a benchmark claim.
