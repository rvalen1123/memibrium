# LOCOMO hybrid-active telemetry instrumentation mutation-window result — 2026-05-01

## Stop/go decision

`go_telemetry_observation`

The preregistered instrumentation mutation window passed: local behavior-preservation tests passed, the server was rebuilt/restarted exactly once from commit `cb56559`, substrate checks remained canonical, telemetry-off smoke hashes matched exactly, the hybrid-active probe passed, and the explicit telemetry-emission probe returned the expected additive telemetry object without polluting the default response shape.

This result authorizes only the next separately gated telemetry-augmented baseline observation window. It does not authorize Phase C implementation.

## Scope executed

- Repo: `/home/zaddy/src/Memibrium`
- Branch: `query-expansion`
- HEAD during mutation window: `cb56559` (`cb565591a27d394d45b285c24a48390ebe3988bd`)
- Rebuild/restart command executed once: `docker compose -f docker-compose.ruvector.yml up -d --build memibrium`
- No LOCOMO benchmark was launched.
- No LOCOMO ingest or cleanup was performed.
- No DB write, schema migration, index rebuild, env edit, retrieval intervention, prompt/judge/evaluator change, or Phase C implementation was performed.

## Pre-mutation local tests

Command:

```bash
git diff --check && python3 -m py_compile hybrid_retrieval.py server.py benchmark_scripts/locomo_bench_v2.py test_hybrid_retrieval_ruvector.py test_locomo_query_expansion.py test_server_recall_telemetry.py && python3 -m unittest test_hybrid_retrieval_ruvector test_locomo_query_expansion test_server_recall_telemetry
```

Result: 70 tests passed.

## Pre-mutation snapshot

- Captured at: `2026-05-01T21:43:15.017658+00:00`
- Health: `{"engine": "memibrium", "status": "ok"}`
- Server container: `server_image=sha256:e61857cc17f69f5cc6c76971fabe02b6657156148847aaaf711939707b6f0356 created=2026-05-01T14:50:21.953131594Z started=2026-05-01T14:50:22.996971396Z`
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
hybrid_telemetry_schema_present=True
server_include_telemetry_present=True
```

- Log flags: `{"contains_hybrid_retrieval_failed": false, "contains_telemetry_serialization": false, "contains_type_vector_missing": false}`

## Post-mutation snapshot

- Captured at: `2026-05-01T21:44:43.275317+00:00`
- Health: `{"engine": "memibrium", "status": "ok"}`
- Server container: `server_image=sha256:565195f02c3ee78f4e951e64a65bd18a2e56addca5a23d89ba9b87e456fdc4ae created=2026-05-01T21:44:07.781283486Z started=2026-05-01T21:44:09.174007932Z`
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
hybrid_telemetry_schema_present=True
server_include_telemetry_present=True
```

- Log flags: `{"contains_hybrid_retrieval_failed": false, "contains_telemetry_serialization": false, "contains_type_vector_missing": false}`

## Smoke-hash comparability

Telemetry was omitted for both smoke sets.

- Pre-mutation aggregate hash: `b15c7ab85bd3d9b2d9f33b4919aa1b6717bb39556d3d107cf14d938d65217625`
- Post-mutation aggregate hash: `b15c7ab85bd3d9b2d9f33b4919aa1b6717bb39556d3d107cf14d938d65217625`
- Aggregate hash match: `True`
- Per-query hash match: `True`
- Smoke queries: `16`

Per-query result counts and hashes are preserved in `docs/eval/results/locomo_hybrid_active_telemetry_instrumentation_smoke_hashes_2026-05-01.json`.

## Hybrid-active probe

Probe: `POST /mcp/recall` with query `hybrid active ruvector smoke probe`, `top_k=1`, and nonexistent domain `__hybrid_active_probe_no_rows__`.

- HTTP OK: `True`
- Status: `200`
- Response JSON: `[]`
- Fresh log flags: `{"contains_hybrid_retrieval_failed": false, "contains_telemetry_serialization": false, "contains_type_vector_missing": false}`

Pass interpretation: empty list is valid because the probe domain intentionally has no rows; no hybrid fallback or `type "vector" does not exist` log appeared.

## Telemetry-emission probe

Probe: `POST /mcp/recall` with query `hybrid telemetry ruvector smoke probe`, `top_k=3`, nonexistent domain `__hybrid_telemetry_probe_no_rows__`, and `include_telemetry=true`.

- Telemetry response OK/status: `True` / `200`
- Plain response OK/status for same query without telemetry: `True` / `200`
- Plain response shape: `list`
- Telemetry response contains top-level `results` and `telemetry`: `True`
- Result ids/order/count match plain response: `True`
- Server telemetry: `{"embedding_error": null, "embedding_success": true, "hybrid_path_attempted": true, "hybrid_retriever_present": true, "legacy_fallback_executed": false, "response_result_count": 0}`
- Requested top_k: `3`
- Semantic returned count: `0`
- Lexical returned count: `0`
- Temporal executed: `False`
- Temporal stream returned count: `0`
- Fused count before cap: `0`
- Final returned count: `0`
- Final items list: `[]`
- Fresh log flags: `{"contains_hybrid_retrieval_failed": false, "contains_telemetry_serialization": false, "contains_type_vector_missing": false}`

## Artifact inventory

- Pre snapshot JSON: `docs/eval/results/locomo_hybrid_active_telemetry_instrumentation_pre_snapshot_2026-05-01.json`
- Post snapshot JSON: `docs/eval/results/locomo_hybrid_active_telemetry_instrumentation_post_snapshot_2026-05-01.json`
- Hybrid probe JSON: `docs/eval/results/locomo_hybrid_active_telemetry_instrumentation_hybrid_probe_2026-05-01.json`
- Telemetry probe JSON: `docs/eval/results/locomo_hybrid_active_telemetry_instrumentation_telemetry_probe_2026-05-01.json`
- Smoke summary JSON: `docs/eval/results/locomo_hybrid_active_telemetry_instrumentation_smoke_hashes_2026-05-01.json`
- Helper script: `scripts/locomo_telemetry_mutation_window.py`

## Conclusion

The mutation window passed with `go_telemetry_observation`.

The next track step is the separately gated telemetry-augmented baseline observation run. Phase C remains blocked pending that observation, analysis, and a telemetry-grounded intervention preregistration.
