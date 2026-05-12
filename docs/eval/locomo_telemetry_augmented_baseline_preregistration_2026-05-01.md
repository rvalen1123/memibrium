# LOCOMO telemetry-augmented hybrid-active baseline pre-registration — 2026-05-01

Repo: `/home/zaddy/src/Memibrium`  
Branch at preregistration start: `query-expansion`  
Current HEAD at preregistration start: `6c0e38f` (`docs: record LOCOMO hybrid failure-mode audit`)

## Status and dependency chain

This document pre-registers the next observational measurement step after the committed read-only failure-mode audit:

1. Hybrid mutation/rebuild window — done.
2. Canonical hybrid-active substrate baseline — done and committed.
3. Failure-mode audit — done and committed at `6c0e38f`.
4. Telemetry-augmented hybrid-active baseline — this preregistration.

This is not Phase C. It is measurement infrastructure and an observational baseline rerun intended to capture evidence missing from the first canonical hybrid-active baseline. No retrieval/scoring/output behavior may be intentionally changed by this preregistration.

## Motivation

The failure-mode audit established two firm conclusions:

1. Final-context under-retrieval / under-context is the dominant measured signature for this active hybrid configuration, at this commit and canonical substrate, on LOCOMO conv-26.
2. Some high-`n_memories` zero-score cases are evaluator/format/negative-inference artifacts rather than clear Memibrium failures.

The audit also left two key questions unresolved:

1. Whether low final context is caused by candidate-fetch starvation, threshold/fusion cutoff, or output-cap/context-transfer loss.
2. Whether adversarial `0/47` is genuine failure, evaluator/category-format mismatch, or downstream of the same under-retrieval problem affecting other categories.

The audit stop/go decision was `go_telemetry_preregistration`. This document responds to that decision without implementing any Phase C intervention.

## Hard scope

Allowed in this preregistration and its later execution window:

- Modify source code only to add behavior-preserving telemetry/instrumentation hooks.
- Add tests proving telemetry is opt-in and does not change retrieval order/count/content when disabled or enabled.
- Build/restart the server exactly under an explicitly authorized atomic mutation window.
- Run read-only health/source/env/log/probe checks needed to verify instrumentation and hybrid-active status.
- Run the same canonical no-intervention conv-26 LOCOMO baseline condition with telemetry enabled only if all gates pass.
- Write telemetry and comparison artifacts under `docs/eval/results/`.
- Clean LOCOMO rows after any LOCOMO launch and verify count `0`, as required by benchmark hygiene.

Not allowed:

- No Phase C intervention implementation.
- No retrieval parameter changes, threshold/fusion changes, top-k changes, prompt changes, judge changes, date normalization changes, rerank changes, append/gated append changes, entity-attribution guard, or evaluator correction.
- No tuning after inspecting telemetry.
- No repeated rebuild/retry loops outside the predeclared rollback/stop path.
- No benchmark launch unless the instrumentation, substrate, hybrid-active, contamination, and retrieval-shape gates all pass.

## Experiment class

Observational telemetry baseline.

The intended comparison is:

- Prior canonical hybrid-active baseline at commit `f2466c9` / committed report chain through `6c0e38f`: 14.82% 5-category, 19.41% protocol 4-category, 199 questions, query expansion fallback 0/199, mean `n_memories=4.5327`, `n=15` saturation 22/199.
- New telemetry-augmented baseline: same benchmark condition and canonical substrate, with extra traces only.

If telemetry changes retrieval shape beyond the preregistered tolerance, the telemetry run is not comparable and must be rejected as a mutated-behavior run.

## Instrumentation design to pre-register

Instrumentation should be controlled by an explicit environment/config flag, tentatively:

- `LOCOMO_RETRIEVAL_TELEMETRY=1`

When disabled, the code path must be functionally identical to the current baseline path.

Telemetry should be emitted to the benchmark result JSON rather than changing the public `/mcp/recall` response by default. If server-side introspection requires response augmentation, it must be opt-in via request field such as `include_telemetry=true`, and ordinary recall responses must remain unchanged.

### Instrumented code paths

Minimum paths to instrument:

1. `hybrid_retrieval.HybridRetriever.search()`
   - `query`
   - `top_k`
   - `fetch_k`
   - `use_rrf`
   - `rerank`
   - parsed temporal window present/absent
   - whether multi-hop logic ran
   - whether chronology sort ran

2. `hybrid_retrieval.HybridRetriever._semantic_search()`
   - requested `top_k`
   - returned count
   - candidate ids / refs / score summary
   - score min/max/mean for cosine score
   - first N candidates with id, refs, created_at, score, content hash/snippet
   - exception if any, without falling through silently in telemetry payload

