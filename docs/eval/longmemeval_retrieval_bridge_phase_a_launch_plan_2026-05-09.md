# LongMemEval Retrieval Bridge Phase A Launch Plan — 2026-05-09

> **For Hermes:** Use this as the exact launch checklist only after the user explicitly approves the side effects in the approval block below. Do not treat this plan itself as launch approval.

**Goal:** Run only Phase A retrieval coverage for the frozen second LongMemEval oracle slice, then stop before answer generation unless a separate approval is given.

**Architecture:** The launch is a bounded retrieval-only bridge from frozen LongMemEval rows into a namespaced Memibrium domain. It ingests only the selected source sessions needed for the second slice, performs retrieval/context calls, writes retrieval artifacts, evaluates offline Phase A gates using commit `7e106d8`, and cleans up the namespaced bridge domain. It does not retune `category_contract_v1` and does not run Phase B answer/judge scoring.

**Tech Stack:** Python harnesses under `docs/eval/results/`, Memibrium server at `http://localhost:9999`, Docker compose file `docker-compose.ruvector.yml`, cleaned dataset pin `/tmp/longmemeval-cleaned-pin/longmemeval_oracle.json`.

---

## Status

Documentation-only readiness rung. This file does not authorize runtime mutation, DB writes/deletes, retrieval calls, answer model calls, judge calls, Hermes config changes, or full LongMemEval `_s` / `_m`.

Current pushed source of truth before this plan:

- `0d4df19` — retrieval bridge preregistration.
- `3e157d4` — prep-only Phase A harness and artifacts.
- `7e106d8` — offline Phase A gate evaluator and placeholder fail-closed report.

Frozen bridge selection:

- Dataset revision: `98d7416c24c778c2fee6e6f3006e7a073259d48f`.
- Dataset SHA256: `821a2034d219ab45846873dd14c14f12cfe7776e73527a483f9dac095d38620c`.
- Selection artifact: `docs/eval/results/longmemeval_oracle_canary_25_second_slice_selection_20260508.json`.
- Bridge selection SHA256: `9cd322852a4e947730f811e6913012270e3bac9cc569b3394ee49e5b1d80edbb`.
- Domain: `longmemeval-bridge-v1-20260508-second-slice`.
- Condition: `longmemeval_bridge_v1_retrieval_plus_category_contract_v1`.

## Approval block required before launch

Before executing Phase A, state the exact side effects and get explicit approval for each approved item. If any item is not approved, do not perform it.

Required approvals for Phase A retrieval coverage:

1. Memibrium Docker/server rebuild or no rebuild.
2. DB writes for namespaced LongMemEval bridge ingestion.
3. Retrieval/context calls against the live Memibrium server.
4. Cleanup deletes for the namespaced bridge domain after artifacts are preserved.

Not part of Phase A unless separately approved:

- Answer model calls.
- Judge model calls.
- Phase B answer scoring.
- Full LongMemEval `_s` / `_m`.
- Hermes config or memory-provider wiring.
- Direct `/mcp/tools` curl inspection.

Recommended phrasing to user before launch:

> Planned side effects: inspect git status; optionally rebuild/restart the Memibrium Docker server if you approve that; ingest the frozen second-slice LongMemEval source sessions into namespaced domain `longmemeval-bridge-v1-20260508-second-slice`; run retrieval/context calls for the 25 selected questions; write retrieval and coverage artifacts under a new timestamped results directory; run the offline Phase A gate evaluator; delete the namespaced bridge memories and verify zero residual rows. I will not call answer models, judges, run full LongMemEval, change Hermes config, or inspect `/mcp/tools`. Please approve which of: rebuild, DB ingest, retrieval calls, cleanup deletes.

## Phase A launch invariants

Keep these invariant during implementation/execution:

1. `category_contract_v1` remains unchanged.
2. Use only the frozen second slice.
3. Use one shared retrieved evidence artifact for any future baseline/treatment answer arms.
4. Stop after Phase A report unless explicit Phase B approval exists.
5. Preserve enough source refs for artifact-only review.
6. Treat `stale_only`, `adjacent_entity_only`, and `unsupported` as retrieval/coverage failures for answer-side mechanism claims.
7. Never report Phase A as a product benchmark or retrieval benchmark claim beyond this 25-row canary.

## Artifact layout

For an approved launch, create a new timestamped directory:

```text
docs/eval/results/longmemeval_retrieval_bridge_phase_a_YYYYMMDDTHHMMSSZ/
```

Required files:

```text
ingest_manifest.json
retrieval_results.jsonl
retrieval_coverage_audit.json
longmemeval_retrieval_bridge_phase_a_gate_report.json
cleanup_report.json
run_metadata.json
```

Optional diagnostic files:

```text
raw_recall_payloads_redacted.jsonl
context_packet_payloads_redacted.jsonl
source_ref_index.json
```

Do not write secrets, tokens, API keys, passwords, connection strings, or raw environment dumps to artifacts. Runtime metadata must be redacted and limited to non-secret identities such as commit SHA, Docker image digest if available, endpoint host/path without credentials, and model/deployment names where non-secret.

## Retrieval JSONL schema

Each line in `retrieval_results.jsonl` must contain at least the fields required by the offline gate evaluator from `7e106d8`:

```json
{
  "question_id": "...",
  "question_type": "...",
  "question": "...",
  "query_variants": [],
  "retrieved_memory_ids": [],
  "scores": [],
  "source_refs": [],
  "evidence_snippets": [],
  "timestamp_source_metadata": [],
  "fallback_error_flags": [],
  "candidate_pool": {
    "schema": "memibrium.recall.candidate_pool.v1",
    "candidate_group_count": 0,
    "groups": [],
    "total_candidates_before_merge": 0,
    "total_merged_candidates": 0,
    "ranked_returned_count": 0,
    "top_ranked_ids": []
  },
  "score_components": [],
  "source_ref_analysis": {
    "answer_session_ids": [],
    "retrieved_session_ids": [],
    "supporting_source_refs": [],
    "retrieved_answer_session_ids": [],
    "missing_answer_session_ids": [],
    "retrieved_non_answer_session_ids": []
  },
  "coverage_rationale": "...",
  "coverage_class": "gold_supported",
  "retrieval_status": "ok"
}
```

Allowed `coverage_class` values:

- `gold_supported`
- `gold_supported_with_conflict`
- `partial_support`
- `stale_only`
- `adjacent_entity_only`
- `unsupported`
- `unanswerable_supported`
- `unanswerable_contaminated`

Placeholder-only state may use `coverage_class: null` only with `retrieval_status: not_run_runtime_not_authorized`; live Phase A must not use that placeholder status.

## Gate thresholds

Evaluate these before any answer generation:

1. Coverage audit completeness: `25/25` rows have a coverage class and preserved retrieval artifacts.
2. Retrieval operational success: no uncaught 500s, serialization errors, missing JSON fields, or non-`ok` retrieval statuses.
3. Preference coverage: at least `3/4` single-session-preference rows are `gold_supported` or `gold_supported_with_conflict`.
4. Knowledge-update coverage: at least `3/5` knowledge-update rows are `gold_supported`, `gold_supported_with_conflict`, or `partial_support`; `stale_only` counted separately.
5. Abstention contamination: no more than `1/4` abstention rows may be `unanswerable_contaminated`; contamination means affirmative answer leakage, not mere source presence. Negative, contrastive, or insufficiency-supporting context should classify as `unanswerable_supported`.
6. Evidence identity: every answerable row with non-`unsupported` coverage preserves source refs sufficient for artifact-only review.
7. Diagnostics completeness: live Phase A rows preserve candidate-pool and score-component telemetry when the server exposes recall telemetry; missing telemetry must be explicit in `timestamp_source_metadata` rather than silently omitted.
8. Substrate comparability: `telemetry.server.substrate_readiness` must be captured when available. Do not compare a run against the 84%/canonical substrate unless embedding provider/model/dim and LEANN cold-tier status match the preregistered substrate.

If any Phase A gate fails, stop before answer generation. The output is a retrieval coverage diagnostic only.

## Substrate readiness interpretation

The live server can expose `telemetry.server.substrate_readiness` with non-secret runtime identities:

- `embedding.provider`, `embedding.model`, `embedding.expected_dim`, and `embedding.actual_dim` distinguish local Ollama-compatible embeddings such as `nomic-embed-text` from API/Azure embeddings such as `text-embedding-3-small`.
- `embedding.endpoint_host` may be recorded, but secrets, tokens, passwords, DSNs, and full credential-bearing URLs must be redacted.
- `leann.cold_tier_status=leann_ready` means `USE_LEANN=true`, LEANN is available, and a searcher/index is loaded.
- `leann.cold_tier_status=leann_installed_index_not_loaded` means LEANN code is available/requested but the cold-tier index/searcher is not ready.
- `leann.cold_tier_status=candidates_leann_not_installed_or_disabled` means cold-tier diagnostics are still vector-engine candidate based and must not be interpreted as LEANN compression results.

## Task 1: Preflight and runtime identity capture

