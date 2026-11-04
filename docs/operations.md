# Running Memibrium

Two supported ways to run it: the server as a local Python process, or the `docker-compose.ruvector.yml` stack (ruvector-postgres + Ollama + server). Everything Azure (Terraform trees, Azure OpenAI / Foundry settings, the Caddy gateway block) is legacy and is described only in the [last section](#legacy-azure-subscription-closed-not-maintained).

Sections: Prerequisites · How the LLM clients pick an endpoint · Run locally · Run with the RuVector compose stack · Install the plugin · Environment variables · Testing · Network exposure · Legacy: Azure.

---

## Prerequisites

- Python 3.11+ and `pip install -r requirements.txt`.
- PostgreSQL with the `vector` extension (pgvector), or ruvector-postgres.
- An OpenAI-compatible endpoint for embeddings and chat that **does not need an API key**. Ollama is the default and the only one this repo is set up for; see the next section for why.
- Optional, for PDF ingestion: `pip install pymupdf` (or `pip install pypdf`). Neither is in `requirements.txt`. Without one, `ingest_engine._extract_pdf_text` logs `No PDF library available` and returns empty text, so a `.pdf` passed to `/mcp/ingest/file` or `/mcp/ingest/directory` yields zero chunks instead of an error.
- Node.js 18+ only for plugin hosts that launch MCP servers through `npx`.

## How the LLM clients pick an endpoint

`server.py` builds three clients at import time. Outside the legacy Azure branch, each one passes the literal string `"ollama"` as its API key; there is no environment variable for the key.

| Client (in `server.py`) | Base URL variable | Default base URL | Model variable | Default model |
|---|---|---|---|---|
| `EmbedClient` (embeddings) | `EMBEDDING_BASE_URL`, falling back to `OPENAI_BASE_URL` | `http://localhost:11434/v1` | `EMBEDDING_MODEL` | `nomic-embed-text` |
| `ChatClient` (importance scoring, reflect synthesis, query expansion) | `OLLAMA_CHAT_BASE` | `http://ollama:11434/v1` (the compose service name) | `CHAT_MODEL` | `gemma4:e4b` |
| `LocalSLMClient` (fast importance scoring in `IngestAgent`) | `SLM_BASE_URL` | `http://ollama:11434/v1` | `SLM_MODEL` | `qwen2.5:0.5b` |

Consequences:

- `OPENAI_API_KEY` is read (as `FOUNDRY_KEY`) but no active client sends it. It reaches only the unused helper `_make_llm_client` and the Azure diagnostic behind `/mcp/test_embeddings`. Setting it has no effect.
- `OPENAI_BASE_URL` affects embeddings only, and only when `EMBEDDING_BASE_URL` is unset. It does not change the chat or SLM endpoint.
- A hosted provider that requires a real key (OpenAI, OpenRouter, and so on) therefore does not work for any of the three clients without a code change. Endpoints that accept any key work: Ollama, LM Studio, or vLLM / TGI started without authentication. Point each base-URL variable at that endpoint.
- Outside the compose network the host name `ollama` does not resolve, so a local run must set `OLLAMA_CHAT_BASE` and `SLM_BASE_URL` explicitly.
- `EMBEDDING_DIM` (default `1536`) must equal the width your embedding model returns. At startup `verify_startup_embedding_dimension` embeds a probe string and raises `RuntimeError` on a mismatch unless `ALLOW_EMBEDDING_DIM_MISMATCH=true`. `nomic-embed-text` returns 768-dimensional vectors, so with that model set `EMBEDDING_DIM=768` before the first start (the `memories.embedding` column is created with this width).

## Run locally

`server.py` does not load `.env` (there is no `python-dotenv` import); it reads `os.environ` at import time. Export the file into your shell before starting:

```bash
pip install -r requirements.txt
cp .env.example .env              # then edit the values
set -a; . ./.env; set +a          # export every variable in .env into this shell
python server.py                  # uvicorn on 0.0.0.0:9999; startup creates/migrates the schema
curl http://localhost:9999/health
```

A working `.env` for Ollama on the same machine sets at least `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `EMBEDDING_BASE_URL=http://localhost:11434/v1`, `EMBEDDING_MODEL`, `EMBEDDING_DIM` (matching that model), `OLLAMA_CHAT_BASE=http://localhost:11434/v1`, `CHAT_MODEL`, `SLM_BASE_URL=http://localhost:11434/v1` and `SLM_MODEL`, and the models must already be pulled (`ollama pull <model>` for each).

Optional engines:

```bash
export USE_RUVECTOR=true          # needs ruvector-postgres instead of plain pgvector
pip install leann sentence-transformers
export USE_LEANN=true             # LEANN cold tier for crystallized/shed memories
export LEANN_EMBEDDING_MODE=sentence-transformers
export LEANN_EMBEDDING_MODEL=facebook/contriever
```

Both fall back to pgvector when unavailable (unless `REQUIRE_RUVECTOR=true`).

Startup migrates whatever database the `DB_*` variables point at. Never point a development run at a database you care about.

## Run with the RuVector compose stack

```bash
docker compose -f docker-compose.ruvector.yml up -d
```

This starts four services:

| Service | What it does |
|---|---|
| `ruvector-db` | `ruvnet/ruvector-postgres:2.0.5` on 5432, with a `pg_isready` healthcheck |
| `ollama` | `ollama/ollama:0.40.13` on 11434 |
| `ollama-pull` | One-shot: pulls the models the server is configured to call (`EMBEDDING_MODEL`, `CHAT_MODEL`, `SLM_MODEL`; by default `nomic-embed-text gemma4:e4b phi3:mini`, several GB on the first run), then exits. If `OLLAMA_MODELS` is set, it pulls exactly that space-separated list instead. |
| `memibrium` | The server on 9999, built from the `Dockerfile` and run as built (nothing is mounted over `/app`) |

All three ports are published on `127.0.0.1` only, because `/mcp/*` has no inbound authentication yet (MED-234). `MEMIBRIUM_BIND` changes the host address for all of them; publish on another interface only behind an authenticating proxy. For live code editing, add a `docker-compose.override.yml` that mounts the repo at `/app` under the `memibrium` service.

The server starts only once the database is healthy and `ollama-pull` has exited successfully, because its startup check embeds a probe string. Follow the first-run download with `docker compose -f docker-compose.ruvector.yml logs -f ollama-pull`. Later runs reuse the `ollama_data` volume, and the pull only re-verifies.

**Defaults the compose file sets** (each one overridable from your shell or a `.env` next to the compose file):
- `EMBEDDING_MODEL=nomic-embed-text` with `EMBEDDING_DIM=768`, the width nomic returns.
- `CHAT_MODEL=gemma4:e4b`.
- `SLM_MODEL=phi3:mini`.
- All three point at the `ollama` service.

`EMBEDDING_DIM` fixes the width of `memories.embedding` when the table is first created. If you change the embedding model, start against a fresh `ruvector_data` volume (or run `reembed.py`); changing the variable alone isn't enough. Only the variables listed in the compose file's `environment:` block reach the server.

**Upgrading an existing stack.** Before MED-252 the compose file left `EMBEDDING_DIM` at the server default of 1536. A `ruvector_data` volume from then has a 1536-wide column. The new 768 default makes the startup dimension check refuse to start on it. Pick one:
- Keep the data: set `EMBEDDING_DIM=1536` together with a 1536-wide `EMBEDDING_MODEL`.
- Re-embed into a 768-wide store with `reembed.py`.
- Start over: `docker compose -f docker-compose.ruvector.yml down -v` deletes the volumes and every stored memory.

**Embeddings-only setup** (for example a retrieval benchmark): pull just nomic and turn off the chat-backed background work.

```bash
OLLAMA_MODELS=nomic-embed-text ENABLE_BACKGROUND_SCORING=false ENABLE_CONTRADICTION_DETECTION=false \
ENABLE_HIERARCHY_PROCESSING=false docker compose -f docker-compose.ruvector.yml up -d --build
```

`/mcp/reflect` and recall with `expand: true` call the chat model, so leave the chat model in `OLLAMA_MODELS` if you need those (or leave `OLLAMA_MODELS` unset to pull all three configured models).

Check `docker compose -f docker-compose.ruvector.yml logs memibrium` for `Vector extension loaded` and no dimension error, then `curl http://127.0.0.1:9999/health`. CI runs this stack end to end, against the image as built, in `.github/workflows/compose-smoke.yml`. The run checks the model pull, health, the RuVector extension, 768-wide embeddings, retain, a deduplicated duplicate retain, and recall.

Compose-only variables (not read by `server.py`): `OLLAMA_MODELS` (pull list override) and `MEMIBRIUM_BIND` (host address for the published ports, default `127.0.0.1`).

## Install the plugin

**Claude Code:**
```bash
claude plugin marketplace add rvalen1123/memibrium
claude plugin install memibrium@memibrium
```

**Copilot CLI:**
```bash
/plugin marketplace add rvalen1123/memibrium
/plugin install memibrium@memibrium
```

**Cursor / other MCP clients:** see [DISTRIBUTION.md](../DISTRIBUTION.md).

The plugin's `.mcp.json` points the client at `http://localhost:9999/mcp`, the MCP endpoint (`POST /mcp`, stateless streamable HTTP with JSON replies; protocol versions and tools in [api.md](api.md#mcp-endpoint)). The server must already be running there. It serves 10 tools by default; `confirm`, `revert`, `consolidate` and `freeze` are never offered to agents, so confirming, freezing or reverting a memory stays a human call to its REST route. The four path tools (`ingest_file`, `ingest_directory`, `ingest_jsonl`, `compile_wiki`) are served over MCP only when `MCP_INGEST_ROOTS` lists the directories agents may ingest from (see [Environment variables](#environment-variables)).

To check the endpoint without a client:

```bash
curl -s http://localhost:9999/mcp -H 'content-type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

Then ask your agent something like *"What do you know about my project?"*; a governed memory answer with lifecycle states means the wiring works.

---

## Environment variables

Names only; never commit values. Most settings are module-level constants read at import time in `server.py` (the `# ── Configuration` block near the top, plus `LocalSLMClient` and `IngestAgent` class attributes). Two modules read their own: `ct_ranker.py` (the `CT_RANKER_*` weights) and `ingest_engine.py` (the `INGEST_*` chunking sizes). `.env.example` lists the common ones.

| Group | Variables (default) | Read in |
|---|---|---|
| Embeddings | `EMBEDDING_BASE_URL` (falls back to `OPENAI_BASE_URL`, then `http://localhost:11434/v1`), `EMBEDDING_MODEL` (`nomic-embed-text`), `EMBEDDING_DIM` (`1536`; must match the model), `ALLOW_EMBEDDING_DIM_MISMATCH` (`false`) | `server.py` |
| Chat | `OLLAMA_CHAT_BASE` (`http://ollama:11434/v1`), `CHAT_MODEL` (`gemma4:e4b`) | `server.py` |
| Local SLM scoring | `SLM_BASE_URL` (`http://ollama:11434/v1`), `SLM_MODEL` (`qwen2.5:0.5b`) | `server.py` (`LocalSLMClient`) |
| Read but not sent | `OPENAI_API_KEY`, `OPENAI_BASE_URL` (see [above](#how-the-llm-clients-pick-an-endpoint)) | `server.py` |
| PostgreSQL | `DB_HOST` (`localhost`), `DB_PORT` (`5432`), `DB_NAME` (`memory`), `DB_USER` (`memory`), `DB_PASSWORD` | `server.py` |
| Vector engine | `USE_RUVECTOR` (`false`), `REQUIRE_RUVECTOR` (`false`), `RUVECTOR_GNN` (`true`), `RECALL_EXTRA_VECTOR_CANDIDATES` (`false`) | `server.py` |
| LEANN cold tier | `USE_LEANN` (`false`), `LEANN_INDEX_DIR` (`./data/leann`), `LEANN_BACKEND` (`hnsw`), `LEANN_EMBEDDING_MODE` (`openai`), `LEANN_EMBEDDING_MODEL` (defaults to `EMBEDDING_MODEL`) | `server.py` |
| CT parameters | `IMPORTANCE_THRESHOLD` (`0.4`), `SHEDDING_THRESHOLD` (`0.05`), `CONSOLIDATE_INTERVAL_MIN` (`30`), `DECAY_RATE` (`0.02`), `CRYSTALLIZE_CONFIRMATIONS` (`3`) | `server.py` |
| CT ranker | `CT_RANKER_RETRIEVAL_WEIGHT` (`0.55`), `CT_RANKER_CT_WEIGHT` (`0.45`), `CT_RANKER_CT_HEAVY_RETRIEVAL_WEIGHT` (`0.40`), `CT_RANKER_CT_HEAVY_CT_WEIGHT` (`0.60`), `CT_RANKER_SHED_PENALTY` (`0.20`), `CT_RANKER_FROZEN_BONUS` (`0.05`), `CT_RANKER_FEEDBACK_SCALE` (`0.05`), `CT_RANKER_MAX_FEEDBACK_BONUS` (`0.30`); parsed by `parse_env_float`, which falls back to the default on an unparsable value | `ct_ranker.py` |
| Background work | `ENABLE_BACKGROUND_SCORING`, `ENABLE_CONTRADICTION_DETECTION`, `ENABLE_HIERARCHY_PROCESSING` (all `true`), `SCORE_BATCH_SIZE` (`5`), `SCORE_BATCH_TIMEOUT` (`1.0`), `RETAIN_DIAGNOSTICS_MAX_PENDING` (`50`) | `server.py` |
| MCP endpoint | `MCP_INGEST_ROOTS` (unset): `os.pathsep`-separated directories that the path tools may use over `POST /mcp`, canonicalised with `realpath` at import. Unset or empty: `ingest_file`, `ingest_directory`, `ingest_jsonl` and `compile_wiki` are not served over MCP. Does not affect the REST routes. | `server.py` |
| Ingestion | `INGEST_MAX_CHUNK_CHARS` (`2000`), `INGEST_MIN_CHUNK_CHARS` (`100`), `INGEST_OVERLAP_CHARS` (`200`) | `ingest_engine.py` |
| Tests only | `MEMIBRIUM_TEST_DSN` (a disposable Postgres; see [Testing](#testing)) | the DB-backed test files |

The Azure variables are listed under [Legacy](#legacy-azure-subscription-closed-not-maintained).

---

## Testing

CI (`.github/workflows/ci.yml`) runs every step with `shell: bash` (so `-eo pipefail`) on Python 3.11, 3.12 and 3.13, against a `pgvector/pgvector:0.8.7-pg16` service pinned by digest. To reproduce it locally:

```bash
pip install -r requirements.txt

# 1. No database, server, LLM or network
python test_taxonomy.py              # 40 tests
python test_ingest_unit.py           # 34 tests
for t in test_coldstore_vector_candidates.py test_context_graph_v0.py test_ct_ranker.py \
         test_hybrid_retrieval_ruvector.py test_recall_hybrid_ct.py test_server_recall_telemetry.py \
         test_startup_vector_config.py test_temporal_memory.py test_locomo_context_packet_canary.py \
         test_locomo_query_expansion.py test_longmemeval_oracle_canary.py test_mcp_endpoint.py; do
  python "$t" || break
done

# 2. Database-backed: start a throwaway Postgres + pgvector (same image CI uses)
docker run --rm -d --name memibrium-test-pg -p 5432:5432 \
  -e POSTGRES_USER=memibrium -e POSTGRES_PASSWORD=memibrium -e POSTGRES_DB=memibrium_test \
  pgvector/pgvector:0.8.7-pg16
export MEMIBRIUM_TEST_DSN=postgresql://memibrium:memibrium@localhost:5432/memibrium_test
python test_retain_idempotency.py -v           # 18 tests; with the DSN set none may skip
python test_hybrid_retrieval_tiebreak_db.py -v # 4 tests; with the DSN set none may skip
docker stop memibrium-test-pg
```

With `MEMIBRIUM_TEST_DSN` set, CI fails the job if either DB-backed file reports a skip (it greps the `-v` output for `... skipped` / `skipped=`), so a skip locally means the database tests did not run. The DB user must be allowed to `CREATE DATABASE` and `DROP`/`CREATE TABLE` (the `POSTGRES_USER` of the official image is a superuser). Without the DSN those cases skip instead of failing. Use only a disposable database: the tests create and drop objects.

End-to-end tests need a running server (and are not in CI):

```bash
python test_production_e2e.py    # retain → recall → confirm → crystallize → freeze → revert
python test_ingest_e2e.py        # file, directory, JSONL, taxonomy, compile, cross-check recall
python test_ruvector_e2e.py      # needs ruvector-postgres
python test_leann_e2e.py         # needs pip install leann
```

---

## Network exposure

`python server.py` binds `0.0.0.0:9999` and no route checks a credential (MED-234), including the MCP endpoint `POST /mcp`. Over MCP the file-ingest tools are off unless `MCP_INGEST_ROOTS` is set and then confined to those roots, but the REST ingest routes still read any path the process can read, and the REST governance routes (`/mcp/confirm`, `/mcp/freeze`, `/mcp/revert`, `/mcp/consolidate`) check no caller. `POST /mcp` refuses requests that carry an `Origin` header, which stops browser pages, not other clients. The compose stack publishes its ports on `127.0.0.1` for the same reason. Bind it to a private network or put an authenticating proxy in front; do not expose port 9999 publicly. The repo's `Caddyfile` is legacy Azure configuration (both its site blocks point at Azure hosts) and is not a supported edge; see below.

---

## Legacy: Azure (subscription closed, not maintained)

The Azure subscription this configuration targeted was closed on 2026-11-02. Nothing below works or is maintained; it is kept so the files still in the repo make sense until they are removed under **MED-233** ("Remove dead Azure config from Memibrium (Caddy gateway header, Terraform trees)").

- **Terraform:** two trees for an Azure VM bootstrapped by cloud-init (Python, Caddy, PostgreSQL + pgvector, Memibrium): the older root tree (`main.tf`, `variables.tf`, `outputs.tf`, `modules/`) and the newer `deploy/` tree (with its own `deploy/terraform.tfvars.example`). The older VM layout ran the server on `127.0.0.1:8787`, the newer one on `127.0.0.1:9999`.
- **`Caddyfile`:** a TLS block for an `*.cloudapp.azure.com` host proxying `/mcp*` and `/health` to `127.0.0.1:8787`, and an `http://:9999` block forwarding to an Azure API Management gateway with `header_up api-key {$AZURE_GATEWAY_API_KEY}`. The gateway key that was once committed in plain text is dead with the subscription.
- **Azure OpenAI / Foundry variables** (still read by `server.py`, no longer passed through by the compose file since MED-252; set none of them): `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT`, `AZURE_API_VERSION`, `AZURE_EMBEDDING_ENDPOINT`, `AZURE_EMBEDDING_DEPLOYMENT`, `AZURE_EMBEDDING_API_KEY`, `AZURE_CHAT_ENDPOINT`, `AZURE_CHAT_DEPLOYMENT`, `AZURE_CHAT_API_KEY`, and the Terraform input `TF_VAR_foundry_api_key`. When `AZURE_EMBEDDING_ENDPOINT` + key or `AZURE_CHAT_ENDPOINT` + key are set, `EmbedClient` / `ChatClient` switch to the Azure branch.
- **`/mcp/test_embeddings`** compares the Ollama embedder with an Azure deployment; the Azure half returns an error without the variables above.
- `deploy.ps1`, `debug_azure.py` and `debug_env.py` belong to the same era.
