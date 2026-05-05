# LOCOMO telemetry serialization fix mutation-window pre-registration — 2026-05-02

Repo: `/home/zaddy/src/Memibrium`  
Branch at preregistration start: `query-expansion`  
Current HEAD at preregistration start: `876eb04` (`docs: record LOCOMO telemetry baseline block`)  
Parent blocked observation: `docs/eval/results/locomo_hybrid_active_telemetry_baseline_199q_comparison_2026-05-01.md`  
Parent instrumentation result: `docs/eval/results/locomo_hybrid_active_telemetry_instrumentation_result_2026-05-01.md`

## Status and dependency chain

This document pre-registers Step 5a: the next valid unit after the blocked telemetry-augmented hybrid-active LOCOMO baseline observation.

Completed upstream state:

1. Phase B complete.
2. Phase B.5 root-cause diagnostic complete.
3. Hybrid-active blocker resolved.
4. Canonical substrate env alignment complete.
5. Canonical hybrid-active baseline complete.
6. Read-only failure-mode audit complete.
7. Telemetry baseline pre-registration complete.
8. Telemetry instrumentation pre-registration complete.
9. Opt-in telemetry instrumentation code/tests complete.
10. Telemetry instrumentation live mutation window complete with `go_telemetry_observation`.
11. Step 5 telemetry-augmented baseline observation attempted and blocked.

Blocked verdict from Step 5:

- Specific verdict: `telemetry_baseline_blocked_runtime_serialization_error`
- Stop/go output: `no_go_insufficient_evidence_expand_telemetry`
- Benchmark-side failure: `RuntimeError: MCP recall failed after 3 attempts: non-200 response; status=500; response=Internal Server Error`
- Server-side failure: `TypeError: Object of type Decimal is not JSON serializable`
- Failing path: `server.py::handle_recall()` opt-in telemetry response construction, returning `JSONResponse(_serialize_result({"results": result, "telemetry": response_telemetry}))`

This blocked run is not a comparable telemetry baseline. It must not be used to select a Phase C intervention and must not update the intervention prior.

## Purpose

The purpose of this pre-registration is single-purpose and behavior-preserving:

Fix JSON serialization of Decimal values in the opt-in telemetry response path so that telemetry-enabled recall responses serialize cleanly across production-like telemetry payloads.

The correction exists only to restore the measurement path needed for the telemetry-augmented baseline observation. It is not a retrieval, scoring, fusion, context, prompt, judge, evaluator, substrate, or Phase C intervention.

## Hard authorization boundary

This file itself pre-registers the future correction window. It does not authorize implementation yet.

After this pre-registration is committed, the next step must stop for review/authorization before any code changes are made.

### Authorized only after explicit correction-window authorization

1. Edit source code only for Decimal-safe JSON serialization in the opt-in telemetry response path.
2. Add or update tests proving Decimal-containing telemetry payloads serialize cleanly.
3. Run local syntax/unit tests.
4. Commit the source/test correction if local tests pass.

### Authorized only after separate live mutation-window authorization

1. Capture a pre-mutation live-server snapshot.
2. Run one rebuild/restart of the Memibrium server service.
3. Verify health, substrate, live source, hybrid-active status, telemetry emission, telemetry serialization safety, and telemetry-off behavior preservation.
4. Write and commit result artifacts.

### Not authorized by this pre-registration

- No immediate implementation before explicit authorization.
- No direct retry of the Step 5 LOCOMO benchmark.
- No LOCOMO benchmark launch.
- No LOCOMO ingest.
- No LOCOMO cleanup/deletion except if a separately authorized future LOCOMO launch contaminates the DB.
- No ad hoc live-server patch.
- No rebuild/restart before an explicit mutation-window authorization.
- No DB writes, schema migration, index rebuild, or data mutation.
- No env/substrate change.
- No Phase C implementation.
- No retrieval logic, SQL filter/order, score, fusion, threshold/cutoff, top-k, rerank, prompt, judge/evaluator, date-normalization, append/gated append, entity-attribution, legacy context assembly, or query-expansion behavior change.
- No inference of retrieval-cause family from the blocked partial run.