**Objective:** Establish clean repo/runtime identity before any side effects.

**Files:**
- Read-only: repository state.
- Create later: `run_metadata.json` after launch directory exists.

**Commands:**

```bash
cd /home/zaddy/src/Memibrium
git status --short --branch
git log -1 --oneline
python3 -m py_compile server.py
python3 -m py_compile docs/eval/results/run_longmemeval_oracle_canary.py
python3 -m unittest test_longmemeval_oracle_canary
```

Expected:

- Branch is the current diagnostics/launch branch for this runbook (for example, `diagnostics/longmemeval-retrieval-quality`) or a documented successor.
- Tracked files clean before launch, except known untracked `docs/reference/` and older LOCOMO canary noise.
- Tests pass.

If Docker/server rebuild is approved, follow `memibrium-operations` rebuild discipline:

```bash
cd /home/zaddy/src/Memibrium
python3 -m py_compile server.py
docker compose -f docker-compose.ruvector.yml up -d --build memibrium
curl -s http://localhost:9999/health | jq .
docker logs --tail 50 memibrium-server
```

If rebuild is not approved, do not rebuild/restart. Perform only a non-mutating health check if retrieval calls are approved:

```bash
curl -s http://localhost:9999/health | jq .
```

Do not print env files. If config identity is needed, inspect only redacted non-secret fields.

## Task 2: Build the ingest manifest

**Objective:** Convert the frozen second-slice selection into a namespaced ingest plan without writing DB rows yet.

**Files:**
- Read: `/tmp/longmemeval-cleaned-pin/longmemeval_oracle.json`
- Read: `docs/eval/results/longmemeval_oracle_canary_25_second_slice_selection_20260508.json`
- Write: `ingest_manifest.json`

**Required manifest fields:**

```json
{
  "mode": "retrieval_bridge_phase_a_ingest_manifest",
  "dataset_sha256": "821a2034d219ab45846873dd14c14f12cfe7776e73527a483f9dac095d38620c",
  "selection_sha256": "9cd322852a4e947730f811e6913012270e3bac9cc569b3394ee49e5b1d80edbb",
  "domain": "longmemeval-bridge-v1-20260508-second-slice",
  "selected_question_ids": [],
  "source_session_ids": [],
  "answer_session_ids": [],
  "planned_memory_count": 0,
  "created_memory_ids": []
}
```

Validation:

- Selection proof passes using `validate_selection()`.
- Selected question IDs match the selection artifact order.
- Source and answer session IDs are deduplicated in stable order.

## Task 3: Ingest only namespaced source evidence

**Objective:** Write LongMemEval source-session evidence into Memibrium under the bridge domain, preserving source refs.

**Side effect:** DB writes. Requires explicit approval.

**Rules:**

- Use domain exactly `longmemeval-bridge-v1-20260508-second-slice`.
- Write enough metadata to map each memory back to `{question_id, session_id, turn_index, role, date, has_answer}`.
- Do not ingest outside the selected second-slice source/answer sessions.
- Do not alter production/user memory domains.
- Record all created memory IDs in `ingest_manifest.json`.

**Verification:**

- Manifest `created_memory_ids` is non-empty after ingest.
- Created count equals planned count or any discrepancy is explained in `ingest_manifest.json`.
- No secrets in stdout/artifacts.

## Task 4: Run retrieval/context calls for 25 questions

**Objective:** Produce `retrieval_results.jsonl` with one row per selected question.

**Side effect:** live Memibrium retrieval/context calls. Requires explicit approval.

**Rules:**

- Use identical retrieval settings for every future answer arm.
- Preserve query variants and source refs.
- Capture operational failures as `fallback_error_flags`, but fail closed at gate time.
- Do not call answer models or judges.
- Do not call `/mcp/tools`.

**Per-row output:**

- `retrieval_status: ok` only if the call returned valid JSON and required fields were captured.
- Non-OK statuses must include a reason, e.g. `error_500`, `serialization_error`, `missing_json_field`, `timeout`.

## Task 5: Classify retrieval coverage

**Objective:** Assign one allowed coverage class to each retrieved row and write `retrieval_coverage_audit.json`.

**Files:**
- Read: `retrieval_results.jsonl`
- Write: `retrieval_coverage_audit.json`

**Classification rule:**

Use artifact evidence only. The coverage class should be explainable from retrieved snippets/source refs and the gold answer/rubric in the dataset. Do not use answer-generation output because Phase B has not run.

**Audit row fields:**

