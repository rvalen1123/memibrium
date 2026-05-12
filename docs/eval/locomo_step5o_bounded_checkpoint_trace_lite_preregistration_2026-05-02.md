# LOCOMO bounded checkpoint / trace-lite reproduction preregistration — Step 5o

Date: 2026-05-02 local / 2026-05-03 UTC
Repo: `/home/zaddy/src/Memibrium`
Branch: `query-expansion`
HEAD at preregistration start: `9ea7bd5ad98c195553d80d1d0f3a5961c393d479` (`docs: record LOCOMO commit boundary bisection`)

## Status entering Step 5o

Step 5n completed read-only commit-boundary/source bisection and produced primary label `bisection_identifies_commit_range`.

Step 5n narrowed the issue to `f2466c9..cb56559` as an effective runtime/source boundary:

- lower observational boundary: `f2466c9` low-context artifact;
- upper committed target-source boundary: `cb56559` (`feat: add opt-in LOCOMO recall telemetry`);
- post-boundary benchmark/hybrid source stable through `c9a7623`/`662514a`;
- `5cb6f0b`/`6294164` classified as serialization-only/docs-artifacts, not a retrieval-path culprit.

Critical Step 5n static finding: committed f2466c9 benchmark source already had the all-expanded-query accumulation mechanics. With `USE_QUERY_EXPANSION=1` and legacy assembly off, f2466c9 source loops over every expanded query, accumulates per-query recall results, dedupes, and caps final context at `ANSWER_CONTEXT_TOP_K=15`. Therefore f2466c9's low-context result is not explained by committed f2466c9 source alone.

Known regimes remain:

- Regime A, f2466c9 low-context baseline: 5-cat `14.82%`, protocol 4-cat `19.41%`, mean `n_memories=4.5327`, distribution `2:57, 3:110, 11:1, 12:3, 13:3, 14:3, 15:22`.
- Regime B, 91fede6 telemetry retry high-context, rejected as noncomparable: 5-cat `58.29%`, protocol 4-cat `69.41%`, mean `n_memories=14.6231`, distribution `11:3, 12:6, 13:17, 14:11, 15:162`.
- Regime C, 662514a corrected telemetry-off third regime: 5-cat `55.28%`, protocol 4-cat `70.07%`, mean `n_memories=11.9296`, distribution `4:51, 12:6, 13:10, 14:12, 15:120`.

Phase C remains blocked.

## Objective

Design a bounded, separately authorized execution window that can adjudicate whether the f2466c9 low-context artifact is reproducible under its effective checkpoint/runtime path, and whether the post-cb56559/current path reproduces high-context trace mechanics, without running another full 199Q LOCOMO benchmark initially.

Primary measurement target is retrieval-count path, not score:

- expanded-query count;
- per-expanded-query recall result counts;
- candidate-before-dedupe count;
- candidate-after-dedupe count;
- final answer-context count;
- telemetry/wrapper response shape;
- source/runtime/container/env identity;
- LOCOMO hygiene before/after.

Scores may be recorded if naturally produced by a bounded harness, but scores are secondary and must not be used to promote a Phase C baseline.

## Current authorization status

This document is preregistration only.

Authorized now:

- write this preregistration artifact;
- create fixed-row selection artifact from existing committed result files;
- commit documentation/result artifacts only;
- read current health/hygiene for final verification.

Not authorized by this preregistration alone:

- running Step 5o execution;
- checking out historical commits;
- rebuilding/restarting Docker containers;
- mutating source, env, DB schema, runtime, or benchmark harness;
- ingesting LOCOMO memories;
- running a full 199Q benchmark;
- selecting or implementing Phase C intervention.

Execution requires a separate explicit user authorization after this preregistration is committed.

## Proposed execution mode after explicit authorization

Step 5o execution should be a bounded checkpoint / trace-lite reproduction, not a full benchmark.

The preferred implementation is an execution artifact under `docs/eval/results/` that:

1. snapshots source hashes, git commit, docker image/container identity, env keys with secrets redacted, and LOCOMO hygiene;
2. proves the input slice and fixed row identities;
3. ingests only the minimum required `conv-26` conversation state for the fixed-row probe, using the same ingestion path required by the checkpoint under test;
4. invokes the benchmark answer path for the selected fixed rows only, with trace-lite instrumentation that records retrieval-count path fields;
5. cleans all LOCOMO-linked rows after each checkpoint arm;
6. verifies hygiene returns to zero before proceeding or finishing;
7. emits structured JSON artifacts for each arm and a comparison summary.

If direct invocation of selected rows is not possible without source edits, the execution artifact may wrap/import the existing benchmark functions and monkeypatch only inside the artifact process to limit evaluated rows. Product and benchmark source files must not be edited for Step 5o execution unless a later preregistration explicitly changes this constraint.

## Checkpoint arms

Minimum arms:

### Arm A — f2466c9 checkpoint

Purpose: test whether f2466c9 source/runtime can reproduce the low-context family on fixed rows.

Checkpoint: `f2466c9`.

