# LOCOMO No-Expansion (Arm B) — Pre-Registration

**Date:** 2026-04-30
**Branch:** `query-expansion`
**Author:** Ricky Valentine
**Status:** Pre-registered. To be filed before the next eval run executes.

---

## 1. Purpose

Test whether query expansion is net-helpful, net-harmful, or neutral on
LOCOMO conv-26.

The 2026-04-30 fallback diagnosis identified a paradox: questions where
query expansion silently failed (fallback to original query only) scored
+7.21pp higher than questions where expansion succeeded. The within-category
breakdown confirmed the paradox is not explained by category mix:

- adversarial: +18.9pp fallback advantage (n=15 vs 32)
- unanswerable: +8.2pp (n=26 vs 44)
- single-hop: −4.3pp (n=11 vs 21) — the only category where expansion wins
- multi-hop, temporal: small fallback n; not interpretable

Before any prompt-or-parser fix to expansion is treated as an accuracy
intervention, this run determines whether the planned fix direction is
correct at all.

## 2. Hypotheses

**H1 (primary, accuracy):** On full LOCOMO conv-26 (199Q), running with
query expansion entirely disabled (Arm B) yields strictly higher accuracy
than the 2026-04-29 query-expansion baseline (Arm A).

**H2 (mechanistic):** If H1 holds, the per-category gain pattern matches
the prediction: adversarial and unanswerable improve most; single-hop is
roughly neutral or slightly worse; multi-hop and temporal directionally
improve but with low confidence due to small fallback-side n in the
diagnosis.

**H3 (latency):** With expansion disabled, average and p95 latency are
strictly lower than Arm A (cheaper code path; no LLM expansion call).

## 3. Arm definitions

**Arm A (reference, not re-run):** Query expansion as currently
implemented. Reference artifact:
`docs/eval/results/locomo_conv26_query_expansion_199q_2026-04-29.json`.
Headline: 47.487%, 3285ms avg, 8473ms p95.

**Arm B (this run):** Original query only, no expansion at all. The
expansion code path must be bypassed, not just have a "broken" prompt.
Specifically:
- `expand_query()` must not be called, OR
- expansion call must short-circuit and return `[question]` before any
  LLM invocation
- Confirm via log inspection that no expansion LLM calls occur during
  the run

**Arm C (NOT in this pre-registration):** Expansion with fixed prompt and
parser validation. Branched on Arm B's outcome (see §6). Requires its own
pre-registration if pursued. Because Arm C would exercise the patched
parser path from commit `ddb0aa8`, it must not use the 2026-04-29 Arm A
artifact as its direct reference. If Arm C is pursued, first define a
fresh post-parser-patch Arm A reference or otherwise pre-register the
comparison so parser and prompt effects are not conflated.

## 4. Slice and substrate

- **Source:** LOCOMO conv-26, full slice (199Q).
- **Same substrate as Arm A:** identical model, decoding parameters,
  retrieval config, RECALL_TOP_K, judge model, and judge prompt.
- **Same commit as the change-under-test:** Arm B is run on whatever
  commit cleanly disables expansion. Record commit hash in artifacts.
- **Arm A is NOT re-run.** The 2026-04-29 baseline is the reference. This
  is a deliberate choice: re-running A introduces run-to-run variance
  that would muddy the comparison. Same-substrate guarantees in §4 must
  be enforced manually since we are comparing across runs, not within a
  single run.

**Risk acknowledged:** Cross-run comparison is weaker than within-run
paired comparison. The decision rules in §5 are sized to this risk.

## 5. Pre-registered decision rules

Three possible outcomes. The rules are written so each outcome has a
deterministic next action.

**Outcome 1: Disable expansion (B is better)**

All of the following must hold:
- B − A ≥ **+1.5pp absolute** on full conv-26
- No category where B harms A by more than **5pp** (mirror of harmed-
  from-fully-correct, applied at category level since this is a
  structural change, not a per-question intervention)
- B latency ≤ A latency on both avg and p95 (expected; failure here
  would suggest measurement artifact)

Action: disable expansion in default config. Parser hygiene patch
becomes purely defensive. Arm C is NOT pursued.

**Outcome 2: Net neutral (Occam — disable expansion anyway)**

|B − A| < **1.5pp** AND no category harm > 5pp.

Action: disable expansion. Justification: expansion provides no
measurable benefit but adds latency, complexity, and an LLM dependency.
Neutral expansion is not worth its cost. Arm C is NOT pursued.

**Outcome 3: Expansion was actually helping (B is worse)**

B − A ≤ **−1.5pp**.

Action: the within-category paradox check missed something. Arm B
becomes a research finding, not a config change. Arm C (fixed
expansion) becomes a candidate next pre-registration. Write a follow-up
diagnosis document that references and supersedes the 2026-04-30
fallback diagnosis for this branch of the decision tree; do not inline-
edit the original dated diagnosis artifact after the run.

**Outcome edge case: B is mixed (some categories large gain, others
large loss)**

If any category shows >5pp harm AND any other category shows >5pp gain,
treat as inconclusive regardless of aggregate delta. Action: do not
change config; document the category-conditional result; consider
conditional expansion (e.g., enable only on single-hop) as a future
pre-registration topic.

## 6. Mechanistic prediction (sanity check, not a decision rule)

Per-category prediction based on the diagnosis hypothesis "expansion
amplifies retrieval ambiguity":

