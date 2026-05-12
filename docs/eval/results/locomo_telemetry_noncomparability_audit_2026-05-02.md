# LOCOMO telemetry noncomparability audit — 2026-05-02

## Verdict

`artifact_insufficient_requires_paired_recall_probe`

Secondary labels:

- `artifact_supports_analysis_or_effective_runtime_mismatch`
- `artifact_does_not_support_static_telemetry_path_perturbation`
- `artifact_does_not_support_simple_flag_mismatch`
- `phase_c_still_blocked`

## Executive interpretation

The artifact-only audit confirms that Step 5d's telemetry-enabled retry was a real high-context run, but does not prove it is comparable to the locked telemetry-off f2466c9 baseline.

The retry's high `n_memories` is mechanically explained by the benchmark-side context assembly visible in the telemetry traces: every question used four expanded queries; every per-query recall returned 10 results; the benchmark accumulated all expanded-query candidates under `USE_QUERY_EXPANSION=true`; every question therefore had exactly 40 pre-dedupe candidates; and 162/199 questions hit the final answer-context cap of 15.

Static source reading does not show `include_telemetry=true` changing server retrieval parameters, hybrid search SQL, RRF fusion, top-k/cap behavior, or benchmark answer-context selection. That weakens, but does not falsify, the telemetry-perturbation hypothesis because no committed artifact directly compares same-query telemetry-on and telemetry-off `/mcp/recall` result IDs.

The strongest artifact-level anomaly is instead that the locked f2466c9 baseline reports the same high-level benchmark condition metadata (`query_expansion=True`, `legacy_context_assembly=False`) yet produced a low-context shape. That is consistent with an effective harness/runtime/artifact mismatch or nonreproducibility, but the audit cannot adjudicate it without a controlled paired flag probe and possibly a later telemetry-off reproducibility rerun.

Phase C remains blocked.

## Scope and boundary

Authorized scope: read committed artifacts and source, write audit artifacts, commit.  
Not authorized and not performed: live recall probes, benchmark reruns, DB writes/cleanup, Docker/env/source/schema mutations, Phase C intervention selection.

Repo: `/home/zaddy/src/Memibrium`  
Branch: `query-expansion`  
Audit prereg commit: `faaa661`  
Prior retry commit: `91fede6`

## Required input integrity

Required JSON/log/markdown artifacts were present and parseable for the locked baseline, telemetry retry, retry traces, retry summary, noncomparable verdict, mutation-window smoke/probe outputs, and blocked attempt evidence.

Question alignment between locked baseline and retry was established by row order and exact question text for all 199 questions.

Condition metadata:

- Locked baseline condition: `{'append_context_expansion': False, 'cleaned': False, 'context_rerank': False, 'gated_append_context_expansion': False, 'legacy_context_assembly': False, 'no_expansion_arm_b': False, 'normalize_dates': False, 'query_expansion': True}`
- Retry condition: `{'append_context_expansion': False, 'cleaned': False, 'context_rerank': False, 'gated_append_context_expansion': False, 'legacy_context_assembly': False, 'no_expansion_arm_b': False, 'normalize_dates': False, 'query_expansion': True}`
- Baseline score metrics: `{'avg_query_ms': 2478, 'expand_query_fallback_count': 0, 'expand_query_fallback_rate': 0.0, 'full_5cat_overall': 14.82, 'overall_score': 14.82, 'protocol_4cat_overall': 19.41, 'total_questions': 199}`
- Retry score metrics: `{'avg_query_ms': 3272, 'expand_query_fallback_count': 0, 'expand_query_fallback_rate': 0.0, 'full_5cat_overall': 58.29, 'overall_score': 58.29, 'protocol_4cat_overall': 69.41, 'total_questions': 199}`

Flag-name note: prereg prose used `LOCOMO_RETRIEVAL_TELEMETRY`, but the benchmark code-effective flag is `INCLUDE_RECALL_TELEMETRY`. Retry prelaunch explicitly set `INCLUDE_RECALL_TELEMETRY=1`, blocked attempt evidence recorded `include_recall_telemetry=True`, and source probes confirmed `bench_include_recall_telemetry_present=True`. This is documentation naming drift, not evidence of a failed telemetry launch.

## Side-by-side retrieval-shape comparison

| Metric | Locked f2466c9 baseline | 91fede6 telemetry retry | Delta |
|---|---:|---:|---:|
| Mean `n_memories` | 4.5327 | 14.6231 | 10.0905 |
| Median delta `n_memories` | — | — | 12 |
| `n_memories == 15` | 22/199 | 162/199 | +140 |
| Retry `n_memories >= 11` | — | 199/199 | — |
| Baseline `n<=3` and retry `n>=11` | — | — | 167/199 |

