# LOCOMO Step 5p full-repro preregistration — 2026-05-03

Repo: `/home/zaddy/src/Memibrium`

Branch at preregistration start: `query-expansion`

HEAD at preregistration start: `665d86457d820e62e921cd6436abd7cac5b42d64` (`docs: execute LOCOMO step 5o trace-lite`)

Preregistration timestamp inspected: `2026-05-03T04:08:50Z`

## Status entering Step 5p

Step 5o bounded checkpoint / trace-lite execution completed at `665d864` with primary label:

`checkpoint_shows_no_static_boundary_effect`

Secondary labels:

- `supports_post_cb56559_high_context_path`
- `supports_effective_harness_mismatch`
- `requires_full_repro_prereg`
- `no_go_phase_c_still_blocked`

Step 5o ruled out static commit-level source drift between `f2466c9` and current as the cause of the original `14.82%` low-context artifact. When the `f2466c9` source was executed today against the current substrate, it produced high/near-high context retrieval on the fixed rows. Current source also produced high/near-high context retrieval on those same rows.

The complication is that Step 5o did not reproduce the Step 5j_v2_exec bimodality: the Step 5j_v2_exec full 199Q run had adversarial rows at low context while non-adversarial rows were high-context-ish, but Step 5o fixed adversarial rows reached final context `15`.

Known regimes after Step 5o:

- Regime A / `f2466c9` low-context artifact: 5-cat `14.82%`, protocol 4-cat `19.41%`, mean `n_memories=4.5327`, `n=15` `22/199`, distribution `2:57, 3:110, 11:1, 12:3, 13:3, 14:3, 15:22`. Status: noncanonical / not tied to committed `f2466c9` static source under current substrate.
- Regime B / `91fede6` telemetry retry high-context, rejected as noncomparable: 5-cat `58.29%`, protocol 4-cat `69.41%`, mean `n_memories=14.6231`, `n=15` `162/199`, distribution `11:3, 12:6, 13:17, 14:11, 15:162`. Status: noncomparable; proves high-context mechanism but not baseline.
- Regime C / `662514a` corrected telemetry-off third regime: 5-cat `55.28%`, protocol 4-cat `70.07%`, mean `n_memories=11.9296`, `n=15` `120/199`, distribution `4:51, 12:6, 13:10, 14:12, 15:120`, adversarial mean `n=4.0`, non-adversarial high-context-ish mean approximately `14.06–14.77`, fallback `0/199`. Status: candidate reproducibility target for Step 5p only; not a Phase C baseline.

Phase C remains blocked.

## Purpose

Step 5p preregisters a full 199-question telemetry-off rerun under the corrected conv-26 slice protocol on current code.

The question is:

> Under the current code/substrate, telemetry disabled, query expansion enabled, and the corrected `conv-26` 199Q slice, does the Step 5j_v2_exec Regime C result reproduce at the score and retrieval-shape level?

Primary target: reproduce or reject Step 5j_v2_exec run-level stability.

Primary mechanism target: retrieval shape and category split, especially whether the adversarial low-context / non-adversarial high-context-ish bimodality reproduces.

Scores are decision inputs, but score-only reproduction is not sufficient to declare a stable baseline if retrieval shape drifts.

## Hard authorization boundary

This Step 5p document authorizes only:

1. Writing this preregistration file.
2. Committing this preregistration file.
3. Read-only prerequisite inspection used to write the preregistration from a clean state.

This Step 5p document does **not** authorize executing the full 199Q run.

A future Step 5p_exec full-repro run may execute only after explicit separate authorization. Until that authorization is given:

- do not run `benchmark_scripts/locomo_bench_v2.py`;
- do not ingest LOCOMO rows;
- do not perform LOCOMO cleanup/deletion;
- do not rebuild, recreate, restart, or mutate Docker containers;
- do not mutate DB schema, DB contents, source code, environment, runtime, vector/index state, prompts, evaluator, retrieval logic, top-k/cap behavior, query-expansion logic, telemetry behavior, or Phase C code;
- do not select or implement a Phase C intervention.

During a later explicitly authorized Step 5p_exec run, the only intended DB writes are the standard LOCOMO ingest writes caused by the benchmark and the mandatory post-run cleanup writes.

## Preregistration-time read-only observations

These observations were captured while writing this preregistration. They are **not** a substitute for the required prelaunch snapshot during a later Step 5p_exec run; execution must recapture them immediately before launch.

Health:

```json
{"status":"ok","engine":"memibrium"}
```

Current source hashes at preregistration inspection:

```text
benchmark_scripts/locomo_bench_v2.py  32dd68d0a0bad7322e8eea67bea90628d0cf42415769802f9e48a4528f3454ff
hybrid_retrieval.py                   2ba660f547432c7fa5ae88955ee97024f5c39848790060358c82dcf0a8259c07
server.py                             150b161bd9bef5c021fd7f1b32472623b3cc03baac6d13ff42edd501ae3f6f1a
```

Input slice facts at preregistration inspection:

```json
{
  "path": "/tmp/locomo/data/locomo10.json",
  "sha256": "79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4",
  "top_level_type": "list",
  "conversation_count": 10,
  "sample_order": ["conv-26", "conv-30", "conv-41", "conv-42", "conv-43", "conv-44", "conv-47", "conv-48", "conv-49", "conv-50"],
  "index0_sample_id": "conv-26",
  "index0_speaker_a": "Caroline",
  "index0_speaker_b": "Melanie",
  "index0_qa_count": 199,
  "index0_category_counts_raw": {"2": 37, "3": 13, "1": 32, "4": 70, "5": 47},
  "total_qa_count": 1986
}
```

Current LOCOMO hygiene at preregistration inspection:

```text
memories|0
temporal_expressions|0
memory_snapshots|0
user_feedback|0
contradictions|0
memory_edges|0
```

Current running server identity at preregistration inspection:

```text
container: memibrium-server
container_id: 37b4e905299874b18421ea577211083f42956fe4659af37b198eb53f1d81d02a
image_id: sha256:76fed12e0da1324ab1e26e927fa3fa1a3aa6e7b340d5f7ab6e481da3e0afe9b6
pid: 822563
started_at: 2026-05-02T12:30:18.612989007Z
status: running / healthy
```

Current DB extension and table-size observations at preregistration inspection:

```text
extensions: plpgsql|1.0, ruvector|0.3.0
contradictions|0|32768
entities|3141|1818624
memories|22|143425536
memory_edges|1|237568
memory_snapshots|0|16384
temporal_expressions|0|417792
user_feedback|0|24576
```

## Locked Step 5p_exec condition

Dataset and slice:

- Dataset: `/tmp/locomo/data/locomo10.json`.
- Required file SHA256 before launch: `79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4`.
- Required top-level type: `list`.
- Required index 0 `sample_id`: `conv-26`.
- Required index 0 speakers: `Caroline` / `Melanie`.
- Required index 0 QA count: `199`.
- Required selector: `--max-convs 1` only after the prelaunch proof reconfirms the index-0 facts.
- Do not use `--max-convs 26`.
- Do not use `--max-questions`.
- Do not use `--start-conv`.
- Do not use `--cleaned`.
- Do not skip categories.

Retrieval / benchmark condition:

- Telemetry disabled/absent: `INCLUDE_RECALL_TELEMETRY` and `LOCOMO_RETRIEVAL_TELEMETRY` unset, empty, or false.
- Query expansion enabled: `USE_QUERY_EXPANSION=1` and CLI `--query-expansion`.
- Answer model: `gpt-4.1-mini`.
- Judge model: `gpt-4.1-mini`.
- Chat/query-expansion model: `gpt-4.1-mini` via `CHAT_MODEL`, `AZURE_OPENAI_DEPLOYMENT`, and `AZURE_CHAT_DEPLOYMENT` where applicable.
- Embedding deployment: `text-embedding-3-small` via `AZURE_EMBEDDING_DEPLOYMENT`.
- No context rerank: `USE_CONTEXT_RERANK` unset/false.
- No append context expansion: `USE_APPEND_CONTEXT_EXPANSION` unset/false.
- No gated append context expansion: `USE_GATED_APPEND_CONTEXT_EXPANSION` unset/false.
- No legacy context assembly: `USE_LEGACY_CONTEXT_ASSEMBLY` unset/false and no `--legacy-context-assembly`.
- No date normalization.
- No no-expansion Arm B.
- Vector substrate must remain ruvector-backed and compatible with `text-embedding-3-small` / 1536d embeddings.

Canonical future launch shape after explicit Step 5p_exec authorization and after all preflight gates pass:

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
python3 benchmark_scripts/locomo_bench_v2.py --max-convs 1 --query-expansion \
  2>&1 | tee /tmp/locomo_step5p_full_repro_2026-05-03.log
