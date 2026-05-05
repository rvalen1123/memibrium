# LOCOMO environment/substrate archaeology — 2026-04-30

## Trigger finding

The `bb9ba5b^ == bfeb90f` boundary reproduction failed against the 04-24 reference even though it used the original code commit and the forced canonical chat/judge stack:

- 04-24 reference: 68.09%, 0/199 query-expansion fallback
- 04-30 `bfeb90f` rerun: 61.81%, 0/199 fallback
- Delta: -6.28pp

This exonerates simple Memibrium code drift and shifts the investigation to environment/substrate drift.

## Methodology bank rule

Code-level bisection assumes the regression is in code. Before bisecting, verify that environmental factors — dependency versions, embedding model, judge model snapshot, LOCOMO data integrity, and DB/substrate state — have not changed between the reference run and the current run. Bisecting code drift cannot find regressions caused by environmental drift, no matter how rigorously the bisection is conducted.

## Read-only checks performed

No benchmark was launched. No DB-writing diagnostic was run. LOCOMO DB remained clean after prior cleanup.

### A. Artifact / data integrity

Current cleaned data file:

- `/tmp/locomo10_cleaned.json`
- sha256: `1b304c7c3d98ff9cef5efd02100a4dfa93fc9ee3babaceca752df9f9aa90b42d`
- bytes: 2,168,972
- dataset length: 10 conversations
- first sample: `conv-26`
- conv-26 QA count: 199
- conv-26 conversation-turn count as loaded from JSON: 56

Other local LOCOMO copies differ:

- `/tmp/locomo/data/locomo10_cleaned.json`: sha256 `e1c44a19e0dd78e1a3932a7c1c5d94b21d5b6efae6e353001f8b49a9f9a4b022`, first conv QA count 198
- `/tmp/locomo/data/locomo10.json`: sha256 `79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4`, first conv QA count 199

Question-list integrity across compared benchmark artifacts:

- `docs/eval/results/locomo_conv26_query_expansion_2026-04-24.json`: 199 questions, question-list sha256 `07717c689e2e5a228b63d46f3b712a92185a8fa32aed524c4f3e7f9714ba556f`
- `docs/eval/results/locomo_conv26_bb9ba5b_parent_boundary_199q_2026-04-30.json`: 199 questions, same question-list sha256
- `docs/eval/results/locomo_conv26_canonical_stack_199q_2026-04-30.json`: 199 questions, same question-list sha256

Interpretation:

- Compared artifacts use the same question sequence.
- There are multiple LOCOMO source-file variants in `/tmp`; data-source provenance must be explicitly pinned for future runs.
- The benchmark script uses `/tmp/locomo10_cleaned.json` for `--cleaned`; this file is outside git and not version-controlled.

### B. Dependencies / image state

Repository dependency spec:

- `requirements.txt` is unchanged between `bfeb90f` and current `HEAD`.
- It uses broad lower bounds, not locked versions:
  - `asyncpg>=0.29.0`
  - `openai>=1.30.0`
  - `starlette>=0.37.0,<1.0.0`
  - `uvicorn>=0.30.0`
  - `httpx>=0.27.0`

Current server container:

- Image: `memibrium-memibrium`
- Image id: `sha256:06fa308ac45809e9341354a0cb57811fc0cf3aa6a87d0639d919605389f80c90`
- Image created: `2026-04-28T02:49:08Z`
- Container started: `2026-04-30T12:27:04Z`
- Python: 3.11.15
- Installed package versions observed:
  - `asyncpg==0.31.0`
  - `httpx==0.28.1`
  - `openai==2.32.0`
  - `pydantic==2.13.1`
  - `starlette==0.52.1`
  - `uvicorn==0.44.0`

Current Dockerfile uses `FROM python:3.11-slim` and `pip install --no-cache-dir -r requirements.txt`, so rebuilds float to newer dependency versions unless constrained by an external cache or lockfile.

Interpretation:

- Dependency drift remains plausible. The current server image was rebuilt on 04-28 with unconstrained dependency ranges.
- The 04-24 reference may have used older installed package versions even at the same source commit.

### C. Embedding / retrieval substrate configuration

Current server environment, redacted:

- `EMBEDDING_BASE_URL=http://ollama:11434/v1`
- `EMBEDDING_MODEL=nomic-embed-text`
- `AZURE_EMBEDDING_ENDPOINT=https://sector-7.services.ai.azure.com`
- `AZURE_EMBEDDING_DEPLOYMENT=text-embedding-3-large-1`
- `AZURE_API_VERSION=2024-06-01`
- `RUVECTOR_GNN=true`
- `USE_RUVECTOR` implied by compose / DB substrate
- Eval toggles all false:
  - `ENABLE_BACKGROUND_SCORING=false`
  - `ENABLE_CONTRADICTION_DETECTION=false`
  - `ENABLE_HIERARCHY_PROCESSING=false`

Current Ollama container:

- `ollama list` returned no models.
- `/root/.ollama` contains only `id_ed25519` and `id_ed25519.pub` in the inspected max-depth listing.

Important code/config history:

- Commit `f2c9573` changed default embeddings from cloud OpenAI-compatible `text-embedding-3-small` to local Ollama `nomic-embed-text` and added the Ollama service.
- The diff shows:
  - `OPENAI_BASE_URL` default changed from `https://api.openai.com/v1` to `https://openrouter.ai/api/v1`
  - `EMBEDDING_MODEL` default changed from `text-embedding-3-small` to `nomic-embed-text`
  - `EMBEDDING_BASE_URL` default added as `http://ollama:11434/v1`
  - Azure embedding endpoint/deployment env support added

Interpretation:

- Embedding substrate drift is the highest-probability current culprit.
- The 04-24 reference was generated before/around the commit that moved defaults from `text-embedding-3-small` to `nomic-embed-text`; the current environment advertises local `nomic-embed-text`, while also carrying Azure embedding env vars that are not necessarily used.
- Because embeddings define the vector substrate, identical benchmark code can retrieve different evidence and score differently.

### D. DB / schema / substrate state

Current DB extension/schema state:

- PostgreSQL extensions: `plpgsql:1.0`, `ruvector:0.3.0`
- `memories.embedding` type: `ruvector(1536)`
- Public tables include:
  - `contradictions`
  - `entities`
  - `entity_relationships`
  - `memories`
  - `memory_edges`
  - `memory_snapshots`
  - `temporal_expressions`
  - `user_feedback`

Current LOCOMO cleanup state:

- `SELECT count(*) FROM memories WHERE domain LIKE 'locomo-%'` returned 0.

Current DB image:

- `ruvnet/ruvector-postgres:latest`
- image id / repo digest: `sha256:d9f86747f3af63c354bc40b1cc4368575fcdbf16ad7582cb82ef20f0d8907dac`
- image created: `2026-03-03T18:18:30Z`
- extension version: `ruvector 0.3.0`

Schema-order asymmetry note:

- Current schema has `entity_relationships`, but eval toggles disabled hierarchy processing for the formal runs, so entity graph population should not affect those runs unless older 04-24 conditions had hierarchy processing enabled or pre-populated side tables.
- The formal run logs show only memories count indirectly; relationship/entity counts were not captured before cleanup.

Interpretation:

- A clean LOCOMO memory domain does not prove identical retrieval substrate. Non-LOCOMO rows, ruvector index behavior, extension version, embedding dimensionality/model, and side tables can still differ.
- Future DB-writing diagnostics should capture post-ingest counts before cleanup: `memories`, `entities`, `entity_relationships`, `temporal_expressions`, `memory_snapshots`, plus memory state/type/domain counts.

### E. Foundry / judge / model drift

Forced run env captured:

- `AZURE_CHAT_ENDPOINT=https://sector-7.services.ai.azure.com/models`
- `AZURE_CHAT_DEPLOYMENT=gpt-4.1-mini`
- `AZURE_OPENAI_DEPLOYMENT=gpt-4.1-mini`
- `CHAT_MODEL=gpt-4.1-mini`
- `ANSWER_MODEL=gpt-4.1-mini`
- `JUDGE_MODEL=gpt-4.1-mini`
- `OPENAI_BASE_URL=<unset>`
- `AZURE_OPENAI_ENDPOINT=<unset>`
- query-expansion fallback: `0/199`

Interpretation:

- Chat/judge provider-side drift remains possible, but is less favored than embedding/substrate drift because the two 04-30 runs show nearly identical degraded scores at different code commits with the same forced chat stack.
- No preserved 04-24 model-version trace was found in result artifacts; only model names are inferred from the locked prereg/user notes.

## Additional artifact-level signal

Returned-memory count changed materially between the 04-24 reference and 04-30 reproductions:

- 04-24 reference: mean `n_memories` 11.65, median 12, min/max 5/15
- 04-30 canonical run: mean 14.68, median 15, min/max 11/15
- 04-30 `bfeb90f` boundary run: mean 14.70, median 15, min/max 10/15

Histogram:

- 04-24 reference: `n_memories=15` for 31/199 questions
- 04-30 canonical: `n_memories=15` for 164/199 questions
- 04-30 `bfeb90f`: `n_memories=15` for 170/199 questions

Paired `bfeb90f_0430 - ref_0424` `n_memories` delta:

- mean +3.05 memories/question
- median +3
- max +10

Interpretation:

- The retrieval/context substrate is not behaving identically. Current runs are usually filling the answer context to the cap, whereas the 04-24 reference often returned fewer memories.
- This supports substrate/config/environment drift rather than benchmark question drift.

## Current ranking of likely causes

1. Embedding substrate drift: highest likelihood. The repo history explicitly shows a transition from `text-embedding-3-small` to `nomic-embed-text`, while current env advertises `nomic-embed-text`. Current returned-memory counts also differ strongly from 04-24.
2. Dependency/image drift: high likelihood. Current image was built on 04-28 from broad lower-bound requirements and has `openai==2.32.0` etc.; 04-24 image/package versions are not pinned in repo.
3. DB/substrate/index state drift: high likelihood. RuVector extension/image/version, HNSW/GNN state, side tables, and non-LOCOMO rows may differ even after LOCOMO-domain cleanup.
4. Foundry model/judge snapshot drift: plausible, but no direct evidence yet from preserved artifacts.
5. LOCOMO question-list drift: mostly ruled out for compared artifacts; source-file provenance remains a reproducibility hazard because `/tmp/locomo10_cleaned.json` is outside git and differs from other local LOCOMO copies.

## Recommended next testable checks

Do not launch a new benchmark yet. Next steps should be read-only or pre-registered DB-writing diagnostics.

1. Find/restore 04-24 runtime evidence if possible:
   - old Docker image id / `docker image ls -a`
   - old container inspect JSON
   - shell history around `docker compose build/up`
   - old logs with embedding model, OpenAI SDK, server image id, ruvector digest, or Foundry model version

2. Add a preflight metadata capture block to future LOCOMO runs:
   - server image id and creation time
   - `pip freeze` subset
   - embedding provider/model/base URL/dimension
   - DB extension versions
   - source-data sha256 and conv/question hash
   - post-ingest table counts before cleanup
   - mean/median/histogram of `n_memories`

3. If user approves a DB-writing diagnostic later, run a tiny isolated ingest-only probe under current stack and capture table counts + embedding dimension, then clean. This is not a scoring run.

4. If evidence supports embedding drift, preregister a single-variable reproduction attempt forcing the likely 04-24 embedding model (`text-embedding-3-small` or exact Azure embedding deployment if identified) while keeping the canonical chat/judge stack fixed.

5. If dependency drift remains plausible after embedding metadata, rebuild an archived/pinned 04-24-style image with frozen package versions and compare only after preregistration.
