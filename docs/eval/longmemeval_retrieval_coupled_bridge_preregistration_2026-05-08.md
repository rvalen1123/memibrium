# LongMemEval retrieval-coupled bridge preregistration — 2026-05-08

Status: documentation-only preregistration. This document does not authorize retrieval ingestion, DB/Docker/runtime mutation, model calls, judge calls, full LongMemEval `_s`/`_m`, prompt retuning, or direct `/mcp/tools` inspection.

## Motivation

The oracle-evidence phase is now frozen:

- Slice 1: unchanged `category_contract_v1` improved answer-side scoring `18/25 -> 21/25`, with `single-session-preference` moving `0/4 -> 3/4`.
- Slice 2: unchanged `category_contract_v1` improved answer-side scoring `16/25 -> 19/25`, with `single-session-preference` moving `0/4 -> 4/4` and all preregistered second-slice gates passing.
- Cross-slice synthesis: `docs/eval/longmemeval_oracle_category_contract_cross_slice_synthesis_2026-05-08.md`.

The next valid evidence rung is not another oracle run and not a prompt retune. It is a retrieval-coupled bridge that tests whether Memibrium can supply the evidence that the already-frozen answer contract can use.

## Communication boundary

This future bridge is still a 25-row canary unless and until an exact upstream LongMemEval `_s` or `_m` protocol is run and reported as such.

Do not frame this preregistration as:

- a product benchmark result,
- full LongMemEval performance,
- retrieval improvement evidence,
- approval to mutate runtime or ingest data.

Defensible framing after preregistration only:

> After two oracle-evidence canaries replicated an answer-side preference-recovery mechanism, the next preregistered rung will separate retrieval coverage from answer synthesis on a frozen 25-row LongMemEval slice. No retrieval/product claim is made until ingestion, recall, coverage, answer generation, and judging are explicitly approved and reported with separate gates.

## Frozen source lineage

Use the same cleaned dataset and evaluator lineage as the oracle phase:

- Dataset: `xiaowu0162/longmemeval-cleaned`.
- Dataset revision: `98d7416c24c778c2fee6e6f3006e7a073259d48f`.
- Oracle SHA256: `821a2034d219ab45846873dd14c14f12cfe7776e73527a483f9dac095d38620c`.
- Upstream LongMemEval commit: `982fbd7045c9977e9119b5424cab0d7790d19413`.
- Judge script SHA256: `ecce9c4c79dc89d99534ac17b383a5cbb5b9f0c69ee98adaf0684742e3d95251`.
- Answer contract: unchanged `category_contract_v1` from the scored oracle runs.

## Frozen slice choice

Use the already-committed second oracle slice as the first retrieval-coupled bridge target:

- Selection artifact: `docs/eval/results/longmemeval_oracle_canary_25_second_slice_selection_20260508.json`.
- Selection SHA256: `9cd322852a4e947730f811e6913012270e3bac9cc569b3394ee49e5b1d80edbb`.
- Seed: `memibrium-longmemeval-oracle-canary-2026-05-08-v2`.
- Shape: 25 total rows; `knowledge-update` 5; `multi-session` 4; `single-session-assistant` 4; `single-session-preference` 4; `single-session-user` 4; `temporal-reasoning` 4; abstention 4.
- Prior-slice question overlap: 0.

Rationale:

1. The slice was preregistered before scoring.
2. Its oracle answer-side gates already passed.
3. Its preference rows provide a clean retrieval question: can retrieval supply the user-preference evidence that `category_contract_v1` successfully uses under oracle conditions?
4. Using a frozen existing slice avoids post-hoc row selection for the first bridge.

Do not add, remove, or replace rows for the first bridge. If a later retrieval-specific slice is needed, preregister it separately before inspecting outcomes.

## Retrieval condition to preregister for a future launch

The future launch, if explicitly approved, should use a fresh, namespaced LongMemEval canary domain and should not touch production user memories.

Proposed condition name:

- `longmemeval_bridge_v1_retrieval_plus_category_contract_v1`

Required namespace/domain:

- `longmemeval-bridge-v1-20260508-second-slice`

