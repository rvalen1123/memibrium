# LOCOMO Conv-26 `bb9ba5b^` Boundary-Test Pre-registration

Date: 2026-04-30
Branch where preregistration is recorded: `query-expansion`
Boundary under test: `bb9ba5b^`
Resolved boundary commit: `bfeb90fc0465fdc24203d216c97cd1bc7226c0a4`
Boundary parent relationship: `bb9ba5b^ == bfeb90f`
Reference artifact: 2026-04-24 conv-26 query-expansion canary committed by `bfeb90f`

## Purpose

This experiment asks whether the code state immediately before `bb9ba5b` reproduces the 2026-04-24 conv-26 query-expansion numbers when run with the forced canonical inference stack.

The question is a commit-boundary test, not an intervention test:

> Does the forced canonical inference stack on commit `bb9ba5b^` reproduce the 04-24 conv-26 query-expansion result?

This pre-registration exists because branch/diff inspection found that `bb9ba5b feat: add opt-in retrieval modes with LOCOMO evaluation` introduced multiple plausible regression candidates at the same boundary:

1. `hybrid_retrieval.py` ruvector/domain/state/vector-cast drift
2. `benchmark_scripts/locomo_bench_v2.py` answer-context/candidate assembly drift

Because both candidates entered together in one commit, this run tests the commit boundary as a unit. It does **not** attempt to isolate which half of `bb9ba5b` is responsible.

## Historical reference

Primary reference: 2026-04-24 conv-26 query-expansion canary, committed by `bfeb90f`.

Reference artifact paths:

- `docs/eval/results/locomo_conv26_query_expansion_2026-04-24.json`
- duplicate historical copy, if present in the target worktree: `docs/eval/locomo_results_conv26_exp.json`

Reference values:

- Conv-26 full 5-category score: `68.09%` (`overall_score` in the artifact)
- Query-expansion fallback: `0/199`
- Average query latency: `8026ms`
- Inference stack encoded in `bfeb90f` benchmark source:
  - Endpoint: `https://sector-7.services.ai.azure.com/models`
  - Path: `/chat/completions`
  - Answer model: `gpt-4.1-mini`
  - Judge model: `gpt-4.1-mini`
  - Query-expansion model: `gpt-4.1-mini` through the `ANSWER_MODEL` path
  - Temperature: `0`
  - API key source: `AZURE_CHAT_API_KEY` env var

## Branch-check evidence motivating this run

Read-only branch/diff inspection on 2026-04-30 found:

- `origin/alert-autofix-1` is stale/divergent and lacks later reconstruction/mainline files. It is not a plausible current LOCOMO regression source from the active branch history.
- `origin/alert-autofix-2` has a workflow-permissions unique change and is also stale/divergent relative to current mainline code. It is not a plausible direct LOCOMO retrieval regression source.
- `origin/deploy` is stale/divergent with deploy/Terraform/cloud-init work. It is not a plausible direct LOCOMO retrieval regression source.
- `origin/reconstruction-backup` equals `origin/main` at `b3ecfbc` and has no diff from main.
- `hybrid_retrieval.py` is identical at `origin/reconstruction-backup`, `origin/main`, and `bfeb90f`, but changes by `541c311` / current `HEAD`.
- `benchmark_scripts/locomo_bench_v2.py` changes substantially between `bfeb90f` and `541c311`.
- The first relevant commit after `bfeb90f` touching both candidate areas is `bb9ba5b`.

Relevant commit range observed:

```text
bfeb90f  eval: add query expansion benchmark results and methodology record
bb9ba5b  feat: add opt-in retrieval modes with LOCOMO evaluation
712b9a6  fix: address LOCOMO review findings
5a4aa2a  fix: address LOCOMO script review findings
3c62420  Add LOCOMO gated append canary artifacts
b04c339  Clarify LOCOMO pre-run hygiene gates
76853cf  Add LOCOMO gated append full conv26 result
3ddac60  Audit LOCOMO gated append full result
5f79cf3  Record LOCOMO gated append churn diagnostics
d765ed3  docs: record LOCOMO query expansion fallback diagnosis
ddb0aa8  fix: validate LOCOMO query expansion parser
8bb3d89  docs: preregister LOCOMO no-expansion arm
18d9b54  feat: support LOCOMO no-expansion arm
1de8250  docs: tighten LOCOMO no-expansion preregistration
3307d16  docs: record LOCOMO no-expansion arm result
541c311  docs: capture LOCOMO next experiment candidates
```