If a required check fails, stop and document. Do not repair in place by changing retrieval behavior or broadening the scope.

## Locked evidence from the blocked observation

The blocked run aborted before producing a valid 199-question telemetry baseline. The last preserved progress marker was 120/199 questions, but this partial run is invalid for comparability and causal inference.

Load-bearing artifacts from the block:

- Prelaunch: `docs/eval/results/locomo_hybrid_active_telemetry_baseline_prelaunch_2026-05-01.json`
- Main placeholder result: `docs/eval/results/locomo_conv26_hybrid_active_telemetry_baseline_2026-05-01.json`
- Trace placeholder result: `docs/eval/results/locomo_conv26_hybrid_active_telemetry_traces_2026-05-01.json`
- Failed run log: `docs/eval/results/locomo_conv26_hybrid_active_telemetry_baseline_2026-05-01.log`
- Comparison/blocked writeup: `docs/eval/results/locomo_hybrid_active_telemetry_baseline_199q_comparison_2026-05-01.md`
- Structured blocked evidence: `docs/eval/results/locomo_hybrid_active_telemetry_baseline_blocked_2026-05-01.json`
- Server log excerpt/full tail: `docs/eval/results/locomo_hybrid_active_telemetry_baseline_failed_server_log_2026-05-01.log`
- Cleanup log: `docs/eval/results/locomo_hybrid_active_telemetry_baseline_cleanup_2026-05-01.log`
- Cleanup count: `docs/eval/results/locomo_hybrid_active_telemetry_baseline_cleanup_count_2026-05-01.txt`
- Cleanup linked counts: `docs/eval/results/locomo_hybrid_active_telemetry_baseline_cleanup_linked_counts_2026-05-01.txt`

Cleanup was completed after the blocked run:

```text
temporal_expressions|0
memory_snapshots|0
user_feedback|0
contradictions|0
memory_edges|0
```

The current LOCOMO contamination count must remain `0` before any future mutation or observation window.

## Methodological interpretation

This is a smoke-set design gap, not a preregistration/gate failure.

The earlier telemetry instrumentation mutation-window smoke probes proved the opt-in telemetry code path emitted. They did not prove serialization safety across the production payload/data-type distribution reached by the 199-question LOCOMO observation.

Future telemetry mutation windows must therefore distinguish:

1. Telemetry-off smoke hashes for behavior preservation.
2. Telemetry-on production-distribution serialization probes for telemetry response safety.

Single-query or tiny telemetry probes only prove code-path emission. They do not prove telemetry serialization safety across varied `n_memories`, score/similarity shapes, candidate/fusion payload types, and nested production telemetry objects.

## Allowed correction scope

The correction scope is intentionally narrow.

Allowed touchpoints:

1. `server.py` serialization boundary:
   - `_serialize_result()` or an equivalent server-side JSON-safe normalization helper;
   - `handle_recall()` opt-in telemetry response construction if needed to ensure the combined `{results, telemetry}` payload is normalized before `JSONResponse` encodes it.

2. Tests:
   - `test_server_recall_telemetry.py` or a new focused test file for serialization helpers and recall telemetry responses;
   - updates to existing telemetry tests only to add Decimal/data-type fixtures, not to loosen behavior-preservation assertions.

3. `hybrid_retrieval.py`, only if investigation proves Decimal values are being inserted by telemetry schema construction and normalizing them at source is necessary to keep telemetry schemas consistently JSON-safe.

Preferred correction shape:

- Centralize JSON-safe normalization at the response serialization boundary.
- Preserve existing datetime/date conversion behavior.
- Add Decimal handling without changing numeric values used for retrieval, ranking, fusion, or final result ordering.
- Convert Decimal values to JSON-safe scalars in telemetry/result payloads before `JSONResponse` encoding.
- Preserve dict/list recursion and add tuple/set support only if tests show they appear in telemetry payloads; do not broaden behavior unnecessarily.