3. `hybrid_retrieval.HybridRetriever._lexical_search()`
   - extracted words and tsquery string
   - whether tsvector path or ILIKE fallback path was used
   - requested `top_k`
   - returned count
   - candidate ids / refs / score summary
   - first N candidates with id, refs, created_at, score, content hash/snippet
   - exception class/message if tsvector path failed and fallback was used

4. `hybrid_retrieval.HybridRetriever._temporal_search()`
   - whether temporal search was executed
   - window start/end
   - requested `top_k`
   - returned count
   - candidate ids / refs / score summary

5. Fusion/output stage in `HybridRetriever.search()`
   - counts by stream before fusion
   - deduped candidate count before fusion if available
   - fused count before final cap
   - final returned count
   - final returned ids / refs / ranks / rrf_score and stream scores
   - cutoff ids just below final `top_k` when available
   - fallback/error flag if hybrid search raises

6. `server.handle_recall()`
   - whether hybrid retriever was present
   - embedding success/failure
   - whether legacy fallback executed
   - response result count
   - optional telemetry object returned only when requested

7. `benchmark_scripts/locomo_bench_v2.py::answer_question()`
   - expanded query strings
   - per-expanded-query recall result count
   - per-expanded-query telemetry object from server if available
   - candidate memories before dedupe
   - base_candidates count after dedupe
   - final answer-context count
   - final answer-context ids/refs/content hashes/snippets actually sent to answerer
   - whether context rerank/append/legacy modes are disabled as expected

### Telemetry content rules

Telemetry artifacts may include LOCOMO memory snippets because LOCOMO transcripts are benchmark data already present in the local dataset and result artifacts. To keep files manageable:

- Store full memory ids and refs.
- Store content SHA256 or short hash for every candidate.
- Store at most a short content snippet per candidate (e.g. 200-300 chars) unless a later audit requires full text.
- Store enough final answer-context text/snippet to determine whether gold evidence reached the answerer.
- Preserve raw counts and ranks even when snippets are truncated.

## Behavior-preservation tests before mutation

Before any server rebuild/restart, add and run unit tests proving:

1. Telemetry disabled preserves `HybridRetriever.search()` return value exactly for a deterministic fake pool.
2. Telemetry enabled preserves returned ids/order/count exactly for the same fake pool.
3. Telemetry captures semantic/lexical/temporal/fused/final counts in the expected schema.
4. Telemetry captures lexical tsvector failure/fallback path without changing returned lexical results.
5. `handle_recall` does not include telemetry unless explicitly requested.
6. `answer_question()` or its helper records telemetry without changing the final selected `memories` list.

Minimum test commands:

```bash
cd /home/zaddy/src/Memibrium
python3 -m py_compile hybrid_retrieval.py server.py benchmark_scripts/locomo_bench_v2.py
python3 -m pytest test_hybrid_retrieval_ruvector.py test_locomo_query_expansion.py -q
```

If these tests fail, stop. Do not rebuild and do not benchmark.

## Atomic mutation window A: instrumentation build/restart/probe

This window requires explicit approval before execution. It mutates source and live server image/container but must not run LOCOMO.

### Pre-mutation snapshot

Record before mutation:

- `date -Is`
- `git branch --show-current`
- `git rev-parse HEAD`
- `git status --short`
- source hashes for `server.py`, `hybrid_retrieval.py`, `benchmark_scripts/locomo_bench_v2.py`
- `curl -fsS http://localhost:9999/health`
- `docker ps --format '{{.Names}}|{{.Status}}|{{.Image}}' | grep -E 'memibrium|ruvector|ollama'`
- `docker inspect memibrium-server --format 'server_image={{.Image}} created={{.Created}} started={{.State.StartedAt}}'`
- redacted server env for DB/vector/embedding/chat/telemetry flags
- read-only LOCOMO contamination count: `SELECT count(id) FROM memories WHERE domain LIKE 'locomo-%';`
- fresh server logs, explicitly checking for hybrid fallback strings

### Build/restart once

After tests pass and approval is in scope, run exactly once:

```bash
cd /home/zaddy/src/Memibrium
docker compose -f docker-compose.ruvector.yml up -d --build memibrium
```

Wait for `/health` with bounded polling. Do not rebuild a second time in this window.

### Post-mutation proof

Record:

- post image/container IDs and started timestamp
- `/health`
- redacted server env, including telemetry flag status
- host/container source hashes for instrumented files
- source grep proving the ruvector-safe dynamic cast is still present and `$1::vector` is absent in semantic search
- read-only DB probe confirming `memories.embedding` is `USER-DEFINED:ruvector`, no `vector` type, and self-distance succeeds
- read-only LOCOMO contamination count remains `0`

### Instrumentation probe, non-LOCOMO

Run a minimal non-LOCOMO recall probe with telemetry requested against a nonexistent domain:

```bash
curl -fsS -X POST http://localhost:9999/mcp/recall \
  -H 'Content-Type: application/json' \
  -d '{"query":"hybrid telemetry ruvector smoke probe", "top_k":1, "domain":"__hybrid_telemetry_probe_no_rows__", "include_telemetry":true}'
```

Positive instrumentation evidence requires:

1. Valid response, even if empty due to nonexistent domain.
2. Telemetry object present only because `include_telemetry=true` was requested.
3. Telemetry records hybrid path attempted and no legacy fallback.
4. Fresh logs after probe do not contain `Hybrid retrieval failed` or `type "vector" does not exist`.

If any criterion fails, stop and write a blocked result. Do not benchmark.

### Rollback / clean-stop

If service health breaks or telemetry probe fails unexpectedly:

1. Capture health/log/source/env evidence.
2. Stop further mutation immediately.
3. Restore service availability with the previously known image or `docker compose -f docker-compose.ruvector.yml up -d memibrium` as appropriate.
4. Do not run LOCOMO.
5. Write a blocked mutation result artifact.

## Retrieval-shape comparability gate before telemetry baseline

Because instrumentation must not change behavior, compare a non-benchmark dry-path/probe and the eventual baseline retrieval shape against the committed baseline.

Baseline locked retrieval shape:

- `n_memories` distribution: `2:57, 3:110, 11:1, 12:3, 13:3, 14:3, 15:22`
- mean `n_memories`: `4.5327`
- `n=15` saturation: `22/199 (11.06%)`
- query expansion fallback: `0/199`

Predeclared comparability gate for the telemetry baseline result:

- Query expansion fallback must remain `0/199`.
- No hybrid fallback strings may appear during the run.
- `n_memories` support should remain in the same structural regime: mostly `n<=3` plus high-n tail, with no large new mid-bucket population introduced by instrumentation.
- Mean `n_memories` must be within ±0.25 absolute of 4.5327.
- `n=15` saturation must be within ±5 questions of 22/199.
- Per-exact-`n` counts should be within ±10 questions for the dominant `n=2` and `n=3` buckets and within ±5 questions for each high-n bucket, unless a deterministic nondeterminism note explains a smaller drift.

If these gates fail, mark the telemetry baseline as non-comparable and stop. Do not use it to select a Phase C intervention.

Important: score comparability alone is insufficient. A run with similar score but changed retrieval shape is not a valid telemetry rerun of the 14.82% baseline.

## Atomic observation window B: telemetry-augmented baseline

This window requires explicit approval before launch. It runs the same canonical no-intervention conv-26 condition with telemetry enabled.

### Pre-launch gates

All must pass:

1. Instrumentation mutation result exists and records telemetry probe pass.
2. Git status is clean except for intentional committed prereg/result artifacts.
3. `/health` is OK.
4. Live source and host source hashes match for `server.py`, `hybrid_retrieval.py`, and benchmark script.
5. Recovered-floor canonical substrate is verified:
   - server embedding path is `text-embedding-3-small`, 1536d;
   - benchmark answer/judge/query-expansion stack is `gpt-4.1-mini`;
   - no `text-embedding-3-large-1` or `grok-4-20-non-reasoning-1` in launch env/logs.
6. LOCOMO contamination count is `0` before launch.
7. Fresh logs have no hybrid fallback strings.
8. Telemetry flag/request path is enabled for benchmark capture.

If any gate fails, stop and write a blocked result.

### Locked benchmark condition

Same as the committed canonical hybrid-active substrate baseline:

- Dataset: `/tmp/locomo/data/locomo10.json`.
- Conversation: the first item, `conv-26`, using `--max-convs 1`.
- Query expansion: enabled.
- Date normalization: disabled.
- Context rerank: disabled.
- Append/gated append: disabled.
- Legacy context assembly: disabled.
- No-expansion Arm B: disabled.
- Answer model: `gpt-4.1-mini`.
- Judge model: `gpt-4.1-mini`.
- Embedding substrate: `text-embedding-3-small`, 1536d, effective inside server.
- No Phase C retrieval or synthesis intervention.

Canonical command, only after gates pass:

```bash
cd /home/zaddy/src/Memibrium
export AZURE_CHAT_ENDPOINT="https://sector-7.services.ai.azure.com/models"
export AZURE_CHAT_DEPLOYMENT="gpt-4.1-mini"
export ANSWER_MODEL="gpt-4.1-mini"
export JUDGE_MODEL="gpt-4.1-mini"
export CHAT_MODEL="gpt-4.1-mini"
export AZURE_EMBEDDING_ENDPOINT="https://sector-7.openai.azure.com/"
export AZURE_EMBEDDING_DEPLOYMENT="text-embedding-3-small"
export LOCOMO_RETRIEVAL_TELEMETRY=1
USE_QUERY_EXPANSION=1 python3 benchmark_scripts/locomo_bench_v2.py --max-convs 1 --query-expansion 2>&1 | tee /tmp/locomo_conv26_hybrid_active_telemetry_baseline_2026-05-01.log
```

