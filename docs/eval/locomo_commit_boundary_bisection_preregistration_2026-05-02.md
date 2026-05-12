# LOCOMO commit-boundary / harness-path bisection preregistration — Step 5n

Date: 2026-05-02
Repo: `/home/zaddy/src/Memibrium`
Branch: `query-expansion`
HEAD at preregistration start: `8da7872db5d4e2a28b4d15cff4c829f382d1728c` (`docs: record LOCOMO harness runtime drift audit`)

## Status entering Step 5n

Step 5k established `audit_supports_query_expansion_path_drift` and `no_go_phase_c_still_blocked`.

Known regimes:

- Regime A, f2466c9 low-context baseline: 5-cat `14.82%`, protocol 4-cat `19.41%`, mean `n_memories=4.5327`, distribution `2:57, 3:110, 11:1, 12:3, 13:3, 14:3, 15:22`.
- Regime B, 91fede6 telemetry retry high-context, rejected as noncomparable: 5-cat `58.29%`, protocol 4-cat `69.41%`, mean `n_memories=14.6231`, distribution `11:3, 12:6, 13:17, 14:11, 15:162`.
- Regime C, 662514a corrected telemetry-off third regime: 5-cat `55.28%`, protocol 4-cat `70.07%`, mean `n_memories=11.9296`, distribution `4:51, 12:6, 13:10, 14:12, 15:120`.

Step 5k's strongest new evidence: Regime C is structured/bimodal, not a uniform middle point. Adversarial rows remain low-context (mean `n=4.0`), while non-adversarial rows are high-context-ish (mean `n≈14.06–14.77`). Regime B telemetry validates the high-context path: four expanded queries per question, ten recall results per expanded query, forty pre-dedupe candidates, and final answer context capped at fifteen.

## Objective

Identify, by read-only artifact/source inspection, whether any commit boundary between the low-context f2466c9 baseline and the corrected/current state plausibly changed the effective query-expansion/context-assembly/retrieval-count path, especially for non-adversarial questions.

This step is hypothesis-grade bisection. It does not prove causality by executing checkpoints. It narrows the culprit commit or commit range and decides whether a later Step 5o checkpoint reproduction is justified.

## Authorized scope

Option 1 only: read-only artifact/source inspection.

Allowed:

1. Inspect git history and diffs over the path from `f2466c9` through `c9a7623`/current.
2. For each intervening commit, classify touches to:
   - query expansion;
   - benchmark context assembly;
   - recall request construction;
   - retrieval/fusion/scoring;
   - candidate generation;
   - candidate deduplication;
   - `top_k`, fetch caps, answer-context caps;
   - embedding generation/model selection;
   - telemetry-only recording/serialization;
   - docs/artifact-only changes.
3. Focus files:
   - `benchmark_scripts/locomo_bench_v2.py`
   - `hybrid_retrieval.py`
   - `server.py`
   - test files that encode intended invariants for those paths
   - docs/results artifacts only as supporting evidence
4. Cross-reference existing Regime B telemetry traces and Step 5k support files to define the known high-context mechanism.
5. Write a bisection report, structured JSON support, and labels.
6. Commit only documentation/result artifacts.
7. Read current server health and LOCOMO hygiene for final non-mutating verification.

Forbidden:

- No LOCOMO benchmark run.
- No live `/mcp/recall` probe.
- No ingest/retain operations.
- No DB writes or cleanup.
- No Docker rebuild/restart or container mutation.
- No source edits to product/benchmark code.
- No environment mutation.
- No checkpoint checkout/reproduction.
- No Phase C intervention selection.

## Commit range and boundaries

Primary range: commits reachable on `query-expansion` after `f2466c9` through `c9a7623`, with current post-audit docs commits used only for context if needed.

Boundary semantics:

- `f2466c9` is the low-context artifact commit and the lower observational boundary.
- `c9a7623` is the corrected-slice preregistration boundary before the valid third-regime execution.
- `662514a` is the third-regime execution result and may be inspected for result artifacts, but source diffs after `c9a7623` should be treated as documentation/execution artifacts unless proven otherwise.
- `8da7872` is the Step 5k audit result and is not part of the suspected code-change window.