| Category | Prediction | Confidence |
|---|---|---|
| adversarial | B improves substantially | High |
| unanswerable | B improves moderately | High |
| single-hop | B roughly neutral or slightly worse | Medium |
| multi-hop | B directionally better | Low (small fallback n) |
| temporal | B directionally better | Low (small fallback n) |

If the run produces a pattern that contradicts this — e.g., B helps
single-hop most and harms adversarial — the mechanism is wrong and the
Outcome 1/2/3 verdict still applies but with a caveat: the *reason*
expansion is bad (or good) is not what the diagnosis identified.

## 7. Disqualifiers (run is invalid, not just negative)

- Expansion LLM calls observed in logs during Arm B (expansion not
  actually disabled).
- LOCOMO DB not cleared before Arm B.
- Different model, decoding params, retrieval config, RECALL_TOP_K, or
  judge from Arm A.
- Background scoring, contradiction detection, or hierarchy processing
  enabled (`ENABLE_BACKGROUND_SCORING` etc. must be `false` and
  verified end-to-end).
- Any test failure in `test_locomo_query_expansion.py`,
  `test_hybrid_retrieval_ruvector.py`, or `test_temporal_memory.py` on
  the commit used for the run.
- Parser hygiene patch landed on the same commit as the disable-
  expansion change. These are independent changes and must land in
  separate commits to keep attribution clean.

## 8. Pre-run hygiene (verified before run)

Same as 2026-04-29 protocol, now established:

- [ ] Docker reachable; `memibrium-server`, `memibrium-ruvector-db`,
      `memibrium-ollama` all up
- [ ] Eval toggles inside container: `ENABLE_BACKGROUND_SCORING=false`,
      `ENABLE_CONTRADICTION_DETECTION=false`,
      `ENABLE_HIERARCHY_PROCESSING=false`
- [ ] LOCOMO DB cleared: `SELECT count(*) FROM memories WHERE domain
      LIKE 'locomo-%'` returns 0 before run
- [ ] Test suites green on run commit: 51 / 6 / 10
- [ ] Working tree committed; commit hash recorded
- [ ] This pre-registration committed before the run starts
- [ ] Pre-run smoke: execute a 3-question Arm B smoke with
      `--no-expansion-arm-b --max-convs 1 --max-questions 3`, inspect
      recent `memibrium-server` logs for `expand|expansion`, and stop if
      any expansion LLM activity appears
- [ ] LOCOMO DB re-cleared after the smoke and verified back to 0 before
      the full Arm B run

Before executing the full Arm B run, use this smoke check to verify the
no-expansion wiring cheaply:

```bash
python3 benchmark_scripts/locomo_bench_v2.py \
  --cleaned --normalize-dates --no-expansion-arm-b \
  --max-convs 1 --max-questions 3

docker logs memibrium-server --since 30s | grep -iE "expand|expansion" || \
  echo "no expansion activity in logs — wiring confirmed"
```

If any expansion LLM activity appears, stop; the §7 expansion-call
disqualifier would apply to the real run. After the smoke, clear LOCOMO
again and verify 0 before starting the full 199Q Arm B run.

**No inter-arm clear required** because Arm A is not being re-run. But
LOCOMO must be cleared before Arm B starts.

## 9. Artifacts to produce

- `docs/eval/results/locomo_conv26_no_expansion_199q_2026-04-30.json`
- `docs/eval/results/locomo_no_expansion_arm_b_comparison_2026-04-30.json`
- `docs/eval/results/locomo_no_expansion_arm_b_comparison_2026-04-30.md`

Comparison markdown must include:

- Slice size and source (199Q, conv-26)
- Reference to Arm A artifact by filename
- Per-arm accuracy, avg latency, p50, p95
- Per-category accuracy delta (B vs A), with n per category
- Verdict against §5 rules: which outcome (1/2/3/edge), which
  threshold drove the decision
- Mechanism check from §6: did the per-category pattern match the
  prediction?
- Reference to this pre-registration file by filename
- Reference to commit hash of the change that disabled expansion

## 10. Reporting integrity

- Report all categories even if delta is small.
- Report latency as both avg and p95.
- Report raw credit numbers (sum / 199), not just rounded percentages —
  the 2026-04-29 run had an exactly-equal score that needed audit; same
  rigor here.
- Do not retroactively re-define thresholds. If the rules in §5 turn
  out to be wrong, document in a follow-up pre-registration; do not
  edit this file's thresholds after the run.

## 11. Out of scope

- Arm C (fixed expansion). Pre-register separately if Outcome 3
  triggers.
- Conditional expansion (enable per-category). Possible future work
  if §5 edge case triggers.
- Any change to gated append (rejected per 2026-04-29 pre-registration).
- Latency-of-gated-mechanisms (separate open pre-registration
  candidate).
- Tenant-scoping audit on Memibrium retrieval (separate gate).
- Fallback rate diagnosis is now closed by the 2026-04-30 diagnosis
  doc; this run is the follow-up action.

## 12. Pre-registration cross-references

- Prior pre-registration:
  `docs/eval/locomo_gated_append_preregistration_2026-04-29.md`
  (gated append, REJECTED)
- Diagnosis doc that motivated this pre-registration:
  `docs/eval/results/locomo_query_expansion_fallback_diagnosis_2026-04-30.md`
- Reference artifact (Arm A):
  `docs/eval/results/locomo_conv26_query_expansion_199q_2026-04-29.json`

---

**Decision once run completes:** apply §5 rules verbatim. Record
verdict and the specific outcome (1/2/3/edge) that was triggered.
