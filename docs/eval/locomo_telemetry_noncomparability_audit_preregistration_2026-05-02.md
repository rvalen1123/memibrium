# LOCOMO telemetry noncomparability audit preregistration — 2026-05-02

Repo: `/home/zaddy/src/Memibrium`  
Branch at preregistration start: `query-expansion`  
HEAD at preregistration start: `91fede6` (`docs: record LOCOMO telemetry baseline retry`)

## Status and dependency chain

This preregisters Step 5e after the telemetry-augmented baseline retry was rejected as noncomparable:

1. Telemetry baseline preregistration — `d35bee4`.
2. Telemetry instrumentation mutation-window preregistration — `ab4bf5d`.
3. Opt-in telemetry instrumentation code/tests — `cb56559`.
4. Telemetry instrumentation live mutation window — `328da53`.
5. Telemetry baseline observation attempt — `876eb04`, blocked by Decimal serialization.
6. Telemetry serialization fix preregistration — `fee3a46`.
7. Telemetry serialization fix implementation/window — `5cb6f0b` / `6294164`, verdict `go_telemetry_observation_retry`.
8. Telemetry baseline retry observation — `91fede6`, verdict `telemetry_baseline_rejected_noncomparable`.
9. This Step 5e noncomparability audit preregistration.

Phase C remains blocked. This preregistration does not authorize any retrieval, scoring, prompt, evaluator, schema, top-k, threshold/fusion, rerank, append, DB, substrate, or runtime mutation.

## Triggering finding

The telemetry-enabled retry completed all 199 LOCOMO conv-26 questions and resolved the previous runtime blocker:

- no `Decimal is not JSON serializable` errors;
- no `TypeError` serialization errors;
- no HTTP 500/Internal Server Error signatures;
- no `Hybrid retrieval failed` or `type "vector" does not exist` signatures;
- query expansion fallback remained `0/199`;
- LOCOMO cleanup verified count `0` and linked counts `0`.

But it failed the preregistered retrieval-shape comparability gates decisively:

| Metric | Locked f2466c9 telemetry-off baseline | 91fede6 telemetry-on retry |
|---|---:|---:|
| 5-category overall | 14.82% | 58.29% |
| Protocol 4-category overall | 19.41% | 69.41% |
| Mean `n_memories` | 4.5327 | 14.6231 |
| `n_memories == 15` | 22/199 | 162/199 |
| Exact-`n` distribution | `2:57, 3:110, 11:1, 12:3, 13:3, 14:3, 15:22` | `11:3, 12:6, 13:17, 14:11, 15:162` |

This is a major methodological finding. It creates at least two incompatible explanations:

1. **Telemetry path perturbation.** The telemetry-on request path changes retrieval/output shape, even though telemetry-off smoke hashes matched pre/post mutation. If true, the telemetry-on retry measured a different runtime regime than the telemetry-off 14.82% reference.
2. **Hybrid-active nondeterminism / non-reproducibility.** The same code/substrate/clean DB can produce structurally different retrieval sizes across runs. If true, the 14.82% reference may not be reproducible and the current comparability gate may be structurally unmeetable.

The audit must distinguish what can be learned from already committed artifacts before authorizing any additional server interaction or benchmark rerun.

## Experiment class

Read-only noncomparability audit, artifact-first.

This Step 5e preregistration authorizes only:

- reading committed JSON/log/markdown artifacts;
- writing a read-only audit report and structured labels under `docs/eval/results/`;
- optionally writing small analysis scripts/notebooks if they only read committed artifacts and do not call the live server;
- committing the audit artifacts.

This Step 5e preregistration does **not** authorize:

- live `/mcp/recall` probes;
- telemetry-on/off paired server experiments;
- LOCOMO benchmark reruns;
- DB writes, LOCOMO ingest, cleanup, rebuild/restart, image changes, env edits, source changes, or schema changes;
- Phase C intervention selection or implementation.

If the read-only audit shows that additional live evidence is necessary, write a separate preregistration for Step 5f rather than running it ad hoc.

## Primary question

Why did the telemetry-enabled retry enter a high-context retrieval regime while the locked hybrid-active reference was low-context?

Specifically, determine from committed artifacts whether the observed noncomparability is more consistent with:

- `artifact_supports_telemetry_path_perturbation`;
- `artifact_supports_baseline_nonreproducibility_or_runtime_drift`;
- `artifact_supports_launch_env_or_flag_mismatch`;
- `artifact_supports_analysis_artifact_mismatch`;
- `artifact_insufficient_requires_paired_recall_probe`;
- `artifact_insufficient_requires_telemetry_off_199q_rerun`;
- `artifact_insufficient_other`.

These are audit labels, not Phase C recommendations.

## Required inputs

Read and compare at minimum:

### Locked telemetry-off hybrid-active reference

- `/home/zaddy/src/Memibrium/docs/eval/results/locomo_conv26_hybrid_active_substrate_baseline_2026-05-01.json`
- `/home/zaddy/src/Memibrium/docs/eval/results/locomo_conv26_hybrid_active_substrate_baseline_2026-05-01.log`
- `/home/zaddy/src/Memibrium/docs/eval/results/locomo_hybrid_active_substrate_baseline_199q_comparison_2026-05-01.md`
- `/home/zaddy/src/Memibrium/docs/eval/results/locomo_hybrid_active_substrate_baseline_prelaunch_2026-05-01.json`

### Telemetry instrumentation and serialization chain

- `/home/zaddy/src/Memibrium/docs/eval/results/locomo_hybrid_active_telemetry_instrumentation_result_2026-05-01.md`
- `/home/zaddy/src/Memibrium/docs/eval/results/locomo_hybrid_active_telemetry_serialization_fix_mutation_window_result_2026-05-02.md`
- `/home/zaddy/src/Memibrium/docs/eval/results/locomo_hybrid_active_telemetry_serialization_fix_smoke_hashes_2026-05-02.json`
- `/home/zaddy/src/Memibrium/docs/eval/results/locomo_hybrid_active_telemetry_serialization_fix_serialization_probe_2026-05-02.json`

### Blocked telemetry attempt

- `/home/zaddy/src/Memibrium/docs/eval/results/locomo_hybrid_active_telemetry_baseline_blocked_2026-05-01.json`
- `/home/zaddy/src/Memibrium/docs/eval/results/locomo_conv26_hybrid_active_telemetry_baseline_2026-05-01.log`
- `/home/zaddy/src/Memibrium/docs/eval/results/locomo_hybrid_active_telemetry_baseline_failed_server_log_2026-05-01.log`

### Completed noncomparable telemetry retry

- `/home/zaddy/src/Memibrium/docs/eval/results/locomo_conv26_hybrid_active_telemetry_baseline_retry_2026-05-02.json`
- `/home/zaddy/src/Memibrium/docs/eval/results/locomo_conv26_hybrid_active_telemetry_traces_retry_2026-05-02.json`
- `/home/zaddy/src/Memibrium/docs/eval/results/locomo_hybrid_active_telemetry_summary_retry_2026-05-02.json`
- `/home/zaddy/src/Memibrium/docs/eval/results/locomo_hybrid_active_telemetry_baseline_retry_noncomparable_2026-05-02.json`
- `/home/zaddy/src/Memibrium/docs/eval/results/locomo_hybrid_active_telemetry_baseline_retry_199q_comparison_2026-05-02.md`
- `/home/zaddy/src/Memibrium/docs/eval/results/locomo_hybrid_active_telemetry_baseline_retry_prelaunch_2026-05-02.json`
- `/home/zaddy/src/Memibrium/docs/eval/results/locomo_hybrid_active_telemetry_baseline_retry_server_log_2026-05-02.log`

### Source code for static audit only

- `/home/zaddy/src/Memibrium/server.py`
- `/home/zaddy/src/Memibrium/hybrid_retrieval.py`
- `/home/zaddy/src/Memibrium/benchmark_scripts/locomo_bench_v2.py`
- relevant tests: `test_hybrid_retrieval_ruvector.py`, `test_locomo_query_expansion.py`, `test_server_recall_telemetry.py`

Static source reading is allowed to understand possible mechanisms. Source modification is not allowed.

## Required analyses

### 1. Artifact integrity and condition alignment

Verify and report:

- branch/head/status captured in each prelaunch/result artifact;
- dataset and conversation identity;
- query expansion enabled, fallback count, and whether flag names match code-effective flags;
- answer/judge model identity;
- embedding deployment/dimension evidence;
- ruvector/vector type evidence;
- live source hash/feature probes where available;
- cleanup state after each launch.

Classify any mismatch as one of:

- harmless documentation/flag alias mismatch;
- launch-condition mismatch requiring new preregistration;
- artifact inconsistency requiring blocked audit.

Special attention: the prereg text mentioned `LOCOMO_RETRIEVAL_TELEMETRY`, while benchmark code uses `INCLUDE_RECALL_TELEMETRY`. Determine from artifacts whether the actual launch used the code-effective telemetry flag and whether this is merely a naming drift or a condition mismatch.

### 2. Side-by-side per-question comparison

Compare the locked telemetry-off baseline JSON to the telemetry-on retry JSON by stable question key:

- question text;
- normalized category;
- ground truth;
- predicted answer;
- score;
- `n_memories`;
- query time;
- row order/index;
- any available expanded-query count.

Required outputs:

- distribution of `delta_n_memories = retry_n - baseline_n`;
- count of rows with `baseline_n <= 3` and `retry_n >= 11`;
- count of rows where score improved, worsened, unchanged;
- category-level `delta_n_memories` and score shift;
- top 20 largest divergences by `delta_n_memories`, preserving question/category/score changes.

Do not infer Phase C cause from score deltas. This analysis is only to characterize noncomparability.

### 3. Telemetry-trace structural audit

Using retry traces, report:

- per-question expanded query counts;
- per-expanded-query returned counts;
- candidate counts before dedupe;
- base candidate count after dedupe;
- final answer-context count;
- whether high final context count is produced by many expanded queries, high per-query returns, dedupe behavior, or final cap behavior;
- whether the final context is almost always at cap because candidate recall is saturated;
- whether telemetry contains server-side stream counts sufficient to distinguish semantic/lexical/temporal/fusion contributions.

If trace schema is insufficient to attribute stream/fusion cause, label that explicitly as telemetry-insufficient rather than inventing a cause.

### 4. Static telemetry-path perturbation audit

Read source and answer:

- Does `include_telemetry=true` alter request payload fields other than telemetry request itself?
- Does `server.handle_recall()` change retrieval parameters, branch selection, result sorting, result filtering, or legacy fallback behavior when telemetry is requested?
- Does `HybridRetriever.search()` change candidate collection, fusion, dedupe, ranking, cutoff, or return count when telemetry is requested?
- Does telemetry construction consume or mutate iterators/lists/dicts that are also used for returned results?
- Does benchmark-side telemetry capture change answer-context assembly, dedupe, break conditions, or final memory selection?
- Is there any global mutable state, cache, class attribute, async background task, or logging side effect that plausibly explains telemetry-on/off divergence?

Required output: a table of suspect mechanisms with evidence for/against each.

### 5. Blocked attempt partial-run comparison

The blocked telemetry attempt at `876eb04` reached 120/199 before Decimal serialization abort. Compare whatever can be extracted from its log/placeholder artifacts against:

- the locked telemetry-off baseline first 120 rows, if available;
- the completed telemetry-on retry first 120 rows.

Question: did the blocked telemetry attempt already show the high-context/high-score regime before it aborted?

If only running accuracy is available, state the limitation. Do not overclaim.

### 6. Distinguish next evidence requirement

After artifact-only analysis, decide which next step is warranted:

- `go_paired_telemetry_flag_probe_preregistration` — if artifacts/source suggest telemetry path perturbation but need direct same-query telemetry-on/off recall comparison.
- `go_telemetry_off_repro_rerun_preregistration` — if artifacts suggest baseline nonreproducibility/runtime nondeterminism and paired probes would be insufficient.
- `go_static_telemetry_fix_preregistration` — only if source audit reveals an obvious behavior-changing telemetry bug with artifact support.
- `go_artifact_reclassification_only` — if the audit can fully explain noncomparability without more runs.
- `blocked_artifacts_insufficient` — if required artifacts are missing/corrupt.
- `no_go_phase_c_still_blocked` — if none of the above can be justified.

Phase C intervention selection is not an allowed output.

## Non-goals

This audit must not:

- recommend candidate-fetch, threshold/fusion/output-cap, synthesis, adversarial, schema, or evaluator interventions;
- treat the 58.29% / 69.41% retry as comparable to f2466c9;
- treat the 14.82% baseline as invalid without evidence;
- treat the telemetry-on high-context regime as production-canonical without evidence;
- run live recall probes or benchmarks;
- mutate code, DB, Docker, env, schema, or artifacts from previous steps.

## Expected output artifacts

Primary report:

- `/home/zaddy/src/Memibrium/docs/eval/results/locomo_telemetry_noncomparability_audit_2026-05-02.md`

Structured labels/summaries:

- `/home/zaddy/src/Memibrium/docs/eval/results/locomo_telemetry_noncomparability_audit_labels_2026-05-02.json`

Optional supporting table if too large for the report:

- `/home/zaddy/src/Memibrium/docs/eval/results/locomo_telemetry_noncomparability_audit_per_question_2026-05-02.json`

## Stop conditions

Stop and write a blocked audit result if:

- required locked baseline JSON is missing or cannot be parsed;
- retry JSON/traces are missing or cannot be parsed;
- question alignment between baseline and retry cannot be established;
- artifact condition metadata contradicts the supposed comparison;
- artifacts show LOCOMO cleanup failed or current LOCOMO contamination is nonzero;
- any analysis would require live server interaction not authorized by this preregistration.

## Final boundary

This Step 5e preregistration authorizes writing and committing the preregistration only. The audit execution itself is a separate step after review/authorization.

Until Step 5e audit completes and is reviewed, Phase C remains blocked.
