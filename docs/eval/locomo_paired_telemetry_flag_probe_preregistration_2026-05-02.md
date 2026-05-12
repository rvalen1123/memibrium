# LOCOMO paired telemetry flag probe preregistration — 2026-05-02

Repo: `/home/zaddy/src/Memibrium`

Branch at preregistration start: `query-expansion`

HEAD at preregistration start: `29f4209` (`docs: record LOCOMO telemetry noncomparability audit`)

## Status and dependency chain

This document preregisters Step 5g after the artifact-only telemetry noncomparability audit returned:

- Primary verdict: `artifact_insufficient_requires_paired_recall_probe`
- Secondary labels:
  - `artifact_supports_analysis_or_effective_runtime_mismatch`
  - `artifact_does_not_support_static_telemetry_path_perturbation`
  - `artifact_does_not_support_simple_flag_mismatch`
  - `phase_c_still_blocked`

Upstream chain:

1. Phase B complete.
2. Phase B.5 root-cause diagnostic complete.
3. Hybrid-active blocker resolved.
4. Canonical substrate env alignment complete.
5. Canonical hybrid-active baseline complete at `f2466c9`.
6. Read-only failure-mode audit complete.
7. Telemetry baseline preregistration complete at `d35bee4`.
8. Telemetry instrumentation preregistration complete at `ab4bf5d`.
9. Opt-in telemetry instrumentation code/tests complete at `cb56559`.
10. Telemetry instrumentation live mutation window complete at `328da53`.
11. Telemetry baseline attempt blocked by Decimal serialization at `876eb04`.
12. Decimal serialization fix prereg/code/live window complete through `6294164`.
13. Telemetry-enabled 199Q retry complete at `91fede6`, but rejected as noncomparable.
14. Artifact-only noncomparability audit prereg/execution complete through `29f4209`.
15. This Step 5g preregistration is the next valid work unit.

Phase C remains blocked. This preregistration does not authorize Phase C selection or any retrieval, scoring, prompt, evaluator, schema, top-k, threshold/fusion, rerank, append-context, DB, substrate, source, Docker, or runtime mutation.

## Purpose

The purpose of the next probe is narrow: directly test whether requesting opt-in recall telemetry changes the live `/mcp/recall` result set for identical non-LOCOMO queries under the same server state.

The Step 5f artifact-only audit weakened the telemetry-perturbation hypothesis by static source reading, but did not falsify it because no artifact compares the same query with `include_telemetry=false` versus `include_telemetry=true`. This paired probe is the cheapest decisive evidence before any 199-question reproducibility rerun.

## Current evidence framing

The 91fede6 telemetry retry's high-context shape is no longer treated as suspicious by itself. It is mechanically explained by current benchmark-side behavior:

- four expanded queries per question;
- `top_k=10` per recall;
- 40 pre-dedupe candidates per question for 199/199 questions;
- final answer-context cap of 15 hit by 162/199 questions.

The unresolved suspicious data point is the earlier f2466c9 canonical baseline:

- condition metadata reports `query_expansion=True` and `legacy_context_assembly=False`;
- mean `n_memories=4.5327`;
- `n_memories == 15` for only 22/199 questions;
- 167/199 questions had `n_memories <= 3`.

That low-context shape does not match current-source expectations under expanded-query non-legacy assembly. Plausible unresolved families include effective harness/runtime path mismatch, artifact mismatch, baseline non-reproducibility, and substrate-level nondeterminism. Telemetry perturbation remains possible only because it has not yet been directly tested by same-query on/off pairs.

## Hard authorization boundary

This Step 5g document authorizes only:

1. Writing this preregistration file.
2. Committing this preregistration file.
3. Read-only prerequisite checks needed to prove the preregistration was written from the expected clean state.

This Step 5g document does **not** authorize executing the paired live recall probe.

The Step 5h paired probe may be run only after explicit separate authorization. Until that authorization is given, do not issue `/mcp/recall` probe calls for this experiment.

## Explicit non-goals and non-touchpoints

Do not perform any of the following during Step 5g or the future Step 5h probe unless a later preregistration explicitly authorizes it:

- no LOCOMO benchmark rerun;
- no LOCOMO ingest;
- no LOCOMO cleanup/deletion except if a separately authorized future launch contaminates the DB;
- no DB writes or schema migration;
- no Docker rebuild, recreate, restart, image change, or compose change;
- no env/substrate change;
- no source-code change;
- no prompt, judge, evaluator, query-expansion, context-assembly, top-k, threshold/fusion, rerank, append-context, date-normalization, entity-attribution, SQL, vector-index, or output-cap change;
- no Phase C intervention selection or implementation;
- no inference from the rejected 58.29% telemetry retry as a comparable baseline;
- no treatment of the 14.82% f2466c9 baseline as stable canonical until reproducibility is resolved.

## Required Step 5h pre-flight gates

The future paired probe must stop before any recall calls if any gate fails.

Record all pre-flight evidence in the future Step 5h result artifact:

1. Git/repo state:
   - `git status --short` is clean;
   - `git branch --show-current` is `query-expansion`;
   - `git rev-parse --short HEAD` is the Step 5g preregistration commit, unless a later documentation-only commit is explicitly named in the Step 5h authorization;
   - source is identical to the last committed state.
2. Server health:
   - `curl -fsS http://localhost:9999/health` returns `{"status":"ok","engine":"memibrium"}`.
3. LOCOMO hygiene:
   - `SELECT count(id) FROM memories WHERE domain LIKE 'locomo-%';` returns `0`;
   - linked LOCOMO-related counts are all `0` for `temporal_expressions`, `memory_snapshots`, `user_feedback`, `contradictions`, and `memory_edges`.
4. Substrate/runtime checks match the post-serialization-window canonical state:
   - `USE_RUVECTOR=true` visible in the running server container;
   - effective embedding deployment remains `text-embedding-3-small`;
   - effective chat/OpenAI deployment remains `gpt-4.1-mini` where visible/relevant;
   - `memories.embedding` is `USER-DEFINED:ruvector`;
   - `ruvector` type is present;
   - `vector` type is absent;
   - live `/app/hybrid_retrieval.py` contains dynamic `$1::{self.vtype}` or equivalent ruvector-safe dynamic cast;
   - live `/app/hybrid_retrieval.py` does not contain hard-coded semantic-search `$1::vector`;
   - live `/app/server.py` includes the Decimal-safe `_serialize_result()` handling from the committed fix.
5. Fresh-log check before probe:
   - capture the current server log tail;
   - establish a timestamp or line-count boundary for distinguishing pre-existing log messages from errors emitted during the paired probe.

If any pre-flight gate fails, do not run the recall pairs. Write a blocked Step 5h result with label `probe_blocked_health_or_substrate_drift` or a more specific blocked label if appropriate.

## Probe design for Step 5h

Experiment class: small paired live `/mcp/recall` behavior-preservation probe.

Probe set:

- exactly 8 fixed non-LOCOMO queries;
- queries intentionally avoid LOCOMO names, LOCOMO questions, LOCOMO corpus strings, and benchmark-specific wording;
- mix includes single-entity, multi-entity, temporal, broad-topic, and low-specificity/no-hit-style requests;
- query strings are fixed below and must not be tuned after seeing results.

Fixed queries:

1. `project telemetry serialization behavior`
2. `Azure embedding deployment configuration`
3. `Docker ruvector database health checks`
4. `Memibrium query expansion context assembly`
5. `recent memory benchmark cleanup procedure`
6. `When was the telemetry serialization fix recorded?`
7. `How do recall telemetry responses preserve legacy result shape?`
8. `nonexistent control query zyxwvu qptrace sentinel`

Request-pairing rule:

For each query, issue the same deterministic request payload twice against `/mcp/recall`:

- telemetry off: `{"query": <query>, "top_k": 10}`
- telemetry on: `{"query": <query>, "top_k": 10, "include_telemetry": true}`

Do not include a domain filter unless a pre-flight inspection shows the production default would otherwise be undefined for `/mcp/recall`; if a domain filter is added, it must be the same for both calls and must be documented before the first pair is executed.

Do not include LOCOMO domains or LOCOMO-specific filters. Do not use benchmark harness code for this probe; call the server endpoint directly so the only intended request difference is `include_telemetry`.

Execution order:

- Preferred order is interleaved by query: off then on for query 1, off then on for query 2, etc.
- If the implementation script randomizes or reverses order to check order effects, that choice must be declared before execution and applied symmetrically. The default is no randomization.
- Do not retry only one side of a divergent pair. If a transient HTTP/network error occurs, mark the pair blocked/error and stop unless the Step 5h authorization explicitly allows whole-pair retries.

Total planned calls: 16 recall calls.

## Required capture fields

For each request and response, capture:

- pair index;
- query string;
- telemetry condition: `off` or `on`;
- exact request payload;
- HTTP status;
- whether response body is valid JSON;
- response top-level shape: list for telemetry-off legacy shape, object with `results` and `telemetry` for telemetry-on shape;
- result count;
- result IDs in order;
- stable result-content hashes in order as fallback identity if IDs are missing;
- score/similarity fields present in each result, preserving numeric values as returned;
- relevant rank/order fields if present;
- telemetry object presence/absence;
- telemetry server summary fields if present, including `hybrid_path_attempted`, `legacy_fallback_executed`, `embedding_success`, and `response_result_count`;
- response body hash for audit traceability;
- wall-clock timestamp and latency for each call.

After all calls, capture a fresh server-log excerpt bounded by the pre-flight log boundary and explicitly scan for:

- `Hybrid retrieval failed`;
- `type "vector" does not exist`;
- `Decimal is not JSON serializable`;
- `TypeError`;
- HTTP 500/Internal Server Error signatures;
- traceback/error lines emitted during the probe.

## Comparison method

