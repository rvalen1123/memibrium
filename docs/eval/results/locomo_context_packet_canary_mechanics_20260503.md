# LOCOMO Context Packet Canary Mechanics Analysis

Date: 2026-05-03
Run ID: `20260503T192225Z`
Analyzed commit: `3be453c feat: add LOCOMO context packet canary`

## Scope

This is an analysis of the committed 7-row fixed-row canary artifacts only. It is not a full LOCOMO benchmark and should not be interpreted as population-level performance evidence.

Artifacts inspected:

- `docs/eval/results/locomo_context_packet_canary_baseline_20260503T192225Z.json`
- `docs/eval/results/locomo_context_packet_canary_treatment_20260503T192225Z.json`
- `docs/eval/results/locomo_context_packet_canary_summary_20260503T192225Z.json`
- `docs/eval/results/locomo_context_packet_canary_result_20260503T192225Z.md`

Input controls:

- Dataset: `/tmp/locomo/data/locomo10.json`
- Dataset sha256: `79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4`
- Sample: `conv-26`
- Fixed rows: 7 preregistered rows from `locomo_step5o_prereg_fixed_rows_2026-05-02.json`
- No full 199Q run was executed.

## Executive conclusion

The canary passes the narrow mechanics gate it was designed to test:

- row identity was preserved;
- condition metadata distinguished baseline vs `context_packet`;
- every treatment prompt included a context-packet section;
- all seven treatment prompt contexts changed relative to baseline;
- context-packet telemetry was present;
- final LOCOMO cleanup returned all tracked counts to zero.

However, the canary also shows that Context Packet v0 is still mostly a recall wrapper, not yet a validated graph/self-model substrate:

- `episodic_evidence_count` was nonzero on all treatment rows, but `self_model_observation_count=0` and `graph_fact_count=0` on every row;
- `missing_evidence` was always `['self_model_observations', 'graph_facts']`;
- each packet included one decision trace, but the only self-model observation ID in provenance was the generic smoke-test observation `obs_smoke_context_graph_v0_timestamp_fix_4474e75`, not row-specific LOCOMO evidence;
- treatment final-context entries lost their `id` field in the captured final-context projection (`id=null`) even though context-packet telemetry retained memory IDs in `provenance_summary`;
- one treatment row duplicated the same evidence chunk in the packet (`adversarial_split_late` includes the session-19 adoption-interview chunk twice in provenance/final context).

Therefore: do not run full 199Q yet. The next defensible step is a slightly stronger preregistered canary/slice that preserves evidence IDs in rendered context, deduplicates packet evidence, records full prompt contexts or structured evidence rows, and adds graph/self-model coverage checks.

## Gate results

| Gate | Result | Evidence |
|---|---:|---|
| Fixed input row identity | PASS | 7/7 fixed rows matched preregistered question hashes |
| Paired baseline/treatment row identity | PASS | summary `row_identity_ok=true` |
| Condition metadata | PASS | baseline `context_packet=false`; treatment `context_packet=true` |
| Prompt context delta | PASS | 7/7 treatment context hashes differ from baseline |
| Context-packet telemetry | PASS | treatment rows all include context-packet telemetry |
| Final cleanup | PASS | final DB check `memories=0, memory_edges=0`; artifact hygiene counts all zero |

Scores, diagnostic only:

| Arm | Overall | Notes |
|---|---:|---|
| baseline_default | 35.71% | current default harness, query expansion off |
| treatment_context_packet | 57.14% | `USE_CONTEXT_PACKET=1`, same rows/settings |

Latency, diagnostic only:

- baseline avg query time: 1512 ms;
- treatment avg query time: 2976 ms;
- treatment first query was highest at 6094 ms, likely includes warm-start effects.

## Per-row mechanics

Important indexing note: LOCOMO evidence labels use numeric session names (`D2`, `D10`, etc.). The benchmark harness currently sorts session keys lexicographically during ingest, so `refs.session_index` does not equal the numeric `D` session number after `session_9`. Evidence-hit accounting below maps LOCOMO `D*` labels through the harness' lexicographic ingest order.

| Row | Category | Q index | Evidence turns | Baseline score / evidence hit | Packet score / evidence hit | Mechanics note |
|---|---|---:|---|---|---|---|
| `adversarial_split_early` | adversarial | 153 | `D2:3` | 0.0 / 1 of 1 | 0.5 / 1 of 1 | Packet preserved the relevant self-care chunk and got partial credit by correcting the subject: Melanie, not Caroline, had the charity-race realization. |
| `adversarial_split_late` | adversarial | 154 | `D2:8` | 0.0 / 1 of 1 | 0.0 / 1 of 1 | Both arms retrieved the relevant adoption chunk, but the model answered that Melanie had no adoption plans. This is likely benchmark adversarial wording: the evidence says Caroline was researching adoption agencies, while question asks about Melanie. |
| `unanswerable_high_context` | unanswerable | 83 | `D2:2` | 1.0 / 1 of 1 | 1.0 / 1 of 1 | Stable pass. Both arms had enough charity-race/mental-health evidence. |
| `unanswerable_c_low_exception` | unanswerable | 149 | `D18:5` | 0.0 / 0 of 1 | 0.0 / 0 of 1 | Stable miss. Neither arm retrieved the exact Grand Canyon/family-thankfulness evidence. Packet retrieved nearby family/museum/beach/camping themes but not the needed Grand Canyon statement. |
| `temporal_high_context` | temporal | 34 | `D5:1` | 0.0 / 1 of 1 | 1.0 / 0 of 1 | Packet improved despite not retrieving the gold turn. It inferred June 2023 from later LGBTQ/pride context. This is useful but not clean source-backed proof for the specific gold evidence. |
| `single_hop_high_context` | single-hop | 33 | `D5:1`, `D8:17`, `D3:1`, `D1:3` | 0.5 / 2 of 4 | 0.5 / 1 of 4 | Stable partial. Packet emphasized later LGBTQ art/activism and missed several gold events; baseline had different partial coverage. |
| `multi_hop_high_context` | multi-hop | 43 | `D10:12`, `D10:14` | 1.0 / 0 of 2 | 1.0 / 2 of 2 | Packet clearly improved evidence grounding: it retrieved both camping-trip gold chunks. Baseline still answered correctly from related outdoor/nature context. |