Baseline exact-`n` distribution: `{'11': 1, '12': 3, '13': 3, '14': 3, '15': 22, '2': 57, '3': 110}`  
Retry exact-`n` distribution: `{'11': 3, '12': 6, '13': 17, '14': 11, '15': 162}`  
Delta distribution: `{'-1': 2, '-3': 1, '0': 20, '1': 5, '10': 10, '11': 10, '12': 92, '13': 48, '2': 2, '3': 2, '8': 3, '9': 4}`

Score shifts:

- Improved: 106/199
- Worsened: 2/199
- Unchanged: 91/199
- Mean score delta: 0.4347
- Median score delta: 0.5000

Category-level shifts:

| Category | N | Baseline mean n | Retry mean n | Mean delta n | Baseline score | Retry score | Mean score delta |
|---|---:|---:|---:|---:|---:|---:|---:|
| adversarial | 47 | 2.62 | 14.68 | 12.06 | 0.0% | 22.3% | 22.3 pp |
| multi-hop | 13 | 7.23 | 14.54 | 7.31 | 30.8% | 42.3% | 11.5 pp |
| single-hop | 32 | 6.22 | 14.69 | 8.47 | 26.6% | 64.1% | 37.5 pp |
| temporal | 37 | 8.14 | 14.41 | 6.27 | 39.2% | 68.9% | 29.7 pp |
| unanswerable | 70 | 2.64 | 14.69 | 12.04 | 3.6% | 77.1% | 73.6 pp |

Top 20 largest `delta_n_memories` rows:

| Index | Category | Base n | Retry n | Delta n | Score | Question |
|---:|---|---:|---:|---:|---|---|
| 53 | single-hop | 2 | 15 | 13 | 0.0→1.0 | What are Melanie's pets' names? |
| 62 | single-hop | 2 | 15 | 13 | 0.0→1.0 | What musical artists/bands has Melanie seen? |
| 65 | multi-hop | 2 | 15 | 13 | 0.0→1.0 | Would Melanie likely enjoy the song "The Four Seasons" by Vivaldi? |
| 69 | temporal | 2 | 15 | 13 | 0.0→1.0 | How long has Melanie been practicing art? |
| 74 | temporal | 2 | 15 | 13 | 0.0→1.0 | When did Melanie get hurt? |
| 84 | unanswerable | 2 | 15 | 13 | 0.0→1.0 | What did Melanie realize after the charity race? |
| 99 | unanswerable | 2 | 15 | 13 | 0.0→1.0 | What was discussed in the LGBTQ+ counseling workshop? |
| 104 | unanswerable | 2 | 15 | 13 | 0.0→1.0 | What was Melanie's favorite book from her childhood? |
| 107 | unanswerable | 2 | 15 | 13 | 0.0→1.0 | What are the new shoes that Melanie got used for? |
| 108 | unanswerable | 2 | 15 | 13 | 0.0→1.0 | What is Melanie's reason for getting into running? |
| 120 | unanswerable | 2 | 15 | 13 | 0.0→1.0 | How did Melanie feel while watching the meteor shower? |
| 122 | unanswerable | 2 | 15 | 13 | 0.0→1.0 | Who performed at the concert at Melanie's daughter's birthday? |
| 125 | unanswerable | 2 | 15 | 13 | 0.0→1.0 | What pets does Melanie have? |
| 126 | unanswerable | 2 | 15 | 13 | 0.0→1.0 | Where did Oliver hide his bone once? |
| 131 | unanswerable | 2 | 15 | 13 | 0.0→1.0 | Which  classical musicians does Melanie enjoy listening to? |
| 132 | unanswerable | 2 | 15 | 13 | 0.0→1.0 | Who is Melanie a fan of in terms of modern music? |
| 145 | unanswerable | 2 | 15 | 13 | 0.0→1.0 | How did Melanie's son handle the accident? |
| 149 | unanswerable | 2 | 15 | 13 | 0.0→1.0 | What was Melanie's reaction to her children enjoying the Grand Canyon? |
| 151 | unanswerable | 2 | 15 | 13 | 0.0→1.0 | How did Melanie feel about her family supporting her? |
| 155 | adversarial | 2 | 15 | 13 | 0.0→1.0 | What type of individuals does the adoption agency Melanie is considering support? |

Full per-question table:
`docs/eval/results/locomo_telemetry_noncomparability_audit_per_question_2026-05-02.json`

## Telemetry-trace structural audit

Retry trace coverage: 199/199.

Key structural facts:

- Expanded query count distribution: `{'4': 199}`
- Per-query recall calls total: 796
- Per-query result-count distribution: `{'10': 796}`
- Per-query calls returning exactly 10 results: 796/796
- Candidate memories before dedupe distribution: `{'40': 199}`
- Base/candidate count after dedupe distribution: `{'11': 3, '12': 6, '13': 17, '14': 11, '15': 16, '16': 22, '17': 16, '18': 30, '19': 13, '20': 18, '21': 8, '22': 20, '23': 8, '24': 4, '25': 4, '26': 2, '28': 1}`
- Final answer-context count distribution: `{'11': 3, '12': 6, '13': 17, '14': 11, '15': 162}`
- Final answer-context cap hits (`15`): 162/199