Decimal representation rule:

- Decimal values that represent scores/similarities/count-like telemetry should be converted to JSON numbers where safe, preferably `float(value)` for score/similarity telemetry and exact integer conversion only when the value is already integral and semantically count-like.
- The correction must not feed converted telemetry values back into retrieval or scoring logic.
- The test suite should lock only JSON serializability and stable response shape, not an over-specific formatting detail unless the implementation requires it.

## Explicit non-touchpoints

The correction must not modify:

- `RECALL_TOP_K`, `ANSWER_CONTEXT_TOP_K`, `RERANK_RECALL_TOP_K`, append-context top-k constants, or benchmark top-k settings.
- Semantic SQL ordering, lexical tsquery/ILIKE matching, temporal SQL, or domain/state filters.
- RRF formula, fusion weights, score normalization used for ranking, thresholds, or cutoff policy.
- Query expansion generation, fallback handling, or fallback counting.
- Multi-hop expansion behavior, chronology sorting behavior, returned-memory order, or memory dedupe behavior.
- Prompt text, answer model, judge model, date normalization, rerank, append/gated append, legacy context assembly, evaluator behavior, or category scoring.
- DB schema, DB rows, indexes, memory lifecycle state, embedding vectors, Docker compose substrate, or env configuration.
- Telemetry schema semantics except JSON-safe scalar normalization.

## Required local tests before any live mutation

Before any rebuild/restart, the correction must pass the existing test suite used for the telemetry instrumentation window and must add explicit Decimal serialization coverage.

Minimum command set:

```bash
cd /home/zaddy/src/Memibrium
git diff --check
python3 -m py_compile hybrid_retrieval.py server.py benchmark_scripts/locomo_bench_v2.py test_hybrid_retrieval_ruvector.py test_locomo_query_expansion.py test_server_recall_telemetry.py
python3 -m unittest test_hybrid_retrieval_ruvector test_locomo_query_expansion test_server_recall_telemetry
```

Existing-suite requirement:

- The existing 70-test suite from the telemetry instrumentation window must pass, or its exact current successor count must be reported if new tests increase the count.
- If `pytest` remains unavailable in the active Python environment, `python3 -m unittest` remains the canonical verifier for this local window.

New explicit Decimal/data-type tests:

1. `_serialize_result()` or equivalent helper converts Decimal values to JSON-serializable values inside nested dict/list structures.
2. Decimal serialization fixtures must include multiple data-type shapes, not a single flat value:
   - top-level Decimal score;
   - nested Decimal under `results[*]` score/similarity fields;
   - nested Decimal under telemetry stream candidate items;
   - Decimal inside telemetry score summaries, e.g. `min`, `max`, `mean`;
   - Decimal under fusion/final fields, e.g. `rrf_score`, `combined_score`, or cutoff candidate score;
   - datetime/date values preserved as ISO strings;
   - ordinary strings, booleans, `None`, ints, and floats preserved.
3. A production failure-class fixture must match the blocked run class: a nested opt-in recall payload with `{"results": result, "telemetry": response_telemetry}` containing Decimal values under returned results, stream candidates, fusion/final items, and score/similarity summaries.
4. `handle_recall()` with telemetry disabled must preserve the default legacy recall response shape as a top-level list and must not add a telemetry object.
5. `handle_recall()` with telemetry enabled must preserve result ids/order/count relative to telemetry disabled and return a top-level object with `results` and `telemetry` that `json.loads(response.body)` can parse without raising.
6. Test payloads should include more than one result item and more than one telemetry stream where practical, to avoid only exercising a trivial empty/no-row path.

Failure rule:

- If these local tests fail, stop with `blocked_pre_mutation_tests_failed`. Do not rebuild/restart and do not run live probes.

## Future live mutation window procedure

This section pre-registers the later Step 5c live mutation window. It requires separate explicit authorization after the code/test fix is committed.

