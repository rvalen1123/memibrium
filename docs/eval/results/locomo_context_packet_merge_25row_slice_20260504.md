# LOCOMO Context Packet Merge 25-Row Slice — 2026-05-04

Run ID: `20260504T003835Z`
Base commit before this slice: `0d277d4 feat: add LOCOMO context packet merge canary`
Scope: preregistered 25-row slice, baseline vs `--context-packet-merge`; no full 199Q LOCOMO run.

## Preregistration

Prereg file:
`docs/eval/results/locomo_context_packet_merge_prereg_25rows_2026-05-03.json`

Selection rule:
- data source: `/tmp/locomo/data/locomo10.json`
- conversation: `conv-26`
- deterministic 25-row balanced slice
- 5 rows per category: single-hop, temporal, multi-hop, unanswerable, adversarial
- selected by stable SHA-256 ordering over `sample_id:index:question`

Selected rows:
- single-hop: 5, 24, 39, 40, 41
- temporal: 30, 55, 69, 74, 80
- multi-hop: 31, 47, 51, 70, 78
- unanswerable: 101, 113, 121, 123, 128
- adversarial: 163, 172, 183, 185, 195

Prereg gates:
- row count between 20 and 30
- exactly one sample id: `conv-26`
- unique one-based indices
- stored source data SHA-256 must match live `/tmp/locomo/data/locomo10.json`
- row identity must match source questions and categories

## Added mechanics gates

The slice runner now reports:
- `baseline_prefix_preserved_by_row`
- `baseline_prefix_preserved_rate`
- `answer_change_diagnostics`

Important implementation note:
The prefix gate now uses treatment-internal `final_context_before_packet_merge` rather than assuming the independent baseline arm retrieves byte-identical context. This is the right comparability gate for a merge intervention: it proves the treatment preserved its own pre-append baseline prefix before adding packet evidence.

## Verification

Passed before running the live slice:
- identity-only slice check with prereg row bounds
- `test_context_graph_v0.py`
- `test_locomo_context_packet_canary.py`
- `test_locomo_query_expansion.py`
- `test_server_recall_telemetry.py`
- `test_ingest_unit.py`
- target `py_compile`
- `git diff --check`

Live run hygiene:
- container rebuilt/restarted before live run
- LOCOMO cleanup before run: ok
- final LOCOMO cleanup after run: ok

## Artifacts

- `docs/eval/results/locomo_context_packet_canary_baseline_20260504T003835Z.json`
- `docs/eval/results/locomo_context_packet_canary_treatment_merge_20260504T003835Z.json`
- `docs/eval/results/locomo_context_packet_canary_summary_merge_20260504T003835Z.json`
- `docs/eval/results/locomo_context_packet_canary_result_merge_20260504T003835Z.md`

## Results

Overall score:
- baseline: `60.0%`
- merge treatment: `56.0%`
- delta: `-4.0 pp`

Category scores:
- single-hop: baseline `70.0%`, treatment `70.0%`
- temporal: baseline `90.0%`, treatment `70.0%`
- multi-hop: baseline `30.0%`, treatment `50.0%`
- unanswerable: baseline `70.0%`, treatment `80.0%`
- adversarial: baseline `40.0%`, treatment `10.0%`

Gold evidence hit rate:
- baseline: `0.7826`
- merge treatment: `0.9565`
- delta: `+0.1739`

Mechanics:
- prompt context changed: `25/25`
- baseline prefix preserved: `25/25` (`1.0`)
- answer changed: `14/25`
- no null packet evidence IDs observed
- final DB hygiene: ok

Rows with score movement:
- row 30 temporal: `1.0 -> 0.0`
- row 51 multi-hop: `0.0 -> 1.0`
- row 113 unanswerable: `0.0 -> 0.5`
- row 163 adversarial: `1.0 -> 0.5`
- row 183 adversarial: `1.0 -> 0.0`

## Interpretation

The merge intervention passed mechanics gates but failed the score-regression gate.

Evidence coverage improved substantially, and baseline-prefix preservation is now proven. However, the treatment score dropped from `60.0%` to `56.0%`, driven mainly by temporal and adversarial regressions. This indicates added packet evidence is creating prompt-noise or answer-selection instability even when gold evidence coverage improves.

This is the intended stop condition. Do not run full 199Q LOCOMO yet.

## Recommended next step

Do not scale row count.

Next should be a controlled prompt-noise ablation on this same 25-row prereg slice:
1. keep baseline-prefix merge mechanics,
2. cap appended packet evidence to a small fixed count, e.g. top 2,
3. optionally append only when packet evidence contains a new gold-ref hit or high lexical overlap,
4. keep all current gates,
5. compare against this `20260504T003835Z` uncapped merge run.

Full LOCOMO remains blocked until the treatment avoids score regression on this preregistered slice while preserving mechanics gates.
