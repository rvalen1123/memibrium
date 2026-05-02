# LOCOMO harness-runtime drift audit — Step 5k

Date: 2026-05-02
Repo: `/home/zaddy/src/Memibrium`
Branch: `query-expansion`
Prereg commit: `e8f99e3`
Audit mode: read-only artifact/source/runtime metadata inspection; no benchmark, no live recall probe, no DB/Docker/source/env mutation.

## Verdict

Primary label: `audit_supports_query_expansion_path_drift`

Secondary labels:

- `audit_supports_artifact_mismatch`
- `audit_supports_harness_code_drift`
- `audit_inconclusive_artifacts_insufficient`
- `audit_requires_commit_boundary_bisection_prereg`
- `no_go_phase_c_still_blocked`

Recommended next step: `go_commit_boundary_bisection_preregistration`

Phase C remains blocked.

## Executive interpretation

The audit narrows the A/B/C regime split to benchmark harness/query-expansion path ambiguity, not server substrate or telemetry serialization.

All three 199Q result artifacts are parseable, all align on the same 199 question texts/order and `conv-26`, and all claim the same high-level condition metadata: `query_expansion=True`, `legacy_context_assembly=False`, context rerank off, append modes off, date normalization off, fallback `0/199`.

Despite that, the retrieval shapes are incompatible:

- Regime A (`f2466c9`) is low-context: mean `n_memories=4.5327`, mostly `n=2/3`.
- Regime B (`91fede6`) is high-context: mean `14.6231`, `n=15` for 162/199.
- Regime C (`662514a`) is a valid telemetry-off third regime: mean `11.9296`, `n=15` for 120/199, but with a category-specific split.

The decisive new observation is Regime C's category-specific shape:

- adversarial: mean `n=4.0`, score `7.45%`
- multi-hop/single-hop/temporal/unanswerable: mean `n≈14.06–14.77`, high scores except multi-hop

This means the third regime is not random noise around A or B. It is a structured hybrid: most non-adversarial questions follow the current high-context query-expansion accumulation path, while adversarial rows remain low-context.

Existing telemetry from Regime B already proves the current benchmark path can produce high context by issuing 4 expanded queries per question, receiving 10 results per expanded query, deduping 40 candidates, and capping final context at 15. Regime C's non-adversarial rows match that mechanism closely. Regime A's low-context artifact is therefore suspicious as an effective-harness/path artifact: its condition metadata says current-style query expansion, but its `n_memories` distribution resembles an earlier/limited context path.

However, artifact-only evidence cannot prove whether Regime A was produced by:

1. a different effective harness source than committed metadata implies;
2. a query-expansion output distribution change, especially for adversarial/category-specific prompts;
3. ingestion/background state nondeterminism changing recall returns; or
4. an undocumented runtime/container/source mismatch during the baseline run.

The next best step is not Phase C and not another speculative intervention. It is a preregistered commit-boundary / harness-path bisection focused on the effective benchmark query-expansion/context-assembly path, using source diffs and, only if later authorized, the smallest bounded probes needed to reproduce the n-count family.

## Scope and side-effect status

Allowed and performed:

- inspected committed JSON/markdown/log artifacts;
- computed hashes/statistics from result artifacts;
- aligned per-question rows by exact question text/order;
- inspected git history/diffs for relevant source files;
- inspected current health and LOCOMO hygiene read-only;
- inspected current container env/source hash metadata read-only;
- wrote audit artifacts.

Forbidden and not performed:

- no LOCOMO benchmark;
- no live `/mcp/recall` probes;
- no memory ingest;
- no DB cleanup/mutation;
- no Docker rebuild/restart;
- no source/runtime/env/schema mutation;
- no Phase C intervention selection.

Current read-only health/hygiene at audit time:

- Health: `{"status":"ok","engine":"memibrium"}`
- LOCOMO hygiene:
  - `memories|0`
  - `temporal_expressions|0`
  - `memory_snapshots|0`
  - `user_feedback|0`
  - `contradictions|0`
  - `memory_edges|0`

