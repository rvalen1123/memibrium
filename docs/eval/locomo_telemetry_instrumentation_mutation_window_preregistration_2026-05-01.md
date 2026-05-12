# LOCOMO telemetry instrumentation mutation-window pre-registration — 2026-05-01

Repo: `/home/zaddy/src/Memibrium`  
Branch at preregistration start: `query-expansion`  
Current HEAD at preregistration start: `d35bee4` (`docs: preregister LOCOMO telemetry baseline`)  
Parent observational preregistration: `docs/eval/locomo_telemetry_augmented_baseline_preregistration_2026-05-01.md`

## Scope

This document pre-registers one atomic mutation window for rebuilding/restarting the live Memibrium server with behavior-preserving telemetry hooks. The purpose is to prove that telemetry instrumentation can be deployed without changing retrieval behavior before the later telemetry-augmented LOCOMO baseline observation window.

This is not Phase C. This is not a LOCOMO benchmark. This does not authorize the telemetry-augmented baseline run. This does not authorize retrieval, scoring, prompt, judge, or evaluator changes.

## Locked chain state

Prior committed state:

1. Hybrid-active rebuild/probe and canonical substrate alignment were completed.
2. Canonical no-intervention hybrid-active conv-26 baseline was completed and committed.
3. Read-only failure-mode audit was completed and committed at `6c0e38f`.
4. Telemetry-augmented baseline preregistration was completed and committed at `d35bee4`.

The failure-mode audit stop/go decision was `go_telemetry_preregistration` because existing artifacts identify final-context under-retrieval / under-context but cannot distinguish candidate-fetch starvation, threshold/fusion cutoff, or output-cap/context-transfer loss.

This mutation-window preregistration is the next smaller gate before any telemetry observation run.

## Authorization boundary

Authorized only after this preregistration is committed and a separate execution step is explicitly in scope:

1. Add behavior-preserving telemetry instrumentation code and tests.
2. Capture pre-mutation live-server/source/env/log/smoke-output snapshots.
3. Rebuild/recreate/restart only the `memibrium` server service once from the instrumented host source.
4. Run bounded health/source/env/DB/log checks.
5. Run a fixed read-only retrieval-output smoke set before and after mutation and compare ordered result-key hashes.
6. Run the existing positive-evidence hybrid-active probe.
7. Run a telemetry-emission probe and validate telemetry schema/fields.
8. Write the mutation-window execution result artifact.

Not authorized in this mutation window:

- No LOCOMO benchmark launch.
- No LOCOMO ingest.
- No LOCOMO cleanup/deletion except read-only contamination count checks.
- No DB writes, schema migration, index rebuild, or data mutation.
- No env/substrate changes except explicitly enabling telemetry as an observation flag/request path.
- No container rebuild/restart retry loop beyond the single predeclared rebuild.
- No Phase C intervention code.
- No retrieval logic, top-k, fusion, threshold, prompt, judge, rerank, date-normalization, append-context, entity-attribution, or evaluator-correction change.

If a required check fails, stop and document. Do not repair in place by changing retrieval behavior or retuning telemetry.

## Instrumentation scope to lock

Telemetry hooks may be added only to observe and serialize intermediate state. They must not change retrieval/scoring/output behavior.

### Code paths allowed for telemetry hooks

1. `hybrid_retrieval.py::HybridRetriever.search()`
   - record query, `top_k`, computed `fetch_k`, `use_rrf`, `rerank`, state/domain filters, parsed temporal-window status;
   - record whether temporal search was launched;
   - record whether multi-hop handling ran;
   - record whether chronology sort ran;
   - record counts at stream, fused, expanded, sorted, and final stages.

2. `hybrid_retrieval.py::HybridRetriever._semantic_search()`
   - record requested `top_k`, returned count, candidate ids/refs/ranks, `created_at`, score summary, and short hash/snippet for candidates;
   - record exception class/message if semantic search fails, without masking behavior changes in tests.

3. `hybrid_retrieval.py::HybridRetriever._lexical_search()`
   - record extracted words and tsquery string;
   - record whether the tsvector path returned rows or the ILIKE fallback was used;
   - record requested `top_k`, returned count, candidate ids/refs/ranks, score summary, and short hash/snippet;
   - record tsvector exception class/message when fallback is used.

4. `hybrid_retrieval.py::HybridRetriever._temporal_search()`
   - record temporal window start/end, requested `top_k`, returned count, candidate ids/refs/ranks, score summary, and short hash/snippet.

5. `hybrid_retrieval.py` fusion/finalization path inside `HybridRetriever.search()`
   - record semantic/lexical/temporal counts before fusion;
   - record deduped/fused count before the final cap;
   - record final returned count;
   - record final returned ids/refs/ranks/rrf scores/stream scores;
   - record cutoff candidates just below final `top_k` when available.

