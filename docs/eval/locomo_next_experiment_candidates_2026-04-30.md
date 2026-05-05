# LOCOMO Next Experiment Candidates — 2026-04-30

**Status:** Decision scaffold, not a pre-registration.
**Branch at capture:** `query-expansion`
**Current HEAD at capture:** `3307d16`

This note captures the open decision after two pre-registered LOCOMO cycles:

1. Gated append: rejected / hold. Aggregate accuracy was neutral, churn was high, and fully-correct harms were nonzero.
2. No-expansion Arm B: rejected as a default-config change, but accepted as a quantified latency/accuracy curve point.

The next step should not be chosen reflexively at the end of the run session. Pick the next experiment only when fresh enough to decide what question is actually worth spending another pre-registered run on.

## Current anchor facts

- Query expansion remains net-helpful on full conv-26 substrate:
  - Arm A query expansion: `94.5 / 199` = `47.487437%`
  - Arm B no expansion: `87.5 / 199` = `43.969849%`
  - Delta: `-3.517588pp` for no-expansion
- Query expansion is also the major latency cost:
  - Avg query latency: `3285ms -> 904ms` without expansion (`-72.48%`)
  - p95 query latency: `8473ms -> 1236ms` without expansion (`-85.41%`)
- The fallback diagnostic mechanism prediction failed:
  - fallback-vs-non-fallback was a mechanism-selected subpopulation comparison, not a valid full-population counterfactual.
- Multi-hop is fragile across retrieval/context changes:
  - no-expansion: multi-hop `-11.54pp`
  - gated append: multi-hop `-7.69pp`

## Candidate A — Latency/accuracy Pareto: conditional or async expansion

Question:

> Can we get most of expansion's accuracy at a fraction of its latency?

Possible variants:

- conditional expansion based on retrieval confidence
- expansion only when initial recall is weak
- expansion only for inferred multi-hop/temporal-like questions, if classification cost is justified
- async expansion that does not block initial retrieval/answer path
- two-stage retrieval: fast original-query path first, expansion only if abstention/evidence confidence is low

Why this is high-leverage:

- Most production-relevant if Memibrium is heading toward enterprise deployment under latency SLAs.
- Arm B quantified the tradeoff curve endpoint: expansion buys about +3.5pp full-score accuracy at about +2.4s avg latency and +7.2s p95 latency.
- A Pareto improvement would be practically useful even if it does not beat full expansion on accuracy.

Main risk:

- Prior context manipulation experiments harmed multi-hop and unanswerable. Any gate must preserve multi-hop evidence assembly and abstention behavior.

Likely pre-registration shape:

- Compare against a fresh post-parser-patch full-expansion reference, or run same-substrate paired arms.
- Primary endpoint should include both accuracy and latency, not accuracy alone.
- Decision should be Pareto-style, e.g. retain >=X% of expansion's accuracy gain while recovering >=Y% of no-expansion latency savings, with category harm guardrails.

## Candidate B — Fixed expansion prompt/parser Arm C

Question:

> Does a fixed expansion prompt/parser improve over current expansion?

Why it remains real:

- The 2026-04-30 diagnosis found genuine expansion generation/parsing failures: 28.64% fallback in the reference artifact.
- Parser hygiene landed separately at `ddb0aa8`.
- A stronger transform-only prompt plus strict parser could lower fallback rate.

Why it is now lower-leverage:

- Current expansion is net-helpful despite the 28.64% failure rate.
- Making expansion fire more often could help, hurt, or be neutral.
- The within-category fallback paradox already warned that fixing fallback mechanically is not guaranteed to improve accuracy.

Hard methodology constraint:

- Arm C exercises the post-`ddb0aa8` parser path. It cannot directly compare to the old 2026-04-29 Arm A artifact as if only the prompt changed.
- Arm C requires either:
  - a fresh post-parser-patch Arm A reference, or
  - an explicitly pre-registered same-run paired comparison that separates parser/infrastructure effects from prompt effects.

## Candidate C — Multi-hop fragility diagnostic

Question:

> Why does multi-hop break under every context/retrieval manipulation?

Why this is high-information:

- Two independent runs now show multi-hop as the most or among the most harmed categories.
- Multi-hop is the category most aligned with long-memory product value.
- This is a system understanding task, not another broad feature attempt.

Possible diagnostic design:

- Take multi-hop questions from the paired artifacts.
- Compare answer-context memories across:
  - full expansion reference
  - gated append
  - no-expansion
  - possibly prior rerank/append canaries
- Classify whether losses come from:
  - missing one evidence fragment
  - evidence present but not synthesized
  - context displacement/noise
  - judge/gold-label issue
  - LOCOMO multi-hop ambiguity
- No new accuracy intervention should be implemented inside this diagnostic.

Why choose this over A:

- Best if Memibrium is still in research/system-understanding mode.
- Could prevent repeating failed retrieval/context manipulations.

## Current read

- Candidate A is highest-leverage for production readiness.
- Candidate C is highest-information for research/system understanding.
- Candidate B is safest and most local, but probably least exciting unless fallback rate itself is blocking a downstream experiment.

Do not draft the next pre-registration until the next experiment question is chosen deliberately.

## Non-Memibrium reminder

This session focused entirely on Memibrium. Other project tracks have not advanced here: Listnr, ModalPoint, OID/Dad, Medvinci, Azure migration, ADHS tracks, and any accidentally uploaded archives. The next work block does not have to be another Memibrium experiment.