## Input artifacts

Support JSON: `docs/eval/results/locomo_harness_runtime_drift_audit_support_2026-05-02.json`

Per-question table: `docs/eval/results/locomo_harness_runtime_drift_audit_per_question_2026-05-02.json`

### Regime A — low-context baseline

Artifact: `docs/eval/results/locomo_conv26_hybrid_active_substrate_baseline_2026-05-01.json`

- SHA256: `d44b9288a633bfdb04061f44bb5d37b8240342e5550e2df5f1c2bc2f38187637`
- rows: `199`
- unique convs: `conv-26`
- 5-cat: `14.82%`
- protocol 4-cat: `19.41%`
- fallback: `0`
- condition: query expansion on; cleaned/date normalization/context rerank/append/gated append/no-expansion Arm B/legacy context assembly all off
- mean `n_memories`: `4.5327`
- distribution: `2:57, 3:110, 11:1, 12:3, 13:3, 14:3, 15:22`

### Regime B — telemetry retry high-context

Artifact: `docs/eval/results/locomo_conv26_hybrid_active_telemetry_baseline_retry_2026-05-02.json`

- SHA256: `7d8c911caa8753e6f920bed1402f8e1d72c0a6c4d741f82003f54de5fc2c032d`
- rows: `199`
- unique convs: `conv-26`
- 5-cat: `58.29%`
- protocol 4-cat: `69.41%`
- fallback: `0`
- condition: same high-level metadata as A
- mean `n_memories`: `14.6231`
- distribution: `11:3, 12:6, 13:17, 14:11, 15:162`
- telemetry rows: `199/199`

### Regime C — corrected telemetry-off third regime

Artifact: `docs/eval/results/locomo_corrected_slice_results_query_expansion_raw_2026-05-02.json`

- SHA256: `317dc38bb7cbe8529c3f1d10fbbefe459d6b790c539f8395cf72729dd828f9e9`
- rows: `199`
- unique convs: `conv-26`
- 5-cat: `55.28%`
- protocol 4-cat: `70.07%`
- fallback: `0`
- condition: same high-level metadata as A/B, telemetry absent/off
- mean `n_memories`: `11.9296`
- distribution: `4:51, 12:6, 13:10, 14:12, 15:120`
- validity: startup guard/result gate passed

## Per-question overlap

All three regimes align on 199 exact question texts in the same order.

Summary:

- common question count: `199`
- same order across A/B/C: `true`
- `n_C == n_A`: `19/199`
- `n_C == n_B`: `117/199`
- `n_C` between A and B inclusive: `179/199`

Score pattern counts, where uppercase means that regime scored the row nonzero:

- `ABC`: 38
- `abc`: 54
- `aBC`: 82
- `Abc`: 1
- `aBc`: 17
- `abC`: 7

Thus most improvements from A persist in C: `aBC` rows dominate. C is score-close to B even when its retrieval shape is not exactly B.

## Category-level shape comparison

| Category | N | A mean n | B mean n | C mean n | A score | B score | C score | C==B count | C between A/B |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| adversarial | 47 | 2.6170 | 14.6809 | 4.0000 | 0.00% | 22.34% | 7.45% | 0 | 47 |
| multi-hop | 13 | 7.2308 | 14.5385 | 14.7692 | 30.77% | 42.31% | 38.46% | 12 | 13 |
| single-hop | 32 | 6.2188 | 14.6875 | 14.7500 | 26.56% | 64.06% | 68.75% | 26 | 27 |
| temporal | 37 | 8.1351 | 14.4054 | 14.5405 | 39.19% | 68.92% | 75.68% | 25 | 29 |
| unanswerable | 70 | 2.6429 | 14.6857 | 14.0571 | 3.57% | 77.14% | 73.57% | 54 | 63 |

