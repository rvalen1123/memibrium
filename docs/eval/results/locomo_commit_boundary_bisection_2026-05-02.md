# LOCOMO commit-boundary / harness-path bisection — Step 5n

Date: 2026-05-02
Repo: `/home/zaddy/src/Memibrium`
Branch: `query-expansion`
Prereg commit: `617505f` (`docs: preregister LOCOMO commit boundary bisection`)
Mode: Option 1 read-only artifact/source inspection only.

## Verdict

Primary label: `bisection_identifies_commit_range`

Secondary labels:
- `supports_benchmark_harness_shift`
- `supports_telemetry_wrapper_noncausal`
- `supports_artifact_or_runtime_mismatch`
- `requires_step_5o_checkpoint_prereg`
- `no_go_phase_c_still_blocked`

Culprit range/hypothesis: `f2466c9..cb56559` effective runtime/source boundary, with `cb56559` as the only committed target-source change but not a proven specific culprit.

Confidence: medium for the range; low for specific commit causality.

Phase C remains blocked.

## Executive interpretation

Static bisection did not find a clean source-line explanation for the f2466c9 low-context baseline. The surprising part is that the all-expanded-query accumulation path was already present in the f2466c9 benchmark source: with `USE_QUERY_EXPANSION` enabled, the non-legacy path loops over every expanded query, accumulates per-query recall results, dedupes, and caps the final answer context at `ANSWER_CONTEXT_TOP_K=15`.

That means Regime A (`f2466c9`, mean n=4.5327, mostly n=2/3) is not explained by committed f2466c9 source alone. It is better treated as an effective-harness/runtime/artifact mismatch or nonreproducible baseline until a later bounded checkpoint proves otherwise.

The only intervening commit that changes the preregistered target source files is `cb56559` (`feat: add opt-in LOCOMO recall telemetry`). It changes `benchmark_scripts/locomo_bench_v2.py`, `hybrid_retrieval.py`, and `server.py`, but source inspection shows telemetry wrapper/plumbing behavior: response-shape unwrapping, optional telemetry projections, and legacy list-shape preservation when `include_telemetry` is false. It does not visibly change the query-expansion loop count, recall top_k, candidate accumulation, dedupe key, or final cap in the telemetry-off path.

Post-`cb56559`, the relevant source is stable: `benchmark_scripts/locomo_bench_v2.py` and `hybrid_retrieval.py` have identical hashes from `cb56559` through `c9a7623`/`662514a`; `server.py` only receives a later serialization fix at `5cb6f0b`. Therefore the static range is narrowed to the effective boundary from the low-context artifact at `f2466c9` to the post-telemetry-wrapper source/runtime at `cb56559`, but Step 5n cannot honestly call `cb56559` the behavior-shift culprit without execution.

## Scope and side-effect status

Performed:
- inspected git history and diffs for `f2466c9..c9a7623`;
- classified every intervening commit;
- inspected target source hashes and source snippets for `benchmark_scripts/locomo_bench_v2.py`, `hybrid_retrieval.py`, and `server.py`;
- cross-referenced existing Step 5k artifacts and Regime B telemetry traces;
- wrote docs/results artifacts only.

Not performed:
- no LOCOMO benchmark run;
- no live `/mcp/recall` probe;
- no DB write/cleanup;
- no Docker rebuild/restart;
- no product/benchmark source edits;
- no env/runtime/schema mutation;
- no checkpoint checkout/reproduction;
- no Phase C intervention.

## Per-commit bisection summary

Full table: `docs/eval/results/locomo_commit_boundary_bisection_per_commit_2026-05-02.tsv`

