# LOCOMO telemetry-off 199Q reproducibility corrected-slice preregistration — 2026-05-02

Repo: `/home/zaddy/src/Memibrium`

Branch at preregistration start: `query-expansion`

HEAD at preregistration start: `2f9c9df` (`docs: record blocked LOCOMO telemetry-off reproducibility attempt`)

## Status and dependency chain

This document preregisters Step 5j_v2 after the Step 5j execution attempt was correctly aborted and committed with verdict:

`repro_blocked_scope_mismatch_aborted`

Upstream chain:

1. Phase B complete.
2. Phase B.5 root-cause diagnostic complete.
3. Hybrid-active blocker resolved.
4. Canonical substrate env alignment complete.
5. Canonical hybrid-active baseline completed earlier at `f2466c9` with low-context retrieval shape.
6. Read-only failure-mode audit complete.
7. Telemetry instrumentation and Decimal serialization fix windows complete.
8. Telemetry-enabled 199Q retry completed at `91fede6`, but was rejected as noncomparable because it produced a high-context retrieval shape.
9. Artifact-only noncomparability audit completed with verdict `artifact_insufficient_requires_paired_recall_probe`.
10. Paired telemetry flag probe completed at `a4102c2` with verdict `telemetry_perturbation_ruled_out`, caveated because all pairs were empty-result/no-hit pairs.
11. Telemetry-off reproducibility preregistration completed at `4663bcd`.
12. Telemetry-off reproducibility execution attempt completed at `2f9c9df` as a blocked/aborted run because `--max-convs 26` selected all 10 dataset conversations (`1986` questions), not a conv-26-only 199Q slice.
13. This Step 5j_v2 corrected-slice preregistration is the next valid work unit.

Phase C remains blocked. This preregistration does not authorize Phase C selection or any retrieval, scoring, prompt, evaluator, schema, top-k, threshold/fusion, rerank, append-context, DB schema, Docker, source, or runtime mutation.

## Purpose

The purpose is to repair the launch-scope error from Step 5j before retrying the same telemetry-off reproducibility question.

The substantive benchmark question remains unchanged:

> With telemetry off and the canonical conv-26 query-expansion condition restored, does a fresh 199-question run reproduce the `f2466c9` low-context regime, the current-source high-context regime, or a third regime?

The new load-bearing requirement is slice correctness:

> Prove before launch that exactly one conversation, `sample_id == "conv-26"`, with exactly 199 eligible questions will be evaluated; enforce the same proof at launch-time from benchmark output; reject any result JSON that does not contain exactly 199 conv-26 rows.

## Step 5j blocked-run lesson

Step 5j showed that `--max-convs 26` is not a sample-id selector. In the current harness, it is a count/slice cap. Because the local LOCOMO file has 10 conversations, `--max-convs 26` selected all 10. The first conversation happened to be `conv-26`, so the mistake looked plausible until the log showed:

```text
Conversations to process: 10
Total questions: 1986 (1986 evaluated, skipping cats set())
[1/10] Conv conv-26: Caroline & Melanie
```

The run was killed after 60/199 questions within the first conversation, no result JSON was produced, and cleanup restored LOCOMO contamination to zero. Do not resume from that run and do not use its partial score/context as evidence.

## Hard authorization boundary

This Step 5j_v2 document authorizes only:

1. Writing this preregistration file.
2. Committing this preregistration file.
3. Read-only prerequisite checks used to write the preregistration from a clean state.

This Step 5j_v2 document does **not** authorize executing the corrected LOCOMO run.

The future Step 5j_v2_exec corrected reproducibility run may be executed only after explicit separate authorization. Until that authorization is given, do not run the LOCOMO benchmark, do not ingest LOCOMO rows, and do not perform LOCOMO cleanup/deletion.

## Explicit non-goals and non-touchpoints

Do not perform any of the following during Step 5j_v2:

- no LOCOMO benchmark rerun;
- no LOCOMO ingest;
- no LOCOMO cleanup/deletion;
- no DB writes or schema migration;
- no Docker rebuild, recreate, restart, image change, or compose change;
- no env/substrate change;
- no source-code change;
- no prompt, judge, evaluator, query-expansion, context-assembly, top-k, threshold/fusion, rerank, append-context, date-normalization, entity-attribution, SQL, vector-index, or output-cap change;
- no Phase C intervention selection or implementation.

During the future Step 5j_v2_exec execution, the only intended DB writes are the standard LOCOMO ingest writes caused by the benchmark and the mandatory post-run cleanup writes. Those writes require the separate Step 5j_v2_exec authorization.

## Corrected slice mechanism

Primary corrected mechanism: **Option 3 — `--max-convs 1` with explicit dataset-order proof**.

Observed read-only slice facts at preregistration time:

- Input file: `/tmp/locomo/data/locomo10.json`.
- File SHA256 at preregistration inspection: `79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4`.
- Top-level type: list.
- Conversation count: 10.
- Index 0 sample: `conv-26`.
- Index 0 speakers: `Caroline` and `Melanie`.
- Index 0 QA count: `199`.
- Remaining sample order at inspection: `conv-30`, `conv-41`, `conv-42`, `conv-43`, `conv-44`, `conv-47`, `conv-48`, `conv-49`, `conv-50`.

Given those facts, `--max-convs 1` is safe only if the future prelaunch slice proof reconfirms the exact same load-bearing facts from the exact input file immediately before launch.

Fallback mechanism: **Option 1 — temporary single-conversation input JSON**.

If the future prelaunch slice proof does not find `sample_id == "conv-26"` at index 0 with `199` QA rows in `/tmp/locomo/data/locomo10.json`, then do not launch with `--max-convs 1`. Instead, stop and either:

1. write a blocked result with label `corrected_slice_preflight_failed`, or
2. preregister a separate temporary single-conversation input artifact construction step that writes a JSON containing only `sample_id == "conv-26"`, captures its SHA256, and runs a harness path that consumes that constrained file.

The current CLI does not expose a data-path argument; it hard-codes `/tmp/locomo/data/locomo10.json` unless `--cleaned` is used. Therefore Option 1 would require either a carefully scoped temporary input-file swap or a source change/data-path selector, both of which are outside this preregistration and require separate authorization.

Do not use `--max-convs 26` again for this task.

## Locked condition for future Step 5j_v2_exec

Dataset and slice:

- Dataset: LOCOMO `/tmp/locomo/data/locomo10.json`.
- Slice selector: `--max-convs 1`, only after prelaunch proof that index 0 is `conv-26` with exactly `199` QA rows.
- Expected benchmark output: exactly `Conversations to process: 1` and `Total questions: 1986 (199 evaluated, ... question cap absent ...)` is not acceptable; the expected evaluated count must be `199`.
- Expected evaluated questions: `199`.
- Do not use `--max-questions`.
- Do not use `--cleaned`.
- Do not use `--start-conv`.
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

Canonical launch command for Step 5j_v2_exec, after preflight passes:

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
python3 benchmark_scripts/locomo_bench_v2.py --max-convs 1 --query-expansion 2>&1 | tee /tmp/locomo_conv26_telemetry_off_reproducibility_v2_2026-05-02.log
```

The benchmark writes the default query-expansion raw result path:

`/tmp/locomo_results_query_expansion_raw.json`

Immediately after a completed run, copy that JSON and the run log into result artifacts before cleanup or further runs.

## Required Step 5j_v2_exec preflight gates

The future run must stop before benchmark launch if any gate fails. Record preflight evidence in a structured result artifact.

### 1. Git/repo state

- `git status --short` is clean, allowing only the prelaunch artifact being actively written before commit if the runner writes it first.
- `git branch --show-current` is `query-expansion`.
- `git rev-parse --short HEAD` is the Step 5j_v2 preregistration commit, unless a later documentation-only commit is explicitly named in the Step 5j_v2_exec authorization.
- Source is identical to the last committed state.

### 2. Server health and hygiene

- `curl -fsS http://localhost:9999/health` returns `{"status":"ok","engine":"memibrium"}`.
- `SELECT count(id) FROM memories WHERE domain LIKE 'locomo-%';` returns `0`.
- Linked LOCOMO-related counts are all `0` for `temporal_expressions`, `memory_snapshots`, `user_feedback`, `contradictions`, and `memory_edges`.

### 3. Prelaunch slice proof

Read `/tmp/locomo/data/locomo10.json` with Python JSON parsing immediately before launch and record:

- file existence;
- file SHA256;
- top-level type;
- top-level conversation count;
- ordered `sample_id` list;
- index 0 `sample_id`;
- index 0 speaker names;
- index 0 QA count;
- all category counts for index 0;
- total QA count across the whole input file.

Required pass conditions:

- file exists;
- top-level type is list;
- top-level conversation count is at least 1;
- index 0 `sample_id` is exactly `conv-26`;
- index 0 QA count is exactly `199`;
- ordered sample list begins with `conv-26`;
- `--max-convs 1` over this file can only select the index 0 conversation.

If any pass condition fails, do not launch.

### 4. Canonical substrate/runtime