```

The benchmark is expected to write:

`/tmp/locomo_results_query_expansion_raw.json`

Before launch, inspect and archive/remove any existing `/tmp/locomo_results_query_expansion_raw.json` and `/tmp/locomo_step5p_full_repro_2026-05-03.log` so stale artifacts cannot be mistaken for Step 5p_exec output.

## Required prelaunch gates for future Step 5p_exec

A future Step 5p_exec runner must stop before benchmark launch if any gate fails.

### 1. Git and source identity

- `git status --short` is clean, allowing only preregistered Step 5p_exec output artifacts being actively written.
- Branch is `query-expansion` unless the execution authorization explicitly names a detached/headless artifact workflow.
- HEAD is this Step 5p preregistration commit or a later documentation-only commit explicitly named in the execution authorization.
- Host source hashes for `benchmark_scripts/locomo_bench_v2.py`, `hybrid_retrieval.py`, and `server.py` are captured.
- Container source hashes for the same files are captured when Docker server is used.
- Host/container source hashes match for live code paths.
- Benchmark source still proves `--max-convs` is a slice cap (`data = data[:max_convs]`), not a sample-id selector.
- Benchmark source still includes query-expansion accumulation, telemetry-disabled legacy shape preservation, result-condition metadata, `n_memories`, and fallback count fields.

### 2. Health and hygiene

- `curl -fsS http://localhost:9999/health` returns exactly `{"status":"ok","engine":"memibrium"}` or an equivalent parseable JSON with those values.
- `memories` with `domain LIKE 'locomo-%'` is zero.
- Linked LOCOMO-related counts are zero for `temporal_expressions`, `memory_snapshots`, `user_feedback`, `contradictions`, and `memory_edges`.
- If hygiene is nonzero, do not clean as part of Step 5p preregistration. Stop and require separate authorization or label `full_repro_blocked_health_or_hygiene` during execution.

### 3. Corrected slice proof

Immediately before launch, parse `/tmp/locomo/data/locomo10.json` and record:

- file existence;
- file SHA256;
- top-level type;
- conversation count;
- ordered `sample_id` list;
- index 0 `sample_id`;
- index 0 speaker names;
- index 0 QA count;
- index 0 category counts;
- total QA count across the full input file.

Required pass conditions:

- file exists;
- SHA256 equals `79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4`;
- top-level type is `list`;
- index 0 `sample_id` is exactly `conv-26`;
- index 0 speakers are `Caroline` and `Melanie`;
- index 0 QA count is exactly `199`;
- ordered sample list begins with `conv-26`;
- `--max-convs 1` over this exact file can only select index 0.

If any pass condition fails, do not launch and label `full_repro_blocked_slice_identity_mismatch`.

### 4. Canonical substrate and env

Capture the effective launch env and live server env with secrets redacted as `[REDACTED]`.

Required nonsecret values / assertions:

- `USE_QUERY_EXPANSION=1` for launch.
- `INCLUDE_RECALL_TELEMETRY` absent/false.
- `LOCOMO_RETRIEVAL_TELEMETRY` absent/false.
- `ANSWER_MODEL=gpt-4.1-mini`.
- `JUDGE_MODEL=gpt-4.1-mini`.
- `CHAT_MODEL=gpt-4.1-mini` for the benchmark process.
- `AZURE_OPENAI_DEPLOYMENT=gpt-4.1-mini`.
- `AZURE_CHAT_DEPLOYMENT=gpt-4.1-mini` where applicable.
- `AZURE_EMBEDDING_DEPLOYMENT=text-embedding-3-small`.
- `USE_CONTEXT_RERANK`, `USE_APPEND_CONTEXT_EXPANSION`, `USE_GATED_APPEND_CONTEXT_EXPANSION`, and `USE_LEGACY_CONTEXT_ASSEMBLY` absent/false.
- No date-normalization flag.
- No no-expansion Arm B flag.
- `ENABLE_BACKGROUND_SCORING`, `ENABLE_CONTRADICTION_DETECTION`, and `ENABLE_HIERARCHY_PROCESSING` captured from the live server/container env.
- DB env uses `DB_PASSWORD` and secrets are redacted; for local temporary servers against the Dockerized ruvector DB, the live credential in this setup is `DB_PASSWORD=memory`, but artifacts must record it as `[REDACTED]`.

If source/env cannot prove the locked condition, label `full_repro_blocked_source_or_env_mismatch`.

### 5. Stateful-substrate snapshot addendum

