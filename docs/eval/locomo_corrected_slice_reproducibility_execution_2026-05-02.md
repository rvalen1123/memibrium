# LOCOMO corrected-slice telemetry-off reproducibility execution — Step 5j_v2_exec

Date: 2026-05-02
Branch: `query-expansion`
Start HEAD: `c9a7623839b092631abb0aa64a3cbc6704bf7267` (`c9a7623`)
Prior preregistration: `docs/eval/locomo_telemetry_off_199q_reproducibility_corrected_slice_preregistration_2026-05-02.md`

## Scope

Authorized action: execute the corrected conv-26 199Q telemetry-off reproducibility run from Step 5j_v2.

This remained measurement-substrate work. Phase C stayed blocked. No source, Docker, schema, or runtime mutation was performed before launch. The only expected benchmark side effect was LOCOMO ingest, followed by mandatory cleanup.

## Prelaunch state

- Repo: `/home/zaddy/src/Memibrium`
- Branch: `query-expansion`
- HEAD: `c9a7623839b092631abb0aa64a3cbc6704bf7267`
- Working tree: clean before launch
- Health: `{"status":"ok","engine":"memibrium"}`
- Prelaunch LOCOMO hygiene: clean
  - `memories|0`
  - `temporal_expressions|0`
  - `memory_snapshots|0`
  - `user_feedback|0`
  - `contradictions|0`
  - `memory_edges|0`

## Prelaunch slice proof

Artifact: `docs/eval/results/locomo_corrected_slice_prelaunch_proof_2026-05-02.json`

Pass conditions all true:

- `/tmp/locomo/data/locomo10.json` exists
- SHA256: `79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4`
- top-level type: `list`
- top-level conversations: `10`
- ordered sample IDs:
  - `conv-26`, `conv-30`, `conv-41`, `conv-42`, `conv-43`, `conv-44`, `conv-47`, `conv-48`, `conv-49`, `conv-50`
- index 0 sample: `conv-26`
- index 0 speakers: Caroline / Melanie
- index 0 QA count: `199`
- index 0 category counts:
  - `1`: 32
  - `2`: 37
  - `3`: 13
  - `4`: 70
  - `5`: 47
- total QA count across full file: `1986`
- `--max-convs 1` over this exact file can only select index 0 / `conv-26`

## Launch command

The run used a guarded launch controller:

`docs/eval/results/run_locomo_5j_v2_guarded.py`

Canonical command executed by the controller:

```bash
python3 benchmark_scripts/locomo_bench_v2.py --max-convs 1 --query-expansion
```

Environment assertions captured by the guard:

- `INCLUDE_RECALL_TELEMETRY` absent
- `LOCOMO_RETRIEVAL_TELEMETRY` absent
- `USE_QUERY_EXPANSION=1`
- `AZURE_EMBEDDING_DEPLOYMENT=text-embedding-3-small`
- `AZURE_CHAT_DEPLOYMENT=gpt-4.1-mini`
- `AZURE_OPENAI_DEPLOYMENT=gpt-4.1-mini`

Explicitly not used:

- `--max-convs 26`
- `--max-questions`
- `--cleaned`
- `--start-conv`
- adversarial skip
- legacy context assembly
- context rerank
- append/gated append context expansion
- no-expansion Arm B
- date normalization

## Startup guard result

Artifact: `docs/eval/results/locomo_corrected_slice_guard_summary_2026-05-02.json`

Guard status: `passed_startup_guard`

Observed required startup evidence:

- `Conversations to process: 1`
- `Total questions: 199 (199 evaluated, skipping cats set())`
- first conversation line: `[1/1] Conv conv-26: Caroline & Melanie`

Process return code: `0`

## Result validity gate

Artifact: `docs/eval/results/locomo_corrected_slice_result_validation_2026-05-02.json`

Copied raw result artifact: `docs/eval/results/locomo_corrected_slice_results_query_expansion_raw_2026-05-02.json`