This table is the strongest Step 5k evidence. Regime C is not a uniform middle point. It preserves high-context behavior for non-adversarial classes but not for adversarial rows.

## Regime B telemetry mechanism

Regime B telemetry rows: `199/199`.

Structural facts from telemetry:

- expanded query count distribution: `4:199`
- per-query recall calls: `796`
- per-query result-count distribution: `10:796`
- candidate memories before dedupe: `40:199`
- base/candidate count after dedupe mean: `17.8844`
- base/candidate count after dedupe distribution: `11:3, 12:6, 13:17, 14:11, 15:16, 16:22, 17:16, 18:30, 19:13, 20:18, 21:8, 22:20, 23:8, 24:4, 25:4, 26:2, 28:1`
- final answer-context count distribution: `11:3, 12:6, 13:17, 14:11, 15:162`

Interpretation: B's high context is not server returning >10 in one call. It is benchmark-side accumulation across four expanded queries, followed by dedupe and final cap at 15.

Regime C has no telemetry rows by design, but its non-adversarial n-shape is consistent with this same accumulation mechanism.

## Harness/source audit

Git history from A to C:

- `f2466c9` records the low-context substrate baseline artifact.
- `cb56559` adds opt-in LOCOMO recall telemetry and modifies `benchmark_scripts/locomo_bench_v2.py`, `hybrid_retrieval.py`, and `server.py`.
- `91fede6` records the telemetry retry high-context regime.
- `662514a` records the corrected telemetry-off third regime.

Diff summary from `f2466c9` to `662514a` over relevant source files:

- `benchmark_scripts/locomo_bench_v2.py`: 115 insertions, 16 deletions
- `hybrid_retrieval.py`: 167 insertions, 15 deletions
- `server.py`: 59 insertions, 3 deletions

Focused source reading:

- Current benchmark `answer_question()` expands queries when `USE_QUERY_EXPANSION` is true.
- In the non-legacy path, it loops over every expanded query and only breaks early when `not USE_QUERY_EXPANSION`.
- It accumulates candidates from all expanded-query recalls, dedupes, and uses `candidates[:ANSWER_CONTEXT_TOP_K]` for the final answer context when no rerank/append mode is active.
- This code path mechanically predicts high final contexts when all four recalls return 10 results.
- Regime B telemetry confirms exactly that for all 199 rows.

Telemetry-specific source reading:

- `INCLUDE_RECALL_TELEMETRY` adds `include_telemetry` to recall payloads and stores telemetry rows.
- Static source does not show a separate answer-context branch conditioned on `INCLUDE_RECALL_TELEMETRY` or `return_telemetry`.
- Server/hybrid telemetry code records projections and response metadata; the already-preregistered Step 5h empty/no-hit probe found no same-query telemetry perturbation, but did not cover populated LOCOMO recalls.

Baseline artifact mismatch concern:

- The f2466c9 commit itself is artifact-only (`docs: record LOCOMO hybrid-active substrate baseline`) and does not modify benchmark/server/hybrid source relative to parent `8d471fa`.
- Therefore the low-context result is not explained by a committed source diff at f2466c9 itself.
- The baseline prelaunch artifact recorded host/container source hashes and canonical substrate checks, but it did not preserve telemetry traces or per-expanded-query recall counts.
- Its condition metadata claims `query_expansion=True` and `legacy_context_assembly=False`, but its n-shape is difficult to reconcile with current non-legacy all-expansions accumulation.

## Runtime/substrate audit

Evidence against simple substrate drift:

- A prelaunch recorded canonical substrate checks passing (`text-embedding-3-small`, `gpt-4.1-mini`, ruvector, DB self-distance, clean LOCOMO count).
- B prelaunch recorded canonical launch env for answer/judge/chat/embedding and clean LOCOMO count.
- C prelaunch slice proof and guard were valid; current health/hygiene remain clean.
- B and C share the same relevant committed source after telemetry instrumentation; `git diff 91fede6..662514a` for `benchmark_scripts/locomo_bench_v2.py`, `server.py`, and `hybrid_retrieval.py` is empty.