| Commit | Subject | Target source changed | Final verdict |
|---|---|---|---|
| `81d1597` | docs: preregister LOCOMO hybrid failure-mode audit | none | `docs_only_no_behavior_change` |
| `6c0e38f` | docs: record LOCOMO hybrid failure-mode audit | none | `docs_only_no_behavior_change` |
| `d35bee4` | docs: preregister LOCOMO telemetry baseline | none | `docs_only_no_behavior_change` |
| `ab4bf5d` | docs: preregister LOCOMO telemetry instrumentation window | none | `docs_only_no_behavior_change` |
| `cb56559` | feat: add opt-in LOCOMO recall telemetry | benchmark_scripts/locomo_bench_v2.py, hybrid_retrieval.py, server.py | `weak_plausible_behavior_change_not_specific_culprit` |
| `328da53` | docs: record LOCOMO telemetry instrumentation window | none | `support_script_and_artifacts_only_no_runtime_path_change` |
| `876eb04` | docs: record LOCOMO telemetry baseline block | none | `docs_only_no_behavior_change` |
| `fee3a46` | docs: preregister LOCOMO telemetry serialization fix window | none | `docs_only_no_behavior_change` |
| `5cb6f0b` | fix: serialize Decimal values in recall telemetry | server.py | `serialization_only_unlikely_behavior_change` |
| `6294164` | docs: record LOCOMO telemetry serialization fix window | none | `docs_only_no_behavior_change` |
| `91fede6` | docs: record LOCOMO telemetry baseline retry | none | `docs_only_no_behavior_change` |
| `faaa661` | docs: preregister LOCOMO telemetry noncomparability audit | none | `docs_only_no_behavior_change` |
| `29f4209` | docs: record LOCOMO telemetry noncomparability audit | none | `docs_only_no_behavior_change` |
| `544a003` | docs: preregister LOCOMO paired telemetry flag probe | none | `docs_only_no_behavior_change` |
| `a4102c2` | docs: record LOCOMO paired telemetry flag probe | none | `docs_only_no_behavior_change` |
| `4663bcd` | docs: preregister LOCOMO telemetry-off reproducibility | none | `docs_only_no_behavior_change` |
| `2f9c9df` | docs: record blocked LOCOMO telemetry-off reproducibility attempt | none | `docs_only_no_behavior_change` |
| `c9a7623` | docs: preregister LOCOMO corrected slice reproducibility | none | `docs_only_no_behavior_change` |

Key read: all commits other than `cb56559` and `5cb6f0b` are docs/results/support-script artifacts for the preregistered target runtime path. `5cb6f0b` is serialization-only. `cb56559` is the only target-source boundary.

## Source hash evidence

| Commit | benchmark hash | hybrid hash | server hash |
|---|---|---|---|
| `f2466c9` | `78721cdc4b76` | `a35fe1624ff1` | `5efefae8f05b` |
| `cb56559` | `32dd68d0a0ba` | `2ba660f54743` | `d0532ea7a474` |
| `5cb6f0b` | `32dd68d0a0ba` | `2ba660f54743` | `150b161bd9be` |
| `c9a7623` | `32dd68d0a0ba` | `2ba660f54743` | `150b161bd9be` |
| `662514a` | `32dd68d0a0ba` | `2ba660f54743` | `150b161bd9be` |

Interpretation: the benchmark and hybrid retriever source hashes change at `cb56559` and then remain stable through the valid third-regime run. `server.py` changes at `cb56559`, then at `5cb6f0b` for JSON serialization only, and then remains stable through the corrected run.

## Static code findings

At `f2466c9`, the benchmark already had these mechanics:
- f2466c9 benchmark already has USE_QUERY_EXPANSION gating expand_query(question).
- f2466c9 non-legacy path loops over all queries returned by expand_query(question).
- f2466c9 only breaks early when not USE_QUERY_EXPANSION; with query expansion enabled it accumulates recalls across expanded queries.
- f2466c9 uses RECALL_TOP_K/candidate_recall_top_k per query and then candidates[:ANSWER_CONTEXT_TOP_K].

At `cb56559`, source inspection found these changes:
- Introduces _extract_recall_payload() to unwrap list or {results, memories, telemetry}.
- Introduces recall_for_query() wrapper that optionally adds include_telemetry and then returns recalled results.
- Replaces duplicated recall payload/unwrapping code with recall_for_query() in both legacy and non-legacy branches.
- Adds recall_telemetry counters/projections and optional row[recall_telemetry] output.
- Adds HybridRetriever include_telemetry parameter; when false, return path remains final_results list.
- Server returns legacy list shape unless include_telemetry is true; include_telemetry true returns {results, telemetry}.

Post-boundary stability:
- benchmark_scripts/locomo_bench_v2.py hash is identical at cb56559, 5cb6f0b, c9a7623, and 662514a.
- hybrid_retrieval.py hash is identical at cb56559, 5cb6f0b, c9a7623, and 662514a.
- server.py changes at 5cb6f0b are serialization-only; after 5cb6f0b server.py hash is identical through c9a7623/662514a.

