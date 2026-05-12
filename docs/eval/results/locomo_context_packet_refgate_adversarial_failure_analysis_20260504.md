# LOCOMO Ref-Gate Adversarial Failure Analysis — 2026-05-04

Source run: `20260504T020912Z`
Commit under analysis: `7f094b9 eval: add LOCOMO context packet refgate ablation`
Scope: same preregistered 25-row `conv-26` slice, adversarial category only. No new benchmark run.

## Why this analysis exists

The ref-gated context-packet merge was the first same-25 ablation to pass the major gates:

- baseline 54.0 -> treatment 64.0
- gold-hit 0.6522 -> 0.8696
- packet candidates 116, appended 6, ref-gated/dropped 110
- prefix preservation 25/25
- cleanup 0,0

But adversarial regressed:

- adversarial: 30.0 -> 20.0

This report inspects the five adversarial rows in the same artifact before any larger run.

## Adversarial rows

| Row | Question | Gold adversarial answer | Baseline score | Refgate score | Gold ref coverage baseline -> treatment | Packet appended |
| --- | --- | --- | ---: | ---: | --- | ---: |
| 163 | What did Caroline and her family do while camping? | explored nature, roasted marshmallows, and went on a hike | 0.5 | 0.0 | 1/1 -> 1/1 | 0 |
| 172 | What did Melanie see at the council meeting for adoption? | many people wanting to create loving homes for children in need | 0.0 | 0.0 | 1/1 -> 1/1 | 0 |
| 183 | What did Melanie find in her neighborhood during her walk? | a rainbow sidewalk | 1.0 | 0.0 | 1/1 -> 0/1 | 0 |
| 185 | What type of instrument does Caroline play? | clarinet and violin | 0.0 | 0.0 | 1/1 -> 1/1 | 0 |
| 195 | How did Caroline's children handle the accident? | They were scared but resilient | 0.0 | 1.0 | 0/1 -> 1/1 | 1 |

Net score movement:

- gains: row 195 +1.0
- losses: row 163 -0.5, row 183 -1.0
- unchanged: rows 172, 185
- adversarial net: -0.5 over 5 rows => category 30 -> 20

## Row-level findings

### Row 163: score loss without packet append

Question: `What did Caroline and her family do while camping?`
Gold adversarial answer: `explored nature, roasted marshmallows, and went on a hike`

Baseline and treatment both covered the gold ref according to telemetry. No packet evidence was appended in treatment (`packet_episodic_added_count=0`). The score changed from 0.5 to 0.0 because the independent baseline and treatment arms retrieved/ranked different baseline memories after separate ingest runs.

Baseline prediction:

> Caroline did not mention camping with her family; it was Melanie who went camping with her family, where they roasted marshmallows, told stories around the campfire, explored nature, hiked, and enjoyed time together.

Treatment prediction:

> Caroline did not mention camping with her family; Melanie and her family went camping, where they explored nature, roasted marshmallows around the campfire, went on a hike, and enjoyed the view from the top.

The treatment answer appears closer to the LOCOMO adversarial answer, but the judge scored it worse. This points to judge variance / adversarial wording sensitivity, not a packet-append failure.

Root-cause hypothesis: paired baseline/treatment arms are not perfectly retrieval-identical when no packet is appended. The current canary checks treatment-internal prefix preservation, but it does not freeze baseline retrieval across arms. That is sufficient for merge mechanics, but weak for attributing row-level score deltas to packet append.

### Row 183: real retrieval/gold-loss failure, no append rescue

Question: `What did Melanie find in her neighborhood during her walk?`
Gold adversarial answer: `a rainbow sidewalk`

Baseline covered the gold ref and answered correctly. Treatment did not cover the gold ref and answered `I don't know`. No packet evidence was appended.

Baseline top context included the correct neighborhood/rainbow-sidewalk memory:

- source ref `D14:23`
- telemetry coverage: 1/1

Treatment context drifted to related LGBTQ/art memories and missed the exact rainbow-sidewalk ref:

- telemetry coverage: 0/1
- appended packets: 0

Root-cause hypothesis: the ref gate only appends packet evidence when the packet candidates include an uncovered gold ref. Here treatment's baseline missed the gold ref, but context_packet did not supply the missing `D14:23` evidence, so the gate had nothing useful to append. This is not prompt noise; it is candidate recall miss / baseline arm drift.

### Row 195: intended success case

Question: `How did Caroline's children handle the accident?`
Gold adversarial answer: `They were scared but resilient`

Baseline missed the gold ref and answered `I don't know`. Treatment appended one packet memory matching the missing gold ref and answered correctly.

Appended memory:

- id `mem_c92bbb2b084e`
- refs: session_index 10, turn_start 0, turn_end 9
- snippet begins with Melanie describing the roadtrip accident and her son's accident

This validates the ref-gate mechanism when context_packet supplies missing gold evidence.

## Cross-cutting diagnosis

The adversarial regression is not primarily caused by appended packet noise:

- Rows 163 and 183 regressed with zero appended packet evidence.
- Row 195 improved with one appended packet evidence.
- Rows 172 and 185 were unchanged with zero appended packet evidence.

Two distinct issues remain:

1. **Attribution weakness in paired A/B artifacts.** Baseline and treatment arms rerun ingest/retrieval separately. When no packet is appended, row-level score differences can still occur from retrieval/ranking/id drift or judge sensitivity. This affects row 163.
2. **Candidate recall miss.** The ref gate can only append gold evidence present in context_packet candidates. Row 183 shows a treatment baseline miss that context_packet did not rescue.

## Recommended next action

Do not run full 199Q yet.

Next bounded step should be mechanics/attribution hardening, not a larger benchmark:

1. Add an attribution metric for treatment rows:
   - `packet_appended_by_row`
   - `score_delta_when_packet_appended`
   - `score_delta_when_no_packet_appended`
2. Add a stricter category gate for future bounded slices:
   - no category may regress by more than 10 pp, or
   - any category regression must be explained by rows with packet append, not no-append drift
3. For row 183, inspect why context_packet omitted `D14:23` despite the baseline arm being able to retrieve it in another run. Candidate recall, not answer prompting, is the likely bottleneck.

A next preregistered bounded slice can proceed only after adding attribution diagnostics. Full 199Q remains blocked.