Required runtime side effects for the future launch:

1. Inspect git status first.
2. Confirm the active branch and commit.
3. Confirm Memibrium health.
4. Ingest only the source conversations needed for the frozen 25 selected rows into the namespaced LongMemEval bridge domain.
5. Run retrieval/context construction for the 25 selected questions.
6. Record retrieved evidence IDs, source session/turn refs, timestamps, and compact snippets needed for coverage auditing.
7. Generate answers using unchanged `category_contract_v1` only after retrieval artifacts are saved.
8. Judge answers with the pinned judge only after answer artifacts are saved.
9. Cleanup the namespaced LongMemEval bridge domain after artifacts are committed or after any failed/partial launch, with row counts verified.

Runtime mutation is not approved by this document. Before any launch, the operator must explicitly approve the mutation window and exact scope.

## Retrieval artifact requirements

A future retrieval-coupled run must preserve separate artifacts for each phase:

1. `ingest_manifest.json`
   - dataset SHA,
   - selection SHA,
   - selected question IDs,
   - source session IDs,
   - memory IDs created,
   - domain/namespace,
   - commit SHA,
   - timestamp,
   - redacted runtime metadata.

2. `retrieval_results.jsonl`
   - question ID,
   - question type,
   - retrieval query/query variants,
   - returned memory IDs in rank order,
   - scores if available,
   - source session/turn refs,
   - compact evidence snippets,
   - timestamp/source metadata,
   - fallback/error flags.

3. `retrieval_coverage_audit.json`
   - per-row evidence coverage class,
   - gold-supporting evidence present/missing,
   - stale/conflicting evidence present,
   - whether retrieved context contains enough information to answer under the oracle rubric,
   - whether the row should proceed to answer scoring or stop at retrieval miss.

4. `answer_predictions.jsonl`
   - generated only after retrieval artifacts exist,
   - unchanged `category_contract_v1`,
   - no oracle evidence injected except retrieved context.

5. `judge_results.jsonl` and `scored_summary.json`
   - generated only after answer predictions exist,
   - pinned judge prompt/model lineage,
   - paired against the same selected rows.

6. `cleanup_report.json`
   - counts of created and deleted memories/links,
   - final zero-count verification for the namespaced domain,
   - errors if cleanup is partial.

## Coverage classes

Classify every row before answer scoring:

| Class | Meaning | Proceed to answer score? |
| --- | --- | --- |
| `gold_supported` | Retrieved context contains the required gold-supporting fact(s) without unresolved conflict. | Yes |
| `gold_supported_with_conflict` | Retrieved context contains gold-supporting fact(s) plus stale/conflicting facts that the answer contract must resolve. | Yes, but mark conflict |
| `partial_support` | Retrieved context contains some but not all facts required by the rubric. | Yes, but score separately and do not treat answer failure as pure synthesis failure |
| `stale_only` | Retrieved context contains older/stale facts but misses the newer gold fact. | No for answer-side mechanism claims; retrieval/recency miss |
| `adjacent_entity_only` | Retrieved context contains related but wrong entity/role/item evidence. | No for answer-side mechanism claims; premise/entity miss |
| `unsupported` | Retrieved context lacks answer-supporting evidence. | No for answer-side mechanism claims; retrieval miss |
| `unanswerable_supported` | For `_abs` rows, retrieved context supports that the asked fact is absent/unsupported. | Yes |
| `unanswerable_contaminated` | For `_abs` rows, retrieval includes adjacent facts likely to induce a false answer. | Yes, but mark contamination |

## Gate structure

Separate gates by layer. Do not collapse them into one score.

### Phase A — retrieval coverage gates

These gates must be evaluated before answer generation:

1. Coverage audit completeness: `25/25` rows have a coverage class and preserved retrieval artifacts.
2. Retrieval operational success: no uncaught 500s, serialization errors, or missing JSON fields in retrieval artifacts.
3. Preference coverage: at least `3/4` single-session-preference rows are `gold_supported` or `gold_supported_with_conflict`.
4. Knowledge-update coverage: at least `3/5` knowledge-update rows are `gold_supported`, `gold_supported_with_conflict`, or `partial_support`; stale-only rows must be counted separately.
5. Abstention contamination: no more than `1/4` abstention rows may be `unanswerable_contaminated` by adjacent facts.
6. Evidence identity: every answerable row must preserve source refs sufficient for artifact-only review.

