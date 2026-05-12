# LOCOMO Conv-26 Canonical-Stack Reproduction Pre-registration

Date: 2026-04-30
Branch: `query-expansion`
Current code target: `541c311`
Reference artifact: 2026-04-24 conv-26 query-expansion canary at `bfeb90f`

## Purpose

This experiment asks whether the 2026-04-24 conv-26 query-expansion result is recoverable when the current benchmark code is run with the 04-24 inference stack forced explicitly.

The question is reproduction, not improvement:

> Does forcing the 04-24 inference stack on current code reproduce the 04-24 conv-26 query-expansion numbers?

This pre-registration does **not** compare against the 2026-04-29 Arm A result as a valid baseline. The 04-29 result is treated as substrate-contaminated because its artifact lacks inference-stack metadata and exhibited a 57/199 query-expansion fallback rate with a category trade signature consistent with model/provider drift.

## Historical reference

Primary reference: 2026-04-24 conv-26 query-expansion canary, committed by `bfeb90f`.

Reference artifact paths:

- `docs/eval/results/locomo_conv26_query_expansion_2026-04-24.json`
- duplicate historical copy: `docs/eval/locomo_results_conv26_exp.json`

Reference values:

- Conv-26 score: `68.09%` (`overall_score` in the artifact)
- Protocol 4-category conv-26 score was reported in prior summaries as `79.93%`, but the 04-24 artifact itself does not persist a `protocol_4cat_overall` field
- Query-expansion fallback: `0/199`
- Average query latency: `8026ms`
- Inference stack encoded in `bfeb90f` benchmark source:
  - Endpoint: `https://sector-7.services.ai.azure.com/models`
  - Path: `/chat/completions`
  - Answer model: `gpt-4.1-mini`
  - Judge model: `gpt-4.1-mini`
  - Query-expansion model: `gpt-4.1-mini` via `ANSWER_MODEL` default path
  - Temperature: `0`
  - API key: `AZURE_CHAT_API_KEY` env var

## Archaeology smoke motivating this run

Smoke artifact:

- `docs/eval/results/locomo_conv26_canonical_stack_smoke_10q_2026-04-30.json`
- `docs/eval/results/locomo_conv26_canonical_stack_smoke_10q_2026-04-30.log`

Smoke design:

- Current code at `541c311`
- Conv-26, first 10 evaluated questions
- `--cleaned --normalize-dates --query-expansion --max-convs 1 --max-questions 10`
- LOCOMO DB was clean before run and cleaned after run
- Forced 04-24 inference stack through env and captured resolved env in log

Smoke result:

- Overall score: `80.0%` (`8.0/10`)
- Query-expansion fallback: `0/10`
- Average query latency: `3634ms`

Interpretation of smoke:

- The 04-29 fallback collapse is strongly attributable to inference-stack drift, not the current parser/code path alone.
- The latency did not reproduce 04-24 latency and is therefore kept out of the quality reproduction decision rule.
- The 10Q category breakdown is too small for category-level claims; it is not used as evidence of temporal/single-hop/multi-hop recovery.

## Hypothesis

Forcing the 04-24 inference stack on current `541c311` code will recover the 04-24 conv-26 query-expansion fallback behavior and most or all of the 04-24 conv-26 quality.

Expected result:

- Query-expansion fallback near zero (`<=2/199` expected)
- Conv-26 full 5-category score near `68.09%`
- Protocol 4-category score near the 04-24 conv-26 reference (`79.93%`)

Latency is expected to differ from 04-24 and is observational only.

## Fixed run configuration

Run from repo root:

```bash
cd /home/zaddy/src/Memibrium
```

Required commit/branch state:

```bash
git status --short --branch
git rev-parse --short HEAD
```

Expected:

- branch: `query-expansion`
- commit: `541c311` or a descendant that only adds this pre-registration/artifact documentation and does not modify benchmark execution code
- no unstaged code changes that affect benchmark execution

Required LOCOMO DB hygiene before run:

```bash
docker exec -i memibrium-ruvector-db psql -U memory -d memory -t -A -c \
  "SELECT count(*) FROM memories WHERE domain LIKE 'locomo-%';"
```

Must be `0`. If not, run:

```bash
scripts/clear_locomo_domains.sh
```

and verify `0` again.

Forced inference stack:

```bash
set -a
source .env
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

Benchmark command:

```bash
python3 benchmark_scripts/locomo_bench_v2.py \
  --cleaned --normalize-dates --query-expansion \
  --max-convs 1
```

Do not use `--max-questions` for the pre-registered run. The target is full conv-26 (`199` questions).

After run, copy the volatile output and log into `docs/eval/results/` with date/condition names before cleanup or further runs.

Cleanup after run:

```bash
scripts/clear_locomo_domains.sh
```

Verify remaining LOCOMO count is `0`.

## Decision rules

Primary quality reference: 04-24 conv-26 artifact `overall_score` of `68.09%`.

Primary mechanism reference: 04-24 query-expansion fallback `0/199`.

### Strong reproduction

Declare strong reproduction if both are true:

- Full 5-category conv-26 score is within ±2 percentage points of `68.09%`, i.e. `[66.09%, 70.09%]`
- Query-expansion fallback is `<=2/199`

Interpretation: 04-24 capability is fully recoverable on current code when the inference stack is forced. The 04-29 Arm A artifact should not be used as a quality baseline.

### Partial reproduction

Declare partial reproduction if both are true:

- Full 5-category conv-26 score is within ±5 percentage points of `68.09%`, i.e. `[63.09%, 73.09%]`
- Query-expansion fallback is `<=5/199`

and the run does not meet strong reproduction.

Interpretation: model/provider drift accounts for most of the 04-29 divergence, but residual code/DB/provider-side differences may remain. Do not promote downstream A/B/C interventions until a new canonical baseline is established.

### Failed reproduction

Declare failed reproduction if either is true:

- Full 5-category conv-26 score is outside ±5 percentage points of `68.09%`
- Query-expansion fallback is `>5/199`

Interpretation: forcing the canonical inference stack is insufficient. Code changes between `bfeb90f` and `541c311`, DB substrate differences, prompt/parser differences, or provider-side changes also materially affect the result. Next step becomes bisection or a `bfeb90f` worktree smoke/full conv-26 reproduction, not an intervention experiment.

## Secondary metrics

Report but do not use as reproduction gates:

- Protocol 4-category score versus `79.93%`
- Average query latency versus `8026ms`
- Per-category scores
- Per-category deltas versus 04-24
- `I don't know` / refusal rate if available
- Average retrieved memories

Latency is explicitly out of scope for the reproduction decision. If latency differs materially, record it as a follow-up hypothesis, not a failure of quality reproduction.

Per-category metrics are descriptive only unless the full 199Q run provides enough support for a separate pre-registered category-level claim. The 10Q smoke category split must not be cited as evidence of category recovery.

## Out of scope

- Full LOCOMO 1986Q reproduction
- Any A/B/C intervention scaffold based on the contaminated 04-29 Arm A reference
- Latency mechanism claims
- Promotion or rejection of query expansion as a default production feature
- New parser/prompt fixes during the run

## Expected artifact policy

Commit after run:

- Pre-registration file
- Smoke artifacts already referenced above
- Full conv-26 canonical-stack result JSON
- Full conv-26 canonical-stack run log with resolved env
- A compact result summary markdown with decision-rule verdict

Do not commit:

- stale `/tmp` files unrelated to this run
- partial interrupted artifacts unless clearly marked as interrupted
- raw secrets or API keys

## Integrity notes

This pre-registration exists because a historical artifact lacked full inference-stack metadata. The canonical-stack smoke showed that printing resolved env at runtime is necessary and sufficient to avoid repeating that failure mode. Every future benchmark artifact used as a reference must capture inference-stack identity directly in the artifact or in an adjacent committed log.