This addendum implements the Step 5o methodology lesson: inference-stack identity must include stateful substrate dimensions. A future Step 5p_exec must capture the following before launch and again after completion/abort where applicable.

Container/runtime identity:

- server/container name, container ID, image ID, image tag/config image;
- container state and health;
- server PID and container `StartedAt` timestamp;
- relevant process list for benchmark/server processes;
- bounded server logs around the execution window, with a prelaunch log boundary.

Git/source identity:

- branch, HEAD, `git status --short`;
- host source hashes for `server.py`, `hybrid_retrieval.py`, and `benchmark_scripts/locomo_bench_v2.py`;
- container source hashes for those files if live Docker server is used;
- source-behavior probes for query expansion, telemetry flags, result metadata, and `--max-convs` semantics.

Redacted environment affecting chat/embedding/retrieval/telemetry/background tasks:

- `ANSWER_MODEL`, `JUDGE_MODEL`, `CHAT_MODEL`;
- `OPENAI_BASE_URL`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_DEPLOYMENT`, `AZURE_CHAT_ENDPOINT`, `AZURE_CHAT_DEPLOYMENT`;
- `AZURE_EMBEDDING_ENDPOINT`, `AZURE_EMBEDDING_DEPLOYMENT`, `EMBEDDING_BASE_URL`, `EMBEDDING_MODEL`;
- `USE_QUERY_EXPANSION`, `INCLUDE_RECALL_TELEMETRY`, `LOCOMO_RETRIEVAL_TELEMETRY`;
- `USE_CONTEXT_RERANK`, `USE_APPEND_CONTEXT_EXPANSION`, `USE_GATED_APPEND_CONTEXT_EXPANSION`, `USE_LEGACY_CONTEXT_ASSEMBLY`;
- `USE_RUVECTOR`, `RUVECTOR_GNN`;
- `ENABLE_BACKGROUND_SCORING`, `ENABLE_CONTRADICTION_DETECTION`, `ENABLE_HIERARCHY_PROCESSING`;
- DB connection keys with passwords/API keys redacted.

Database hygiene and size state:

- LOCOMO contamination count and linked LOCOMO-related counts;
- row counts and approximate relation sizes for `memories`, `entities`, `memory_edges`, `temporal_expressions`, `memory_snapshots`, `user_feedback`, and `contradictions`;
- any additional active memory tables used by the running server.

Vector/index metadata if queryable without mutation:

- vector/ruvector extension versions;
- `memories.embedding` type and dimension metadata where available;
- index names/definitions for memory/vector indexes;
- ruvector/HNSW/GNN metadata where exposed by read-only catalog queries.

Postgres/planner state if safely queryable:

- Postgres version;
- `pg_extension` versions;
- `pg_stat_user_tables` row estimates, last vacuum/analyze/autovacuum/autoanalyze timestamps;
- relevant planner/settings output such as `enable_seqscan`, `work_mem`, `random_page_cost`, `effective_cache_size`, and any ruvector-specific settings if exposed;
- do not run `ANALYZE`, `VACUUM`, index rebuilds, or any planner/index mutation as part of this snapshot.

Embedding/cache state if discoverable without mutation:

- embedding deployment/model identity;
- embedding dimension proof if available from schema or non-mutating metadata;
- any local/server embedding cache counts, paths, timestamps, or sizes if discoverable read-only;
- explicitly record `not_discoverable_read_only` where no safe read-only cache introspection exists.

If this required snapshot cannot be captured sufficiently to compare state before and after launch, label `full_repro_blocked_runtime_state_snapshot_failure` and do not interpret the full run as canonical even if a result JSON exists.

## Launch-time startup guard for future Step 5p_exec

Run the benchmark under a controller that reads early stdout/stderr and enforces the slice guard before the full run proceeds.

Required startup evidence:

```text
Conversations to process: 1
Total questions: 199 (199 evaluated, skipping cats set())
[1/1] Conv conv-26: Caroline & Melanie
```

Abort immediately if:

- conversations to process is not `1`;
- evaluated question count is not `199`;
- skipped categories are non-empty;
- the first conversation line is not `[1/1] Conv conv-26: Caroline & Melanie`;
- required startup lines do not appear within the preregistered guard window.

If aborted by the startup guard, preserve the partial log, perform mandatory authorized cleanup if any LOCOMO rows were ingested, and label the run with the appropriate blocked label.

## Result validity gate for future Step 5p_exec

A completed run is valid only if all of the following hold:

- result JSON exists at `/tmp/locomo_results_query_expansion_raw.json` after completion;
- JSON parses;
- `details` has exactly `199` rows;
- every row is `conv-26` or equivalent sample-id field exactly matching `conv-26`;
- no row is from another conversation;
- telemetry is disabled/absent in metadata and detail rows;
- condition metadata has `query_expansion=True`;
- condition metadata has `legacy_context_assembly=False`;
- condition metadata has context-rerank, append, gated append, date normalization, and no-expansion Arm B off;
- query-expansion fallback count/rate are present;
- `n_memories` is present for every row;
- result artifact includes category labels/counts sufficient to stratify adversarial vs non-adversarial rows;
- cleanup after the run restores LOCOMO hygiene and linked counts to zero;
- no fresh runtime log evidence of `Hybrid retrieval failed`, `type "vector" does not exist`, `Decimal is not JSON serializable`, `TypeError`, HTTP 500/Internal Server Error, benchmark traceback, or unhandled exception.

If result validity fails because of slice/source/env/snapshot/runtime/cleanup, do not compare score or retrieval shape as a valid reproducibility result.

## Comparison targets against Step 5j_v2_exec

Primary Step 5j_v2_exec target:

- 5-cat overall: `55.28%`; score reproduction tolerance `±2pp`, acceptable range `53.28%–57.28%`.
- Protocol 4-cat overall: `70.07%`; score reproduction tolerance `±2pp`, acceptable range `68.07%–72.07%`.
- Mean `n_memories`: `11.9296`.
- Exact `n_memories` distribution target: `4:51, 12:6, 13:10, 14:12, 15:120`.
- `n_memories == 15`: `120/199`.
- Adversarial mean `n_memories`: `4.0` over `47` adversarial rows.
- Non-adversarial high-context-ish mean `n_memories`: approximately `14.06–14.77`.
- Query-expansion fallback: `0/199`.

Mechanism diagnostics to compute:

- exact `n_memories` distribution;
- mean `n_memories` overall;
- `n=15` count/rate;
- `n=4` count/rate;
- adversarial category count, score, mean `n_memories`, distribution, and `n=4` count;
- non-adversarial aggregate count, score, mean `n_memories`, distribution, and `n=15` count;
- per-category score and retrieval-shape summaries for temporal, single-hop, multi-hop, unanswerable, and adversarial;
- query-expansion fallback count/rate and fallback row identities if any;
- latency summaries, marked diagnostic only;
- fresh log error flags.

## Decision labels for future Step 5p_exec

A future Step 5p_exec report must include one bimodality label, one score label, and one overall/blocked status label as applicable. Include `no_go_phase_c_still_blocked` in all non-intervention outcomes.

### Bimodality labels

Use `5j_v2_exec_bimodality_reproduces` if all of the following are true:

- result validity gate passes;
- adversarial row count is `47`;
- adversarial mean `n_memories` is within `±0.25` of `4.0`;
- at least `45/47` adversarial rows have `n_memories <= 4`;
- non-adversarial mean `n_memories` is in the preregistered high-context-ish range `14.06–14.77`;
- overall `n=15` count is within `±10` rows of `120/199`;
- query-expansion fallback is `0/199`, or any nonzero fallback is explicitly isolated and does not explain the bimodality.

Use `5j_v2_exec_bimodality_does_not_reproduce` if the result validity gate passes but any required bimodality condition fails.

### Score labels

Use `score_reproduces_within_tolerance` if both are true:

- 5-cat overall is within `53.28%–57.28%`;
- protocol 4-cat overall is within `68.07%–72.07%`.

Use `score_drifts_significantly` if the result validity gate passes and either score is outside its tolerance range.

If a blocked label prevents score comparison, do not emit either score label as a completed-run result; report the blocked label instead.

### Overall / blocked labels

Use `full_repro_prereg_complete` for this documentation-only Step 5p preregistration artifact.

For future Step 5p_exec, use one or more of:

- `full_repro_execution_complete_valid` — all preflight, startup, result-validity, snapshot, and cleanup gates pass.
- `full_repro_blocked_health_or_hygiene` — health fails or LOCOMO hygiene is nonzero before launch.
- `full_repro_blocked_slice_identity_mismatch` — prelaunch, startup, or result JSON slice identity differs from exactly `conv-26` / 199 rows.
- `full_repro_blocked_source_or_env_mismatch` — source hashes, host/container identity, or effective env do not match the locked condition.
- `full_repro_blocked_runtime_state_snapshot_failure` — required stateful substrate snapshot cannot be captured before launch or after run/abort.
- `full_repro_blocked_cleanup_failure` — post-run/abort cleanup does not restore LOCOMO and linked counts to zero.
- `full_repro_blocked_runtime_error` — valid launch begins but benchmark/runtime fails by JSON, HTTP, vector, serialization, traceback, or missing-artifact error.
- `no_go_phase_c_still_blocked` — always include unless a later, separately authorized Phase C decision explicitly supersedes this measurement track.

## Interpretation plan

If `5j_v2_exec_bimodality_reproduces` and `score_reproduces_within_tolerance`:

- Current state has stable run-to-run behavior at the regime level for Regime C.
- The mystery is bounded primarily to original `f2466c9` conditions / lost substrate state.
- Regime C may become the target for a later baseline decision preregistration, but Phase C is still not automatically authorized.

If `5j_v2_exec_bimodality_reproduces` and `score_drifts_significantly`:

- Retrieval substrate may be stable while answer/judge layer varies.
- Do not call the baseline fully stable.
- Require answer/judge stability audit before any Phase C baseline promotion.

If `5j_v2_exec_bimodality_does_not_reproduce` and scores reproduce within tolerance:

- Do not call baseline stable; retrieval shape controls comparability.
- Treat score reproduction as potentially masking retrieval-substrate variance.
- Require substrate nondeterminism audit before Phase C.

If `5j_v2_exec_bimodality_does_not_reproduce` and scores drift significantly:

- Step 5j_v2_exec itself did not reproduce.
- No single-run baseline is canonical.
- Require substrate nondeterminism audit before Phase C.

If a blocked label occurs:

- Do not interpret score/retrieval shape.
- Fix or preregister the blocking condition separately.
- Phase C remains blocked.

## Post-run cleanup requirement for future Step 5p_exec

Any authorized Step 5p_exec launch must be followed by cleanup before final reporting, even if startup guard or runtime errors abort the run after LOCOMO ingestion starts.

Required sequence:

1. Copy `/tmp/locomo_results_query_expansion_raw.json` if present and `/tmp/locomo_step5p_full_repro_2026-05-03.log` into `docs/eval/results/` with unique Step 5p run IDs.
2. Write prelaunch snapshot, postrun snapshot, validation/comparison JSON, markdown report, and cleanup proof artifacts.
3. Delete `locomo-%` memories and linked rows using the established cleanup procedure.
4. Verify:
   - `SELECT count(id) FROM memories WHERE domain LIKE 'locomo-%';` returns `0`;
   - linked LOCOMO-related counts for `temporal_expressions`, `memory_snapshots`, `user_feedback`, `contradictions`, and `memory_edges` are all `0`.
5. Capture health after cleanup.
6. Verify no orphan LOCOMO benchmark or temporary server processes.
7. Commit all Step 5p_exec result and cleanup artifacts.

If cleanup fails, label `full_repro_blocked_cleanup_failure`, stop, and do not proceed to Phase C.

## Planned output paths

This preregistration:

- `docs/eval/locomo_step5p_full_repro_preregistration_2026-05-03.md`

Future Step 5p_exec artifacts, if separately authorized:

- `docs/eval/results/locomo_step5p_full_repro_prelaunch_snapshot_<RUN_ID>.json`
- `docs/eval/results/locomo_step5p_full_repro_raw_<RUN_ID>.json`
- `docs/eval/results/locomo_step5p_full_repro_log_<RUN_ID>.log`
- `docs/eval/results/locomo_step5p_full_repro_validation_<RUN_ID>.json`
- `docs/eval/results/locomo_step5p_full_repro_comparison_<RUN_ID>.md`
- `docs/eval/results/locomo_step5p_full_repro_labels_<RUN_ID>.json`
- `docs/eval/results/locomo_step5p_full_repro_postrun_snapshot_<RUN_ID>.json`
- `docs/eval/results/locomo_step5p_full_repro_cleanup_<RUN_ID>.json`
- `docs/eval/results/locomo_step5p_full_repro_post_execution_verification_<RUN_ID>.json`

## Phase boundary

Step 5p is still measurement-substrate work. Phase C remains blocked.

This preregistration does not promote `14.82%`, `55.28%`, or `58.29%` to a canonical Phase C baseline. A later Step 5p_exec result, even if valid and reproducing, only authorizes a subsequent explicit baseline-decision preregistration. It does not authorize intervention selection or implementation.