- `USE_RUVECTOR=true` visible in the running server container.
- Live recall server uses or is configured for `text-embedding-3-small` where observable.
- Benchmark launch env resolves `text-embedding-3-small` for embeddings.
- Benchmark launch env resolves `gpt-4.1-mini` for answer, judge, chat, and query expansion.
- No forbidden launch model or embedding deployment appears in the launch env/log.
- `memories.embedding` is `USER-DEFINED:ruvector`.
- `ruvector` type is present.
- `vector` type is absent.
- Live `/app/hybrid_retrieval.py` contains dynamic `$1::{self.vtype}` or equivalent ruvector-safe dynamic cast.
- Live `/app/hybrid_retrieval.py` does not contain hard-coded semantic-search `$1::vector`.
- Live `/app/server.py` includes the Decimal-safe `_serialize_result()` handling.

### 5. Host/container source identity and source behavior

- Capture SHA256 for host and container `server.py`, `hybrid_retrieval.py`, and `benchmark_scripts/locomo_bench_v2.py`.
- Host and container hashes must match for these files.
- Source contains `INCLUDE_RECALL_TELEMETRY` flag handling.
- Telemetry is disabled in effective env.
- Source contains current non-legacy expanded-query accumulation behavior.
- Source contains diagnostic `--legacy-context-assembly`, but it is not enabled.
- Source confirms `--max-convs` applies `data = data[:max_convs]`; therefore the prelaunch index-0 proof is required.

### 6. Result path hygiene

- Inspect `/tmp/locomo_results_query_expansion_raw.json` and `/tmp/locomo_conv26_telemetry_off_reproducibility_v2_2026-05-02.log` before launch.
- If existing files are present, record their size/hash/mtime and archive or remove them before launch so post-run copies cannot accidentally preserve stale artifacts.
- Do not use `--start-conv`.
- Do not resume from the Step 5j partial aborted run.

### 7. Fresh-log boundary

- Capture prelaunch server log tail.
- Establish timestamp or line-count boundary for distinguishing pre-existing messages from run-emitted errors.

## Launch-time slice guardrail

The future runner must not wait until the benchmark completes to notice slice mismatch.

Run the benchmark under a controller that reads early stdout/stderr and enforces this guardrail as soon as the startup lines appear.

Required early lines:

- `Conversations to process: 1`
- `Total questions: ... (199 evaluated...` with no question cap and no skipped categories;
- `[1/1] Conv conv-26:`

Abort conditions:

- if `Conversations to process:` is present and not `1`, kill immediately;
- if `Total questions:` is present and evaluated count is not `199`, kill immediately;
- if the first conversation line is present and is not `[1/1] Conv conv-26:`, kill immediately;
- if these lines do not appear within the first 30 seconds after benchmark startup, kill and label `slice_guard_timeout` unless logs show the process is still in preflight before benchmark startup.

If killed by this guardrail, preserve the partial log, clean any LOCOMO ingest, and write blocked label `slice_mismatch_invalid` or `slice_guard_timeout` as appropriate.

## Result validity gate

A completed run is valid only if the result JSON satisfies all of the following:

- file exists at `/tmp/locomo_results_query_expansion_raw.json` after completion;
- JSON is parseable;
- `details` exists and has exactly `199` rows;
- every row has `conv == "conv-26"` or equivalent sample id field exactly matching `conv-26`;
- no row is from any other sample id;
- condition metadata has `query_expansion=True`, `legacy_context_assembly=False`, and telemetry disabled/absent;
- query expansion fallback count is present;
- `n_memories` is present for every row.

If any validity condition fails after completion, label `slice_mismatch_invalid`; do not compare score or retrieval shape as a valid reproducibility result.

## Required capture fields for Step 5j_v2_exec

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
- prelaunch slice proof;
- result-path hygiene record;
- fresh-log boundary.

Run artifacts:

- raw benchmark JSON copied from `/tmp/locomo_results_query_expansion_raw.json`;
- run log copied from `/tmp/locomo_conv26_telemetry_off_reproducibility_v2_2026-05-02.log`;
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
- slice validity proof from result JSON;
- fresh log checks for `Hybrid retrieval failed`, `type "vector" does not exist`, `Decimal is not JSON serializable`, `TypeError`, HTTP 500/Internal Server Error, and traceback/error lines.

## Decision rules and labels

Primary comparability axes are slice validity first, retrieval shape second, score third. Do not choose Phase C from score movement alone.

### `telemetry_off_low_context_baseline_reproduced`

Use this label if all are true:

- launch-time slice guard passed;
- result validity gate passed with exactly 199 `conv-26` rows;
- query expansion fallback is `0/199` or no more than `2/199` with explicit fallback details;
- mean `n_memories` is within `±0.50` of `4.5327`;
- `n_memories == 15` is within `±10` of `22/199`;
- at least `150/199` questions have `n_memories <= 3`;
- 5-category overall is within `±5` percentage points of `14.82%`, or the score deviation is explained by answer/judge nondeterminism while retrieval-shape gates match;
- no hybrid fallback, vector-type, serialization, HTTP 500, or traceback errors occur.

