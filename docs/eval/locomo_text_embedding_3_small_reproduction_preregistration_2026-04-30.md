# LOCOMO Conv-26 text-embedding-3-small substrate reproduction pre-registration

Date: 2026-04-30
Branch where preregistration is recorded: `query-expansion`
Target run code: exact `bfeb90f` / `bb9ba5b^` worktree
Reference artifact: `docs/eval/results/locomo_conv26_query_expansion_2026-04-24.json`
Reference score: `68.09%`
Reference query-expansion fallback: `0/199`
Reference retrieval shape: mean `n_memories=11.65`, `n_memories=15` saturation `31/199 = 15.6%`

## Purpose

This experiment asks whether forcing the best-evidence candidate 04-24 embedding substrate, `text-embedding-3-small`, recovers both:

1. the 04-24 conv-26 query-expansion score, and
2. the 04-24 returned-memory-count distribution.

This is an embedding-substrate reproduction test, not a new retrieval intervention.

The mechanism under test is that 04-30 reproductions degraded because fresh LOCOMO ingestion used a different embedding space from the 04-24 reference. Specifically, the candidate drift is from `text-embedding-3-small` 1536-dimensional embeddings to `text-embedding-3-large-1` embeddings requested at 1536 dimensions.

## Why this experiment exists

The locked canonical-stack reproduction and the exact `bfeb90f` boundary rerun both failed to reproduce the 04-24 score even with the forced canonical chat/judge stack and zero query-expansion fallback:

- 04-24 reference: `68.09%`, fallback `0/199`
- 04-30 exact `bfeb90f` boundary rerun: `61.81%`, fallback `0/199`
- Delta: `-6.28pp`

That result exonerated simple post-`bfeb90f` Memibrium code drift. Subsequent archaeology found that retrieval shape changed materially:

- 04-24 reference: mean `n_memories=11.65`, median `12`, `n_memories=15` for `31/199` questions
- 04-30 `bfeb90f` boundary rerun: mean `n_memories=14.70`, median `15`, `n_memories=15` for `170/199` questions

The same question list and original code commit produced much more cap-saturated retrieval on 04-30. This is strong mechanistic evidence for runtime/substrate drift.

## Hypothesis under test

The 04-24 reference was produced using `text-embedding-3-small` 1536-dimensional embeddings, while the 04-30 reproductions ingested LOCOMO using `text-embedding-3-large-1` with `dimensions=1536` requested by `EmbedClient`.

If this embedding-space drift caused the regression, then forcing `text-embedding-3-small` for fresh LOCOMO ingestion at `bfeb90f`, while keeping the canonical chat/judge stack fixed, should move both score and `n_memories` distribution back toward the 04-24 reference.

## Evidence status and limitations

Primary 04-24 runtime evidence was not recovered.

Evidence supporting this candidate is indirect:

- 04-24 artifacts do not capture embedding runtime metadata, but they do capture the distinctive `n_memories` distribution.
- Session-memory archaeology recovered April 22 environment-style evidence for `AZURE_EMBEDDING_DEPLOYMENT=text-embedding-3-small`.
- Current server env and code path use Azure `AZURE_EMBEDDING_DEPLOYMENT=text-embedding-3-large-1` with `dimensions=1536` requested in `EmbedClient`.
- The 04-30 `bfeb90f` and current-code runs show the same saturated retrieval shape despite different code commits.

Confounds and limitations:

- The exact 04-24 embedding model is inferred, not proven by a primary container/env/log artifact.
- If this experiment succeeds, it supports the embedding-substrate hypothesis but does not uniquely prove that no other substrate drift occurred.
- If this experiment fails, the `text-embedding-3-small` candidate is rejected as the primary explanation and the next suspects become dependency/image drift, DB/index/substrate drift, and provider-side model snapshot drift.

## Probe results before preregistration

Two cheap probes were run before drafting this preregistration.

### A. Dimension-passing convention

Code/history check:

```bash
grep -rn "dimensions" --include="*.py" . | grep -iE "embed|EmbedClient|embedding" | head -40
git grep -n "dimensions" bfeb90f -- '*.py' | grep -iE "embed|EmbedClient|embedding" | head -40
```

Result:

- `f2c9573^`: `EmbedClient` directly called `self.client.embeddings.create(input=[text], model=EMBED_MODEL)` with no `dimensions` argument.
- `f2c9573`, `bfeb90f`, and current `HEAD`: Azure embedding path sets `self._dimensions = 1536 if _use_azure_embed else None` and passes `kwargs['dimensions'] = self._dimensions` in both single and batch embedding calls.

Interpretation:

- At the target run code `bfeb90f`, forcing Azure `text-embedding-3-small` will still pass `dimensions=1536`.
- For `text-embedding-3-small`, this matches the native output dimensionality, so the actual variable being tested is the embedding model/deployment, not an additional dimension-truncation switch.
- The comparison against current `text-embedding-3-large-1` still matters because `text-embedding-3-large` native output is 3072, and the active current path truncates/requests 1536.

### B. Candidate deployment availability

Availability probes using `AzureOpenAI` succeeded for both relevant endpoint forms:

- `https://sector-7.openai.azure.com/`, deployment `text-embedding-3-small`: success, `1536` dimensions, model `text-embedding-3-small`
- `https://sector-7.services.ai.azure.com`, deployment `text-embedding-3-small`: success, `1536` dimensions, model `text-embedding-3-small`
- `https://sector-7.openai.azure.com/`, deployment `text-embedding-3-large-1`: success, `3072` native dimensions, model `text-embedding-3-large`
- `https://sector-7.services.ai.azure.com`, deployment `text-embedding-3-large-1`: success, `3072` native dimensions, model `text-embedding-3-large`

No benchmark data was produced by these probes.

## Fixed run configuration

Run from the existing or recreated exact `bfeb90f` worktree:

```bash
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

- `HEAD == bfeb90fc0465fdc24203d216c97cd1bc7226c0a4`
- `git rev-parse bb9ba5b^ == bfeb90fc0465fdc24203d216c97cd1bc7226c0a4`
- no uncommitted changes affecting benchmark execution

## Required server embedding stack

The server container must be recreated with effective embedding stack:

```text
AZURE_EMBEDDING_ENDPOINT=https://sector-7.openai.azure.com/
AZURE_EMBEDDING_DEPLOYMENT=text-embedding-3-small
AZURE_EMBEDDING_API_KEY=[present, redacted]
```

`EmbedClient` must resolve to:

```text
effective_client=AzureOpenAI
effective_embedding_endpoint=https://sector-7.openai.azure.com/
effective_embedding_deployment=text-embedding-3-small
effective_dimensions_arg=1536
effective_output_dimensions=1536
```

The resolved effective embedding identity must be logged before formal launch. Do not rely only on `EMBEDDING_MODEL` because `AZURE_EMBEDDING_*` overrides the local embedding path in `EmbedClient`.

Acceptable endpoint fallback if the historical endpoint becomes unavailable before execution:

- `https://sector-7.services.ai.azure.com` with deployment `text-embedding-3-small`, only if the comparison artifact explicitly records that the endpoint differed from the preferred historical candidate.

This fallback weakens the historical-runtime claim but still tests the model/deployment hypothesis.

## Forced canonical inference stack

The answer, judge, and query-expansion model stack must remain the forced canonical stack already used in the boundary reproduction:

```text
AZURE_CHAT_ENDPOINT=https://sector-7.services.ai.azure.com/models
ANSWER_MODEL=gpt-4.1-mini
JUDGE_MODEL=gpt-4.1-mini
AZURE_CHAT_DEPLOYMENT=gpt-4.1-mini
AZURE_OPENAI_DEPLOYMENT=gpt-4.1-mini
CHAT_MODEL=gpt-4.1-mini
USE_QUERY_EXPANSION=1
OPENAI_BASE_URL=<unset for benchmark process>
AZURE_OPENAI_ENDPOINT=<unset for benchmark process>
temperature=0 in benchmark code
```