```json
{
  "question_id": "...",
  "question_type": "...",
  "coverage_class": "...",
  "gold_supporting_evidence_present": [],
  "gold_supporting_evidence_missing": [],
  "stale_conflicting_evidence_present": [],
  "source_refs": [],
  "classification_notes": "..."
}
```

If classification requires an LLM, stop and ask for explicit model-call approval first. Prefer deterministic artifact-only classification for Phase A.

## Task 6: Evaluate Phase A gates offline

**Objective:** Run the committed offline gate evaluator and decide whether Phase A passes.

**Command:**

```bash
cd /home/zaddy/src/Memibrium
python3 docs/eval/results/run_longmemeval_oracle_canary.py \
  --dataset /tmp/longmemeval-cleaned-pin/longmemeval_oracle.json \
  --selection docs/eval/results/longmemeval_oracle_canary_25_second_slice_selection_20260508.json \
  --retrieval-bridge-phase-a-report \
  --retrieval-results-file docs/eval/results/longmemeval_retrieval_bridge_phase_a_YYYYMMDDTHHMMSSZ/retrieval_results.jsonl \
  --phase-a-report-file docs/eval/results/longmemeval_retrieval_bridge_phase_a_YYYYMMDDTHHMMSSZ/longmemeval_retrieval_bridge_phase_a_gate_report.json
```

Expected output if gates pass:

```json
{
  "mode": "retrieval_bridge_phase_a_gate_evaluation_offline",
  "overall_pass": true,
  "phase_b_recommendation": "phase_a_passed_answer_generation_still_requires_explicit_approval"
}
```

If gates fail:

- Stop.
- Do not answer-score.
- Write failure notes in `run_metadata.json`.
- Preserve artifacts for review.

## Task 7: Cleanup namespaced bridge data

**Objective:** Remove only namespaced LongMemEval bridge data and verify zero residual rows.

**Side effect:** DB deletes. Requires explicit approval.

**Rules:**

- Delete only rows for domain `longmemeval-bridge-v1-20260508-second-slice` and directly linked rows.
- Include Context Graph/link tables only if ingestion wrote to them.
- Use table-specific ID/link columns; do not assume every table uses `memory_id`.
- Verify with `count(id)` where applicable.
- Write `cleanup_report.json`.

**Cleanup report fields:**

```json
{
  "mode": "retrieval_bridge_phase_a_cleanup",
  "domain": "longmemeval-bridge-v1-20260508-second-slice",
  "created_memory_count": 0,
  "deleted_memory_count": 0,
  "final_domain_count_verified": 0,
  "linked_rows_deleted": {},
  "cleanup_status": "complete"
}
```

## Task 8: Commit and report

**Objective:** Preserve source/artifacts and report only canary-level retrieval coverage.

**Commands:**

```bash
cd /home/zaddy/src/Memibrium
git diff --check
python3 -m unittest test_longmemeval_oracle_canary
git status --short --branch
git add docs/eval/results/longmemeval_retrieval_bridge_phase_a_YYYYMMDDTHHMMSSZ/ docs/eval/longmemeval_retrieval_bridge_phase_a_launch_plan_2026-05-09.md
git commit -m "eval: run LongMemEval retrieval bridge phase A"
git push origin query-expansion
```

Do not add:

- `docs/reference/`
- unrelated LOCOMO canary noise
- raw secret-bearing logs
- raw env dumps

## Phase A report wording

If Phase A passes:

> On the frozen 25-row LongMemEval retrieval-bridge canary, Phase A retrieval coverage passed the preregistered coverage gates. This means the retrieved evidence is adequate to request a separate Phase B answer-side run, but no answer or product benchmark score has been measured yet.

If Phase A fails:

> On the frozen 25-row LongMemEval retrieval-bridge canary, Phase A retrieval coverage failed at [gate names]. Per preregistration, answer generation remains blocked; this is retrieval coverage diagnostic evidence only, not an answer-contract or product benchmark result.

## Stop conditions

Stop immediately if any occurs:

- Git tracked state is dirty before launch for unrelated files.
- Dataset SHA or selection SHA mismatches.
- Runtime health check fails and rebuild was not approved.
- Ingest writes outside the bridge domain.
- Retrieval output has missing IDs, missing source refs for non-unsupported answerable rows, or non-OK statuses.
- Phase A gates fail.
- Any secret appears in artifacts/log snippets.
- User approval scope is exceeded.

## Next valid action after this plan

The next valid action is either:

1. User explicitly approves Phase A side effects listed in the approval block; or
2. Further code-only preparation of a retrieval ingestion/retrieval runner using TDD, with no runtime calls or DB/Docker mutation.

This plan does not authorize Phase A execution by itself.
