# LOCOMO telemetry-off 199Q reproducibility preregistration — 2026-05-02

Repo: `/home/zaddy/src/Memibrium`

Branch at preregistration start: `query-expansion`

HEAD at preregistration start: `a4102c2` (`docs: record LOCOMO paired telemetry flag probe`)

## Status and dependency chain

This document preregisters the next evidence step after the paired telemetry flag probe.

Upstream chain:

1. Phase B complete.
2. Phase B.5 root-cause diagnostic complete.
3. Hybrid-active blocker resolved.
4. Canonical substrate env alignment complete.
5. Canonical hybrid-active baseline completed earlier at `f2466c9` with low-context retrieval shape.
6. Read-only failure-mode audit complete.
7. Telemetry baseline preregistration complete.
8. Telemetry instrumentation and Decimal serialization fix windows complete.
9. Telemetry-enabled 199Q retry completed at `91fede6`, but was rejected as noncomparable because it produced a high-context retrieval shape.
10. Artifact-only noncomparability audit completed with verdict `artifact_insufficient_requires_paired_recall_probe`.
11. Paired telemetry flag probe completed at `a4102c2` with verdict `telemetry_perturbation_ruled_out`, caveated because all pairs were empty-result/no-hit pairs.
12. This Step 5i preregistration is the next valid work unit.

Phase C remains blocked. This preregistration does not authorize Phase C selection or any retrieval, scoring, prompt, evaluator, schema, top-k, threshold/fusion, rerank, append-context, DB schema, Docker, source, or runtime mutation.

## Purpose

The purpose is to test whether the earlier `f2466c9` 14.82% / low-context canonical hybrid-active baseline is reproducible under the current committed source, current live server, and canonical substrate when recall telemetry is disabled.

This is an observational reproducibility run, not an intervention. It also serves as an effective benchmark-harness/runtime drift audit because the unresolved anomaly is now the earlier low-context baseline, not the later telemetry retry.

The core question:

> With telemetry off and the canonical conv-26 query-expansion condition restored, does a fresh 199-question run reproduce the `f2466c9` low-context regime, the current-source high-context regime, or a third regime?

## Current evidence framing

The `91fede6` telemetry retry is no longer suspicious by itself. Its high-context shape is mechanically explained by current benchmark-side behavior:

- 4 expanded queries per question;
- `top_k=10` per recall;
- 40 pre-dedupe candidates per question for 199/199 questions;
- final answer-context cap of 15 hit by 162/199 questions.

The unresolved suspicious data point is the earlier `f2466c9` canonical baseline. It reports the same high-level condition metadata:

- `query_expansion=True`;
- `legacy_context_assembly=False`;
- query expansion fallback `0/199`.

But it produced a low-context retrieval shape:

- 5-category overall: `14.82%`;
- protocol 4-category overall: `19.41%`;
- mean `n_memories=4.5327`;
- `n_memories == 15`: `22/199`;
- exact `n_memories` distribution: `2:57, 3:110, 11:1, 12:3, 13:3, 14:3, 15:22`.

The rejected telemetry retry produced the high-context regime:

- 5-category overall: `58.29%`;
- protocol 4-category overall: `69.41%`;
- mean `n_memories=14.6231`;
- `n_memories == 15`: `162/199`;
- exact `n_memories` distribution: `11:3, 12:6, 13:17, 14:11, 15:162`.

The paired flag probe found no evidence that `include_telemetry=true` changes result lists under the observed no-hit path. Because all paired queries returned zero results, it did not directly test non-empty result ordering/score preservation. The next evidence requirement is therefore a telemetry-off full-run reproducibility check before any Phase C selection.

## Hard authorization boundary

This Step 5i document authorizes only:

1. Writing this preregistration file.
2. Committing this preregistration file.
3. Read-only prerequisite checks needed to prove the preregistration was written from the expected clean state.

This Step 5i document does **not** authorize executing the 199-question LOCOMO run.

The future Step 5j reproducibility run may be executed only after explicit separate authorization. Until that authorization is given, do not run the LOCOMO benchmark, do not ingest LOCOMO rows, and do not perform LOCOMO cleanup/deletion.

## Explicit non-goals and non-touchpoints

Do not perform any of the following during Step 5i:

- no LOCOMO benchmark rerun;
- no LOCOMO ingest;
- no LOCOMO cleanup/deletion;
- no DB writes or schema migration;
- no Docker rebuild, recreate, restart, image change, or compose change;
- no env/substrate change;
- no source-code change;
- no prompt, judge, evaluator, query-expansion, context-assembly, top-k, threshold/fusion, rerank, append-context, date-normalization, entity-attribution, SQL, vector-index, or output-cap change;
- no Phase C intervention selection or implementation.

During the future Step 5j execution, the only intended DB writes are the standard LOCOMO ingest writes caused by the benchmark and the mandatory post-run cleanup writes. Those writes require the separate Step 5j authorization.

## Experiment class

Observational reproducibility run and effective runtime/harness drift audit.

This run intentionally uses telemetry off to match the earlier `f2466c9` baseline condition more closely than the rejected `91fede6` telemetry retry. It must not use telemetry artifacts as a Phase C baseline unless the run completes, hygiene is restored, and comparability is adjudicated by the decision rules below.

## Locked condition for future Step 5j

Dataset and slice:

- Dataset: LOCOMO `/tmp/locomo/data/locomo10.json`.
- Conversation cap: `--max-convs 26`.
- Expected evaluated questions: `199`.
- Do not use `--max-questions` for the preregistered full run.
- Do not use `--cleaned`.
- Do not skip adversarial questions.

Retrieval/benchmark condition:

- Query expansion: enabled with `--query-expansion` and effective `USE_QUERY_EXPANSION=1`.
- Recall telemetry: disabled; `INCLUDE_RECALL_TELEMETRY` must be unset, empty, or `0`.
- Legacy context assembly: disabled; `USE_LEGACY_CONTEXT_ASSEMBLY` unset/empty and no `--legacy-context-assembly`.
- Context rerank: disabled.
- Append context expansion: disabled.
- Gated append context expansion: disabled.
- No-expansion Arm B: disabled.
- Date normalization: disabled.
- Answer/judge/query-expansion model stack: canonical `gpt-4.1-mini` stack, captured immediately before launch.
- Embedding substrate: canonical Azure `text-embedding-3-small`, 1536d, captured immediately before launch and consistent between live recall server and benchmark env.
- Vector substrate: `memories.embedding` is `USER-DEFINED:ruvector`; `ruvector` type present; `vector` type absent.

Canonical launch shape for Step 5j, after preflight passes:

```bash
cd /home/zaddy/src/Memibrium
set -a
. ./.env
set +a
export AZURE_CHAT_DEPLOYMENT="gpt-4.1-mini"
export AZURE_OPENAI_DEPLOYMENT="gpt-4.1-mini"
export ANSWER_MODEL="gpt-4.1-mini"
export JUDGE_MODEL="gpt-4.1-mini"
export CHAT_MODEL="gpt-4.1-mini"
export AZURE_EMBEDDING_DEPLOYMENT="text-embedding-3-small"
export USE_QUERY_EXPANSION=1
unset INCLUDE_RECALL_TELEMETRY
unset LOCOMO_RETRIEVAL_TELEMETRY
unset USE_CONTEXT_RERANK
unset USE_APPEND_CONTEXT_EXPANSION
unset USE_GATED_APPEND_CONTEXT_EXPANSION
unset USE_LEGACY_CONTEXT_ASSEMBLY
python3 benchmark_scripts/locomo_bench_v2.py --max-convs 26 --query-expansion 2>&1 | tee /tmp/locomo_conv26_telemetry_off_reproducibility_2026-05-02.log
```

Do not add flags to this command during execution unless a new preregistration supersedes this one.

The benchmark writes the default query-expansion raw result path:

`/tmp/locomo_results_query_expansion_raw.json`

Immediately after a completed run, copy that JSON and the run log into result artifacts before cleanup or further runs.

## Required Step 5j preflight gates

The future run must stop before benchmark launch if any gate fails. Record preflight evidence in a structured result artifact.

1. Git/repo state:
   - `git status --short` is clean;
   - `git branch --show-current` is `query-expansion`;
   - `git rev-parse --short HEAD` is the Step 5i preregistration commit, unless a later documentation-only commit is explicitly named in the Step 5j authorization;
   - source is identical to the last committed state.
2. Server health:
   - `curl -fsS http://localhost:9999/health` returns `{"status":"ok","engine":"memibrium"}`.
