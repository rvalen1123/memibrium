# LOCOMO telemetry serialization fix mutation-window result — 2026-05-02

## Stop/go decision

`go_telemetry_observation_retry`

The preregistered Decimal-safe telemetry serialization correction mutation window passed. Local tests passed, the server was rebuilt/restarted exactly once from commit `5cb6f0b`, substrate checks remained canonical, expanded telemetry-off smoke hashes matched exactly, the hybrid-active probe passed, the explicit telemetry-emission probe passed, and the 40-query telemetry-on production-distribution serialization probe returned HTTP 200/valid JSON for every request with no Decimal serialization, TypeError, hybrid fallback, or missing-vector-type log errors.

This result authorizes only requesting/entering the separately gated telemetry-augmented baseline retry observation window under the original telemetry baseline preregistration. It does not authorize Phase C implementation.

## Scope executed

- Repo: `/home/zaddy/src/Memibrium`
- Branch: `query-expansion`
- HEAD during mutation window: `5cb6f0b` (`5cb6f0bf9de64e2879a9f6cdd0f24660bf9ac32b`)
- Code/test correction already committed before this live window: `fix: serialize Decimal values in recall telemetry`
- Rebuild/restart command executed once: `docker compose -f docker-compose.ruvector.yml up -d --build memibrium`
- No LOCOMO benchmark was launched.
- No LOCOMO ingest or cleanup was performed.
- No DB write, schema migration, index rebuild, env edit, retrieval intervention, prompt/judge/evaluator change, or Phase C implementation was performed.

## Pre-mutation local tests

Command:

```bash
git diff --check
python3 -m py_compile hybrid_retrieval.py server.py benchmark_scripts/locomo_bench_v2.py test_hybrid_retrieval_ruvector.py test_locomo_query_expansion.py test_server_recall_telemetry.py
python3 -m unittest test_hybrid_retrieval_ruvector test_locomo_query_expansion test_server_recall_telemetry
```

Result: `72` tests passed.

The two new Decimal regression tests first failed before the fix with `TypeError: Object of type Decimal is not JSON serializable`, including the same `server.py::handle_recall()` / `JSONResponse` failure class as the blocked Step 5 observation.

## Pre-mutation snapshot

- Artifact: `docs/eval/results/locomo_hybrid_active_telemetry_serialization_fix_pre_snapshot_2026-05-02.json`
- Captured from live server before rebuild/restart.
- Branch/head/status: `query-expansion` / `5cb6f0bf9de64e2879a9f6cdd0f24660bf9ac32b` / clean
- Health: `{"status":"ok","engine":"memibrium"}`
- Server container before rebuild: `server_image=sha256:565195f02c3ee78f4e951e64a65bd18a2e56addca5a23d89ba9b87e456fdc4ae created=2026-05-01T21:44:07.781283486Z started=2026-05-01T21:44:09.174007932Z`
- `USE_RUVECTOR`: `true`
- Azure embedding deployment: `text-embedding-3-small`
- Azure chat deployment: `gpt-4.1-mini`
- Azure OpenAI deployment: `gpt-4.1-mini`
- Local embedding env still present but superseded by Azure embedding path in server code: `nomic-embed-text`
- Chat model env: `gemma4:e4b`
- DB probe: `{"locomo_contamination_count": 0, "memories_embedding_type": "USER-DEFINED:ruvector", "nonnull_embeddings": 20, "ruvector_extension_version": "0.3.0", "ruvector_type_count": 1, "self_distance": "1.7872301e-07", "vector_type_count": 0}`
- Live source feature probe:

```text
hardcoded_vector_cast_present=False
dynamic_vtype_cast_present=True
decimal_import_present=True
server_include_telemetry_present=True
```

## Pre-mutation telemetry serialization sample

- Artifact: `docs/eval/results/locomo_hybrid_active_telemetry_serialization_fix_pre_serialization_probe_2026-05-02.json`
- Query count: `10`
- Telemetry requested: `include_telemetry=true`
- All responses HTTP 200/valid JSON: `true`
- Fresh log flags:

```json
{
  "contains_decimal_not_json_serializable": false,
  "contains_type_error": false,
  "contains_hybrid_retrieval_failed": false,
  "contains_type_vector_missing": false
}
```

Interpretation: because the host source is bind-mounted into the running container, the source-level Decimal fix was visible before the rebuild. The preregistered rebuild/restart was still executed exactly once to refresh the live container/image evidence chain.

## Rebuild/restart

Executed exactly once:

```bash
docker compose -f docker-compose.ruvector.yml up -d --build memibrium
```

Bounded health wait passed with:

```json
{"status":"ok","engine":"memibrium"}
```

No second rebuild/restart was performed.

## Post-mutation snapshot

