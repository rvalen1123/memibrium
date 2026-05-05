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

Additional comparability gate discovered during the mutation window:

- The rebuilt server must use the recovered-floor substrate before this baseline launches: `text-embedding-3-small` for embeddings and `gpt-4.1-mini` for answer/judge/query-expansion.
- If the rebuilt server instead advertises `text-embedding-3-large-1`, `grok-4-20-non-reasoning-1`, or any other changed substrate, stop and pre-register a separate env-alignment mutation or redefine the baseline as a new substrate experiment before any LOCOMO launch.

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
- Answer/judge/query-expansion model stack: canonical `gpt-4.1-mini` stack; capture `ANSWER_MODEL`, `JUDGE_MODEL`, `AZURE_CHAT_DEPLOYMENT`, and endpoint immediately before launch.
- Embedding substrate: Azure `text-embedding-3-small`, 1536d, matching the recovered 66.08% floor; capture effective identity and dimensions rather than assuming.
- Current mutation-window note: after rebuild, env drifted to `text-embedding-3-large-1` and `grok-4-20-non-reasoning-1`; under this preregistration that state is **not launch-ready** for the comparable substrate baseline.

Canonical command, only after the recovered-floor substrate is verified in both server and benchmark-run env:

```bash
cd /home/zaddy/src/Memibrium
export AZURE_CHAT_ENDPOINT="https://sector-7.services.ai.azure.com/models"
export AZURE_CHAT_DEPLOYMENT="gpt-4.1-mini"
export ANSWER_MODEL="gpt-4.1-mini"
export JUDGE_MODEL="gpt-4.1-mini"
export CHAT_MODEL="gpt-4.1-mini"
export AZURE_EMBEDDING_ENDPOINT="https://sector-7.openai.azure.com/"
export AZURE_EMBEDDING_DEPLOYMENT="text-embedding-3-small"
USE_QUERY_EXPANSION=1 python3 benchmark_scripts/locomo_bench_v2.py --max-convs 26 --query-expansion 2>&1 | tee /tmp/locomo_conv26_hybrid_active_substrate_baseline_2026-05-01.log
```

If server-side embedding env is not already `text-embedding-3-small`, this command alone is insufficient because recall embeddings are generated inside `memibrium-server`; stop and align/restart server env under a separate documented mutation before launch.

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
4. Confirm recovered-floor substrate identity, not merely any working embedding/chat path:
   - server logs and `/mcp/test_embeddings` show `text-embedding-3-small`, 1536d;
   - benchmark env resolves `ANSWER_MODEL=gpt-4.1-mini` and `JUDGE_MODEL=gpt-4.1-mini`;
   - no `grok-4-20-non-reasoning-1` or `text-embedding-3-large-1` appears in launch env/logs.
5. Confirm no LOCOMO contamination:
   - `SELECT count(id) FROM memories WHERE domain LIKE 'locomo-%';` must be `0` before launch.
6. Capture fresh server log tail and note whether hybrid fallback strings are absent before launch.

If contamination count is nonzero, or if the recovered-floor substrate identity is not verified, stop and document. Cleanup/env alignment is a mutation and must be explicitly scoped before continuing.

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
