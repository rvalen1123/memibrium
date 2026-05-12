# LOCOMO runtime configuration archaeology — 2026-04-30

## Purpose

Follow-up to `docs/eval/locomo_environment_substrate_archaeology_2026-04-30.md`.

The prior archaeology showed that the 04-30 reproductions saturate the 15-memory answer-context cap far more often than the 04-24 reference, even when rerun at the original `bfeb90f` code commit. This document records read-only attempts to recover the 04-24 runtime configuration, especially the embedding provider/deployment/dimension used during ingestion.

No benchmark was launched. No DB-writing diagnostic was run.

## Current working state

- Repo: `/home/zaddy/src/Memibrium`
- Branch: `query-expansion`
- Starting HEAD for this archaeology pass: `5535a58 docs: archaeology report substrate drift n_memories regression`
- Working tree before this document: clean and synced with `origin/query-expansion`

## Hypothesis refinement

Commit `f2c9573` predates `bfeb90f`, so the simple hypothesis that the 04-24 run was pre-`f2c9573` and the 04-30 runs were post-`f2c9573` is disconfirmed.

The refined question is runtime-specific rather than default-code-specific:

> What `.env` / container / deployment configuration was active for 04-24 LOCOMO ingestion?

Best-fit candidate from the evidence is embedding-space drift, not necessarily code-default drift:

- 04-24 may have used native 1536-dimensional `text-embedding-3-small`.
- 04-30 currently uses Azure `text-embedding-3-large-1` through `EmbedClient` with `dimensions=1536` requested.
- These are different 1536-dimensional embedding spaces. Cosine thresholds and retrieval cap behavior are not comparable across them.

## 1. 04-24 artifact metadata inspection

Checked all 04-24 JSON artifacts under `docs/eval/results/`.

Artifacts inspected:

- `locomo_baseline_2026-04-24.json`
- `locomo_conv26_noexp_2026-04-24.json`
- `locomo_conv26_query_expansion_2026-04-24.json`
- `locomo_normalized_2026-04-24.json`
- `locomo_query_expansion_2026-04-24.json`
- `locomo_query_expansion_overlap_2026-04-24.json`

Result schema summary:

- Result artifacts contain aggregate metrics and per-question details.
- Per-question detail keys are only:
  - `cat`
  - `conv`
  - `ground_truth`
  - `n_memories`
  - `predicted`
  - `query_time_ms`
  - `question`
  - `score`
- No explicit embedding/provider/runtime metadata is present.
- No artifact-level keys such as `config`, `metadata`, `embedding`, `condition`, `inference_stack_identity`, or `run_metadata` are present.

The 04-24 canary artifact therefore preserves the retrieval symptom (`n_memories`) but not the embedding stack identity.

Relevant 04-24 canary artifact:

- `docs/eval/results/locomo_conv26_query_expansion_2026-04-24.json`
- `overall_score`: 68.09
- `total_questions`: 199
- `expand_query_fallback_count`: 0
- explicit embedding metadata: absent

## 2. Shell history / local runtime traces

Searched local shell history for embedding/Azure/LOCOMO/docker-compose traces.

Observed relevant shell-history lines are late 04-28/04-29 style LOCOMO commands only:

- `set -a; source .env; set +a`
- `export JUDGE_MODEL=gpt-4.1-mini`
- `export ANSWER_MODEL=gpt-4.1-mini`
- `python3 benchmark_scripts/locomo_bench_v2.py --cleaned --normalize-dates --query-expansion ...`

No recovered 04-24 run command was found.

No recovered shell-history line directly captured:

- `AZURE_EMBEDDING_DEPLOYMENT` used on 04-24
- `EMBEDDING_MODEL` used on 04-24
- `EMBEDDING_BASE_URL` used on 04-24
- server image id used on 04-24
- package versions used on 04-24

Local `.env` metadata currently shows:

- `.env` mtime/ctime: `2026-04-23 03:19:27 -0500`
- `.env.example` mtime/ctime: `2026-04-13 10:59:07 -0500`
- `docker-compose.ruvector.yml` mtime/ctime: `2026-04-27 21:47:57 -0500`

Current `.env`, redacted, contains both local and Azure embedding configuration:

- `EMBEDDING_MODEL=nomic-embed-text`
- `EMBEDDING_BASE_URL=http://ollama:11434/v1`
- `AZURE_EMBEDDING_ENDPOINT=https://sector-7.services.ai.azure.com`
- `AZURE_EMBEDDING_DEPLOYMENT=text-embedding-3-large-1`
- `AZURE_EMBEDDING_API_KEY=[REDACTED]`

Because `.env` is untracked, the mtime/ctime is not enough to prove the exact values that were active at 04-24 run time.

## 3. Docker image/container traces