3. LOCOMO hygiene:
   - `SELECT count(id) FROM memories WHERE domain LIKE 'locomo-%';` returns `0`;
   - linked LOCOMO-related counts are all `0` for `temporal_expressions`, `memory_snapshots`, `user_feedback`, `contradictions`, and `memory_edges`.
4. Canonical substrate/runtime:
   - `USE_RUVECTOR=true` visible in the running server container;
   - live recall server uses or is configured for `text-embedding-3-small` where observable;
   - benchmark launch env resolves `text-embedding-3-small` for embeddings;
   - benchmark launch env resolves `gpt-4.1-mini` for answer, judge, chat, and query expansion;
   - no forbidden launch model or embedding deployment appears in the launch env/log;
   - `memories.embedding` is `USER-DEFINED:ruvector`;
   - `ruvector` type is present;
   - `vector` type is absent;
   - live `/app/hybrid_retrieval.py` contains dynamic `$1::{self.vtype}` or equivalent ruvector-safe dynamic cast;
   - live `/app/hybrid_retrieval.py` does not contain hard-coded semantic-search `$1::vector`;
   - live `/app/server.py` includes the Decimal-safe `_serialize_result()` handling.
5. Host/container source identity:
   - capture SHA256 for host and container `server.py`, `hybrid_retrieval.py`, and `benchmark_scripts/locomo_bench_v2.py`;
   - host and container hashes must match for these files.
6. Benchmark source behavior probes:
   - source contains `INCLUDE_RECALL_TELEMETRY` flag handling;
   - telemetry is disabled in effective env;
   - source contains current non-legacy expanded-query accumulation behavior;
   - source contains diagnostic `--legacy-context-assembly`, but it is not enabled.
7. Result path hygiene:
   - inspect `/tmp/locomo_results_query_expansion_raw.json` and `/tmp/locomo_conv26_telemetry_off_reproducibility_2026-05-02.log` before launch;
   - if existing files are present, record their size/hash/mtime and either archive or remove them before launch so post-run copies cannot accidentally preserve stale artifacts;
   - do not use `--start-conv`.
8. Fresh-log boundary:
   - capture prelaunch server log tail;
   - establish timestamp or line-count boundary for distinguishing pre-existing messages from run-emitted errors.

If any gate fails, do not run the benchmark. Write a blocked Step 5j result with label `repro_blocked_health_or_substrate_drift` or a more specific blocked label.

## Required capture fields for Step 5j

Prelaunch artifact:

- date/time;
- branch, HEAD, status;
- health response;
- Docker container status for Memibrium services;
- redacted server env for relevant nonsecret keys only;
- benchmark effective env for relevant nonsecret keys only;
- DB type and LOCOMO hygiene probes;
- host/container source hashes;
- benchmark source behavior probes;
- result-path hygiene record;
- fresh-log boundary.

Run artifacts:

- raw benchmark JSON copied from `/tmp/locomo_results_query_expansion_raw.json`;
- run log copied from `/tmp/locomo_conv26_telemetry_off_reproducibility_2026-05-02.log`;
- post-run server log excerpt;
- structured comparison JSON/markdown;
- cleanup proof artifact.

Comparison artifact fields:

- total evaluated questions;
- full 5-category overall;
- protocol 4-category overall using the established protocol-4 category rule;
- category scores/counts;
- query expansion fallback count/rate;
- average query latency;
- exact `n_memories` distribution;
- mean `n_memories`;
- `n_memories == 15` count/rate;
- count of `n_memories <= 3`;
- count of `n_memories >= 11`;
- comparison against `f2466c9` low-context reference;
- comparison against `91fede6` high-context reference;
- fresh log checks for `Hybrid retrieval failed`, `type "vector" does not exist`, `Decimal is not JSON serializable`, `TypeError`, HTTP 500/Internal Server Error, and traceback/error lines.

## Decision rules and labels

Primary comparability axes are retrieval shape first, score second. Do not choose Phase C from score movement alone.

### `telemetry_off_low_context_baseline_reproduced`

Use this label if all are true:

- run completed all `199` questions;
- query expansion fallback is `0/199` or no more than `2/199` with explicit fallback details;
- mean `n_memories` is within `±0.50` of `4.5327`;
- `n_memories == 15` is within `±10` of `22/199`;
- at least `150/199` questions have `n_memories <= 3`;
- 5-category overall is within `±5` percentage points of `14.82%`, or the score deviation is explained by answer/judge nondeterminism while retrieval-shape gates match;
- no hybrid fallback, vector-type, serialization, HTTP 500, or traceback errors occur.

Interpretation: the f2466c9 low-context baseline is reproducible enough to treat as a real current-condition regime. Phase C still remains blocked until deciding whether the low-context regime or high-context regime is the intended canonical baseline and until the telemetry-on high-context discrepancy is separately explained.

### `telemetry_off_high_context_current_regime_reproduced`

Use this label if all are true:

- run completed all `199` questions;
- query expansion fallback is `0/199` or no more than `2/199` with explicit fallback details;
- mean `n_memories >= 13.5`;
- `n_memories == 15 >= 140/199`;
- all or nearly all questions have `n_memories >= 11`;
- retrieval-shape gates are close to the `91fede6` high-context reference;
- no hybrid fallback, vector-type, serialization, HTTP 500, or traceback errors occur.

Interpretation: the f2466c9 14.82% low-context artifact is likely nonreproducible or produced by an effective harness/runtime/artifact mismatch. Reframe the baseline chain around high-context current-code behavior before Phase C.

### `telemetry_off_third_regime_observed`

Use this label if the run completes without blocking errors but retrieval shape matches neither the low-context nor high-context regime.

Interpretation: substrate/provider/harness nondeterminism or an unmodeled runtime variable is material. Do not choose Phase C. Preregister a variance/repeated-run or runtime-drift audit before any intervention.

### `repro_blocked_health_or_substrate_drift`

Use this label if any preflight substrate, health, git, source, result-path, or hygiene gate fails before launch.

### `repro_blocked_runtime_error`

Use this label if the run starts but is blocked by HTTP 500, invalid JSON, serialization failure, vector-type error, benchmark crash, missing output artifact, or log evidence of hybrid fallback/runtime error.

### `repro_rejected_hygiene_failure`

Use this label if the run completes but post-run cleanup cannot restore LOCOMO contamination count and linked LOCOMO-related counts to `0`.

## Post-run cleanup requirement for Step 5j

Any authorized Step 5j LOCOMO launch must be followed by cleanup before final reporting:

1. Copy `/tmp` result/log artifacts into `docs/eval/results/` with unique telemetry-off reproducibility names.
2. Create comparison markdown and structured labels JSON.
3. Delete `locomo-%` memories and linked rows using the established cleanup procedure.
4. Verify:
   - `SELECT count(id) FROM memories WHERE domain LIKE 'locomo-%';` returns `0`;
   - linked LOCOMO-related counts are all `0`.
5. Capture health after cleanup.
6. Commit all result and cleanup artifacts.

If cleanup fails, stop and report `repro_rejected_hygiene_failure`. Do not continue to Phase C.

## Phase C boundary after Step 5j

Phase C remains blocked after this preregistration. It may remain blocked after the future run depending on the label:

- Low-context reproduction: decide canonical regime and explain telemetry/high-context discrepancy before Phase C.
- High-context reproduction: reframe the comparable baseline around current high-context behavior, then preregister Phase C only from that baseline.
- Third regime: estimate variance or audit runtime drift before Phase C.
- Blocked/rejected: fix the blocking condition under a separate preregistration.

Do not treat either `14.82%` or `58.29%` as a stable canonical reference until the future Step 5j result is committed and interpreted under these decision rules.

## Planned output paths for Step 5j

Preregistration:

- `docs/eval/locomo_telemetry_off_199q_reproducibility_preregistration_2026-05-02.md`

Future execution artifacts:

- `docs/eval/results/locomo_telemetry_off_199q_reproducibility_prelaunch_2026-05-02.json`
- `docs/eval/results/locomo_conv26_telemetry_off_reproducibility_2026-05-02.json`
- `docs/eval/results/locomo_conv26_telemetry_off_reproducibility_2026-05-02.log`
- `docs/eval/results/locomo_telemetry_off_199q_reproducibility_comparison_2026-05-02.md`
- `docs/eval/results/locomo_telemetry_off_199q_reproducibility_labels_2026-05-02.json`
- `docs/eval/results/locomo_telemetry_off_199q_reproducibility_cleanup_2026-05-02.json`