Server-side stream facts across 796 per-query recall calls:

- Semantic returned-count distribution: `{'0': 32, '11': 1, '12': 1, '17': 1, '18': 1, '20': 760}`
- Lexical returned-count distribution: `{'12': 1, '15': 1, '16': 1, '17': 1, '18': 3, '2': 1, '20': 780, '3': 2, '6': 3, '7': 3}`
- Temporal returned-count distribution: `{'0': 790, '3': 6}`
- Fused-before-cap distribution: `{'15': 1, '16': 2, '17': 1, '18': 3, '19': 1, '20': 33, '23': 2, '24': 4, '25': 19, '26': 59, '27': 119, '28': 162, '29': 153, '30': 109, '31': 70, '32': 43, '33': 9, '34': 6}`
- Server final returned-count distribution: `{'10': 796}`
- Server cutoff-count distribution: `{'5': 796}`

Interpretation: high final context in the retry is not caused by a single server recall returning >10. It is caused by benchmark-side accumulation across four expanded queries. The server recall layer generally returned capped top-10 results per expanded query; the benchmark then deduped and selected up to 15 final memories.

Telemetry schema was sufficient to distinguish expanded-query count, per-query result counts, candidate-before/after-dedupe, final answer-context count, and server stream counts. It was not sufficient to compare telemetry-off result IDs for the same query because no paired telemetry-off trace exists.

## Static telemetry-path perturbation audit

| Suspect mechanism | Static verdict | Evidence for | Evidence against |
|---|---|---|---|
| Server include_telemetry changes retrieval parameters or branch selection | not_supported_by_static_source | None | server.py handle_recall passes the same query, embedding, top_k, state_filter, and domain to hybrid_retriever.search; include_telemetry is only an additional boolean argument (server.py:1901-1908).; Non-telemetry response returns search_result directly; telemetry response unwraps (result, telemetry) then serializes {'results': result, 'telemetry': ...} (server.py:1909-1963). |
| HybridRetriever include_telemetry changes SQL top_k/fetch_k, fusion, cutoff, or return count | not_supported_by_static_source | None | hybrid_retrieval.py computes fetch_k=top_k*2 unconditionally before telemetry allocation (lines 707-708).; semantic, lexical, temporal searches receive same fetch_k/state/domain regardless of telemetry; telemetry only records stream projections after result lists are materialized (lines 713-727).; RRF fusion, optional rerank, multihop, chronology sorting, and final_results=final[:top_k] are outside telemetry conditionals except for recording telemetry (lines 750-805). |
| Telemetry construction mutates returned result objects or consumes shared iterators | unlikely_static_mechanism | _normalize_scores mutates score fields in result dicts before telemetry and final return, but this happens regardless of telemetry and predates telemetry instrumentation. | Telemetry projection creates new dicts and reads fields; it does not alter memory dictionaries (hybrid_retrieval.py:384-404).; _stream_telemetry and _record_final_telemetry enumerate lists and project items; they do not pop/sort/filter returned lists (hybrid_retrieval.py:418-464). |
| Benchmark INCLUDE_RECALL_TELEMETRY changes answer-context assembly | not_supported_by_static_source | When INCLUDE_RECALL_TELEMETRY is true, benchmark calls answer_question(..., return_telemetry=True, evidence_refs=...) and stores recall_telemetry in each result row (locomo_bench_v2.py:1151-1178). | answer_question always builds recall_telemetry locally, independent of return_telemetry; return_telemetry only changes the function's return tuple at the end (lines 674-683, 816-818).; recall_for_query adds payload['include_telemetry']=True only when INCLUDE_RECALL_TELEMETRY is true, then _extract_recall_payload extracts the same results list from either a list response or {'results': ...} response (lines 685-703, 548-551).; Context assembly loops over the recalled list returned by recall_for_query; there is no conditional branch on return_telemetry or INCLUDE_RECALL_TELEMETRY in dedupe/candidate/final selection (lines 705-765). |
| Query expansion plus current non-legacy assembly explains high context counts independently of telemetry | mechanism_explains_retry_shape_not_divergence | With USE_QUERY_EXPANSION=true, the non-legacy assembly loops over all expanded queries and only breaks early if NOT USE_QUERY_EXPANSION (locomo_bench_v2.py:729-737).; Telemetry traces show every question used 4 expanded queries, every per-query recall returned 10 memories, candidate_memories_before_dedupe was exactly 40 for all 199 questions, and final context hit cap 15 for 162/199.; This mechanism directly matches the retry high-context shape. | The locked baseline artifact reports the same condition metadata: query_expansion=True and legacy_context_assembly=False, yet its n_memories distribution is low-context. Therefore this source-level mechanism cannot by itself explain baseline-vs-retry divergence without an additional runtime/artifact/source-version difference. |
| Effective flag-name mismatch caused unintended telemetry state | documentation_alias_drift_not_condition_mismatch | Prereg text used LOCOMO_RETRIEVAL_TELEMETRY, while benchmark code-effective flag is INCLUDE_RECALL_TELEMETRY. | Retry prelaunch benchmark env explicitly set INCLUDE_RECALL_TELEMETRY=1; blocked attempt benchmark_condition also recorded include_recall_telemetry=True; benchmark source probe confirmed bench_include_recall_telemetry_present=True.; This is documentation naming drift, not evidence of failed telemetry activation. |
| Baseline artifact was produced by a different effective benchmark code/context assembly than its condition metadata indicates | plausible_artifact_or_effective_runtime_mismatch_requires_disambiguation | The baseline low-context distribution is consistent with early-break/legacy-style assembly over expanded queries: many rows at n=2 or n=3 rather than cap 15.; The current source with query_expansion=True and legacy_context_assembly=False should collect candidates from all four expanded queries and usually fill 15, as the retry traces demonstrate. | Baseline prelaunch reported source/hash/substrate checks and condition metadata matching canonical stack, and no direct baseline telemetry traces exist to prove its internal assembly path.; Artifact-only audit cannot inspect live f2466c9-era effective benchmark function behavior during that exact run beyond committed metadata. |