- Artifact: `docs/eval/results/locomo_hybrid_active_telemetry_serialization_fix_post_snapshot_2026-05-02.json`
- Health: `{"status":"ok","engine":"memibrium"}`
- Server container after rebuild: `server_image=sha256:76fed12e0da1324ab1e26e927fa3fa1a3aa6e7b340d5f7ab6e481da3e0afe9b6 created=2026-05-02T12:30:16.960478122Z started=2026-05-02T12:30:18.612989007Z`
- `USE_RUVECTOR`: `true`
- Azure embedding deployment: `text-embedding-3-small`
- Azure chat deployment: `gpt-4.1-mini`
- Azure OpenAI deployment: `gpt-4.1-mini`
- Local embedding env still present but superseded by Azure embedding path in server code: `nomic-embed-text`
- Chat model env: `gemma4:e4b`
- DB probe: `{"locomo_contamination_count": 0, "memories_embedding_type": "USER-DEFINED:ruvector", "nonnull_embeddings": 20, "ruvector_extension_version": "0.3.0", "ruvector_type_count": 1, "self_distance": "1.7872301e-07", "vector_type_count": 0}`
- Live source feature probe:

```text
hardcoded_vector_cast_present=False
dynamic_vtype_cast_present=True
decimal_import_present=True
server_include_telemetry_present=True
```

Substrate verdict: pass.

## Expanded telemetry-off smoke-hash comparability

- Artifact: `docs/eval/results/locomo_hybrid_active_telemetry_serialization_fix_smoke_hashes_2026-05-02.json`
- Smoke query count: `40`
- Telemetry omitted for both smoke sets.
- Pre-mutation aggregate hash: `ccdb88c7852853bfa4fa514b5a389c528c0425bbb970cd0e55772814080acc54`
- Post-mutation aggregate hash: `ccdb88c7852853bfa4fa514b5a389c528c0425bbb970cd0e55772814080acc54`
- Aggregate hash match: `true`

Behavior-preservation verdict: pass.

## Hybrid-active probe

- Artifact: `docs/eval/results/locomo_hybrid_active_telemetry_serialization_fix_hybrid_probe_2026-05-02.json`
- Probe: `POST /mcp/recall` with query `hybrid active ruvector smoke probe`, `top_k=1`, and nonexistent domain `__hybrid_active_probe_no_rows__`.
- Status: `200`
- Fresh log flags:

```json
{
  "contains_decimal_not_json_serializable": false,
  "contains_hybrid_retrieval_failed": false,
  "contains_type_error": false,
  "contains_type_vector_missing": false
}
```

Hybrid-active verdict: pass. Empty response remains valid for the intentionally nonexistent domain.

## Telemetry-emission probe

- Artifact: `docs/eval/results/locomo_hybrid_active_telemetry_serialization_fix_telemetry_probe_2026-05-02.json`
- Probe: `POST /mcp/recall` with query `hybrid telemetry ruvector smoke probe`, `top_k=3`, nonexistent domain `__hybrid_telemetry_probe_no_rows__`, and `include_telemetry=true`.
- Telemetry response status: `200`
- Matching plain response status: `200`
- Telemetry response shape: top-level object with `results` and `telemetry`
- Plain response shape: top-level list
- Fresh log flags:

```json
{
  "contains_decimal_not_json_serializable": false,
  "contains_hybrid_retrieval_failed": false,
  "contains_type_error": false,
  "contains_type_vector_missing": false
}
```

Telemetry-emission verdict: pass.

## Telemetry-on production-distribution serialization probe

- Artifact: `docs/eval/results/locomo_hybrid_active_telemetry_serialization_fix_serialization_probe_2026-05-02.json`
- Query count: `40`
- Query source: expanded fixed smoke set sampled from LOCOMO-like conv-26/person/event/date/adversarial query distribution.
- Telemetry requested for every query: `include_telemetry=true`
- Varied requested top-k values: `1`, `3`, `5`, `10`, `15`
- All responses HTTP 200 and valid JSON: `true`
- Fresh log flags:

```json
{
  "contains_decimal_not_json_serializable": false,
  "contains_type_error": false,
  "contains_hybrid_retrieval_failed": false,
  "contains_type_vector_missing": false
}
```

Telemetry serialization verdict: pass.

## Artifact inventory

Primary result:

- `docs/eval/results/locomo_hybrid_active_telemetry_serialization_fix_mutation_window_result_2026-05-02.md`

Supporting evidence:

- `docs/eval/results/locomo_hybrid_active_telemetry_serialization_fix_pre_snapshot_2026-05-02.json`
- `docs/eval/results/locomo_hybrid_active_telemetry_serialization_fix_pre_serialization_probe_2026-05-02.json`
- `docs/eval/results/locomo_hybrid_active_telemetry_serialization_fix_post_snapshot_2026-05-02.json`
- `docs/eval/results/locomo_hybrid_active_telemetry_serialization_fix_smoke_hashes_2026-05-02.json`
- `docs/eval/results/locomo_hybrid_active_telemetry_serialization_fix_hybrid_probe_2026-05-02.json`
- `docs/eval/results/locomo_hybrid_active_telemetry_serialization_fix_telemetry_probe_2026-05-02.json`
- `docs/eval/results/locomo_hybrid_active_telemetry_serialization_fix_serialization_probe_2026-05-02.json`

## Conclusion

The mutation window passed with `go_telemetry_observation_retry`.

The next valid track step is Step 5d: request/enter the separately gated telemetry-augmented hybrid-active baseline retry observation window under the original preregistration `docs/eval/locomo_telemetry_augmented_baseline_preregistration_2026-05-01.md`, using distinct retry artifact names.

Phase C remains blocked pending a complete, comparable telemetry baseline retry, cleanup, analysis, and telemetry-grounded intervention preregistration.