Current Memibrium server image/container:

- image tag: `memibrium-memibrium:latest`
- image id: `sha256:06fa308ac45809e9341354a0cb57811fc0cf3aa6a87d0639d919605389f80c90`
- image created: `2026-04-28T02:49:08Z`
- container name: `memibrium-server`
- container created: `2026-04-28T02:49:09Z`
- container started: `2026-04-30T12:27:04Z`

Current `memibrium-server` env confirms:

- `AZURE_OPENAI_ENDPOINT=https://sector-7.openai.azure.com/`
- `OPENAI_BASE_URL=https://openrouter.ai/api/v1`
- `EMBEDDING_MODEL=nomic-embed-text`
- `EMBEDDING_BASE_URL=http://ollama:11434/v1`
- `AZURE_EMBEDDING_ENDPOINT=https://sector-7.services.ai.azure.com`
- `AZURE_EMBEDDING_DEPLOYMENT=text-embedding-3-large-1`
- `AZURE_API_VERSION=2024-06-01`
- `CHAT_MODEL=gemma4:e4b`
- `AZURE_CHAT_ENDPOINT=https://sector-7.services.ai.azure.com`
- `AZURE_CHAT_DEPLOYMENT=grok-4-20-non-reasoning-1`
- eval toggles false:
  - `ENABLE_BACKGROUND_SCORING=false`
  - `ENABLE_CONTRADICTION_DETECTION=false`
  - `ENABLE_HIERARCHY_PROCESSING=false`

No pre-04-28 `memibrium-server` image/container was recovered.

Other local Docker traces:

- `memibrium-ruvector-db` exists and was created `2026-04-23T22:10:10 -0500`.
- `memibrium-ollama` exists and was created `2026-04-23T22:10:10 -0500`.
- old `memibrium-db` container exists, created `2026-04-08T00:22:26Z`, but it is only a DB container and does not contain server embedding config.
- old image `angry-euler-caa196-ruvector-memory:latest`, created `2026-04-21T06:19:52Z`, is a separate ruvector-memory service image and not the Memibrium server image.

Docker logs for `memibrium-server` over `2026-04-23..2026-04-25` returned no lines, consistent with the current container being created on 04-28. Docker logs for old DB containers did not contain embedding/runtime evidence.

## 4. Git history relevant to runtime defaults

`f2c9573` landed before `bfeb90f`:

- `f2c9573`: `2026-04-23 18:12:25 -0500 docs: update benchmark notes with reconstruction status and failure-mode analysis`
- `bfeb90f`: `2026-04-24 17:41:58 -0500 eval: add query expansion benchmark results and methodology record`

`f2c9573` changed runtime defaults and compose support:

- added `ollama` service
- changed `OPENAI_BASE_URL` default from `https://api.openai.com/v1` to `https://openrouter.ai/api/v1`
- changed `EMBEDDING_MODEL` default from `text-embedding-3-small` to `nomic-embed-text`
- added `EMBEDDING_BASE_URL` default `http://ollama:11434/v1`
- added Azure embedding env support:
  - `AZURE_EMBEDDING_ENDPOINT`
  - `AZURE_EMBEDDING_DEPLOYMENT`
  - `AZURE_EMBEDDING_API_KEY`
- hardcoded compose `CHAT_MODEL: gemma4:e4b` unless overridden elsewhere
- bind-mounted repo into `/app`

Nearby `aee3bc7`, dated `2026-04-24 01:06:04 -0500`, changed the benchmark script to remove a hardcoded Azure API key fallback and use env-only for `AZURE_CHAT_API_KEY`.

This is relevant to the chat/judge stack archaeology, but it does not recover the embedding stack used by server ingestion.

## 5. Session-memory evidence

Prior session summaries add useful but non-authoritative context:

- 2026-04-16 benchmark dashboard reported embeddings as `openai/text-embedding-3-small` and achieved 10/10 small recall accuracy.
- 2026-04-17/18 local embedding migration work moved toward `nomic-embed-text` and encountered 768-vs-1536 HNSW/index issues.
- 2026-04-21 notes documented local Ollama `nomic-embed-text` as 768-dimensional and `text-embedding-3-small` as 1536-dimensional.
- 2026-04-26 LOCOMO/Azure notes mention Azure embeddings and the need to pass `dimensions=1536` for `text-embedding-3-large`/deployment-style names such as `text-embedding-3-large-1`.
- One prior summary explicitly records April 22 environment-style details:
  - `AZURE_OPENAI_ENDPOINT=https://sector-7.openai.azure.com/`
  - `AZURE_OPENAI_DEPLOYMENT=gpt-4.1-mini`
  - `AZURE_API_VERSION=2024-12-01-preview`
  - `AZURE_EMBEDDING_ENDPOINT=https://sector-7.openai.azure.com/`
  - `AZURE_EMBEDDING_DEPLOYMENT=text-embedding-3-small`

