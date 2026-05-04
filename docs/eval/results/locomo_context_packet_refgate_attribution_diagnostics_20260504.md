# LOCOMO Ref-Gate Attribution Diagnostics — 2026-05-04

Run ID: `20260504T071410Z`
Base commit before this slice: `1668068 docs: analyze LOCOMO refgate adversarial failures`
Scope: same preregistered 25-row `conv-26` refgate diagnostic run; attribution diagnostics only; no full 199Q LOCOMO.

## Why this slice

The adaptive-retrieval paper (`arXiv:2604.26649`) supports selective retrieval, but the next safe Memibrium step was not a new retrieval architecture. We needed attribution first:

- distinguish rows where packet evidence was appended from rows where no packet evidence was appended;
- split score deltas by append/no-append;
- add category regression gates;
- re-check row 183 candidate behavior.

## Code change

Canary paired-artifact validation now emits:

- `packet_appended_by_row`
- `packet_append_attribution`
  - `rows_with_packet_append`
  - `rows_without_packet_append`
  - `score_delta_when_packet_appended`
  - `score_delta_when_no_packet_appended`
  - `changed_when_packet_appended`
  - `changed_when_no_packet_appended`
- `category_regression_gates`
  - per-category baseline/treatment/delta
  - severe regression flag using a 20pp threshold
  - `no_severe_category_collapse`
  - `minimum_category_delta`

Retrieval mechanics were not intentionally changed.

## Verification

Before the run:

- `python3 docs/eval/results/run_locomo_context_packet_canary.py --identity-only --fixed-rows-path docs/eval/results/locomo_context_packet_merge_prereg_25rows_2026-05-03.json --min-prereg-rows 20 --max-prereg-rows 30` — PASS
- `python3 test_context_graph_v0.py` — PASS, 7 tests
- `python3 test_locomo_context_packet_canary.py` — PASS, 9 tests
- `python3 test_locomo_query_expansion.py` — PASS, 64 tests
- `python3 test_server_recall_telemetry.py` — PASS, 4 tests
- `python3 test_ingest_unit.py` — PASS, 34 passed
- `python3 -m py_compile ...` — PASS
- `git diff --check` — PASS
- cleanup before run — PASS

After the run:

- live health: `{"status":"ok","engine":"memibrium"}`
- final LOCOMO residue: `0,0`

## Run artifacts

- Baseline: `docs/eval/results/locomo_context_packet_canary_baseline_20260504T071410Z.json`
- Treatment: `docs/eval/results/locomo_context_packet_canary_treatment_merge_refgate_20260504T071410Z.json`
- Summary: `docs/eval/results/locomo_context_packet_canary_summary_merge_refgate_20260504T071410Z.json`
- Markdown: `docs/eval/results/locomo_context_packet_canary_result_merge_refgate_20260504T071410Z.md`

## Gates

- prereg row count: PASS, 25
- exact row identity: PASS
- condition metadata: PASS
- prompt-context delta: PASS, 25/25
- baseline-prefix preservation: PASS, 25/25
- refgate telemetry: PASS
- gold-hit gate: PASS
- no severe category collapse by 20pp threshold: PASS, but minimum category delta is exactly `-20.0`
- final cleanup: PASS
- score non-regression: FAIL

## Results

Overall:

- baseline: `60.0%`
- refgate treatment: `56.0%`
- delta: `-4.0 pp`

Category:

- single-hop: `60.0 -> 70.0` (`+10.0`)
- temporal: `80.0 -> 80.0` (`0.0`)
- multi-hop: `50.0 -> 50.0` (`0.0`)
- unanswerable: `80.0 -> 60.0` (`-20.0`)
- adversarial: `30.0 -> 20.0` (`-10.0`)

Gold-hit:

- baseline: `0.6522`
- treatment: `0.7826`
- delta: `+0.1304`

## Attribution diagnostics

Packet append split:

- rows with packet append: `9`
- rows without packet append: `16`
- mean score delta when packet appended: `+0.0556`
- mean score delta when no packet appended: `-0.0938`
- changed answers when packet appended: `7`
- changed answers when no packet appended: `12`

Rows with packet append:

- `39`, `41`, `55`, `69`, `123`, `128`, `183`, `185`, `195`

Non-appended regressions:

- row `121` (`unanswerable`): `-1.0`, gold coverage `1 -> 0`
- row `163` (`adversarial`): `-0.5`, gold coverage `1 -> 1`

## Row 183 update

Earlier run `20260504T020912Z` made row 183 look like a candidate-recall miss because treatment had zero appended packet evidence and gold coverage dropped. This diagnostic rerun changed that picture:

- row `183` now appended one ref-gated packet memory;
- treatment gold coverage stayed `1/1`;
- treatment still regressed `1.0 -> 0.0`.

Appended packet memory:

- id: `mem_c0aa385e507f`
- refs: `session_index=6`, `turn_start=20`, `turn_end=29`
- snippet: `Caroline: Thanks, Mel! Glad you like it. It's a symbol of togetherness, to celebrate differences...`

Prediction movement:

- baseline: `Melanie found a cool rainbow sidewalk for Pride Month...`
- treatment: `Melanie did not find anything ... it was Caroline who found a cool rainbow sidewalk...`

Interpretation: row 183 is not purely candidate recall. It is a role/attribution confusion induced or amplified by appended gold-near context. The appended memory is evidence-bearing but appears to steer answer attribution toward Caroline rather than Melanie.

## Conclusion

This diagnostic run strengthens the blocker:

- Refgate remains useful for evidence coverage.
- Score behavior is unstable across runs and not yet attributable cleanly to added evidence alone.
- Appended evidence has positive mean effect, but no-append rows still regress, which means paired A/B retrieval/judge drift remains a confound.
- Row 183 is an attribution/role-confusion case, not just a candidate recall miss.

Full 199Q remains blocked.

## Next safe step

Do not scale row count yet.

Next should be either:

1. freeze baseline final context and run treatment as a replay/transform against the same context to remove paired retrieval drift; or
2. add role-aware evidence formatting for ref-gated appended packet memories and test only on the same 25-row slice.

Preferred next: frozen-context replay, because it isolates treatment mechanics before adding more model-facing prompt changes.