For each query pair, compare the telemetry-off `results` list to the telemetry-on `results` list, not the entire top-level response object.

Primary equality fields:

1. Result count.
2. Result IDs in order.
3. If any result lacks an ID, stable result-content hashes in order.
4. Score/similarity numeric fields by result and rank.

Numeric tolerance:

- Exact equality is required for integer counts, IDs, ordering, and content hashes.
- Score/similarity values should be exact after JSON parsing when represented identically.
- To avoid false positives from JSON float formatting, pre-register an absolute tolerance of `1e-12` for numeric score/similarity fields. Any numeric-only delta above `1e-12` is material.

Telemetry shape expectations:

- Telemetry-off response should preserve the legacy top-level list shape and should not include a telemetry object.
- Telemetry-on response should be a top-level object containing `results` and `telemetry`.
- A telemetry-on shape failure is a probe failure even if result IDs match.

Do not judge answer quality. Do not score benchmark questions. Do not compare against the f2466c9 or 91fede6 aggregate benchmark metrics in Step 5h beyond citing them as motivation.

## Stop/go labels for Step 5h

The Step 5h result artifact must assign exactly one primary label:

### `telemetry_perturbation_ruled_out`

Use if all 8 pairs meet all of the following:

- HTTP status is 200 on both sides;
- both responses are valid JSON;
- telemetry-off top-level shape is the legacy list;
- telemetry-on top-level shape is an object with `results` and `telemetry`;
- result counts are identical;
- result IDs/order are identical, or content-hash order is identical where IDs are missing;
- score/similarity fields are identical within the preregistered `1e-12` absolute tolerance;
- server log excerpt has no fresh relevant errors.

Next track if assigned: preregister a telemetry-off 199Q reproducibility rerun or an effective benchmark-harness/runtime drift audit for the f2466c9 low-context baseline. Do not move to Phase C yet.

### `telemetry_perturbation_confirmed`

Use if any pair shows material divergence in any of:

- result count;
- result IDs/content hashes;
- ordering;
- score/similarity fields beyond tolerance;
- server-side path fields indicating different retrieval path execution.

Next track if assigned: preregister a server-side telemetry path diagnosis/fix window before any telemetry-based baseline is used.

### `inconclusive_partial_divergence`

Use if the only observed differences are limited, intermittent, or plausibly explained by score-only nondeterminism at or below the materiality threshold boundary, or if a small subset requires a broader paired probe to distinguish nondeterminism from telemetry perturbation.

Next track if assigned: preregister an expanded paired probe set and inspect query-type divergence. Do not run 199Q yet unless separately justified.

### `probe_blocked_health_or_substrate_drift`

Use if any required pre-flight gate fails before recall pairs are executed.

Next track if assigned: document the drift and preregister a correction/restoration window if mutation is required.

### `probe_blocked_runtime_error`

Use if any call returns HTTP 500, invalid JSON, serialization failure, traceback, or fresh server error that prevents paired comparison.

Next track if assigned: preregister a focused runtime-error diagnosis/fix window.

## Required Step 5h output artifacts

The future Step 5h run should write and commit these artifacts if authorized:

Primary report:

- `/home/zaddy/src/Memibrium/docs/eval/results/locomo_paired_telemetry_flag_probe_2026-05-02.md`

Structured raw/summary artifacts:

- `/home/zaddy/src/Memibrium/docs/eval/results/locomo_paired_telemetry_flag_probe_pairs_2026-05-02.json`
- `/home/zaddy/src/Memibrium/docs/eval/results/locomo_paired_telemetry_flag_probe_labels_2026-05-02.json`
- `/home/zaddy/src/Memibrium/docs/eval/results/locomo_paired_telemetry_flag_probe_preflight_2026-05-02.json`
- `/home/zaddy/src/Memibrium/docs/eval/results/locomo_paired_telemetry_flag_probe_server_log_2026-05-02.log`

If a helper script is needed, it must be committed only if it is read-only with respect to server state and writes only result artifacts. It must not write to the DB, change env, rebuild/restart containers, or invoke benchmark ingestion.

## Interpretation constraints

The paired probe can directly adjudicate only whether the opt-in telemetry flag changes same-query live recall outputs under the current server state.

It cannot by itself prove:

- that f2466c9's 14.82% baseline is reproducible;
- that 91fede6's 58.29% telemetry retry is a comparable baseline;
- that current high-context behavior is canonical for Phase C;
- that retrieval quality improved or regressed;
- that a Phase C intervention should target fusion, thresholds, top-k, answer-context caps, query expansion, temporal/entity handling, or evaluator behavior.

If telemetry perturbation is ruled out, the next hard gate remains a separately preregistered telemetry-off 199Q reproducibility test of the f2466c9 low-context baseline or an equivalent effective-runtime/harness drift audit.

## Final boundary

This Step 5g preregistration authorizes writing and committing the preregistration only. The paired live recall probe is Step 5h and requires explicit separate authorization.

Until Step 5h completes and is reviewed, Phase C remains blocked.
