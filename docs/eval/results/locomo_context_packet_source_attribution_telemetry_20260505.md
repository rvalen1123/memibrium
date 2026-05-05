# LOCOMO context-packet source attribution telemetry — 2026-05-05

Status: implemented as default-off/eval-only telemetry. This is diagnostic plumbing only; it is not a benchmark result or LOCOMO performance claim.

## Why this was added

Candidate-pool preservation made artifact replay possible, and the follow-up candidate-pool generation audit showed that missing gold atoms were usually absent from the preserved `context_packet_candidate_pool`. However, those artifacts did not preserve enough provenance to tell whether a missing atom was caused by:

- query wording or decomposition,
- vector recall/ranking,
- top-k candidate cap,
- ref-gate or merge-cap behavior,
- multimodal/image metadata-only evidence that is not present in dialogue text.

This change adds opt-in source attribution so future canary/audit runs can classify those cases without changing default benchmark/runtime behavior.

## Implemented behavior

Changed files:

- `server.py`
- `benchmark_scripts/locomo_bench_v2.py`
- `docs/eval/results/run_locomo_context_packet_canary.py`
- `test_context_graph_v0.py`
- `test_locomo_query_expansion.py`
- `test_locomo_context_packet_canary.py`

### Server

`/mcp/context_packet` now accepts optional request field:

```json
{"include_source_attribution": true}
```

Default behavior remains unchanged when omitted or false.

When enabled and the endpoint performs internal `query_agent.recall`, the response includes `source_attribution` with schema `memibrium.context_packet.source_attribution.v1`, request query/domain/top_k, retrieval path, recall tier/total searched when available, and compact evidence projections.

Evidence projections include only diagnostic-safe compact fields:

- rank
- memory id
- stage
- refs
- score
- created_at
- content hash
- snippet

### Benchmark/canary telemetry

`benchmark_scripts/locomo_bench_v2.py` adds default-off env flag:

```bash
INCLUDE_CONTEXT_PACKET_SOURCE_ATTRIBUTION=1
```

When enabled, context-packet requests include `include_source_attribution: true` and store the returned data under:

```text
recall_telemetry.context_packet_source_attribution
```

The compact `recall_telemetry.context_packet` projection intentionally excludes raw `source_attribution`, so source attribution remains separate diagnostic telemetry.

### Frozen artifact replay

`docs/eval/results/run_locomo_context_packet_canary.py` now preserves `context_packet_source_attribution` through frozen baseline row loading and frozen full-context replay.

## TDD coverage added

- `test_context_packet_source_attribution_is_opt_in_and_records_internal_recall_source`
- `test_context_packet_source_attribution_default_off_and_enabled_in_eval_telemetry`
- `test_frozen_baseline_rows_from_artifact_preserves_context_packet_source_attribution`
- `test_answer_question_with_frozen_context_replay_preserves_artifact_source_attribution`

## Verification

Passed after implementation:

```bash
python3 -m unittest test_context_graph_v0 test_locomo_query_expansion test_locomo_context_packet_canary -v
# Ran 116 tests, OK

python3 -m py_compile server.py benchmark_scripts/locomo_bench_v2.py docs/eval/results/run_locomo_context_packet_canary.py test_context_graph_v0.py test_locomo_query_expansion.py test_locomo_context_packet_canary.py

git diff --check

python3 docs/eval/results/run_locomo_context_packet_canary.py --identity-only --fixed-rows-path docs/eval/results/locomo_context_packet_merge_prereg_25rows_2026-05-03.json --min-prereg-rows 20 --max-prereg-rows 30
# ok: true
```

No DB/Docker/runtime mutation was performed. No full 199Q LOCOMO run was performed. No cumulative run was performed.

## Commit decision

Recommended commit scope is only the telemetry implementation, tests, and this documentation file. Do not include pre-existing `docs/reference/` noise or older untracked `20260505T111609Z` artifacts. The candidate-pool generation audit artifacts from `20260505T162823Z` are useful, but should remain a separate decision from the source-attribution telemetry commit unless explicitly bundled.
