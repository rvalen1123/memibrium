# Benchmark notes (LOCOMO)

> Relocated verbatim from the root `README.md` in the MED-242 docs pass (2026-11-02). The [README](../README.md) is now the short entry point; this file keeps the full text.

The dated preregistrations and results that back these notes are indexed in [docs/eval/README.md](eval/README.md).

---

## Benchmark Notes

**Current status (April 2026):** `hybrid_retrieval.py` is a reconstruction from pyc metadata + test contracts, on branch `reconstruction-backup`. It passes all tests but is not bit-identical to the historical code state that produced earlier benchmark numbers.

**Reconstructed-baseline temporal accuracy:** 37.7% (n=321, 95% CI ±5.3%) at chunk_size=10, full 10 conversations, gpt-4.1-mini judge/answer. The historical 29.6% baseline is not directly comparable because the codebase changed.

**⚠️ CRITICAL CORRECTION (April 2026):** All baseline measurements from the reconstruction period (29.6% historical, 37.7% reconstructed) were taken against a corrupted database. The `entity_relationships` table had a foreign-key reference to `entities(entity_id)` but `entities` was created *after* `entity_relationships` in the schema initialization, causing fresh database builds to silently degrade. A full database rebuild (commit `747ace7`) moved the baseline to ~62% on barely-cleaned data, no normalization. **All prior failure-mode analyses, prediction calibrations, and intervention rationales should be treated as measurements of a degraded system, not the actual Memibrium pipeline.**

**Post-rebuild baseline (healthy DB):** ~62% temporal accuracy (4/10 conversations, in progress). This is the new ground truth. A fresh failure-mode analysis on the rebuilt system is required before any intervention predictions are valid.

**Failure-mode analysis (condition 4, n=193 failures) — ⚠️ SUPERCEDED:**

| Category | Count | % of failures |
|----------|-------|---------------|
| retrieval-missing | 107 | 55.4% |
| relative-date-resolution | 69 | 35.8% |
| composition | 13 | 6.7% |
| gold-label-error | 4 | 2.1% |

> **Note:** The above breakdown was produced on a corrupted database where retrieval was silently degraded. The "retrieval-missing" bucket was massively inflated. A new breakdown on the healthy DB will look different.

The dominant failure mode was **retrieval-missing at 55.4%**, followed by relative-date-resolution at 35.8%. The smoke-test hypothesis that "relative-date dominates" was directionally correct for *reasoning* failures, but retrieval-missing is the overall largest category and has the higher ceiling (71.0% vs 59.2% if perfectly fixed).

> **Note:** The "higher ceiling" claim above is also suspect — it was derived from the broken-DB failure distribution.

**Why date normalization is still the right #1 intervention:** It is a prerequisite substrate cleanup, not the biggest bucket. Normalizing relative dates at ingest directly addresses the 35.8% relative-date failures, likely reduces retrieval-missing as a side effect, and creates a cleaner substrate for subsequent retrieval-precision work.

> **Note:** The "right #1 intervention" claim requires re-validation on the healthy DB. The failure-mode distribution has changed.

**Eval limitation:** 13.4% of temporal questions have suspicious gold labels, and 2.1% are confirmed contradictions. Any benchmark delta under ~3 points should be treated as noise until labels are cleaned.

> **Note:** The 13.4% suspicious-label rate is independent of the DB state and likely still valid. The 2.1% confirmed contradictions were manually verified and also remain valid.

Historical focused LOCOMO experiments produced two practical takeaways:

1. Temporal QA improved meaningfully only after preserving source chronology explicitly:
   - ingest original `event_at` timestamps
   - store chronology metadata in `refs` (`session_index`, `chunk_index`, `turn_start`, `turn_end`)
   - sort temporal recall results chronologically
   - use smaller chunks (~3 turns) for temporal evaluation

2. Multi-hop retrieval is currently safest with adjacency-only expansion:
   - session-adjacent chunk expansion was mildly helpful
   - broad second-hop retrieval using bridge terms consistently reduced focused multi-hop accuracy
   - constrained second-hop variants also remained worse than adjacency-only
   - current evidence supports treating retrieval precision loss as the primary observed failure, while answer-composition bottlenecks remain unproven

Practical guidance: keep adjacency-only as the active multi-hop baseline, and do overlap / failure-mode analysis before adding more retrieval breadth.