Known commits requiring focused inspection:

- `cb56559` — opt-in LOCOMO recall telemetry hooks; touched benchmark/server/hybrid retrieval paths.
- `5cb6f0b` / `6294164` window — Decimal serialization fix and telemetry serialization artifact window.
- Any commit between `f2466c9` and `c9a7623` that touches benchmark source, hybrid retriever source, server recall path, tests, or retrieval-mode flags.

## Evidence to collect

For each commit in the range:

- commit SHA, subject, parent;
- changed file list;
- whether code files changed versus docs/results only;
- focused diff hunks for the target files;
- impact labels:
  - `query_expansion_logic`
  - `benchmark_context_assembly`
  - `recall_payload_or_response_shape`
  - `retrieval_fusion_or_scoring`
  - `candidate_generation_or_dedup`
  - `topk_or_cap_behavior`
  - `embedding_or_model_selection`
  - `telemetry_recording_only`
  - `serialization_only`
  - `docs_or_artifacts_only`
  - `tests_only`
- qualitative verdict per commit:
  - `plausible_behavior_change`
  - `weak_plausible_behavior_change`
  - `unlikely_behavior_change`
  - `docs_only_no_behavior_change`
  - `insufficient_static_evidence`

## Preregistered interpretation rules

A commit can be labeled `plausible_behavior_change` only if source diff shows a possible path by which final `n_memories` could change, such as:

- changing the number of expanded queries;
- changing whether all expanded queries are consumed versus early break;
- changing recall top_k/fetch_k/cap;
- changing how recall responses are unwrapped;
- changing candidate deduplication keys;
- changing fusion/cutoff ordering or returned results;
- changing server recall behavior under a flag used in the runs;
- changing benchmark answer-context selection.

A commit should be labeled `telemetry_recording_only` or `serialization_only` if the diff only records, projects, or serializes already-computed data and does not alter candidate construction, sorting, filtering, or caps.

If a commit has telemetry hooks that pass through the recall response, inspect carefully for response-shape handling. Telemetry code that changes from returning a list to returning `{results, telemetry}` can be behavior-preserving only if benchmark unwrapping is robust and source evidence supports that.

If the only plausible code change is telemetry instrumentation but the later telemetry-off Regime C is also high-context-ish, do not call telemetry perturbation the primary explanation unless the diff contains a non-telemetry code path change.

## Output labels

Exactly one primary stop/go label:

- `bisection_identifies_specific_commit` — one commit has strong static evidence as the behavior-shift culprit.
- `bisection_identifies_commit_range` — multiple commits or a window plausibly contributed; Step 5o checkpoint reproduction may be justified.
- `bisection_finds_no_retrieval_path_changes` — static diffs do not touch relevant paths; mechanism likely runtime/container/DB/embedding/state rather than committed code.
- `bisection_inconclusive` — artifacts/diffs are insufficient or conflicting.

Secondary labels may include:

- `supports_benchmark_harness_shift`
- `supports_server_recall_shift`
- `supports_hybrid_retriever_shift`
- `supports_telemetry_wrapper_noncausal`
- `supports_artifact_or_runtime_mismatch`
- `requires_step_5o_checkpoint_prereg`
- `no_go_phase_c_still_blocked`

## Decision rules

If `bisection_identifies_specific_commit`:

- Record the commit, exact source mechanism, confidence, and whether Step 5o should confirm it with a bounded checkpoint.
- Do not run the checkpoint in Step 5n.

If `bisection_identifies_commit_range`:

- Record the smallest range and the competing mechanisms.
- Recommend a Step 5o checkpoint plan only if the range cannot be narrowed by source/artifact inspection.

If `bisection_finds_no_retrieval_path_changes`:

- Shift suspicion to runtime/container/state/embedding nondeterminism or artifact mismatch.
- Recommend a non-execution substrate artifact audit or separately preregistered trace-lite probe; do not proceed to Phase C by default.

If `bisection_inconclusive`:

- Preserve unresolved evidence gaps and do not select interventions.

## Phase boundary

Phase C remains blocked throughout Step 5n. No regime is promoted to canonical Phase C baseline by this preregistration or its read-only execution.
