# LongMemEval Retrieval Bridge Phase A Live Pass — 2026-05-25

## Status

Accepted retrieval-only Phase A pass for the frozen second-slice bridge run.

This artifact is a curated summary of the successful live retrieval run, retained so the raw generated result directories can be cleaned from the working tree without losing the operational decision record.

## Scope

- Mode: retrieval bridge Phase A runtime scaffold
- Condition: `longmemeval_bridge_v1_retrieval_plus_category_contract_v1`
- Domain: `longmemeval-bridge-v1-20260508-second-slice`
- Selection file: `docs/eval/results/longmemeval_oracle_canary_25_second_slice_selection_20260508.json`
- Run directory: `docs/eval/results/longmemeval_retrieval_bridge_phase_a_20260525T202207Z`
- Created at: `2026-05-25T20:22:48.439576+00:00`
- Dataset SHA256: `821a2034d219ab45846873dd14c14f12cfe7776e73527a483f9dac095d38620c`
- Selection SHA256: `9cd322852a4e947730f811e6913012270e3bac9cc569b3394ee49e5b1d80edbb`

Guardrails preserved:

- No answer model calls.
- No judge calls.
- No full LongMemEval `_s` / `_m` run.
- No direct `/mcp/tools` inspection.

Communication boundary:

- Retrieval coverage evidence only.
- No answer/product benchmark claim.
- Phase B / answer generation still requires explicit approval.

## Result

Overall Phase A gate: PASS.

Retrieval rows:

- Total rows: 25
- Retrieval status `ok`: 25

Question type coverage:

- knowledge-update: 5
- multi-session: 4
- single-session-assistant: 4
- single-session-preference: 4
- single-session-user: 4
- temporal-reasoning: 4

Coverage classes:

- gold_supported: 13
- partial_support: 8
- unanswerable_supported: 3
- unanswerable_contaminated: 1
- unsupported: 0
- stale_only: 0

## Gate Summary

All gates passed:

- coverage_audit_completeness
- retrieval_operational_success
- preference_coverage
- knowledge_update_coverage
- abstention_contamination
- evidence_identity
- diagnostics_completeness
- overall

Key gate details:

- Preference coverage: 4/4 adequate; target was 3/4.
- Knowledge-update coverage: 4/5 adequate; target was 3/5.
- Abstention contamination: 1/4; target maximum was 1/4.
- Evidence identity: no missing source-ref question IDs and no missing retrieved-memory-ID question IDs.

## Diagnostics Completeness

Diagnostics completeness gate passed:

- rows with recall telemetry: 25/25
- rows with candidate pool: 25/25
- rows with score components: 25/25
- rows with source-ref analysis: 25/25
- rows with coverage rationale: 25/25
- rows with explicit substrate-readiness presence/absence: 25/25

Candidate-pool group labels observed in telemetry:

- semantic
- lexical
- temporal

Score components were preserved for all 25 rows.

## Cleanup

Cleanup completed:

- Created memories: 446
- Deleted memories: 446
- Final domain count verified: 0
- Cleanup status: complete
- Recovery cleanup: not needed

Linked rows deleted:

- user_feedback: 0
- memory_snapshots: 0
- memory_edges: 0
- contradictions: 0
- temporal_expressions: 0
- context_graph_edges: 0
- decision_traces: 0
- self_model_observations: 0

## Caveats

The live server was not rebuilt or restarted for this run.

The branch code adds server-side substrate-readiness telemetry, but the live server used for this run did not expose populated server substrate readiness. The run still recorded explicit substrate-readiness presence/absence for 25/25 rows, satisfying Phase A diagnostics completeness, but this does not support a substrate-comparable benchmark claim.

Use this result as the cleanup/readiness gate for retrieval diagnostics. Do not use it as an 84%-style answer benchmark or product-performance claim.

## Decision

Proceed to repo cleanup after preserving this summary and the diagnostic code changes.

Recommended next gates after cleanup:

1. Merge the retrieval diagnostics branch after CI passes.
2. Deploy/restart the server from merged code when ready.
3. Run a small telemetry smoke to confirm populated server substrate readiness.
4. Only then consider answer-generation or full LongMemEval benchmark work, with explicit approval.
