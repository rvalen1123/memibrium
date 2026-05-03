# LOCOMO Context Packet Canary Mechanics Hardening — 2026-05-03

Run ID: `20260503T201307Z`
Base before slice: `4cf751d docs: analyze LOCOMO context packet canary mechanics`
Scope: same fixed 7-row conv-26 canary only; no full 199Q LOCOMO run.

## Code/harness changes

- Preserved context-packet evidence IDs in answer-context telemetry:
  - `_memory_telemetry_projection()` now uses `id` or `memory_id`.
  - Result: treatment `final_context` no longer has `id=null` for packet evidence.
- Deduplicated context-packet episodic evidence before rendering and telemetry:
  - Added `_dedupe_context_packet_episodic_evidence()`.
  - Packet prompt rendering, `n_memories`, and final-context telemetry now use deduped evidence.
  - Compact packet telemetry records both rendered evidence count and duplicate count via `deduped_episodic_evidence_count`.
- Added explicit session-order telemetry to the canary input proof:
  - `ordering=lexicographic`
  - `ingest_to_dialogue_session`
  - `dialogue_to_ingest_session`
  - note that `refs.session_index` follows lexicographic ingest order, not numeric D-session order.
- Added canary-native LOCOMO gold evidence hit telemetry:
  - Parses gold refs like `D5:1`.
  - Maps `D*` refs through the lexicographic session mapping before comparing against `refs.session_index` and `turn_start`/`turn_end`.
  - Adds hit-rate comparison to summary artifacts.

## Verification

Passed:

- `python3 docs/eval/results/run_locomo_context_packet_canary.py --identity-only`
- `python3 test_context_graph_v0.py`
- `python3 test_locomo_context_packet_canary.py`
- `python3 test_locomo_query_expansion.py`
- `python3 test_server_recall_telemetry.py`
- `python3 test_ingest_unit.py`
- `python3 -m py_compile server.py benchmark_scripts/locomo_bench_v2.py docs/eval/results/run_locomo_context_packet_canary.py test_context_graph_v0.py test_locomo_context_packet_canary.py test_locomo_query_expansion.py`
- `git diff --check`

Live server was rebuilt/restarted before rerunning the canary.

## Canary result

Artifacts:

- `docs/eval/results/locomo_context_packet_canary_baseline_20260503T201307Z.json`
- `docs/eval/results/locomo_context_packet_canary_treatment_20260503T201307Z.json`
- `docs/eval/results/locomo_context_packet_canary_summary_20260503T201307Z.json`
- `docs/eval/results/locomo_context_packet_canary_result_20260503T201307Z.md`

Gates:

- row identity: PASS, exact fixed 7 rows
- condition metadata: PASS
- context-packet telemetry: PASS
- prompt-context delta: PASS, 7/7 rows changed
- final cleanup: PASS
- packet evidence IDs: PASS, treatment `final_context` null-id count = 0/54
- dedupe telemetry: PASS, row 154 recorded 2 duplicate packet evidence items removed
- session mapping telemetry: PASS, summary records lexicographic session map
- canary-native gold-evidence telemetry: PASS, summary records hit rates

Scores are diagnostic only:

- baseline score: 3.0 / 7 = 42.86%
- context-packet treatment score: 3.0 / 7 = 42.86%

Canary-native gold evidence hit rates:

- baseline: 5 / 7 rows hit at least one gold ref = 0.7143
- treatment: 4 / 7 rows hit at least one gold ref = 0.5714
- delta: -0.1429

Per-row outcome:

| Row | Label | Baseline score | Treatment score | Baseline gold hits | Treatment gold hits | Notes |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| 153 | adversarial_split_early | 0.0 | 0.5 | 1/1 | 1/1 | Treatment partially helps despite adversarial answer target. |
| 154 | adversarial_split_late | 0.0 | 0.0 | 1/1 | 1/1 | Treatment deduped 2 duplicate packet evidence items but answer still failed. |
| 83 | unanswerable_high_context | 1.0 | 1.0 | 1/1 | 1/1 | Both arms correct. |
| 149 | unanswerable_c_low_exception | 0.0 | 0.0 | 0/1 | 0/1 | Neither arm retrieved gold evidence. |
| 34 | temporal_high_context | 0.5 | 0.0 | 1/1 | 0/1 | Treatment lost gold evidence and regressed. |
| 33 | single_hop_high_context | 0.5 | 0.5 | 2/4 | 1/4 | Treatment lower evidence coverage, same score. |
| 43 | multi_hop_high_context | 1.0 | 1.0 | 0/2 | 0/2 | Both arms correct without exact gold refs; likely semantic neighbor evidence. |

## Interpretation

The mechanics hardening worked:

- no `id=null` packet evidence remains in telemetry,
- duplicate packet evidence is removed before prompt rendering,
- the confusing LOCOMO session mapping is explicitly represented,
- row-level gold-evidence hit rates are now measurable.

But the treatment is not ready for a larger LOCOMO slice:

- treatment no longer shows a diagnostic score lift on the same fixed rows,
- treatment has lower gold-evidence hit-rate than baseline,
- temporal row 34 regressed exactly when treatment lost its gold evidence,
- self-model and graph-fact counts remain absent/zero in this canary substrate.

## Recommendation

Do not run full 199Q LOCOMO yet.

Next preregistered slice should be another mechanics-only improvement before scaling:

1. Compare raw `context_packet` episodic evidence against baseline recall for gold-hit overlap.
2. Add a packet fallback/merge canary that preserves baseline top-k evidence and appends/dedupes packet evidence, instead of replacing baseline context.
3. Keep same 7 fixed rows and require:
   - no row identity drift,
   - condition metadata correct,
   - no packet evidence IDs missing,
   - no duplicate rendered packet evidence,
   - treatment gold-hit rate not below baseline,
   - prompt delta remains source-backed.
4. Only if that passes, preregister a 20-30 row slice.