The benchmark process env and the server container env are related but distinct. The benchmark process must force chat/judge/query-expansion. The server container must force embedding ingestion/retrieval.

## Required pre-run hygiene

Docker must be reachable, and these containers must be up after any server recreation:

- `memibrium-server`
- `memibrium-ruvector-db`
- `memibrium-ollama`

Eval toggles inside `memibrium-server` must be false:

```text
ENABLE_BACKGROUND_SCORING=false
ENABLE_CONTRADICTION_DETECTION=false
ENABLE_HIERARCHY_PROCESSING=false
```

LOCOMO DB must be clear before launch:

```sql
SELECT count(*) FROM memories WHERE domain LIKE 'locomo-%';
```

Required pre-launch value: `0`.

If not zero, run `scripts/clear_locomo_domains.sh` from the main checkout and verify again.

## Metadata capture requirements

The formal run log or companion metadata artifact must capture, without secrets:

- run code commit SHA and worktree path
- server image id and image created time
- server container created/started time
- sanitized server env for embedding, chat, toggles, DB, and ruvector vars
- installed package versions for at least:
  - `openai`
  - `httpx`
  - `asyncpg`
  - `pydantic`
  - `starlette`
  - `uvicorn`
- effective embedding provider/client
- effective embedding endpoint
- effective embedding deployment/model
- `dimensions` argument passed to embedding calls
- observed output vector dimension from a non-ingesting probe
- DB extension versions
- `memories.embedding` type and dimension
- LOCOMO source data sha256 and conv-26 question-list hash
- pre-ingest LOCOMO memory count
- post-ingest, pre-cleanup counts for:
  - `memories`
  - `entities`
  - `entity_relationships`
  - `temporal_expressions`
  - `memory_snapshots`
- per-question `n_memories`
- if available without code surgery, retrieval scores and memory ids used for answer context
- post-cleanup LOCOMO memory count

If `n_memories` is not captured per question, the run is disqualified because the mechanism criterion cannot be evaluated.

## Benchmark command

After pre-run hygiene and metadata capture, run exactly one full conv-26 query-expansion benchmark from the `bfeb90f` worktree:

```bash
set -a
source /home/zaddy/src/Memibrium/.env
set +a

# Forced canonical chat/judge/query-expansion stack
export AZURE_CHAT_ENDPOINT="https://sector-7.services.ai.azure.com/models"
export ANSWER_MODEL="gpt-4.1-mini"
export JUDGE_MODEL="gpt-4.1-mini"
export AZURE_CHAT_DEPLOYMENT="gpt-4.1-mini"
export AZURE_OPENAI_DEPLOYMENT="gpt-4.1-mini"
export CHAT_MODEL="gpt-4.1-mini"
export USE_QUERY_EXPANSION="1"
unset OPENAI_BASE_URL
unset AZURE_OPENAI_ENDPOINT

python3 benchmark_scripts/locomo_bench_v2.py \
  --cleaned --normalize-dates \
  --max-convs 1
```

`bfeb90f` does not expose a `--query-expansion` CLI flag; query expansion is enabled by `USE_QUERY_EXPANSION=1`.

Do not use any retrieval intervention or diagnostic flag for the formal run.

A pre-launch sanity check of `<=5` questions in `/tmp/` is permitted only to verify worktree wiring, server reachability, and env propagation. Sanity-check results must not be copied to `docs/eval/results/` and must not be used for or against the formal verdict.

## Artifact policy

Use condition-specific names. Expected final artifacts under `docs/eval/results/`:

- `locomo_conv26_text_embedding_3_small_199q_2026-04-30.json`
- `locomo_conv26_text_embedding_3_small_199q_2026-04-30.log`
- `locomo_text_embedding_3_small_199q_comparison_2026-04-30.json`
- `locomo_text_embedding_3_small_199q_comparison_2026-04-30.md`