## Evidence/provenance quality findings

### What works

1. Packet mode now uses real recall output.

The server fix in `3be453c` changed `/mcp/context_packet` from reading only `recall['memories']` to reading `recall['results']` first. The treatment artifacts confirm non-empty episodic evidence and memory IDs in `provenance_summary`.

2. Prompt-context delta is real, not a metadata-only change.

All treatment prompts contained `Context Packet (episodic evidence):` and had different context hashes from baseline.

3. Packet evidence can improve grounding on some rows.

Best examples:

- `adversarial_split_early`: treatment recovered the self-care realization and explicitly corrected the actor mismatch.
- `multi_hop_high_context`: treatment retrieved both camping-trip evidence chunks.

### What does not work yet

1. No graph/self-model evidence is active for LOCOMO rows.

Every treatment row had:

- `self_model_observation_count=0`
- `graph_fact_count=0`
- `missing_evidence=['self_model_observations', 'graph_facts']`

So this canary does not validate Context Graph v0's graph/self-model value. It validates context-packet recall plumbing and prompt rendering only.

2. Provenance includes a stale/generic self-model observation ID.

Treatment `provenance_summary.self_model_observation_ids` repeatedly contains:

- `obs_smoke_context_graph_v0_timestamp_fix_4474e75`

But `self_model_observation_count=0`, so this ID is coming through a decision trace rather than a row-specific observation. Do not treat it as supporting evidence for LOCOMO answers.

3. Rendered final context loses memory IDs.

Treatment `recall_telemetry.final_context` entries have `id=null` because packet rendering converts evidence into prompt text and the final-context projection dedupes by content. The packet telemetry still has `provenance_summary.memory_ids`, but row-level prompt/evidence inspection would be easier and safer if rendered context preserved the packet memory ID beside each line.

4. Dedupe is incomplete.

`adversarial_split_late` had `episodic_evidence_count=8` but only 7 unique provenance memory IDs. The same adoption-interview memory chunk appeared twice. This should be fixed before any larger slice, otherwise packet top-k capacity is wasted and provenance counts overstate unique evidence.

5. One improvement is not strictly source-backed to the gold turn.

`temporal_high_context` improved from 0 to 1, but packet evidence-hit accounting did not find the gold `D5:1` chunk in treatment context. It likely inferred the answer from adjacent/later LGBTQ chronology. That may be semantically acceptable for the judge, but it weakens any claim that packet mode retrieved the exact source evidence.

6. Existing refs/session indexing is confusing.

Harness ingest sorts sessions lexicographically:

```python
sessions = sorted([k for k in conv if k.startswith('session_') and not k.endswith('date_time')])
```

This yields `session_1, session_10, session_11, ..., session_2, ...`, so `refs.session_index` is not numeric LOCOMO `D` session order. It does not invalidate the canary because both arms share it, but it makes provenance inspection error-prone and should be corrected or explicitly recorded before larger experiments.

## Interpretation of score deltas

The treatment's 57.14% vs baseline's 35.71% is encouraging but not benchmark-grade evidence because:

- n=7 fixed rows is intentionally tiny;
- some rows improved without exact gold evidence retrieval;
- the packet substrate is not yet exercising graph/self-model facts;
- answer/judge variance could dominate at this size;
- the canary had one known prompt/provenance transformation issue (`id=null` in final context);
- the row mix is deliberately diagnostic, not representative.

Use the result as evidence that `--context-packet` materially changes prompt context and can improve answers in controlled rows, not as evidence that it improves LOCOMO overall.

## Recommendation

Do not run full 199Q LOCOMO yet.

Next gated slice should be another preregistered canary/small slice after mechanics hardening. Required fixes/checks before scaling:

1. Preserve packet evidence IDs in rendered context/final-context telemetry.
   - Each rendered packet evidence line should carry `memory_id`, `refs`, and `created_at` in a structured way.
   - Canary artifacts should store structured packet evidence rows, not only a 1000-character prompt preview.

2. Deduplicate packet episodic evidence by memory ID and/or content hash before prompt rendering.
   - Add a test for duplicate evidence from `/mcp/context_packet`.

3. Add gold-evidence hit-rate telemetry to the canary harness.
   - For each row, map LOCOMO evidence labels to harness refs and report `gold_evidence_retrieved_n/total` for each arm.
   - Record exact matched memory IDs/refs.

4. Fix or make explicit the session-order mapping.
   - Prefer natural numeric ordering for LOCOMO session keys.
   - If changing ingest ordering would affect comparability, preregister the change and run a substrate baseline first.

5. Decide what is being evaluated:
   - If evaluating context-packet recall wrapper only, graph/self-model missingness is acceptable but must be reported as such.
   - If evaluating Context Graph v0, require nonzero graph/self-model rows or a separate graph-population step.

6. Rerun the same 7-row canary after hardening.
   - Gate: row identity, condition metadata, prompt delta, unique evidence count, gold evidence hit-rate, preserved memory IDs, final cleanup.

Only after that should a larger preregistered slice be considered, e.g. 20-30 fixed rows stratified by category and evidence position. Full 199Q remains blocked until the larger slice passes the same mechanics gates.
