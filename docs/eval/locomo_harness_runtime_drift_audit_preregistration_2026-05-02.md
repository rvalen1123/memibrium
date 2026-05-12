# LOCOMO harness-runtime drift audit preregistration — Step 5k

Date: 2026-05-02
Repo: `/home/zaddy/src/Memibrium`
Branch: `query-expansion`
HEAD at preregistration start: `662514a` (`docs: record LOCOMO corrected slice reproducibility run`)

## Status

Phase C remains blocked.

Step 5j_v2_exec produced a valid corrected-slice telemetry-off run, but the result was neither the original low-context f2466c9 baseline nor the rejected 91fede6 high-context telemetry retry.

Preregistered decision label from Step 5j_v2_exec: `telemetry_off_third_regime_observed`.

This Step 5k is an artifact-first, read-only harness-runtime drift / reproducibility-family audit. It is designed to decide what evidence is required next before any intervention selection.

## Inputs and locked regimes

### Regime A — f2466c9 low-context baseline

Known reference:

- Commit: `f2466c9`
- 5-cat: `14.82%`
- protocol 4-cat: `19.41%`
- total questions: `199`
- query expansion fallback: `0/199`
- mean `n_memories`: `4.5327`
- `n=15`: `22/199`
- distribution: `2:57, 3:110, 11:1, 12:3, 13:3, 14:3, 15:22`

Status: not yet proven stable after Step 5j_v2_exec.

### Regime B — 91fede6 telemetry retry high-context regime

Known rejected noncomparable retry:

- Commit: `91fede6`
- 5-cat: `58.29%`
- protocol 4-cat: `69.41%`
- total questions: `199`
- query expansion fallback: `0/199`
- mean `n_memories`: `14.6231`
- `n=15`: `162/199`
- distribution: `11:3, 12:6, 13:17, 14:11, 15:162`

Status: rejected as noncomparable; do not use as Phase C baseline.

### Regime C — 662514a corrected telemetry-off third regime

Valid corrected-slice execution:

- Commit: `662514a`
- 5-cat: `55.28%`
- protocol 4-cat: `70.07%`
- total questions: `199`
- query expansion fallback: `0/199`
- mean `n_memories`: `11.9296`
- `n=15`: `120/199`
- distribution: `4:51, 12:6, 13:10, 14:12, 15:120`
- result validity: exactly 199 rows, all `conv-26`, telemetry off, query expansion on

Status: valid third regime; not a Phase C baseline until drift/nonreproducibility is adjudicated.

## Audit question

Why did a valid telemetry-off corrected-slice run produce Regime C instead of Regime A or B?

The audit must distinguish among:

1. **Harness-code drift / artifact mismatch.** Regime A may not have been produced by the same effective harness path, result file, flags, or dataset slice that later artifacts assumed.
2. **Runtime/server-source drift.** Live server code, effective retrieval code, env, dependency version, or container image changed between Regime A and later runs in a way not captured by high-level benchmark metadata.
3. **Benchmark-side query-expansion path change.** The high-level `query_expansion=True` flag may hide differences in number of expanded queries, fallback behavior, per-expanded-query recall, dedupe, cap, or context assembly.
4. **Stateful nondeterminism / ingestion drift.** Same source/substrate/clean DB may produce different memory counts because ingestion, background scoring, graph edges, or hierarchy timing is unstable.
5. **Telemetry perturbation already ruled out only narrowly.** Step 5h ruled out same-query telemetry off/on perturbation for eight empty/no-hit non-LOCOMO pairs, not for populated LOCOMO production-distribution calls.
6. **Artifact insufficiency.** Existing artifacts may be insufficient to adjudicate without another preregistered non-benchmark probe.

## Allowed actions

Read-only only:

- inspect committed markdown/JSON/log artifacts;
- inspect git history, diffs, and source files;
- compute hashes/statistics from artifacts;
- compare per-question rows when stable keys exist;
- inspect current live server health and LOCOMO hygiene only;
- inspect current container/source/env metadata if non-mutating;
- write and commit audit artifacts.