Copied log artifact: `docs/eval/results/locomo_corrected_slice_reproducibility_log_2026-05-02.log`

Result validity: `valid`

Pass conditions all true:

- result JSON exists and parses
- `details` rows: exactly `199`
- `total_questions`: `199`
- unique `conv` values: only `conv-26`
- all rows are `conv-26`
- query expansion on
- telemetry absent from rows
- legacy context assembly off
- context rerank off
- append context expansion off
- gated append context expansion off
- no-expansion Arm B off
- date normalization off
- fallback count present
- `n_memories` present on all 199 rows
- startup guard passed

Fresh log error flags: all false for `Traceback`, `ERROR`, `Internal Server Error`, `TypeError`, `Decimal is not JSON serializable`, `type "vector" does not exist`, and `Hybrid retrieval failed`.

## Score and retrieval shape

Scores:

- 5-cat overall: `55.28%`
- protocol 4-cat overall: `70.07%`
- query expansion fallback: `0/199` (`0.00%`)

Category scores:

- temporal: `75.68%` over 37
- multi-hop: `38.46%` over 13
- single-hop: `68.75%` over 32
- unanswerable: `73.57%` over 70
- adversarial: `7.45%` over 47

`n_memories` summary:

- count: `199`
- mean: `11.9296`
- min: `4`
- max: `15`
- distribution:
  - `4`: 51
  - `12`: 6
  - `13`: 10
  - `14`: 12
  - `15`: 120

## Preregistered decision label

Primary label: `telemetry_off_third_regime_observed`

Rationale:

- Valid slice was proven and enforced; this was not a slice mismatch.
- Telemetry was off and query expansion was on.
- Score/retrieval shape did not reproduce the f2466c9 low-context reference:
  - reference low-context: 5-cat `14.82%`, 4-cat `19.41%`, mean `n_memories=4.5327`, `n=15: 22/199`
  - current valid run: 5-cat `55.28%`, 4-cat `70.07%`, mean `n_memories=11.9296`, `n=15: 120/199`
- It also did not reproduce the rejected 91fede6 high-context telemetry retry exactly:
  - rejected high-context: 5-cat `58.29%`, 4-cat `69.41%`, mean `n_memories=14.6231`, `n=15: 162/199`
  - current valid run: 5-cat `55.28%`, 4-cat `70.07%`, mean `n_memories=11.9296`, `n=15: 120/199`

Interpretation: the corrected, valid telemetry-off reproducibility run observed a third regime: high-ish context and high score relative to f2466c9, but materially below the rejected telemetry retry's cap saturation. This supports runtime/substrate or harness-state instability/non-reproducibility as an unresolved family. It does not unblock Phase C by itself.

## Cleanup and hygiene

Cleanup artifact: `docs/eval/results/locomo_corrected_slice_cleanup_2026-05-02.json`

Deleted linked rows:

- `memory_edges`: 417
- `contradictions`: 1
- `user_feedback`: 0
- `memory_snapshots`: 0
- `temporal_expressions`: 66
- `memories`: 49

Post-cleanup counts:

- `remaining_memories`: 0
- `remaining_temporal_expressions`: 0
- `remaining_memory_snapshots`: 0
- `remaining_user_feedback`: 0
- `remaining_contradictions`: 0
- `remaining_memory_edges`: 0

Post-cleanup health artifact: `docs/eval/results/locomo_corrected_slice_postcleanup_health_2026-05-02.json`

Health after cleanup: `{"status":"ok","engine":"memibrium"}`

## Next valid step

Phase C remains blocked.

The next step should be a preregistered harness-runtime drift audit / reproducibility-family audit before selecting interventions. The audit should explain why a valid telemetry-off corrected slice produced a third regime instead of the f2466c9 low-context baseline or the rejected telemetry retry high-context regime.

Do not treat `55.28%` as a Phase C baseline until the drift/non-reproducibility family is adjudicated.