6. `server.py::handle_recall()`
   - record whether `hybrid_retriever` was present;
   - record embedding success/failure;
   - record whether legacy fallback executed;
   - record response result count;
   - return telemetry only when explicitly requested, e.g. request field `include_telemetry=true`, or when an explicitly scoped telemetry flag requires it;
   - ordinary `/mcp/recall` responses without telemetry request must remain response-compatible with the baseline path.

7. `benchmark_scripts/locomo_bench_v2.py::answer_question()` and minimal helpers for the later observation window
   - record expanded query strings;
   - record per-expanded-query recall counts and telemetry objects returned from server;
   - record candidate memories before dedupe, base candidate count after dedupe, final answer-context count, final answer-context ids/refs/content hashes/snippets;
   - compute gold evidence-ref coverage during the later LOCOMO observation by comparing static question evidence refs against candidate/fused/final refs.

Benchmark-side hooks may be committed with the instrumentation code, but this mutation window does not authorize running LOCOMO. It only authorizes unit tests and the non-LOCOMO smoke/probe sequence below.

### Explicit non-touchpoints

The instrumentation must not modify:

- `RECALL_TOP_K`, `ANSWER_CONTEXT_TOP_K`, `RERANK_RECALL_TOP_K`, or append-context top-k constants;
- semantic SQL ordering, lexical tsquery/ILIKE matching, temporal SQL, or domain/state filters;
- RRF formula, fusion weights, score normalization, thresholds, or cutoff policy;
- multi-hop expansion behavior, chronology sorting behavior, or returned-memory order;
- prompt text, answer model, judge model, query-expansion model, date normalization, rerank, append/gated append, legacy context assembly, or evaluator behavior;
- DB schema, indexes, rows, memory lifecycle state, or embedding vectors.

Telemetry code must consume copies or immutable projections where practical. It must not exhaust generators, mutate candidate lists before final selection, hold references that later code mutates in a behavior-changing way, or insert blocking calls that change async ordering materially.

## Behavior-preservation tests before live mutation

Before any rebuild/restart, the instrumentation code must pass tests that prove telemetry is opt-in and behavior-preserving.

Minimum tests:

1. Telemetry disabled preserves `HybridRetriever.search()` returned ids/order/count exactly for deterministic fake semantic/lexical/temporal results.
2. Telemetry enabled preserves `HybridRetriever.search()` returned ids/order/count exactly for the same deterministic fake results.
3. Telemetry captures semantic, lexical, temporal, fused, cutoff, and final counts in a stable schema.
4. Telemetry captures lexical tsvector failure/fallback metadata without changing returned lexical results.
5. `server.py::handle_recall()` does not include telemetry unless explicitly requested.
6. `server.py::handle_recall()` returns the same result ids/order/count with `include_telemetry=false` and `include_telemetry=true`; the latter may include an additional telemetry object only.
7. Benchmark-side telemetry helpers record expanded-query/final-context metadata without changing the final selected memory list.

Minimum command set:

```bash
cd /home/zaddy/src/Memibrium
python3 -m py_compile hybrid_retrieval.py server.py benchmark_scripts/locomo_bench_v2.py
python3 -m pytest test_hybrid_retrieval_ruvector.py test_locomo_query_expansion.py -q
```

If these tests fail, stop. Do not rebuild/restart the live server and do not run any probes.

## Fixed smoke set for retrieval-output hash comparability

The mutation window must include a small fixed read-only retrieval-output smoke set before and after the rebuild. This catches behavior drift before the larger 199-question telemetry observation comparability gate.

### Smoke request settings

For every query:

- route: `POST http://localhost:9999/mcp/recall`
- `top_k`: `10`
- `include_telemetry`: omitted or `false` for the hash comparison request
- `domain`: omitted unless a stable, pre-existing, non-LOCOMO smoke domain is explicitly documented before the first hash
- response projection: ordered result keys only, where each key is `id` if present, otherwise `sha256(content)`; do not store full content in the smoke-hash artifact

The smoke hash is:

1. per-query SHA256 of the newline-joined ordered result keys;
2. aggregate SHA256 of `query + "\t" + per_query_hash` for all queries in the exact order listed below.

### Fixed smoke queries