### Step 0 — pre-mutation snapshot

Record all of the following before rebuild/restart:

- `date -Is`
- `git branch --show-current`
- `git rev-parse HEAD`
- `git status --short`
- `curl -fsS http://localhost:9999/health`
- `docker ps --format '{{.Names}}|{{.Status}}|{{.Image}}' | grep -E 'memibrium|ruvector|ollama'`
- `docker inspect memibrium-server --format 'server_image={{.Image}} created={{.Created}} started={{.State.StartedAt}}'`
- `docker image inspect <pre_image_id> --format 'image_created={{.Created}} repo_tags={{json .RepoTags}}'`
- redacted `docker exec memibrium-server env` for DB/vector/embedding/chat/telemetry keys
- host source hashes for `server.py`, `hybrid_retrieval.py` if touched, `benchmark_scripts/locomo_bench_v2.py`, and telemetry test/helper files
- container source hashes for `/app/server.py`, `/app/hybrid_retrieval.py`, and `/app/benchmark_scripts/locomo_bench_v2.py`
- read-only DB probe for `ruvector`/`vector` type visibility, `memories.embedding` type, extension version, non-null embeddings, and `(embedding <=> embedding)` self-distance
- read-only LOCOMO contamination count: `SELECT count(id) FROM memories WHERE domain LIKE 'locomo-%';`
- fresh server log tail, explicitly checking for `Hybrid retrieval failed`, `type "vector" does not exist`, `Decimal is not JSON serializable`, and `TypeError`
- pre-mutation telemetry-off smoke-set per-query hashes and aggregate hash
- pre-mutation telemetry-on production-distribution serialization probe results if the current live build can be queried safely without launching LOCOMO; expected status may include the known Decimal failure, but it must be captured as evidence rather than repaired ad hoc

Do not redact nonsecret model names or vector dimensions. Do redact API keys, tokens, passwords, connection strings, and credentials.

### Step 1 — single rebuild/restart

Run exactly once, only after explicit mutation-window authorization:

```bash
cd /home/zaddy/src/Memibrium
docker compose -f docker-compose.ruvector.yml up -d --build memibrium
```

Wait for health with bounded polling. Do not rebuild a second time in this window. If health fails, capture evidence and stop.

### Step 2 — substrate verification

Post-rebuild evidence must show all of:

- `/health` returns `{"status":"ok","engine":"memibrium"}`.
- `USE_RUVECTOR=true` is visible in the running container.
- Effective embedding deployment remains canonical `text-embedding-3-small`.
- Effective chat/answer model remains canonical `gpt-4.1-mini` where visible/relevant.
- `ruvector` type is present in the DB.
- `vector` type is absent in the DB.
- `memories.embedding` is `USER-DEFINED:ruvector`.
- Self-distance operator probe succeeds.
- Live `/app/hybrid_retrieval.py` contains dynamic `$1::{self.vtype}` or equivalent ruvector-safe dynamic cast.
- Live `/app/hybrid_retrieval.py` does not contain hard-coded semantic-search `$1::vector`.
- LOCOMO contamination count remains `0`.

If substrate drifts, stop with `rollback_substrate_drift`.

### Step 3 — hybrid-active probe

Run the established non-LOCOMO hybrid-active probe:

```bash
curl -fsS -X POST http://localhost:9999/mcp/recall \
  -H 'Content-Type: application/json' \
  -d '{"query":"hybrid active ruvector smoke probe", "top_k":1, "domain":"__hybrid_active_probe_no_rows__"}'
```

Positive evidence requires:

1. HTTP 200 and valid JSON response.
2. Empty list is acceptable because the domain is intentionally nonexistent.
3. Fresh logs after the probe do not contain `Hybrid retrieval failed`, `type "vector" does not exist`, `Decimal is not JSON serializable`, or `TypeError`.

If this fails, stop with `rollback_health_or_probe_failure`.

### Step 4 — telemetry-emission probe