Expected source facts to prove before any row probe:

- `benchmark_scripts/locomo_bench_v2.py` SHA256: `78721cdc4b76e41b1960b1f8340469e048b3808b62f0889d94cae8921850d57b`;
- `hybrid_retrieval.py` SHA256: `a35fe1624ff17bc19190a8ee5959a767b690cb44303907fbfb7f5373fb771fce`;
- `server.py` SHA256: `5efefae8f05b45974dab6a379403e1a94d00a60e2bfb76b403d4ebe4a7e360d5`.

Primary expected label if reproduced: `checkpoint_reproduces_low_context_at_f2466c9`.

Operational expectation from Regime A: selected rows should tend toward low context for the same rows where A had `n=2/3`, unless ingestion/runtime differences dominate.

### Arm B — post-cb56559/current source checkpoint

Purpose: test whether post-cb56559/current source reproduces high-context trace mechanics on fixed non-adversarial rows and the category-specific low-context split on adversarial rows.

Allowed checkpoint options after authorization, in preference order:

1. `cb56559` if runnable without unrelated serialization/runtime blockers;
2. `5cb6f0b` if Decimal/date serialization is required for telemetry/traces;
3. current `9ea7bd5` only if documented as source-equivalent for benchmark/hybrid path and execution artifacts are isolated from docs commits.

Expected source facts for current/post-fix source-equivalent arm:

- `benchmark_scripts/locomo_bench_v2.py` SHA256: `32dd68d0a0bad7322e8eea67bea90628d0cf42415769802f9e48a4528f3454ff`;
- `hybrid_retrieval.py` SHA256: `2ba660f547432c7fa5ae88955ee97024f5c39848790060358c82dcf0a8259c07`;
- `server.py` SHA256 after serialization fix: `150b161bd9bef5c021fd7f1b32472623b3cc03baac6d13ff42edd501ae3f6f1a`.

Primary expected label if reproduced: `checkpoint_reproduces_high_context_after_cb56559`.

Operational expectation from Regime B/C: selected non-adversarial rows should show 4 expanded queries, near 40 pre-dedupe candidates when each query returns 10, and final context near/capped at 15; selected adversarial rows may stay low-context in telemetry-off current regime and must be measured separately.

## Fixed row set

Fixed rows are selected from existing artifacts only; no benchmark or recall call was used to choose them.

Selection artifact: `docs/eval/results/locomo_step5o_prereg_fixed_rows_2026-05-02.json`.

Rows are 1-based positions in the aligned 199-row conv-26 result artifacts:

| Label | Row | Category | Question SHA256 | A_n | B_n | C_n | Purpose |
|---|---:|---|---|---:|---:|---:|---|
| `adversarial_split_early` | 153 | adversarial | `27b4847984de1d6c9dde59d26f076fd6f729ed02020feb2ba8bea5a54afae319` | 3 | 15 | 4 | adversarial low-context split |
| `adversarial_split_late` | 154 | adversarial | `753a2d308908a185eb2cca48e15941005e2fcac20dcd978d50ecf28f95f45641` | 2 | 15 | 4 | second adversarial split row |
| `unanswerable_high_context` | 83 | unanswerable | `d655f74fe3f7194564489450f0b77e69eacf705269e77bbae3c6d34242ab00be` | 3 | 15 | 15 | non-adversarial high-context path |
| `unanswerable_c_low_exception` | 149 | unanswerable | `17f1b00d7eceafed2640e81b2342bf064f8284f124a4a676ef8d14d6054be2d7` | 2 | 15 | 4 | non-adversarial exception in C |
| `temporal_high_context` | 34 | temporal | `46df9a32c68bda07d28e4b3d23f462cfc0a0839af1de47f130d74aac7afea8b3` | 3 | 15 | 15 | temporal high-context path |
| `single_hop_high_context` | 33 | single-hop | `c26b7a216dfc7eacc85248cb275a25ec02964b1e0a40a550c014e7dbdc43b7a8` | 3 | 15 | 15 | single-hop high-context path |
| `multi_hop_high_context` | 43 | multi-hop | `43ab1d1387937c9833a68417daeae616a8ac101c2473f6079464b448e0e5d42c` | 3 | 15 | 15 | multi-hop high-context path |

The execution artifact must prove row identity by exact question text hash before evaluating. If any fixed-row hash mismatches at a checkpoint, label `checkpoint_blocked_row_identity_mismatch` and stop that arm.

## Preflight gates for any future execution

Before any checkpoint arm executes:

1. Git state and source identity:
   - branch/commit recorded;
   - working tree clean or only preregistered execution artifacts present;
   - target file hashes match arm expectations.
2. Runtime health:
   - `GET /health` returns `{"status":"ok","engine":"memibrium"}` for the intended server instance.
3. LOCOMO hygiene:
   - `memories` with `domain LIKE 'locomo-%'` is zero;
   - linked tables are zero for LOCOMO-linked IDs: `temporal_expressions`, `memory_snapshots`, `user_feedback`, `contradictions`, `memory_edges`.