## Hypothesis

If the LOCOMO regression is introduced by `bb9ba5b` as a coupled change set, then running `bb9ba5b^` (`bfeb90f`) with the forced canonical inference stack should reproduce the 04-24 conv-26 query-expansion reference.

Expected result if `bb9ba5b` is responsible:

- Query-expansion fallback near zero (`<=2/199` expected)
- Full conv-26 5-category score near `68.09%`

Latency is observational only and is not part of the reproduction decision.

## Fixed run configuration

This run must be launched from a separate worktree at the exact boundary commit. Do not run it from current `query-expansion` `HEAD`.

Recommended worktree setup:

```bash
cd /home/zaddy/src/Memibrium

git fetch --all --prune

git worktree add /home/zaddy/src/Memibrium-worktrees/locomo-bb9ba5b-parent-2026-04-30 bb9ba5b^

cd /home/zaddy/src/Memibrium-worktrees/locomo-bb9ba5b-parent-2026-04-30
```

Required commit verification before launch:

```bash
git status --short --branch
git rev-parse HEAD
git rev-parse bb9ba5b^
git log -1 --oneline --decorate HEAD
```

Expected:

- detached worktree or equivalent checked-out state
- `HEAD` exactly equals `bfeb90fc0465fdc24203d216c97cd1bc7226c0a4`
- `git rev-parse bb9ba5b^` also equals `bfeb90fc0465fdc24203d216c97cd1bc7226c0a4`
- no uncommitted changes affecting benchmark execution

## Required pre-run hygiene

Docker must be reachable, and these containers must be up:

- `memibrium-server`
- `memibrium-ruvector-db`
- `memibrium-ollama`

Check:

```bash
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
```

Eval toggles inside `memibrium-server` must all resolve false:

```bash
docker exec memibrium-server sh -lc '
  printf "ENABLE_BACKGROUND_SCORING=%s\n" "$ENABLE_BACKGROUND_SCORING"
  printf "ENABLE_CONTRADICTION_DETECTION=%s\n" "$ENABLE_CONTRADICTION_DETECTION"
  printf "ENABLE_HIERARCHY_PROCESSING=%s\n" "$ENABLE_HIERARCHY_PROCESSING"
'
```

Required values:

```text
ENABLE_BACKGROUND_SCORING=false
ENABLE_CONTRADICTION_DETECTION=false
ENABLE_HIERARCHY_PROCESSING=false
```

LOCOMO DB must be clear before launch:

```bash
docker exec -i memibrium-ruvector-db psql -U memory -d memory -t -A -c \
  "SELECT count(*) FROM memories WHERE domain LIKE 'locomo-%';"
```

Must be `0`. If not, run from a worktree containing the cleanup script or from the main checkout:

```bash
scripts/clear_locomo_domains.sh
```

and verify `0` again.

## Forced canonical inference stack

Before launching the benchmark, source credentials and force the 04-24 stack:

```bash
set -a
source /home/zaddy/src/Memibrium/.env
set +a

export AZURE_CHAT_ENDPOINT="https://sector-7.services.ai.azure.com/models"
export ANSWER_MODEL="gpt-4.1-mini"
export JUDGE_MODEL="gpt-4.1-mini"
export AZURE_CHAT_DEPLOYMENT="gpt-4.1-mini"
export AZURE_OPENAI_DEPLOYMENT="gpt-4.1-mini"
export CHAT_MODEL="gpt-4.1-mini"
unset OPENAI_BASE_URL
unset AZURE_OPENAI_ENDPOINT
```