Run the established explicit telemetry probe:

```bash
curl -fsS -X POST http://localhost:9999/mcp/recall \
  -H 'Content-Type: application/json' \
  -d '{"query":"hybrid telemetry ruvector smoke probe", "top_k":3, "domain":"__hybrid_telemetry_probe_no_rows__", "include_telemetry":true}'
```

Pass criteria:

1. HTTP 200 and valid JSON response.
2. Top-level object contains `results` and `telemetry` only because `include_telemetry=true` was requested.
3. A matching plain request without telemetry returns the same result ids/order/count and remains a top-level list.
4. Fresh logs after the probe do not contain `Hybrid retrieval failed`, `type "vector" does not exist`, `Decimal is not JSON serializable`, or `TypeError`.

If this fails, stop with `rollback_health_or_probe_failure` or `rollback_serialization_still_failing`, whichever matches the evidence.

### Step 5 — telemetry-off smoke hash, expanded

Run an expanded fixed telemetry-off smoke set before and after mutation and compare ordered result-key hashes exactly.

Requirements:

- Expand the prior 16-query set to 30–50 fixed queries.
- Prefer queries sampled from the LOCOMO conv-26 query distribution, without launching the LOCOMO benchmark or ingesting LOCOMO rows during the smoke procedure.
- `include_telemetry` must be omitted or false.
- Route: `POST http://localhost:9999/mcp/recall`.
- Recommended `top_k`: `10`, unless the helper preserves the prior setting exactly for comparability.
- Response projection: ordered result keys only, where each key is `id` if present, otherwise `sha256(content)`; do not store full content in smoke-hash artifacts.
- Aggregate hash rule: exact match required pre/post.

If the aggregate hash differs, inspect per-query divergence only to identify the drift, then stop with `rollback_smoke_drift`. Do not proceed to telemetry observation.

Telemetry-off smoke hashes remain a behavior-preservation gate. They are separate from telemetry-on serialization probes.

### Step 6 — telemetry-on production-distribution serialization probe

Run a new telemetry serialization probe after the rebuild/restart and after basic telemetry emission passes.

Requirements:

- 30–50 telemetry-enabled recall queries.
- Prefer queries sampled from the LOCOMO conv-26 query distribution if possible.
- Include varied expected retrieval regimes:
  - low/empty result cases;
  - `n_memories` in the 2–3 range;
  - high-tail cases approaching the `top_k`/15 cap;
  - lexical-heavy queries;
  - semantic-heavy queries;
  - temporal/date-bearing queries;
  - person/entity-heavy queries;
  - adversarial/unanswerable-like query forms where possible.
- `include_telemetry=true` for every request.
- Preserve status, response shape, result count, selected score-summary fields, and any serialization/log errors in the artifact.
- All responses must be valid JSON and HTTP 200.
- All responses must serialize cleanly; no request may fail with HTTP 500.
- Fresh logs must not show:
  - `Decimal is not JSON serializable`
  - `Object of type Decimal is not JSON serializable`
  - `TypeError`
  - `Hybrid retrieval failed`
  - `type "vector" does not exist`

This probe is not a benchmark and must not be scored. It is a production-distribution telemetry serialization safety gate.

If any telemetry-on serialization probe fails, stop with `rollback_serialization_still_failing`.

### Step 7 — result artifact

Write a mutation-window result artifact under:

`docs/eval/results/locomo_hybrid_active_telemetry_serialization_fix_mutation_window_result_2026-05-02.md`

Recommended supporting artifacts:

- `docs/eval/results/locomo_hybrid_active_telemetry_serialization_fix_pre_snapshot_2026-05-02.json`
- `docs/eval/results/locomo_hybrid_active_telemetry_serialization_fix_post_snapshot_2026-05-02.json`
- `docs/eval/results/locomo_hybrid_active_telemetry_serialization_fix_smoke_hashes_2026-05-02.json`
- `docs/eval/results/locomo_hybrid_active_telemetry_serialization_fix_hybrid_probe_2026-05-02.json`
- `docs/eval/results/locomo_hybrid_active_telemetry_serialization_fix_telemetry_probe_2026-05-02.json`
- `docs/eval/results/locomo_hybrid_active_telemetry_serialization_fix_serialization_probe_2026-05-02.json`

