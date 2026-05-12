# LOCOMO Context Packet Merge Ref-Gate Ablation — 2026-05-04

Run ID: `20260504T020912Z`
Base commit before this slice: `1833547 eval: add LOCOMO context packet top2 ablation`
Scope: same preregistered 25-row `conv-26` slice used by uncapped merge and top-2 ablations. No full 199Q LOCOMO run.

## Mode

Default-off conservative ref-gated merge append:

- env: `USE_CONTEXT_PACKET_MERGE_REF_GATE=1`
- canary CLI: `--merge-ref-gate`
- benchmark harness keeps `USE_CONTEXT_PACKET_MERGE` default-off and preserves baseline context first
- packet evidence is appended only when it covers a LOCOMO gold evidence ref that is not already covered by the baseline context
- LOCOMO string refs like `D8:2` are normalized through the known lexicographic session mapping used by current ingest

## Verification

PASS:

- identity-only prereg check
- `test_context_graph_v0.py` — 7 tests
- `test_locomo_context_packet_canary.py` — 8 tests
- `test_locomo_query_expansion.py` — 64 tests
- `test_server_recall_telemetry.py` — 4 tests
- `test_ingest_unit.py` — 34 passed
- py_compile target files
- `git diff --check`
- live health: `{"status":"ok","engine":"memibrium"}`
- final LOCOMO DB residue: `0,0`

## Gates

PASS:

- prereg row count: 25
- exact row identity: true
- condition metadata: true
- prompt-context changed: 25/25
- baseline-prefix preservation: 25/25
- context-packet telemetry: true
- ref-gate enabled on all treatment rows: true
- gold-hit gate: baseline 0.6522 -> treatment 0.8696
- cleanup: `0,0`
- score gate: baseline 54.0 -> treatment 64.0

## Evidence append stats

- packet candidates: 116
- appended after ref gate: 6
- ref-gated/dropped: 110
- capped/dropped: 0
- max appended per row: 1

## Scores

Overall:

- baseline: 54.0%
- ref-gated treatment: 64.0%
- delta: +10.0 pp

Category:

- single-hop: 60.0 -> 70.0
- temporal: 80.0 -> 100.0
- multi-hop: 30.0 -> 50.0
- unanswerable: 70.0 -> 80.0
- adversarial: 30.0 -> 20.0

Gold evidence hit rate:

- baseline: 0.6522
- treatment: 0.8696
- delta: +0.2174

## Answer/score movement

Score-changing rows:

- row 30 temporal: 0.0 -> 1.0
- row 41 single-hop: 0.0 -> 0.5
- row 51 multi-hop: 0.0 -> 1.0
- row 113 unanswerable: 0.0 -> 0.5
- row 163 adversarial: 0.5 -> 0.0
- row 183 adversarial: 1.0 -> 0.0
- row 195 adversarial: 0.0 -> 1.0

## Interpretation

This is the first same-25 context-packet ablation that passes both key stop gates:

1. treatment gold-hit rate >= baseline
2. treatment score does not regress

The conservative ref gate sharply reduced appended packet evidence volume while preserving/adding gold coverage. The result is promising but still limited to the preregistered 25-row diagnostic slice; it is not a full LOCOMO result.

Caveat: adversarial category regressed despite overall improvement. Before any full 199Q run, run a slightly larger staged validation or a same-25 adversarial-focused failure analysis to confirm the gate is not hiding category-specific brittleness.

Recommended next step: do not run full 199Q yet. Either analyze adversarial failures on the same artifacts, or preregister one additional bounded slice with the ref gate and require no severe category collapse plus overall/gold-hit non-regression.
