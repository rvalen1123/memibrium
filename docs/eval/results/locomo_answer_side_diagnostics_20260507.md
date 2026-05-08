# LOCOMO answer-side diagnostics — 2026-05-07

Scope: default-off/eval-only answer-prompt diagnostics for the fixed-row Memibrium LOCOMO context-packet canary. This is implementation and verification documentation only. It is not a full 199Q benchmark, not a cumulative benchmark, and not a score claim.

## Why this exists

The 25-row source-attribution canary audit from run `20260506T103203Z` showed that the next bottleneck is not more entity/time post-filter tuning. Remaining non-full rows were mostly answer-side synthesis/conflict errors or multimodal metadata/object projection gaps:

- Row 113: final context included the relevant D8:6 turn, but the answer object (`sunset with a palm tree`) was present in LOCOMO image metadata (`blip_caption` / image query), not the plain dialogue text.
- Row 185: final context had the gold ref at rank 1, but salient contradictory acoustic-guitar evidence dominated the target answer (`clarinet and violin`).
- Row 163: final context had all gold atoms, but answer synthesis still returned `I don't know`.

## Implementation

Changed files:

- `docs/eval/results/run_locomo_context_packet_canary.py`
- `test_locomo_context_packet_canary.py`

New default-off frozen replay flags:

```bash
--frozen-multimodal-metadata-projection
--frozen-multimodal-metadata-projection-categories <comma-separated normalized categories>
```

Related existing flags that can be combined in frozen replay:

```bash
--frozen-answer-subject-guard
--frozen-answer-subject-guard-categories <comma-separated normalized categories>
--frozen-answer-shape-directive
--frozen-answer-shape-directive-categories <comma-separated normalized categories>
```

New/helper behavior:

- `render_multimodal_metadata_projection(...)` renders retrieved-ref-aligned LOCOMO image/query metadata above raw snippets:
  - `dia_id`
  - `speaker`
  - source memory id
  - dialogue text
  - `blip_caption`
  - `query` as `image_query`
  - `img_url_count`
- `_memory_dialogue_ref_span(...)` maps ingested `refs.session_index` back to LOCOMO `D*` sessions via the existing lexicographic `session_order_mapping`.
- `render_answer_subject_guard(..., ground_truth=...)` can now include the benchmark adversarial target answer and an explicit conflict-surfacing rule.
- `validate_paired_artifacts(...)` can classify prompt deltas from `multimodal_metadata_projection`.

New telemetry when enabled:

- `recall_telemetry.counts.multimodal_metadata_projection_enabled`
- `recall_telemetry.counts.multimodal_metadata_projection_row_count`
- `recall_telemetry.multimodal_metadata_projection_sha256`
- `comparison.prompt_context_delta_source_by_row` may include `multimodal_metadata_projection`.

Default-off behavior is preserved: without the new flag, no multimodal metadata projection is prepended to answer prompts.

## Verification performed

```bash
python3 -m unittest -q test_locomo_context_packet_canary.py
# Ran 47 tests OK

python3 -m py_compile docs/eval/results/run_locomo_context_packet_canary.py test_locomo_context_packet_canary.py benchmark_scripts/locomo_bench_v2.py
# OK

git diff --check
# OK

python3 docs/eval/results/run_locomo_context_packet_canary.py \
  --identity-only \
  --fixed-rows-path docs/eval/results/locomo_context_packet_merge_prereg_25rows_2026-05-03.json \
  --min-prereg-rows 20 \
  --max-prereg-rows 30
# exit 0
```

No 25-row scored rerun was launched in this implementation step because the live runner checks `/mcp/tools`, and the current standing constraint is not to retry direct `/mcp/tools` inspection without permission.

## Suggested next canary, pending explicit approval

Run the same fixed 25-row artifact-pinned/frozen canary, scoped first to likely affected categories/rows, with default-off diagnostics enabled. Candidate flag shape:

```bash
python3 docs/eval/results/run_locomo_context_packet_canary.py \
  --fixed-rows-path docs/eval/results/locomo_context_packet_merge_prereg_25rows_2026-05-03.json \
  --min-prereg-rows 20 \
  --max-prereg-rows 30 \
  --merge-treatment \
  --merge-ref-gate \
  --frozen-context-replay \
  --frozen-baseline-artifact docs/eval/results/locomo_context_packet_canary_treatment_merge_refgate_frozen_shaped_multihop_temporal_goldcov_20260506T103203Z.json \
  --frozen-baseline-artifact-final-context-replay \
  --frozen-answer-shape-directive \
  --frozen-answer-shape-directive-categories multi-hop,temporal \
  --frozen-answer-subject-guard \
  --frozen-answer-subject-guard-categories adversarial \
  --frozen-multimodal-metadata-projection \
  --frozen-multimodal-metadata-projection-categories single-hop,unanswerable \
  --frozen-gold-object-coverage-telemetry \
  --frozen-gold-object-coverage-telemetry-categories single-hop,temporal,multi-hop,unanswerable,adversarial
```

Before running, re-check the current runner help and live preconditions. Treat any output as a same-slice diagnostic only, not a benchmark claim.

## Guardrails

- Do not run full 199Q LOCOMO without explicit approval.
- Do not run cumulative benchmark without explicit approval.
- Do not mutate DB/Docker/runtime state without explicit approval.
- Do not retry direct `/mcp/tools` curl inspection without permission.
- Do not touch or commit `docs/reference/` unless explicitly asked.
- Redact secrets from env/logs/artifacts.