The result artifact must report exactly one stop/go output from the list below.

## Stop/go outputs

Exactly one of the following must be recorded for the correction/mutation-window result:

- `go_telemetry_observation_retry` — local tests pass, substrate proof passes, telemetry-off smoke hash matches exactly, hybrid-active probe passes, telemetry-emission probe passes, telemetry-on production-distribution serialization probe passes with no HTTP 500s or serialization/fallback log errors. Ready to request the separate telemetry observation retry window.
- `rollback_serialization_still_failing` — Decimal or other telemetry serialization failure persists in opt-in telemetry responses or fresh logs.
- `rollback_smoke_drift` — telemetry-off pre/post smoke hash differs, meaning the correction changed default retrieval output/order/count or another live behavior changed.
- `rollback_substrate_drift` — `USE_RUVECTOR`, embedding deployment/dimensions, chat model, DB vector type, or live source cast proof drifts during rebuild.
- `rollback_health_or_probe_failure` — health, hybrid-active probe, telemetry-emission probe, or required live-source/DB/log checks fail for reasons other than the above.
- `blocked_pre_mutation_tests_failed` — local syntax/unit tests fail before any live mutation.
- `blocked_authorization_missing` — implementation, rebuild/restart, or observation is requested without the required explicit authorization.

## Telemetry observation retry after a passing correction window

Only if the correction/mutation-window result is `go_telemetry_observation_retry`, the next valid step is Step 5d: request authorization to rerun the telemetry-augmented hybrid-active baseline observation under the original telemetry baseline pre-registration:

`docs/eval/locomo_telemetry_augmented_baseline_preregistration_2026-05-01.md`

Use distinct retry artifact names, for example:

- `docs/eval/results/locomo_conv26_hybrid_active_telemetry_baseline_retry_2026-05-02.json`
- `docs/eval/results/locomo_conv26_hybrid_active_telemetry_traces_retry_2026-05-02.json`
- `docs/eval/results/locomo_conv26_hybrid_active_telemetry_baseline_retry_2026-05-02.log`
- `docs/eval/results/locomo_hybrid_active_telemetry_baseline_retry_199q_comparison_2026-05-02.md`

The original comparability gates remain in force:

- Query expansion fallback must remain `0/199`.
- No hybrid fallback strings may appear during the run.
- Mean `n_memories` must remain within ±0.25 of `4.5327`.
- `n=15` saturation must remain within ±5 questions of `22/199`.
- Dominant exact-`n` buckets must remain within preregistered tolerances.
- Retrieval shape must stay in the same structural regime.

If these gates fail, reject the telemetry baseline retry as non-comparable and do not use it to select Phase C.

## Phase C boundary

Phase C remains gated and blocked.

This pre-registration does not authorize Phase C, does not select a Phase C intervention family, and does not change the standing interpretation: the active hybrid configuration at canonical substrate under-retrieves/under-contexts for LOCOMO conv-26, but existing valid artifacts cannot yet distinguish candidate fetch starvation, threshold/fusion cutoff, output-cap/context-transfer, evidence-present synthesis failure, entity attribution, temporal mismatch, or adversarial/evaluator mismatch.

The blocked partial telemetry run must not be used to infer retrieval-cause family.

A future Phase C intervention preregistration may be written only after:

1. the Decimal-safe telemetry serialization correction is implemented, tested, committed, deployed/probed under authorization, and passed;
2. the telemetry-augmented baseline retry is explicitly authorized, executed, cleaned, analyzed, and committed;
3. the failure-mode audit is rerun or updated against valid telemetry artifacts;
4. the intervention family is selected from valid telemetry evidence rather than the blocked partial run.