If Phase A fails because coverage is missing, stop. Do not answer-score missing-evidence rows as proof that the answer contract failed.

### Phase B — answer-side gates on retrieved context

Only run if Phase A passes or if the user explicitly approves a diagnostic answer run despite failed coverage.

1. Use unchanged `category_contract_v1`.
2. Report scores separately for:
   - all 25 rows,
   - only rows with `gold_supported` / `gold_supported_with_conflict`,
   - preference rows,
   - knowledge-update rows,
   - temporal-reasoning rows.
3. Preference mechanism gate: among preference rows with adequate retrieval coverage, treatment should preserve at least `75%` correctness.
4. Knowledge-update watch gate: among adequately covered knowledge-update rows, treatment should not underperform the oracle second-slice treatment rate by more than one row. Because retrieval coverage differs, report this as a watch gate, not a hard product claim.
5. Moved-row analysis: compare against a retrieval-context baseline prompt only if both arms use identical retrieved evidence.
6. Stop condition: if answer scoring regresses on adequately covered preference rows, do artifact-only review before any prompt retune.

### Phase C — cleanup and comparability gates

1. Cleanup namespaced LongMemEval bridge memories and linked rows.
2. Verify zero residual rows for the bridge domain.
3. Commit/push artifacts before follow-up experiments.
4. Leave known untracked `docs/reference/` and older LOCOMO canary noise untouched.

## Baselines and comparisons

The first retrieval bridge should compare only conditions that differ in answer contract, not retrieval evidence:

- Retrieval baseline answer condition: generic LongMemEval answer prompt over the retrieved context.
- Retrieval treatment answer condition: unchanged `category_contract_v1` over the exact same retrieved context.

Hard requirement:

- Baseline and treatment must share identical retrieved evidence per question ID. If retrieval differs between arms, the answer-contract comparison is confounded and must be labeled invalid for answer-side claims.

Oracle comparisons are allowed only as ceilings/diagnostics:

- Oracle second-slice treatment: `19/25`.
- Oracle preference treatment: `4/4`.

Do not require retrieval-coupled scores to match oracle scores on the first bridge. The first bridge is intended to separate retrieval coverage from answer synthesis.

## Non-actions

This preregistration does not authorize:

- `docker compose` rebuild/restart,
- DB writes or deletes,
- LongMemEval conversation ingestion,
- Memibrium recall/context calls against live runtime,
- model answer generation,
- judge calls,
- full LongMemEval `_s` / `_m`,
- direct `/mcp/tools` curl inspection,
- Hermes config/memory backend changes,
- product/retrieval benchmark claims.

## Launch approval checklist for a future session

If the user later says to launch the retrieval bridge, first state the exact planned side effects and ask/confirm whether the approval covers:

1. Memibrium Docker/server rebuild or no rebuild.
2. DB writes for namespaced LongMemEval ingestion.
3. Retrieval/context calls against the live server.
4. Answer model calls.
5. Judge model calls.
6. Cleanup deletes for the namespaced bridge domain.

If the user approves only a subset, run only that subset and stop at the appropriate gate.

## Expected final reporting shape

A valid future result report must have this shape:

1. Runtime/substrate identity and mutation window.
2. Dataset/selection hashes.
3. Ingest counts and cleanup counts.
4. Retrieval coverage table by question type.
5. Answer score table separated by coverage class.
6. Paired outcome table only for rows with identical evidence across baseline/treatment.
7. Artifact-review notes for retrieval misses and answer failures.
8. Explicit communication boundary: canary result only, not full LongMemEval `_s`/`_m`.

## Next immediate action

The next immediate action after this preregistration is verification and commit only. Do not implement the retrieval bridge harness or run any live retrieval/model/judge work without a separate explicit instruction.