The resolved env must be printed into the run log before benchmark launch:

```bash
python3 - <<'PY'
import os
print('=== RESOLVED ENV FOR THIS RUN ===')
for k in ['AZURE_CHAT_ENDPOINT','AZURE_OPENAI_ENDPOINT','OPENAI_BASE_URL',
          'AZURE_CHAT_DEPLOYMENT','AZURE_OPENAI_DEPLOYMENT','CHAT_MODEL',
          'ANSWER_MODEL','JUDGE_MODEL']:
    print(f'{k}={os.environ.get(k, "<unset>")}')
print('=================================')
PY
```

Expected resolved stack:

```text
AZURE_CHAT_ENDPOINT=https://sector-7.services.ai.azure.com/models
AZURE_OPENAI_ENDPOINT=<unset>
OPENAI_BASE_URL=<unset>
AZURE_CHAT_DEPLOYMENT=gpt-4.1-mini
AZURE_OPENAI_DEPLOYMENT=gpt-4.1-mini
CHAT_MODEL=gpt-4.1-mini
ANSWER_MODEL=gpt-4.1-mini
JUDGE_MODEL=gpt-4.1-mini
```

## Benchmark command

Run exactly one full conv-26 query-expansion benchmark:

```bash
python3 benchmark_scripts/locomo_bench_v2.py \
  --cleaned --normalize-dates --query-expansion \
  --max-convs 1
```

Do not use `--max-questions`. The target is the full conv-26 run (`199` questions).

Do not use any diagnostic/intervention flag. In particular, this run must not involve current-branch diagnostic infrastructure such as `--legacy-context-assembly`; that flag is not part of the boundary test and should not exist in the `bb9ba5b^` worktree.

## Artifact policy

Capture log and resolved env into a condition-specific log, for example:

```bash
/tmp/locomo_bb9ba5b_parent_boundary_199q_2026-04-30.log
```

After run, copy volatile outputs into `docs/eval/results/` in the main checkout with condition-specific names:

- `docs/eval/results/locomo_conv26_bb9ba5b_parent_boundary_199q_2026-04-30.json`
- `docs/eval/results/locomo_conv26_bb9ba5b_parent_boundary_199q_2026-04-30.log`
- `docs/eval/results/locomo_bb9ba5b_parent_boundary_199q_comparison_2026-04-30.json`
- `docs/eval/results/locomo_bb9ba5b_parent_boundary_199q_comparison_2026-04-30.md`

Comparison artifact must include:

- boundary commit SHA
- `git rev-parse bb9ba5b^`
- run worktree path
- benchmark command
- forced inference-stack env values listed above
- answer model, judge model, and query-expansion model
- endpoint
- decoding temperature
- full 5-category score
- query-expansion fallback count
- average query latency as observational metadata only
- LOCOMO DB pre-run and post-run counts
- decision-rule verdict

Do not commit:

- stale `/tmp` files unrelated to this run
- partial interrupted artifacts unless clearly marked as interrupted
- raw secrets or API keys

## Cleanup after run

After artifacts are copied, clear LOCOMO domains:

```bash
scripts/clear_locomo_domains.sh
```

Verify remaining LOCOMO count is `0`:

```bash
docker exec -i memibrium-ruvector-db psql -U memory -d memory -t -A -c \
  "SELECT count(*) FROM memories WHERE domain LIKE 'locomo-%';"
```

## Decision rules

Primary quality reference: 04-24 conv-26 artifact `overall_score` of `68.09%`.

Primary mechanism reference: 04-24 query-expansion fallback `0/199`.

### Strong reproduction

Declare strong reproduction if both are true:

- Full 5-category conv-26 score is within ±2 percentage points of `68.09%`, i.e. `[66.09%, 70.09%]`
- Query-expansion fallback is `<=2/199`

Interpretation: The code state immediately before `bb9ba5b` reproduces the 04-24 capability under the canonical inference stack. This supports `bb9ba5b` as the commit boundary responsible for the regression. Follow-up work should isolate which part of `bb9ba5b` is responsible; do not infer that from this run alone.