This weakens a simple “telemetry changed retrieval” explanation. The telemetry-on Regime B is high-context, but telemetry-off Regime C is also high-context-ish for non-adversarial rows under the same relevant source. The Step 5h paired flag probe also found telemetry wrapper shape preservation on empty/no-hit calls, though it did not test populated LOCOMO recalls.

## Regime shape cross-check

| Category | A mean/dist | B mean/dist | C mean/dist |
|---|---|---|---|
| adversarial | 2.617 / `2:18, 3:29` | 14.6809 / `13:6, 14:3, 15:38` | 4.0 / `4:47` |
| multi-hop | 7.2308 / `2:2, 3:6, 12:1, 15:4` | 14.5385 / `12:2, 15:11` | 14.7692 / `12:1, 15:12` |
| single-hop | 6.2188 / `2:7, 3:15, 12:1, 13:3, 14:1, 15:5` | 14.6875 / `11:1, 13:2, 14:2, 15:27` | 14.75 / `12:2, 14:2, 15:28` |
| temporal | 8.1351 / `2:5, 3:15, 11:1, 12:1, 14:2, 15:13` | 14.4054 / `11:1, 12:2, 13:5, 14:2, 15:27` | 14.5405 / `13:6, 14:5, 15:26` |
| unanswerable | 2.6429 / `2:25, 3:45` | 14.6857 / `11:1, 12:2, 13:4, 14:4, 15:59` | 14.0571 / `4:4, 12:3, 13:4, 14:5, 15:54` |

Regime C remains the structured hybrid from Step 5k: adversarial rows stay low-context (`n=4` for all 47), while most non-adversarial rows are high-context-ish and score-close to Regime B.

Regime B telemetry mechanism, by category, confirms high context is benchmark-side accumulation rather than one oversized server recall. For every category, expanded query count is `4` for every row and candidate-before-dedupe is `40` for every row; final context is then capped/deduped to mostly `15`.

## Why the primary label is range, not specific commit

Preregistered `bisection_identifies_specific_commit` requires strong static evidence that one commit changed final `n_memories`, such as changing expanded-query count, recall top_k, dedupe, fusion, or final cap. Step 5n did not find that.

`cb56559` is the only target-source change and therefore the upper boundary for any later checkpoint, but its visible code preserves telemetry-off result selection. `5cb6f0b` only serializes `date`/`Decimal` values and does not touch query/candidate/top_k/fusion/cap behavior. The remaining commits are docs/results/preregistration/audit artifacts for this path.

Therefore Step 5n identifies the smallest useful static range:

- lower observational boundary: `f2466c9` low-context result artifact;
- upper committed target-source boundary: `cb56559`;
- stable post-boundary source through `c9a7623`/`662514a`;
- unresolved mechanism: effective harness/runtime mismatch, artifact mismatch, baseline nonreproducibility, or state/substrate nondeterminism rather than a proven source-line change.

## Recommended next step, if continuing

Step 5o should be separately preregistered before any execution. It should not start with another full 199Q benchmark. The smallest defensible execution would be a bounded checkpoint / trace-lite reproduction focused on retrieval-count path, not score:

- compare `f2466c9` effective source versus `cb56559`/current source;
- use fixed rows including adversarial and non-adversarial examples because the split is category-specific;
- record expanded-query count, per-query result counts, candidate-before-dedupe count, dedupe count, final context count, source hashes, env, container image ID, and LOCOMO hygiene;
- no Phase C intervention and no full 199Q rerun unless a later preregistration explicitly authorizes it.

Suggested Step 5o primary labels:

- `checkpoint_reproduces_low_context_at_f2466c9`
- `checkpoint_reproduces_high_context_after_cb56559`
- `checkpoint_shows_no_static_boundary_effect`
- `checkpoint_inconclusive_runtime_state`

## Phase boundary

Phase C remains blocked. Do not promote `14.82%`, `58.29%`, or `55.28%` as the canonical Phase C baseline. The next work is still measurement-substrate adjudication, not intervention selection.

## Artifacts

- Preregistration: `docs/eval/locomo_commit_boundary_bisection_preregistration_2026-05-02.md`
- Support JSON: `docs/eval/results/locomo_commit_boundary_bisection_support_2026-05-02.json`
- Labels JSON: `docs/eval/results/locomo_commit_boundary_bisection_labels_2026-05-02.json`
- Per-commit TSV: `docs/eval/results/locomo_commit_boundary_bisection_per_commit_2026-05-02.tsv`