## Forbidden actions

Do not:

- run LOCOMO benchmark;
- run live `/mcp/recall` probes;
- ingest LOCOMO or any new memories;
- mutate DB, Docker, env, source, schema, runtime, dependencies, or containers;
- rebuild/restart containers;
- implement Phase C or any retrieval intervention;
- classify `55.28%`, `58.29%`, or `14.82%` as canonical Phase C baseline without evidence.

## Required analyses

1. **Artifact inventory and integrity.** Identify exact files for Regime A, B, C; record parseability, row counts, condition metadata, result hashes, and key missing fields.
2. **Per-question overlap.** Align Regime A/B/C by question text when row artifacts exist. Compare score deltas and `n_memories` deltas. If Regime A raw row artifact is missing, state that explicitly.
3. **Retrieval-shape regime comparison.** Compare exact `n_memories` distribution, mean, cap saturation, and category-by-shape relationships across available regimes.
4. **Harness-code and git-diff audit.** Inspect relevant changes between f2466c9, 91fede6, and 662514a in `benchmark_scripts/locomo_bench_v2.py`, `server.py`, `hybrid_retrieval.py`, compose/env-facing files, and telemetry instrumentation commits. Classify changes as retrieval-touching, telemetry-only, artifact-only, or unknown.
5. **Effective-runtime metadata audit.** Compare available prelaunch/snapshot artifacts for env/model/deployment, live source hash/probes, DB/vector metadata, and container/source evidence.
6. **Statefulness/nondeterminism evidence.** Determine whether artifact patterns support ingestion/background timing or memory lifecycle side effects as plausible without additional live probes.
7. **Evidence gap table.** For each remaining candidate family, list what existing artifact would resolve it and whether that artifact exists.

## Decision labels

Use one primary label and optional secondary labels:

- `audit_supports_harness_code_drift`
- `audit_supports_runtime_substrate_drift`
- `audit_supports_stateful_nondeterminism`
- `audit_supports_artifact_mismatch`
- `audit_supports_query_expansion_path_drift`
- `audit_inconclusive_artifacts_insufficient`
- `audit_requires_paired_populated_recall_probe_prereg`
- `audit_requires_reproducibility_replicate_prereg`
- `audit_requires_commit_boundary_bisection_prereg`
- `no_go_phase_c_still_blocked`

## Stop/go outputs

Allowed next-step recommendations:

- `go_paired_populated_recall_probe_preregistration` — if artifact audit suggests telemetry/query-expansion/retrieval path differences can be resolved with bounded same-state non-benchmark populated recall calls.
- `go_reproducibility_replicate_preregistration` — if artifact audit suggests stateful nondeterminism and a second corrected-slice replicate is necessary.
- `go_commit_boundary_bisection_preregistration` — if git/source audit identifies a specific commit boundary likely responsible.
- `go_runtime_substrate_snapshot_preregistration` — if runtime substrate evidence is missing or inconsistent.
- `blocked_artifacts_insufficient` — if existing artifacts cannot support a decisive next test.
- `no_go_phase_c_still_blocked` — always include unless a future valid baseline is established.

## Output artifacts

Expected:

- `docs/eval/results/locomo_harness_runtime_drift_audit_2026-05-02.md`
- `docs/eval/results/locomo_harness_runtime_drift_audit_labels_2026-05-02.json`
- optional support JSON:
  `docs/eval/results/locomo_harness_runtime_drift_audit_support_2026-05-02.json`

## Interpretation constraints

- Do not relabel Step 5j_v2_exec; it remains a valid `telemetry_off_third_regime_observed` result.
- Do not treat score-only similarity to Regime B as comparability; retrieval shape still differs.
- Do not use Regime C as the Phase C baseline until the family causing A/B/C divergence is resolved.
- If evidence is insufficient, prefer a narrow preregistered evidence-gathering step over speculative intervention work.
