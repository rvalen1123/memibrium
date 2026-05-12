# LOCOMO Context Packet Merge Top-2 Ablation — 2026-05-04

Run ID: `20260504T010218Z`
Base commit before this slice: `43b7ebc eval: preregister LOCOMO context packet merge slice`
Scope: same preregistered 25-row `conv-26` slice as uncapped merge run `20260504T003835Z`; no full 199Q run.

## Intervention

Added a default-off prompt-noise ablation for merge mode:

- env: `CONTEXT_PACKET_MERGE_APPEND_TOP_K=2`
- canary CLI: `--merge-append-top-k 2`
- benchmark CLI: `--context-packet-merge-append-top-k 2`

The treatment still preserves baseline retrieval context, but appends at most the first 2 deduped packet episodic memories.

## Verification

- `python3 docs/eval/results/run_locomo_context_packet_canary.py --identity-only --fixed-rows-path docs/eval/results/locomo_context_packet_merge_prereg_25rows_2026-05-03.json --min-prereg-rows 20 --max-prereg-rows 30` — PASS
- `python3 test_context_graph_v0.py` — PASS, 7 tests
- `python3 test_locomo_context_packet_canary.py` — PASS, 8 tests
- `python3 test_locomo_query_expansion.py` — PASS, 63 tests
- `python3 test_server_recall_telemetry.py` — PASS, 4 tests
- `python3 test_ingest_unit.py` — PASS, 34 passed
- `python3 -m py_compile ...` — PASS
- `git diff --check` — PASS
- live `/health` — `{"status":"ok","engine":"memibrium"}`
- final LOCOMO DB residue — `0,0`

## Gates

- prereg row count: PASS, 25 rows
- exact row identity: PASS
- condition metadata: PASS
- prompt-context delta: PASS, 25/25
- baseline-prefix preservation: PASS, 25/25
- packet append cap: PASS, max appended per row = 2
- context-packet telemetry: PASS
- final cleanup: PASS
- gold-hit gate: FAIL, treatment below baseline

Packet cap stats:

- packet candidate evidence total: 106
- packet appended evidence total: 50
- packet capped/dropped evidence total: 56
- min appended per row: 2
- max appended per row: 2

## Results

Top-2 merge run `20260504T010218Z`:

- baseline overall: 64.0%
- treatment overall: 60.0%
- delta: -4.0 pp

Category scores:

| Category | Baseline | Top-2 Treatment |
|---|---:|---:|
| single-hop | 70.0% | 70.0% |
| temporal | 100.0% | 70.0% |
| multi-hop | 30.0% | 50.0% |
| unanswerable | 70.0% | 60.0% |
| adversarial | 50.0% | 50.0% |

Gold evidence hit rate:

- baseline: 0.8261
- top-2 treatment: 0.6957
- delta: -0.1304

Score movements vs same-run baseline:

- temporal: -0.5
- single-hop: +0.5
- single-hop: -0.5
- multi-hop: +1.0
- temporal: -1.0
- unanswerable: +0.5
- unanswerable: -1.0

## Comparison to uncapped merge run

Uncapped merge run `20260504T003835Z`:

- baseline overall: 60.0%
- treatment overall: 56.0%
- delta: -4.0 pp
- gold hit rate: baseline 0.7826, treatment 0.9565, delta +0.1739
- baseline-prefix preservation: 25/25

Top-2 ablation preserved the same overall score delta (-4 pp), but flipped gold-evidence coverage negative. It reduced adversarial damage compared with uncapped merge but worsened temporal rows and did not solve prompt/answer instability.

## Interpretation

This ablation does not pass. Capping appended packet evidence to top 2 reduces prompt noise volume but also discards useful evidence. The evidence mechanism is not reliable enough to scale.

Full 199Q LOCOMO remains blocked.

## Recommended next step

Do not increase row count. Do not run full LOCOMO.

Next ablation should use evidence gating instead of a blind cap on the same 25-row slice:

- append packet evidence only if it is not already in baseline and improves/refines gold-ref coverage, or
- overlap-gate packet evidence against the question and expected evidence refs, while preserving baseline prefix.

Gate any next ablation on:

- treatment gold-hit rate >= baseline,
- no score regression on the 25-row slice,
- baseline-prefix preservation 25/25,
- prompt-context delta recorded,
- cleanup 0,0.
