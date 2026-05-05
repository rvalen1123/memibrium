# LOCOMO Baseline + Context Packet Merge Canary — 2026-05-03

Run ID: `20260503T204932Z`
Base commit before this slice: `f6b81a1 feat: harden LOCOMO context packet canary telemetry`
Scope: same fixed 7-row `conv-26` canary only. This is not a full LOCOMO run.

## Change under test

Added a default-off `USE_CONTEXT_PACKET_MERGE` / `--context-packet-merge` benchmark condition.

Unlike packet replacement, this condition:

1. runs the normal baseline retrieval path,
2. preserves baseline answer-context evidence,
3. requests a Context Graph v0 `context_packet`,
4. appends packet episodic evidence with dedupe,
5. keeps context-packet telemetry separate from baseline retrieval telemetry.

The canary runner gained `--merge-treatment`, producing condition metadata:

- baseline: `context_packet=false`, `context_packet_merge=false`
- treatment: `context_packet=false`, `context_packet_merge=true`

## Verification

Before committing, the following passed:

- `python3 docs/eval/results/run_locomo_context_packet_canary.py --identity-only`
- `python3 test_context_graph_v0.py` — 7 tests
- `python3 test_locomo_context_packet_canary.py` — 6 tests
- `python3 test_locomo_query_expansion.py` — 62 tests
- `python3 test_server_recall_telemetry.py` — 4 tests
- `python3 test_ingest_unit.py` — 34 passed
- `python3 -m py_compile server.py benchmark_scripts/locomo_bench_v2.py docs/eval/results/run_locomo_context_packet_canary.py test_context_graph_v0.py test_locomo_context_packet_canary.py test_locomo_query_expansion.py test_server_recall_telemetry.py test_ingest_unit.py`
- `git diff --check`

The live server was rebuilt/restarted before the bounded canary. LOCOMO hygiene after the run was clean: all tracked LOCOMO tables/counts were `0`.

## Bounded canary result

Artifacts:

- baseline: `docs/eval/results/locomo_context_packet_canary_baseline_20260503T204932Z.json`
- treatment: `docs/eval/results/locomo_context_packet_canary_treatment_merge_20260503T204932Z.json`
- summary: `docs/eval/results/locomo_context_packet_canary_summary_merge_20260503T204932Z.json`
- markdown: `docs/eval/results/locomo_context_packet_canary_result_merge_20260503T204932Z.md`

Gates:

- exact row identity: PASS
- condition metadata: PASS
- prompt-context delta: PASS, 7/7 rows changed
- context-packet telemetry: PASS
- packet evidence IDs: PASS, no null IDs
- final cleanup: PASS
- gold-hit gate: PASS, treatment did not fall below baseline

Diagnostic scores:

- baseline: `50.0%`
- merge treatment: `50.0%`

Gold evidence hit rate:

- baseline: `0.7143`
- merge treatment: `0.8571`
- delta: `+0.1428`

## Per-row mechanics

| Row | Label | Baseline score | Merge score | Baseline gold hits | Merge gold hits | Packet added | Treatment memories |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 153 | adversarial_split_early | 0.0 | 0.0 | 1/1 | 1/1 | 4 | 14 |
| 154 | adversarial_split_late | 0.0 | 0.0 | 1/1 | 1/1 | 3 | 13 |
| 83 | unanswerable_high_context | 1.0 | 1.0 | 1/1 | 1/1 | 5 | 8 |
| 149 | unanswerable_c_low_exception | 0.0 | 0.0 | 0/1 | 0/1 | 4 | 14 |
| 34 | temporal_high_context | 1.0 | 1.0 | 1/1 | 1/1 | 6 | 16 |
| 33 | single_hop_high_context | 0.5 | 0.5 | 2/4 | 4/4 | 6 | 16 |
| 43 | multi_hop_high_context | 1.0 | 1.0 | 0/2 | 2/2 | 7 | 17 |

## Interpretation

The merge condition resolves the key failure from packet replacement: treatment no longer reduces gold-evidence coverage on this fixed slice. It improves gold-hit telemetry on rows 33 and 43 while preserving the same diagnostic score as baseline.

This is still not benchmark evidence. The slice has only 7 preregistered rows and should be treated as a mechanics gate only.

## Remaining concerns

1. Score did not improve despite better evidence coverage.
   - Likely prompt-size/noise or answer-model sensitivity.
   - Needs per-row answer review before scaling.

2. Treatment memory count can grow above baseline top-k.
   - Rows reached 13-17 context entries.
   - A future slice should consider a max merged context cap or packet evidence rank controls.

3. Context Graph packet still contributes episodic evidence only.
   - Self-model and graph-fact sections remain absent/empty in this LOCOMO canary.

4. Baseline context is conceptually preserved through append/dedupe, but row-level exact prefix preservation was not added as a committed canary gate. If strict baseline-prefix preservation matters for later preregistration, add this explicit gate before larger slices.

## Recommendation

Do not run full 199Q LOCOMO yet.

Next acceptable step is a slightly larger preregistered slice, not full LOCOMO:

- fixed 20-30 rows,
- same substrate,
- baseline vs `--context-packet-merge`,
- include all current gates,
- add an explicit baseline-prefix preservation gate,
- add per-row answer-change diagnostics,
- require treatment gold-hit rate >= baseline,
- stop if prompt noise causes score regressions despite higher gold-hit coverage.
