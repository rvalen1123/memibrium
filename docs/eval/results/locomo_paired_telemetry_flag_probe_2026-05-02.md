# LOCOMO paired telemetry flag probe — 2026-05-02

## Verdict

`telemetry_perturbation_ruled_out`

All 8 fixed non-LOCOMO query pairs returned identical result counts, IDs/order, and score/similarity fields within the preregistered `1e-12` tolerance. Telemetry-off preserved the legacy list shape; telemetry-on returned an object with `results` and `telemetry`. No fresh relevant server log errors were detected.

Evidence caveat: all 8 preregistered pairs returned zero results in both conditions. The primary label follows the preregistered stop/go rule, but this probe only exercises empty-result/no-hit behavior and does not stress non-empty result ordering or score comparison.

Phase C remains blocked. This result does not make either the f2466c9 14.82% baseline or the 91fede6 58.29% retry a comparable Phase C baseline.

## Scope and authorization

Authorized by user instruction: `proceed` after Step 5g preregistration commit `544a003`.

Performed: Step 5h preflight, 8 same-query telemetry off/on direct `/mcp/recall` pairs, result comparison, fresh-log scan, artifact writing, commit preparation.

Not performed: LOCOMO benchmark rerun, LOCOMO ingest, DB writes, DB cleanup, Docker rebuild/restart, env/source/schema/runtime mutation, Phase C intervention selection.

## Preflight summary

- Preflight gate status: `pass`
- Gate failures: `[]`
- Branch: `query-expansion`
- HEAD: `544a003`
- Health: `{"status":"ok","engine":"memibrium"}`
- LOCOMO count: `0`
- DB type checks: `embedding_type|USER-DEFINED:ruvector; ruvector_type_count|1; vector_type_count|0`
- Canonical substrate gates passed: `USE_RUVECTOR=true`, `text-embedding-3-small`, `gpt-4.1-mini`, `memories.embedding=USER-DEFINED:ruvector`, ruvector present, vector absent, dynamic `$1::{self.vtype}` present, hardcoded `$1::vector` absent, Decimal-safe `_serialize_result()` present.

## Probe design executed

- Endpoint: `http://localhost:9999/mcp/recall`
- Execution order: off then on, interleaved by query, no randomization.
- Telemetry-off payload: `{ "query": <query>, "top_k": 10 }`
- Telemetry-on payload: `{ "query": <query>, "top_k": 10, "include_telemetry": true }`
- Total calls: 16
- Domain filter: none

## Pair comparison summary

- all_status_200: `True`
- all_valid_json: `True`
- all_shapes_valid: `True`
- all_counts_identical: `True`
- all_ids_or_hashes_identical: `True`
- all_scores_within_tolerance: `True`
- all_paths_consistent: `True`
- material_divergence_count: `0`
- all_preregistered_pairs_empty_result_lists: `True`
- Fresh log errors: `[]`

| Pair | Query | Off count | On count | IDs/order equal | Scores within tol | Shapes | Path consistent |
|---:|---|---:|---:|---|---|---|---|
| 1 | `project telemetry serialization behavior` | 0 | 0 | `True` | `True` | `list / object` | `True` |
| 2 | `Azure embedding deployment configuration` | 0 | 0 | `True` | `True` | `list / object` | `True` |
| 3 | `Docker ruvector database health checks` | 0 | 0 | `True` | `True` | `list / object` | `True` |
| 4 | `Memibrium query expansion context assembly` | 0 | 0 | `True` | `True` | `list / object` | `True` |
| 5 | `recent memory benchmark cleanup procedure` | 0 | 0 | `True` | `True` | `list / object` | `True` |
| 6 | `When was the telemetry serialization fix recorded?` | 0 | 0 | `True` | `True` | `list / object` | `True` |
| 7 | `How do recall telemetry responses preserve legacy result shape?` | 0 | 0 | `True` | `True` | `list / object` | `True` |
| 8 | `nonexistent control query zyxwvu qptrace sentinel` | 0 | 0 | `True` | `True` | `list / object` | `True` |

## Interpretation

Under the current live server state, opt-in recall telemetry did not perturb same-query `/mcp/recall` response shape, hybrid-path telemetry, result counts, or empty result identity for this fixed 8-query non-LOCOMO probe set. Because all preregistered pairs were empty-result pairs, this is strongest as a no-hit/empty-path behavior-preservation check and weaker for non-empty result ordering or score preservation.

Per the preregistered stop/go rule, the primary label is `telemetry_perturbation_ruled_out`. The remaining unresolved families are now centered on the f2466c9 low-context baseline: effective harness/runtime path mismatch, artifact mismatch, baseline non-reproducibility, or substrate-level nondeterminism. Next valid track: preregister a telemetry-off 199Q reproducibility rerun or an equivalent effective benchmark-harness/runtime drift audit for the f2466c9 low-context baseline. Phase C remains blocked until that comparability issue is resolved.

## Protocol deviation note

After the initial Step 5h artifacts were generated, 10 additional non-preregistered, non-LOCOMO, read-only `/mcp/recall` sanity checks were issued manually to understand why the preregistered fixed queries all returned zero results. These calls were not used to tune, replace, or reinterpret the preregistered 8 pairs; all returned zero results. No DB writes, LOCOMO ingest/cleanup, Docker/env/source/schema/runtime mutation, or benchmark execution occurred.

Protocol deviation artifact: `/home/zaddy/src/Memibrium/docs/eval/results/locomo_paired_telemetry_flag_probe_protocol_deviation_2026-05-02.json`

## Output artifacts

- Preflight: `/home/zaddy/src/Memibrium/docs/eval/results/locomo_paired_telemetry_flag_probe_preflight_2026-05-02.json`
- Pair raw data: `/home/zaddy/src/Memibrium/docs/eval/results/locomo_paired_telemetry_flag_probe_pairs_2026-05-02.json`
- Labels/summary: `/home/zaddy/src/Memibrium/docs/eval/results/locomo_paired_telemetry_flag_probe_labels_2026-05-02.json`
- Server log excerpt: `/home/zaddy/src/Memibrium/docs/eval/results/locomo_paired_telemetry_flag_probe_server_log_2026-05-02.log`
- Protocol deviation note: `/home/zaddy/src/Memibrium/docs/eval/results/locomo_paired_telemetry_flag_probe_protocol_deviation_2026-05-02.json`
- Primary report: `/home/zaddy/src/Memibrium/docs/eval/results/locomo_paired_telemetry_flag_probe_2026-05-02.md`