Comparison artifacts must include:

- locked decision rules verbatim
- verdict and threshold driver
- score/fallback summary
- `n_memories` mean, median, min/max, and histogram
- reference vs current `n_memories=15` saturation rate
- inference-stack identity
- embedding-stack identity
- run commit and worktree
- server image/package versions
- source-data and question-list hashes
- DB post-ingest counts before cleanup
- paired overlap vs 04-24 reference with category alias normalization
- cleanup confirmation

## Locked decision rules

These thresholds are fixed before seeing the formal result.

### Strong reproduction

All must hold:

1. Score within ±2pp of `68.09%`: `66.09%` to `70.09%` inclusive.
2. Query-expansion fallback `<=2/199`.
3. `n_memories` distribution within tolerance of 04-24 reference:
   - mean within ±1.5 of `11.65`: `10.15` to `13.15` inclusive
   - `n_memories=15` saturation rate within ±10pp of `15.6%`: `5.6%` to `25.6%` inclusive

### Partial reproduction

All must hold:

1. Score within ±5pp of `68.09%`: `63.09%` to `73.09%` inclusive.
2. Query-expansion fallback `<=5/199`.
3. `n_memories` distribution moves materially toward the 04-24 reference:
   - mean reduces by at least `1.5` from current `14.70`, i.e. mean `<=13.20`
   - `n_memories=15` saturation drops by at least `30pp` from current `85.4%`, i.e. saturation `<=55.4%`

### Failed reproduction

Any one is sufficient:

1. Score outside ±5pp of `68.09%`.
2. Query-expansion fallback `>5/199`.
3. `n_memories` distribution remains close to the 04-30 saturated pattern:
   - mean `>=14.0`, or
   - `n_memories=15` saturation `>=75%`.
4. Per-question `n_memories` is not captured.
5. Effective embedding stack is not `text-embedding-3-small` with 1536-dimensional output.

If score is in range but `n_memories` remains saturated under the failed criterion, the verdict is failed reproduction for this mechanistic hypothesis. Do not reinterpret that outcome as success.

Latency is observational only and is not a decision gate.

## Disqualifiers

The run is invalid for this preregistration if any of the following occur:

- target code is not exact `bfeb90f`
- LOCOMO DB is nonzero before launch and not cleaned to zero
- server effective embedding model/deployment is not `text-embedding-3-small`
- observed embedding output dimension is not `1536`
- benchmark process does not force canonical `gpt-4.1-mini` chat/judge/query-expansion stack
- query expansion is not enabled via `USE_QUERY_EXPANSION=1`
- any retrieval intervention/diagnostic flag is used in the formal run
- answer/judge/query-expansion calls silently route to a non-`gpt-4.1-mini` model
- per-question `n_memories` is absent from the result artifact
- result artifact is partial, overwritten, or lacks 199 conv-26 questions
- LOCOMO source question hash differs from the 04-24 reference without explicit disqualification note
- post-run cleanup is not performed or not verified

## Interpretation plan

If strong or partial reproduction is achieved, embedding substrate drift is supported as the primary explanation for the 04-24 to 04-30 regression. Future LOCOMO work should pin and log embedding identity/dimensions, and the `text-embedding-3-small` reproduction result becomes the restored canonical embedding baseline unless later primary evidence supersedes it.

If reproduction fails because score remains low and `n_memories` remains saturated, reject the `text-embedding-3-small` candidate as sufficient explanation and pivot to dependency/image drift and DB/index/substrate drift.

If score recovers but `n_memories` does not, treat this as failed for the mechanistic hypothesis and investigate compensating drift rather than claiming embedding-substrate validation.

If `n_memories` recovers but score does not, embedding substrate is likely a real mechanism but not the only cause; next preregistration should target dependency/image or model-snapshot drift with the recovered embedding stack held fixed.

## Do not launch from this document alone

This document authorizes only a future pre-registered run after user approval. It does not authorize immediate benchmark launch in the same turn/session.