Static source conclusion: there is no obvious behavior-changing telemetry bug in the server or hybrid retriever source. The retry's high-context shape is better explained by current benchmark context assembly over four expanded queries. However, static reading cannot replace a direct same-query paired flag probe.

## Blocked attempt comparison

The original telemetry attempt at `876eb04` is informative but incomplete:

- Blocked verdict: `telemetry_baseline_blocked_runtime_serialization_error`
- Last progress marker from blocked evidence: `{'completed': 120, 'running_accuracy_percent': 72.1, 'total': 199}`
- Placeholder main result has no details rows.
- Placeholder telemetry traces contain no traces.
- Run log does not include per-question `n_memories` or detailed running score rows.

The blocked attempt's running accuracy at 120/199 was high enough to suggest it may already have been in the high-context telemetry-on regime, but artifacts are insufficient to prove the retrieval shape for those 120 questions. This is a limitation, not a basis for causal inference.

## Audit answer to the preregistered interpretations

1. Telemetry path perturbation: not supported by static source, but not falsified by artifacts because there is no paired same-query telemetry-on/off result-ID comparison.
2. Hybrid-active nondeterminism / baseline nonreproducibility: plausible but not proven. The low-context f2466c9 baseline conflicts with current-source expectations under the same high-level condition metadata.
3. Launch/env/flag mismatch: no evidence of substrate mismatch or failed telemetry activation. The `LOCOMO_RETRIEVAL_TELEMETRY` vs `INCLUDE_RECALL_TELEMETRY` discrepancy is a naming/documentation drift, not an effective launch mismatch.
4. Analysis artifact mismatch: plausible as an effective-harness/source/runtime mismatch class, specifically because baseline condition metadata says non-legacy query expansion while its `n_memories` shape resembles early-break/low-context behavior.

## Next evidence requirement

`go_paired_telemetry_flag_probe_preregistration`

Rationale: The cheapest decisive next step is a controlled paired flag probe, not a full 199Q rerun. It should compare the same fixed queries against the same live state with `include_telemetry=false` versus `include_telemetry=true`, recording result IDs/order/counts and response payload shape. This directly tests the remaining telemetry-perturbation hypothesis.

If paired probe shows telemetry-on/off identical result IDs/counts, then telemetry perturbation is effectively ruled out and the next prereg should target telemetry-off 199Q reproducibility or effective benchmark-harness/runtime drift. If paired probe shows divergence, then a telemetry behavior-fix preregistration is required before any telemetry-based baseline can be used.

## Phase C boundary

Phase C remains blocked. Do not use the 58.29% / 69.41% retry as comparable to the 14.82% / 19.41% baseline. Do not select a candidate-fetch, threshold/fusion, output-cap, synthesis, schema, evaluator, or temporal/entity intervention from this audit.

## Output artifacts

- Primary report: `docs/eval/results/locomo_telemetry_noncomparability_audit_2026-05-02.md`
- Structured labels: `docs/eval/results/locomo_telemetry_noncomparability_audit_labels_2026-05-02.json`
- Per-question/support table: `docs/eval/results/locomo_telemetry_noncomparability_audit_per_question_2026-05-02.json`
- Support summary: `docs/eval/results/locomo_telemetry_noncomparability_audit_support_2026-05-02.json`