4. Input identity:
   - `/tmp/locomo/data/locomo10.json` exists;
   - top-level type list;
   - index 0 `sample_id == "conv-26"`;
   - index 0 QA count exactly 199;
   - fixed row question hashes match this preregistration.
5. Environment:
   - telemetry flags explicitly set according to arm design;
   - `USE_QUERY_EXPANSION=1` and CLI/logic query expansion enabled;
   - legacy/context-rerank/append/gated append/date normalization/no-expansion Arm B disabled unless explicitly tested in a separate preregistration;
   - secrets redacted in artifacts.

If any preflight gate fails, do not probe rows; emit the relevant blocked label.

## Trace-lite required fields

For each selected row and each arm, record:

- checkpoint/commit SHA;
- target source hashes;
- container image ID and started-at timestamp if Docker is involved;
- redacted env subset affecting model/embedding/query expansion/telemetry/retrieval;
- LOCOMO hygiene before and after;
- row label, 1-based index, category, exact question hash;
- expanded queries and expanded-query count;
- for each expanded query:
  - query text hash and optionally redacted/plain query text if already non-secret benchmark text;
  - recall `top_k` requested;
  - returned result count;
  - ordered memory IDs or stable content hashes;
- candidate count before dedupe;
- candidate count after dedupe;
- final answer-context count;
- final context ordered memory IDs/content hashes;
- fallback/error status;
- optional answer and score if naturally produced, explicitly marked secondary.

Do not rely on score-only comparisons. Retrieval-count path is the primary outcome.

## Guardrails during future execution

Hard stops:

- any row identity mismatch;
- unexpected full 199Q launch;
- any conversation other than `conv-26`;
- LOCOMO hygiene nonzero before arm start;
- LOCOMO cleanup/hygiene failure after arm;
- target source hash mismatch;
- telemetry/runtime error that prevents trace-lite fields from being recorded;
- Docker/source/env mutation not listed in the eventual execution authorization.

If an arm starts a long-running process or server, it must be tracked and stopped/cleaned before proceeding. No orphaned benchmark/server processes.

## Output labels

Exactly one primary label after future Step 5o execution:

- `checkpoint_reproduces_low_context_at_f2466c9` — Arm A fixed rows reproduce the low-context retrieval-count family consistent with Regime A.
- `checkpoint_reproduces_high_context_after_cb56559` — Arm B/current fixed rows reproduce high-context mechanics consistent with Regime B/C non-adversarial rows.
- `checkpoint_shows_no_static_boundary_effect` — Arms do not differ materially in trace-lite retrieval-count path, weakening the f2466c9..cb56559 boundary hypothesis.
- `checkpoint_inconclusive_runtime_state` — execution blocked, unstable, or trace-lite artifacts insufficient.

Additional blocked labels:

- `checkpoint_blocked_health_or_hygiene`
- `checkpoint_blocked_row_identity_mismatch`
- `checkpoint_blocked_source_hash_mismatch`
- `checkpoint_blocked_runtime_error`
- `checkpoint_blocked_cleanup_failure`
- `checkpoint_rejected_protocol_violation`

Secondary labels may include:

- `supports_effective_harness_mismatch`
- `supports_runtime_state_nondeterminism`
- `supports_query_expansion_output_drift`
- `supports_post_cb56559_high_context_path`
- `supports_adversarial_category_split`
- `requires_full_repro_prereg`
- `no_go_phase_c_still_blocked`

## Interpretation rules

If Arm A reproduces low-context and Arm B reproduces high-context:

- preserve `f2466c9..cb56559` as an execution-supported boundary;
- do not yet pick Phase C baseline;
- decide whether a narrowly scoped full 199Q reproduction is justified in a later preregistration.

If Arm A is also high-context:

- f2466c9 low-context artifact is likely nonreproducible/effective-runtime artifact;
- do not use 14.82% as baseline;
- consider labeling `checkpoint_shows_no_static_boundary_effect` or `checkpoint_inconclusive_runtime_state` depending on trace quality.

If Arm B/current does not reproduce high-context on non-adversarial rows:

- suspect runtime/state nondeterminism or ingestion path instability;
- do not proceed to Phase C;
- require a substrate/runtime-state audit before further benchmark claims.

If only adversarial rows differ while non-adversarial rows match:

- preserve category-specific split hypothesis;
- any later full run must stratify adversarial vs non-adversarial retrieval path.

## Phase boundary

Step 5o remains measurement-substrate work. Phase C is still blocked. None of `14.82%`, `58.29%`, or `55.28%` may be promoted to canonical Phase C baseline by this preregistration. Even a successful bounded checkpoint only authorizes a later decision about whether to preregister a fuller reproduction; it does not authorize intervention selection.

## Artifacts created by this preregistration

- This preregistration: `docs/eval/locomo_step5o_bounded_checkpoint_trace_lite_preregistration_2026-05-02.md`
- Fixed-row selection artifact: `docs/eval/results/locomo_step5o_prereg_fixed_rows_2026-05-02.json`