Evidence not sufficient to rule out runtime/state nondeterminism:

- A lacks telemetry traces, so it does not reveal per-expanded-query result counts, dedupe counts, or final candidate path.
- A and C were separated by container rebuilds/restarts/mutation windows earlier in the chain.
- Ingestion/background processing may be order/timing-sensitive; existing artifacts do not preserve enough per-memory IDs/context to distinguish retrieval nondeterminism from harness-path mismatch.

## Evidence gap table

| Candidate family | Existing support | Existing counterevidence | Missing decisive artifact |
|---|---|---|---|
| Query-expansion/context-assembly path drift | B telemetry proves all-expansions accumulation creates high context; C non-adversarial rows match high context; A shape conflicts with claimed metadata | A condition metadata says query expansion on and legacy off | A telemetry trace or source/runtime capture proving actual `answer_question()` path during A |
| Artifact/effective-harness mismatch | f2466c9 result is artifact-only; low context resembles a limited/early-break path; no A telemetry trace | A prelaunch claims source/container checks passed | Re-run/bisect at exact historical source/runtime boundary with guard and trace-lite n-count evidence |
| Runtime/substrate drift | A/B/C separated by rebuilds/windows; A lacks trace-level evidence | Canonical env checks passed; B and C source files identical | Runtime substrate snapshot that includes source hash, image ID, env, package versions, and deterministic recall/count probe |
| Stateful nondeterminism | C differs from B despite same relevant source; adversarial category split suggests category/query-dependent output variability | B and C both use clean LOCOMO starts and valid 199 rows | Second corrected telemetry-off replicate or bounded populated recall probe under same state |
| Telemetry perturbation | B telemetry-on high context > A low context | C telemetry-off also high-ish; Step 5h ruled out empty/no-hit same-query perturbation; static source does not show telemetry branch changing selection | Populated paired telemetry-off/on recall probe on post-ingest LOCOMO state, if later preregistered |

## Audit answer

The current best-supported explanation is a query-expansion/context-assembly path divergence whose root is not yet pinned to a specific commit/runtime event.

Regime B shows what the current harness does when four expanded queries each return 10 results. Regime C, with telemetry off and no source difference from B, mostly follows that behavior outside adversarial rows. Regime A's low-context result is therefore the outlier relative to current harness mechanics, despite matching high-level condition metadata.

The audit cannot prove whether Regime A is wrong, nonreproducible, or produced by a different effective path. It can only say that high-level condition metadata is insufficient: future comparability gates must preserve trace-lite fields even when telemetry is off, at minimum expanded-query count, per-query result counts, candidate-before-dedupe count, candidate-after-dedupe count, and final context count.

## Stop/go

Next valid action: `go_commit_boundary_bisection_preregistration`.

The preregistered bisection should be artifact- and source-first. It should identify the narrow boundary between the low-context effective harness and the current all-expansions accumulation path, then authorize only minimal bounded execution if artifacts cannot decide.

Recommended constraints for that preregistration:

1. No Phase C intervention.
2. No full 199Q run initially.
3. No Docker/DB/runtime mutation without an explicit mutation window.
4. If execution is later authorized, use a trace-lite harness mode or wrapper that records only counts needed to classify the path:
   - expanded query count
   - per-expanded-query recall result counts
   - candidate count before dedupe
   - candidate count after dedupe
   - final context count
   - category/sample/question key
5. Include adversarial and non-adversarial fixed rows because C's split is category-specific.
6. Treat any future score as secondary; first classify the retrieval-count path.

## Phase C boundary

Phase C remains blocked.

Do not use Regime A (`14.82%`), Regime B (`58.29%`), or Regime C (`55.28%`) as a Phase C baseline until the harness/runtime drift family is adjudicated.