If server-side embedding env is not already canonical, stop. Benchmark-side exports alone do not change server recall embeddings.

### Required output artifacts

Primary run artifacts:

- `docs/eval/results/locomo_conv26_hybrid_active_telemetry_baseline_2026-05-01.json`
- `docs/eval/results/locomo_conv26_hybrid_active_telemetry_baseline_2026-05-01.log`
- `docs/eval/results/locomo_hybrid_active_telemetry_baseline_prelaunch_2026-05-01.json`
- `docs/eval/results/locomo_hybrid_active_telemetry_baseline_comparison_2026-05-01.md`

Telemetry-specific artifacts:

- `docs/eval/results/locomo_hybrid_active_telemetry_traces_2026-05-01.jsonl`
- optional compact summary: `docs/eval/results/locomo_hybrid_active_telemetry_summary_2026-05-01.json`

Mutation/instrumentation result artifact:

- `docs/eval/results/locomo_hybrid_active_telemetry_instrumentation_result_2026-05-01.md`

### Required telemetry analyses after run

The comparison/summary must report:

1. Overall score, category scores, query expansion fallback count/rate, query latency.
2. `n_memories` distribution, mean, and saturation vs the 14.82% baseline comparability gate.
3. Per-question expanded queries and per-expanded-query recall counts.
4. Candidate counts by stream: semantic, lexical, temporal.
5. Fused candidate count before final cap.
6. Final answer-context count and refs actually sent to answerer.
7. For every question, whether each gold evidence ref appears in:
   - any semantic candidate;
   - any lexical candidate;
   - any temporal candidate;
   - fused candidates before cap;
   - final answer context.
8. For zero-score and abstention rows, classify telemetry-local cause:
   - no stream retrieved gold evidence -> candidate fetch starvation likely;
   - stream retrieved gold evidence but fused/cut before final -> threshold/fusion cutoff likely;
   - fused top candidates include gold evidence but final answer context excludes it -> output-cap/context-transfer likely;
   - final answer context includes gold evidence but answer is wrong/abstains -> evidence-present synthesis failure likely;
   - gold/evaluator issue already known -> evaluator/format artifact;
   - still insufficient -> unresolved.
9. Adversarial category-5 coverage:
   - count of adversarial rows whose gold evidence refs appear in any candidate stream;
   - count whose gold evidence refs appear in final context;
   - abstention/non-abstention breakdown by evidence coverage.

## Decision rules after telemetry baseline

- If retrieval shape is non-comparable, stop with `telemetry_baseline_rejected_noncomparable` and preregister instrumentation correction or rollback. Do not select Phase C.
- If candidate streams generally do not retrieve gold evidence, the next Phase C preregistration may target candidate fetch breadth / query expansion coverage.
- If candidate streams retrieve gold evidence but fusion/final selection drops it, the next Phase C preregistration may target threshold/fusion/output-cap/context-transfer.
- If final context contains gold evidence but answers fail, the next Phase C preregistration may target synthesis/evidence-selection/prompting, not retrieval breadth.
- If adversarial remains low even when gold evidence reaches final context, recommend category-specific adversarial/evaluator handling before general retrieval changes.
- If adversarial lacks candidate evidence just like other low-n categories, treat adversarial 0/47 as at least partly downstream of under-retrieval, not a standalone adversarial policy failure.
- If telemetry remains insufficient, output `no_go_insufficient_evidence_expand_telemetry`.

Possible stop/go outputs:

- `telemetry_baseline_rejected_noncomparable`
- `go_candidate_fetch_preregistration`
- `go_threshold_fusion_or_output_cap_preregistration`
- `go_synthesis_or_evidence_selection_preregistration`
- `go_adversarial_or_evaluator_specific_preregistration`
- `no_go_insufficient_evidence_expand_telemetry`

## Cleanup and preservation

After any LOCOMO launch:

1. Copy `/tmp` result/log/telemetry artifacts into `docs/eval/results/`.
2. Write comparison and telemetry summary artifacts.
3. Clean `locomo-%` rows and linked rows using the established cleanup process.
4. Verify cleanup with `SELECT count(id) FROM memories WHERE domain LIKE 'locomo-%';` returning `0`.
5. Commit all prereg/result artifacts.

Do not proceed to Phase C implementation until telemetry artifacts are committed and reviewed.

## Phase C boundary

This preregistration does not authorize a Phase C intervention. A future Phase C intervention preregistration must cite:

- the canonical hybrid-active baseline;
- the failure-mode audit;
- the telemetry-augmented baseline and its comparability verdict;
- the telemetry-local failure-mode recommendation.

Only then may a specific intervention family be selected and separately authorized.