1. `Caroline adoption agencies LGBTQ individuals`
2. `Melanie charity race mental health self care`
3. `LGBTQ counseling workshop therapeutic methods`
4. `pottery workshop July Melanie`
5. `beach with kids once or twice a year`
6. `camping trip meteor shower family`
7. `Grand Canyon accident children road trip`
8. `necklace Sweden grandmother love faith strength`
9. `pride parade school speech support group`
10. `adoption council meeting loving homes children`
11. `running de-stress clear her mind mental health`
12. `Caroline picnic week before July 6 2023`
13. `Nothing is Impossible book Melanie 2022`
14. `The Four Seasons Vivaldi classical music`
15. `safe and inviting place for people to grow`
16. `hybrid active ruvector smoke probe`

### Smoke comparability rule

- Capture the pre-mutation aggregate smoke hash on the uninstrumented live build.
- Capture the post-mutation aggregate smoke hash on the instrumented live build with telemetry disabled/omitted.
- The aggregate hash must match exactly.
- If the aggregate hash differs, inspect per-query hashes only to identify the divergence, then stop with `rollback_instrumentation_drift`.
- Do not proceed to telemetry observation if the smoke hash differs, even if health and telemetry-emission probes pass.

This smoke set is not a benchmark and must not be scored. It is a behavior-preservation canary only.

## Atomic procedure

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
- host source hashes for `server.py`, `hybrid_retrieval.py`, `benchmark_scripts/locomo_bench_v2.py`, and any new telemetry test/helper files
- container source hashes for `/app/server.py` and `/app/hybrid_retrieval.py`
- read-only DB probe for `ruvector`/`vector` type visibility, `memories.embedding` type, extension version, non-null embeddings, and `(embedding <=> embedding)` self-distance
- read-only LOCOMO contamination count: `SELECT count(id) FROM memories WHERE domain LIKE 'locomo-%';`
- fresh server log tail, explicitly recording whether `Hybrid retrieval failed` or `type "vector" does not exist` appears
- pre-mutation fixed smoke-set per-query hashes and aggregate hash

Do not redact nonsecret model names or vector dimensions. Do redact API keys, tokens, passwords, connection strings, and credentials.

### Step 1 — single rebuild/restart

Run exactly once:

```bash
cd /home/zaddy/src/Memibrium
docker compose -f docker-compose.ruvector.yml up -d --build memibrium
```

Wait for health with bounded polling. Do not rebuild a second time in this window. If health fails, capture evidence and stop.

### Step 2 — post-mutation source/substrate proof

Record:

- post image/container IDs and started timestamp
- `/health`
- redacted server env, especially `USE_RUVECTOR`, embedding deployment/model, embedding dimension evidence, chat deployment/model, and telemetry flags
- `docker exec memibrium-server sha256sum /app/server.py /app/hybrid_retrieval.py`
- host `sha256sum server.py hybrid_retrieval.py benchmark_scripts/locomo_bench_v2.py`
- source grep proving `/app/hybrid_retrieval.py` no longer hard-codes semantic-search `$1::vector`
- source grep proving `/app/hybrid_retrieval.py` still contains `$1::{self.vtype}` or equivalent ruvector-safe dynamic cast
- source grep proving the expected telemetry hook identifiers are present in `/app/hybrid_retrieval.py` and `/app/server.py`
- read-only DB probe still showing `ruvector`, no `vector`, `memories.embedding` as `USER-DEFINED:ruvector`, and successful self-distance operator call
- read-only LOCOMO contamination count remains `0`

Substrate must survive the rebuild:

- `USE_RUVECTOR=true`
- server embedding path remains canonical `text-embedding-3-small`, 1536d
- chat/answer/judge/query-expansion stack remains canonical `gpt-4.1-mini` where visible/relevant
- no `text-embedding-3-large-1` or `grok-4-20-non-reasoning-1` drift in live env/log evidence

If substrate drifts, stop with `rollback_substrate_drift`.

### Step 3 — post-mutation smoke-hash comparison

Run the same fixed smoke set with telemetry disabled/omitted and compute the same per-query and aggregate hashes.

Decision:

- If aggregate hash matches the pre-mutation hash, continue.
- If aggregate hash differs, stop with `rollback_instrumentation_drift`; capture per-query divergence and do not run telemetry observation.

### Step 4 — positive-evidence hybrid-active probe

Run the same minimal non-LOCOMO recall probe used to close the hybrid-active blocker:

```bash
curl -fsS -X POST http://localhost:9999/mcp/recall \
  -H 'Content-Type: application/json' \
  -d '{"query":"hybrid active ruvector smoke probe", "top_k":1, "domain":"__hybrid_active_probe_no_rows__"}'
```

Positive evidence requires all of:

1. Server health is OK.
2. `USE_RUVECTOR=true` is visible in the running container.
3. Live `/app/hybrid_retrieval.py` does not contain the semantic-search hard-code `$1::vector`.
4. Live `/app/hybrid_retrieval.py` contains `$1::{self.vtype}` or equivalent safe dynamic cast.
5. DB probe confirms `memories.embedding` is `USER-DEFINED:ruvector` and self-distance succeeds.
6. The recall probe returns a valid response, even if empty because the domain is intentionally nonexistent.
7. Fresh logs after the probe do not contain `Hybrid retrieval failed` or `type "vector" does not exist`.

If any criterion fails, stop with `rollback_hybrid_inactive`.

### Step 5 — telemetry-emission probe

Run one non-LOCOMO recall probe with telemetry explicitly requested:

```bash
curl -fsS -X POST http://localhost:9999/mcp/recall \
  -H 'Content-Type: application/json' \
  -d '{"query":"hybrid telemetry ruvector smoke probe", "top_k":3, "domain":"__hybrid_telemetry_probe_no_rows__", "include_telemetry":true}'
```

Telemetry-emission pass criteria:

1. Response is valid JSON.
2. Response result list remains valid and may be empty due to nonexistent domain.
3. Telemetry object is present only because `include_telemetry=true` was requested.
4. Telemetry records at least:
   - hybrid path attempted;
   - legacy fallback false;
   - embedding success/failure flag;
   - requested `top_k`;
   - semantic candidate count;
   - lexical candidate count;
   - temporal candidate count or explicit `temporal_executed=false`;
   - fused count before cap;
   - final returned count;
   - final ids/refs list, even if empty;
   - error/fallback fields populated as false/null when no error occurred.
5. A second request without `include_telemetry=true` does not include the telemetry object and returns the same result ids/order/count for the same query/top_k/domain.
6. Fresh logs after the probe do not contain `Hybrid retrieval failed`, `type "vector" does not exist`, or telemetry serialization errors.

If this fails, stop with `rollback_telemetry_broken`.

### Step 6 — post-mutation snapshot and result artifact

If Steps 2-5 pass, capture final evidence:

- final `/health`
- final source/env/substrate proof
- final server log tail
- final read-only LOCOMO contamination count `0`
- pre/post smoke hashes and match verdict
- hybrid-active probe verdict
- telemetry-emission probe verdict

Write result artifact:

`docs/eval/results/locomo_hybrid_active_telemetry_instrumentation_result_2026-05-01.md`

Optional structured support artifact:

`docs/eval/results/locomo_hybrid_active_telemetry_instrumentation_smoke_hashes_2026-05-01.json`

Commit result artifacts before proceeding to the telemetry-augmented baseline observation window.

## Rollback / clean-stop path

If the rebuilt server is unhealthy, substrate drifts, smoke hash differs, hybrid-active probe fails, or telemetry emission is broken:

1. Capture health/log/source/env/smoke/probe evidence.
2. Stop further mutation immediately.
3. Restore service availability using the previous image or `docker compose -f docker-compose.ruvector.yml up -d memibrium` if appropriate.
4. Write a blocked result artifact with the relevant stop/go output.
5. Do not run LOCOMO.
6. Do not patch retrieval behavior in the same window.
7. Do not retry rebuild/restart without a new diagnostic note and renewed authorization.

## Stop/go outputs

Exactly one of the following must be recorded in the result artifact:

- `go_telemetry_observation` — substrate proof passes, smoke hash matches, hybrid-active probe passes, telemetry-emission probe passes; ready to request/enter the separate telemetry-augmented baseline observation window.
- `rollback_instrumentation_drift` — pre/post smoke hash differs; instrumentation changed retrieval output or ordering.
- `rollback_substrate_drift` — `USE_RUVECTOR`, embedding model/dimensions, or chat model substrate drifted during rebuild.
- `rollback_hybrid_inactive` — hybrid-active proof regressed or fallback logs reappeared.
- `rollback_telemetry_broken` — telemetry request fails, schema is missing/malformed, default response is polluted, or telemetry serialization/log errors appear.
- `blocked_pre_mutation_tests_failed` — behavior-preservation tests fail before live mutation.
- `blocked_health_or_runtime_unavailable` — server/container/docker health prevents safe execution.

## Phase boundary

A `go_telemetry_observation` result does not authorize Phase C. It only permits the next separately gated observational window: the telemetry-augmented hybrid-active baseline preregistered in `docs/eval/locomo_telemetry_augmented_baseline_preregistration_2026-05-01.md`.

Phase C remains blocked until:

1. this instrumentation mutation-window result is committed;
2. the telemetry-augmented baseline observation is executed, cleaned, analyzed, and committed;
3. the failure-mode audit is rerun or updated against telemetry artifacts;
4. a specific Phase C intervention family is preregistered from telemetry evidence.
