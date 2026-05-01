# LOCOMO no-intervention hybrid-active substrate baseline pre-registration — 2026-05-01

Repo: `/home/zaddy/src/Memibrium`
Branch: `query-expansion`
Depends on: `docs/eval/locomo_hybrid_rebuild_restart_probe_preregistration_2026-05-01.md`

## Scope

This document pre-registers a separate observational substrate baseline to be run only if the atomic rebuild/restart/probe window positively proves that live hybrid retrieval is active.

This baseline is not Phase C. It tests the substrate transition from stale legacy-recall fallback to Memibrium-as-designed hybrid retrieval with no intervention changes. Its purpose is to prevent later Phase C results from being confounded by the image/source fix.

## Gate

Do not run this baseline unless the mutation-window result document records `hybrid_active=true` with positive evidence:

- `USE_RUVECTOR=true` in the live server container.
- Live `/app/hybrid_retrieval.py` no longer hard-codes `$1::vector` in semantic search.
- Live source contains `$1::{self.vtype}` or equivalent ruvector-safe dynamic casting.
- DB has `memories.embedding` as `USER-DEFINED:ruvector`, no `vector` type, and self-distance succeeds.
- A non-LOCOMO recall probe returns successfully.
- Fresh logs after the probe do not contain `Hybrid retrieval failed` or `type "vector" does not exist`.

If any gate fails, stop; Phase C remains blocked.

## Experiment class

Observational substrate baseline, no intervention.

This run measures the current `query-expansion` branch after the rebuild/restart source-alignment fix only. It does not add retrieval telemetry, reranking, context selection, entity attribution guards, date normalization, prompt changes, judge changes, or Phase C intervention logic.

## Locked condition

Run the same calibrated conv-26/query-expansion condition used by the recovered 66.08% reference floor, but now with positive hybrid-active proof captured immediately before launch.

Condition:

- Dataset: LOCOMO `/tmp/locomo/data/locomo10.json`.
- Conversation cap: `--max-convs 26`.
- Query expansion: enabled.
- Date normalization: disabled.
- Context rerank: disabled.
- Append/gated append: disabled.
- Legacy context assembly: disabled.
- No-expansion Arm B: disabled.
- Answer/judge model stack: canonical `gpt-4.1-mini` stack as configured in env.
- Embedding substrate: active server substrate at launch; expected Azure `text-embedding-3-small`, 1536d if env is configured as in the recovered run. Capture effective identity rather than assuming.

Canonical command:

```bash
cd /home/zaddy/src/Memibrium
USE_QUERY_EXPANSION=1 python3 benchmark_scripts/locomo_bench_v2.py --max-convs 26 --query-expansion 2>&1 | tee /tmp/locomo_conv26_hybrid_active_substrate_baseline_2026-05-01.log
```

The script writes its default query-expansion output path:

`/tmp/locomo_results_query_expansion_raw.json`

Immediately copy the result and log into repo result artifacts with unique names:

- `docs/eval/results/locomo_conv26_hybrid_active_substrate_baseline_2026-05-01.json`
- `docs/eval/results/locomo_conv26_hybrid_active_substrate_baseline_2026-05-01.log`
- `docs/eval/results/locomo_hybrid_active_substrate_baseline_199q_comparison_2026-05-01.md`

## Pre-launch checks

Immediately before benchmark launch:

1. Confirm the mutation-window result exists and says `hybrid_active=true`.
2. Confirm `/health` is OK.
3. Capture effective server env/source/embedding identity:
   - redacted DB/vector/embedding/chat env from `memibrium-server`.
   - `/mcp/test_embeddings` result if available and non-mutating.
   - source hash for host/container `server.py` and `hybrid_retrieval.py`.
4. Confirm no LOCOMO contamination:
   - `SELECT count(id) FROM memories WHERE domain LIKE 'locomo-%';` must be `0` before launch.
5. Capture fresh server log tail and note whether hybrid fallback strings are absent before launch.

If contamination count is nonzero, stop and document. Cleanup is a DB mutation and must be explicitly scoped before continuing.

## Success/failure interpretation

Primary output:

- Full 5-category overall score over the conv-26 capped run.
- Category scores.
- Query-expansion fallback count/rate.
- `n_memories` distribution, mean, and `n=15` saturation.
- Avg query latency from benchmark output.
- Hybrid-active evidence immediately before and after the run.

Comparison floor:

- Recovered stale-live-path floor: 66.08% over 199 questions, query-expansion fallback 0/199, mean `n_memories` 13.1608, `n=15` saturation 31.16%.

Interpretation rules:

- If the score improves, attribute first to substrate/source alignment: legacy fallback -> actual hybrid retrieval. Do not call it Phase C improvement.
- If the score regresses, treat as measured hybrid substrate behavior; do not repair by choosing an intervention in the same window.
- If fallback strings appear during the run, mark the baseline invalid as a hybrid-active substrate baseline and stop.
- If answer/judge/API failures occur, fail closed and document; do not silently convert failures to `I don't know`.

## Post-run cleanup and preservation

After any LOCOMO launch, cleanup is mandatory:

1. Copy `/tmp` result/log artifacts into `docs/eval/results/` with the names above.
2. Create the comparison markdown with score, category table, `n_memories` distribution, fallback counts, and hybrid-active evidence.
3. Delete `locomo-%` rows and linked rows according to the repo's established cleanup script/process.
4. Verify cleanup with `SELECT count(id) FROM memories WHERE domain LIKE 'locomo-%';` returning `0`.
5. Commit all result artifacts and cleanup notes.

Do not proceed to Phase C intervention selection until this baseline result and cleanup are committed.

## Phase C gate after this baseline

Phase C unblocks only when:

1. Mutation-window result is committed and proves `hybrid_active=true`.
2. This substrate baseline result is committed.
3. LOCOMO DB cleanup is verified and recorded.
4. The next Phase C intervention is selected based on the baseline/audit evidence, not on the stale legacy-recall floor.