### Partial reproduction

Declare partial reproduction if both are true:

- Full 5-category conv-26 score is within ±5 percentage points of `68.09%`, i.e. `[63.09%, 73.09%]`
- Query-expansion fallback is `<=5/199`

and the run does not meet strong reproduction.

Interpretation: The code state immediately before `bb9ba5b` recovers most of the 04-24 result. `bb9ba5b` likely accounts for much of the divergence, but residual substrate/provider/DB/history differences may remain. Follow-up isolation must still be pre-registered.

### Failed reproduction

Declare failed reproduction if either is true:

- Full 5-category conv-26 score is outside ±5 percentage points of `68.09%`
- Query-expansion fallback is `>5/199`

Interpretation: Testing the `bb9ba5b` boundary as a unit is insufficient to recover the 04-24 result. Do not isolate the two `bb9ba5b` candidates as though the boundary has been confirmed. Instead, expand the bisection/investigation to earlier commits or substrate differences.

## Disqualifiers

The run is invalid if any of the following are true:

- `HEAD` is not exactly `bfeb90fc0465fdc24203d216c97cd1bc7226c0a4` at launch.
- `git rev-parse bb9ba5b^` does not equal the launched `HEAD`.
- LOCOMO DB count before run is not verified as `0`.
- LOCOMO DB is not cleared and verified as `0` after run.
- Any eval toggle is not false:
  - `ENABLE_BACKGROUND_SCORING`
  - `ENABLE_CONTRADICTION_DETECTION`
  - `ENABLE_HIERARCHY_PROCESSING`
- Resolved inference env is not printed into the run log before launch.
- Forced inference stack deviates from the values locked above.
- Any diagnostic/intervention flag beyond `--cleaned --normalize-dates --query-expansion --max-convs 1` is used.
- `--max-questions` is used.
- Benchmark code in the boundary worktree has uncommitted modifications.

## Secondary metrics

Report but do not use as reproduction gates:

- Protocol 4-category score if derivable
- Average query latency versus `8026ms`
- Per-category scores
- Per-category deltas versus 04-24
- `I don't know` / refusal rate if available
- Average retrieved memories

Latency is explicitly out of scope for the reproduction decision. If latency differs materially, record it as a follow-up hypothesis, not as a failure of quality reproduction.

Per-category metrics are descriptive only unless a separate pre-registration defines category-level claims. The 199Q conv-26 run is not sufficient for broad per-category conclusions without additional safeguards.

## Out of scope

- Running current `query-expansion` `HEAD` with `--legacy-context-assembly`
- Isolating benchmark-script changes from `hybrid_retrieval.py` changes inside `bb9ba5b`
- Drawing conclusions about which half of `bb9ba5b` is responsible
- Full LOCOMO 1986Q reproduction
- Any A/B/C intervention scaffold
- Latency mechanism claims
- New parser/prompt/retrieval fixes during the run

## Follow-up rules

If this run is a strong or partial reproduction, the next step is not to promote a fix. The next step is to pre-register a follow-up isolation experiment that separates the two coupled `bb9ba5b` candidates:

1. `benchmark_scripts/locomo_bench_v2.py` answer-context/candidate assembly drift
2. `hybrid_retrieval.py` ruvector/domain/state/vector-cast drift

If this run is a failed reproduction, do not run the legacy-context 199Q as a substitute. Expand bisection/investigation earlier than `bb9ba5b` or into substrate differences.

## Integrity notes

This pre-registration formalizes the methodology rule surfaced by branch inspection:

> When a single commit introduces multiple plausible regression candidates, test the commit boundary first as a unit. Only isolate the candidates after confirming the commit is responsible. Treating coupled changes as independent before testing them as a unit risks confounded diagnostics.

This file pre-registers only the boundary test. It does not approve the benchmark launch. The benchmark must not be run until explicitly approved after this pre-registration is reviewed.
