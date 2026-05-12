# LOCOMO legacy-context diagnostic smoke comparison — 2026-04-30

## Purpose

Diagnostic probe after the locked canonical-stack 199Q reproduction failed (62.06% vs 68.09%, 0 fallback). This run tests whether restoring bfeb90f-era query-expansion context assembly is a plausible code-drift explanation.

This does **not** revise the locked canonical-stack reproduction verdict.

## Run identity

- Commit: `ebd4c9cee714872ddaf22b75f37eff3f9d4bc0ac`
- Dirty files at run launch: ` M benchmark_scripts/locomo_bench_v2.py;  M test_locomo_query_expansion.py; ?? docs/eval/results/locomo_conv26_legacy_context_smoke_10q_2026-04-30.json; ?? docs/eval/results/locomo_conv26_legacy_context_smoke_10q_2026-04-30.log`
- Stack: Azure Foundry `https://sector-7.services.ai.azure.com/models`, `gpt-4.1-mini` for answer/judge/query expansion, temperature `0`
- Flags: `--cleaned --normalize-dates --query-expansion --legacy-context-assembly --max-convs 1 --max-questions 10`
- Output: `docs/eval/results/locomo_conv26_legacy_context_smoke_10q_2026-04-30.json`
- Log: `docs/eval/results/locomo_conv26_legacy_context_smoke_10q_2026-04-30.log`

## Pre-run hygiene

- Docker/server: memibrium-server, memibrium-ruvector-db, memibrium-ollama up; server/db healthy
- Server toggles: `ENABLE_BACKGROUND_SCORING=false`, `ENABLE_CONTRADICTION_DETECTION=false`, `ENABLE_HIERARCHY_PROCESSING=false`
- LOCOMO DB before: `0`
- Tests: `72 OK` (`test_locomo_query_expansion`, `test_hybrid_retrieval_ruvector`, `test_temporal_memory`)

## Smoke result

| Run | Questions | Score | Fallback | Avg query ms |
|---|---:|---:|---:|---:|
| Current canonical 10Q smoke | 10 | 80.0% | 0/10 | 3634 |
| Legacy-context 10Q smoke | 10 | 85.0% | 0/10 | 4404 |
| Failed canonical full 199Q | 199 | 62.06% | 0/199 | 4212 |
| 04-24 reference full 199Q | 199 | 68.09% | 0/199 | 8026 |

Category scores, legacy smoke: `{'cat-temporal': 100.0, 'cat-multi-hop': 100.0, 'cat-single-hop': 50.0}`

## Paired 10Q overlap vs current canonical smoke

- Common questions: `10`
- Rescued: `1`
- Harmed: `0`

Changed questions:

- multi-hop: delta `0.5` — What fields would Caroline be likely to pursue in her educaton?
  - canonical: `0.5` / Caroline is likely to pursue education in counseling or mental health.
  - legacy: `1.0` / Caroline is likely to pursue education in counseling and mental health, focusing on working with transgender people and supporting their mental health.
  - gold: Psychology, counseling certification

## Interpretation

Legacy-context assembly improved the 10Q smoke from `80.0%` to `85.0%` with `0` query-expansion fallbacks. This is directionally positive but too small to establish the full 199Q baseline.

Conclusion: legacy query-expansion context assembly is a plausible code-drift candidate. The appropriate next step, if approved, is a full 199Q forced-canonical diagnostic run with `--legacy-context-assembly`. Keep this separate from A/B/C intervention work and do not change the locked verdict for the canonical-stack reproduction.

## Cleanup

- LOCOMO DB after cleanup: `0`