Interpretation: the f2466c9 low-context baseline is reproducible enough to treat as a real current-condition regime. Phase C still remains blocked until deciding whether the low-context regime or high-context regime is the intended canonical baseline and until the telemetry-on high-context discrepancy is separately explained.

### `telemetry_off_high_context_current_regime_reproduced`

Use this label if all are true:

- launch-time slice guard passed;
- result validity gate passed with exactly 199 `conv-26` rows;
- query expansion fallback is `0/199` or no more than `2/199` with explicit fallback details;
- mean `n_memories >= 13.5`;
- `n_memories == 15 >= 140/199`;
- all or nearly all questions have `n_memories >= 11`;
- retrieval-shape gates are close to the `91fede6` high-context reference;
- no hybrid fallback, vector-type, serialization, HTTP 500, or traceback errors occur.

Interpretation: the f2466c9 14.82% low-context artifact is likely nonreproducible or produced by an effective harness/runtime/artifact mismatch. Reframe the baseline chain around high-context current-code behavior before Phase C.

### `telemetry_off_third_regime_observed`

Use this label if the run completes without blocking errors and passes slice/result validity, but retrieval shape matches neither the low-context nor high-context regime.

Interpretation: substrate/provider/harness nondeterminism or an unmodeled runtime variable is material. Do not choose Phase C. Preregister a variance/repeated-run or runtime-drift audit before any intervention.

### `corrected_slice_preflight_failed`

Use this label if prelaunch slice proof fails before launch.

### `slice_mismatch_invalid`

Use this label if launch-time guardrail or completed result JSON proves the evaluated slice is not exactly conv-26 / 199 rows.

### `slice_guard_timeout`

Use this label if startup lines required by the launch-time guard do not appear within the preregistered guard window and the process is not merely still in preflight.

### `repro_blocked_health_or_substrate_drift`

Use this label if any non-slice preflight substrate, health, git, source, result-path, or hygiene gate fails before launch.

### `repro_blocked_runtime_error`

Use this label if the run starts with a valid slice but is blocked by HTTP 500, invalid JSON, serialization failure, vector-type error, benchmark crash, missing output artifact, or log evidence of hybrid fallback/runtime error.

### `repro_rejected_hygiene_failure`

Use this label if the run completes or aborts but post-run cleanup cannot restore LOCOMO contamination count and linked LOCOMO-related counts to `0`.

## Post-run cleanup requirement for Step 5j_v2_exec

Any authorized Step 5j_v2_exec LOCOMO launch must be followed by cleanup before final reporting, even if the launch-time slice guard kills the process:

1. Copy `/tmp` result/log artifacts into `docs/eval/results/` with unique corrected-slice telemetry-off reproducibility names.
2. Create comparison or blocked-run markdown and structured labels JSON.
3. Delete `locomo-%` memories and linked rows using the established cleanup procedure.
4. Verify:
   - `SELECT count(id) FROM memories WHERE domain LIKE 'locomo-%';` returns `0`;
   - linked LOCOMO-related counts are all `0`.
5. Capture health after cleanup.
6. Commit all result and cleanup artifacts.

If cleanup fails, stop and report `repro_rejected_hygiene_failure`. Do not continue to Phase C.

## Phase C boundary after Step 5j_v2_exec

Phase C remains blocked after this preregistration. It may remain blocked after the future run depending on the label:

- Low-context reproduction: decide canonical regime and explain telemetry/high-context discrepancy before Phase C.
- High-context reproduction: reframe the comparable baseline around current high-context behavior, then preregister Phase C only from that baseline.
- Third regime: estimate variance or audit runtime drift before Phase C.
- Slice/preflight/runtime blocked: fix the blocking condition under a separate preregistration.

Do not treat either `14.82%` or `58.29%` as a stable canonical reference until the future corrected-slice result is committed and interpreted under these decision rules.

## Planned output paths for Step 5j_v2_exec

Preregistration:

- `docs/eval/locomo_telemetry_off_199q_reproducibility_corrected_slice_preregistration_2026-05-02.md`

Future execution artifacts:

- `docs/eval/results/locomo_telemetry_off_199q_reproducibility_v2_prelaunch_2026-05-02.json`
- `docs/eval/results/locomo_conv26_telemetry_off_reproducibility_v2_2026-05-02.json`
- `docs/eval/results/locomo_conv26_telemetry_off_reproducibility_v2_2026-05-02.log`
- `docs/eval/results/locomo_telemetry_off_199q_reproducibility_v2_comparison_2026-05-02.md`
- `docs/eval/results/locomo_telemetry_off_199q_reproducibility_v2_labels_2026-05-02.json`
- `docs/eval/results/locomo_telemetry_off_199q_reproducibility_v2_cleanup_2026-05-02.json`