Caveat: session summaries are useful leads, not direct runtime logs. The April 22 `AZURE_EMBEDDING_DEPLOYMENT=text-embedding-3-small` line is currently the strongest recovered positive evidence for the candidate 04-24 embedding stack, but it is not a preserved 04-24 container inspect or benchmark metadata record.

## 6. Current effective embedding path

The current code path probe from the preceding archaeology pass showed `EmbedClient` resolves to Azure embeddings when `AZURE_EMBEDDING_ENDPOINT` and key are present:

- effective client: `AzureOpenAI`
- effective endpoint: `https://sector-7.services.ai.azure.com`
- effective model/deployment: `text-embedding-3-large-1`
- `dimensions` argument in active `EmbedClient.embed()` path: 1536

The diagnostic `/mcp/test_embeddings` endpoint separately reported:

- Ollama probe: `nomic-embed-text`, 1536 dimensions, endpoint `http://ollama:11434/v1`
- Azure probe: `text-embedding-3-large-1`, 3072 native dimensions from the test endpoint because that diagnostic call does not pass `dimensions=1536`

Interpretation:

- The active ingestion path is not simply the local `nomic-embed-text` path advertised by `EMBEDDING_MODEL`.
- Azure embedding env takes precedence in `EmbedClient`.
- Current formal 04-30 runs likely ingested with Azure `text-embedding-3-large-1` using `dimensions=1536` in the active embed path.

## 7. Findings

Recovered facts:

1. The 04-24 artifacts do not capture embedding/provider/runtime metadata.
2. Local shell history does not recover the exact 04-24 run command or server env.
3. No pre-04-28 `memibrium-server` image/container/log was recovered.
4. Current `memibrium-server` was recreated on 04-28 and carries `AZURE_EMBEDDING_DEPLOYMENT=text-embedding-3-large-1`.
5. `f2c9573` predates `bfeb90f`, so default-code chronology alone does not explain the difference.
6. Prior session memory contains a strong lead that an April 22 environment used `AZURE_EMBEDDING_DEPLOYMENT=text-embedding-3-small` with Azure endpoint `https://sector-7.openai.azure.com/`.
7. The current environment uses Azure `text-embedding-3-large-1` through `https://sector-7.services.ai.azure.com`, with 1536 dimensions requested by active `EmbedClient`.

## 8. Interpretation

The best-supported current hypothesis is embedding deployment/runtime drift:

- Candidate 04-24 stack: Azure/OpenAI `text-embedding-3-small`, native 1536 dimensions.
- Current 04-30 stack: Azure `text-embedding-3-large-1`, active embed path with `dimensions=1536`.

This would explain why:

- the same question list and same code commit can retrieve different evidence,
- `n_memories=15` saturation jumps from 31/199 to roughly 170/199,
- score remains depressed across both current code and `bfeb90f` under the same 04-30 substrate,
- direct embedding probes still succeed for current deployments.

This is not yet proven because the exact 04-24 runtime config was not recovered from a primary artifact.

## 9. Recommended next move

Do not launch a benchmark yet unless the user explicitly approves a preregistered run.

Recommended next action is to draft, not launch, an embedding-reproduction preregistration using the best-evidence candidate:

- code: exact `bfeb90f` worktree
- inference stack: forced canonical 04-24 chat/judge stack already used in the boundary test
- embedding stack candidate: force `text-embedding-3-small` native 1536-dimensional embeddings via the recovered/available Azure embedding endpoint, with no `dimensions` projection unless the API requires it
- DB: clean LOCOMO domains before and after; fresh ingestion required
- required metadata capture before formal run:
  - server image id / created time
  - package versions
  - effective embed client/provider/endpoint/deployment/dimension
  - source data hash and question-list hash
  - post-ingest counts for `memories`, `entities`, `entity_relationships`, `temporal_expressions`, `memory_snapshots`
  - per-question `n_memories`; if possible, retrieval scores and memory ids

Decision rules should include both score/fallback and retrieval-shape recovery:

- Strong: score within ±2pp of 68.09, fallback ≤2/199, and `n_memories` distribution returns close to the 04-24 shape.
- Partial: score within ±5pp and fallback ≤5/199, with `n_memories` moving materially toward the 04-24 shape.
- Failed: outside ±5pp, fallback >5/199, or `n_memories` still matches the 04-30 saturated pattern.

## 10. Remaining external authority check

Azure/Foundry usage logs would be the most authoritative remaining source for 04-24 embedding deployment history. If accessible, check the sector-7 resource for embedding deployment calls around the 04-24 ingestion window.
