# Running and deploying Memibrium

> Relocated verbatim from the root `README.md` in the MED-242 docs pass (2026-11-02). The [README](../README.md) is now the short entry point; this file keeps the full text.

Sections: Install in 60 Seconds · Deploy (local, RuVector/Docker, Terraform) · Supported LLM Providers · Testing · Edge (Caddy).

---

## Install in 60 Seconds

### Prerequisites

- Python 3.11+, PostgreSQL with pgvector extension
- Any OpenAI-compatible LLM provider (OpenAI, Azure, Ollama, etc.)
- Node.js 18+ (for plugin hosts that use npx)

### 1. Start the server

```bash
pip install asyncpg openai starlette uvicorn

export OPENAI_API_KEY="your-key"
export OPENAI_BASE_URL="https://api.openai.com/v1"
export DB_HOST=localhost DB_NAME=memory DB_USER=memory DB_PASSWORD=memory

python server.py
```

### 2. Install the plugin

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

**Cursor / other MCP clients:** See [DISTRIBUTION.md](../DISTRIBUTION.md)

### 3. Verify

Ask your agent: *"What do you know about my project?"*

You should get a governed memory response with lifecycle states — not a generic "I don't have memory" answer.

---

## Deploy

### Local (any machine)

```bash
pip install asyncpg openai starlette uvicorn

export OPENAI_API_KEY="your-key"
export OPENAI_BASE_URL="https://api.openai.com/v1"  # or your provider
export EMBEDDING_MODEL="text-embedding-3-small"
export CHAT_MODEL="gpt-4.1-mini"
export DB_HOST=localhost DB_NAME=memory DB_USER=memory DB_PASSWORD=memory

# Optional: enable RuVector (GNN re-ranking + SONA self-learning)
# Requires ruvnet/ruvector-postgres instead of standard PostgreSQL
export USE_RUVECTOR=true

python server.py
```

### With RuVector (Docker — recommended)

```bash
# One command — spins up ruvector-postgres + memibrium
docker compose -f docker-compose.ruvector.yml up -d

# Enable LEANN cold tier (optional, 97% storage savings)
pip install leann sentence-transformers
export USE_LEANN=true
export LEANN_EMBEDDING_MODE=sentence-transformers  # or openai
export LEANN_EMBEDDING_MODEL=facebook/contriever    # fast, local, no API key
```

RuVector-postgres is a drop-in pgvector replacement with GNN re-ranking and SONA self-learning. LEANN stores a pruned graph and recomputes embeddings on-demand for crystallized/shed memories. Both fall back to pgvector automatically if not available.

### Cloud (Terraform + Azure VM)

```bash
cd memibrium
cp terraform.tfvars.example terraform.tfvars
# Edit: subscription_id, resource_group, allowed_ssh_cidrs

export TF_VAR_foundry_api_key="your-key-here"
terraform init && terraform plan && terraform apply
```

The VM bootstraps via cloud-init: Python, Caddy, PostgreSQL + pgvector, Memibrium.

### Supported LLM Providers

Any OpenAI-compatible API works out of the box:

| Provider | `OPENAI_BASE_URL` | Notes |
|---|---|---|
| OpenAI | `https://api.openai.com/v1` | Default |
| Azure OpenAI / Foundry | `https://your-resource.openai.azure.com/` | Auto-detected |
| Ollama | `http://localhost:11434/v1` | Local, no API key needed |
| OpenRouter | `https://openrouter.ai/api/v1` | Multi-model access |
| vLLM / TGI | `http://localhost:8000/v1` | Self-hosted inference |

---

## Testing

### Unit tests (no DB, no LLM)

```bash
python test_taxonomy.py       # 40/40 — classifier accuracy, tier priority, skip list, export/import
python test_ingest_unit.py    # 34/34 — markdown/JSON/CSV chunking, provenance, dedup, edge cases
```

### E2E tests (requires running server)

```bash
python server.py &

python test_production_e2e.py    # Core 8 endpoints: retain → recall → confirm → crystallize → freeze → revert
python test_ingest_e2e.py        # Ingestion 6 endpoints: file, directory, JSONL, taxonomy, compile, cross-check recall
python test_ruvector_e2e.py      # RuVector DB layer (requires ruvector-postgres docker)
python test_leann_e2e.py         # LEANN cold tier (requires pip install leann)
```

---

## Edge: Caddy

`Caddyfile` at the repo root has two site blocks:

- A public hostname block that terminates TLS and reverse-proxies `/mcp*` and `/health` to `127.0.0.1:8787`, answering everything else with a static banner. The `8787` port matches the older VM layout in `modules/vm/cloud-init.yaml`; the newer Terraform tree under `deploy/modules/vm/cloud-init.yaml` runs uvicorn on `127.0.0.1:9999` and proxies to that port instead. Check which tree you deployed from before editing the port.
- `http://:9999`, which forwards to an Azure API Management gateway and injects the gateway key from the environment variable `AZURE_GATEWAY_API_KEY` (`header_up api-key {$AZURE_GATEWAY_API_KEY}`). Set it in Caddy's environment (for example `/etc/caddy/caddy.env` referenced by `EnvironmentFile=` in the systemd unit). The key used to be committed in this file in plain text; rotating it is tracked as MED-233.

Caddy does not add authentication in front of `/mcp/*` either; see MED-234.

## Environment variables

All configuration is read from the environment at import time in `server.py` (the `# ── Configuration` block near the top). `.env.example` lists the common ones with defaults. Names only; never commit values:

| Group | Variables |
|---|---|
| LLM provider | `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `CHAT_MODEL`, `OLLAMA_CHAT_BASE`, `SLM_MODEL`, `SLM_BASE_URL` |
| Embeddings | `EMBEDDING_BASE_URL`, `EMBEDDING_MODEL`, `EMBEDDING_DIM` (default `1536`; the `memories.embedding` column is created with this width), `ALLOW_EMBEDDING_DIM_MISMATCH` |
| Azure OpenAI | `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT`, `AZURE_API_VERSION`, `AZURE_EMBEDDING_ENDPOINT`, `AZURE_EMBEDDING_DEPLOYMENT`, `AZURE_EMBEDDING_API_KEY`, `AZURE_CHAT_ENDPOINT`, `AZURE_CHAT_DEPLOYMENT`, `AZURE_CHAT_API_KEY` |
| PostgreSQL | `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` |
| Vector engine | `USE_RUVECTOR`, `REQUIRE_RUVECTOR`, `RUVECTOR_GNN`, `RECALL_EXTRA_VECTOR_CANDIDATES` |
| LEANN cold tier | `USE_LEANN`, `LEANN_INDEX_DIR`, `LEANN_BACKEND`, `LEANN_EMBEDDING_MODE`, `LEANN_EMBEDDING_MODEL` |
| CT parameters | `IMPORTANCE_THRESHOLD`, `SHEDDING_THRESHOLD`, `CONSOLIDATE_INTERVAL_MIN`, `DECAY_RATE`, `CRYSTALLIZE_CONFIRMATIONS` |
| Background work | `ENABLE_BACKGROUND_SCORING`, `ENABLE_CONTRADICTION_DETECTION`, `ENABLE_HIERARCHY_PROCESSING`, `SCORE_BATCH_SIZE`, `SCORE_BATCH_TIMEOUT`, `RETAIN_DIAGNOSTICS_MAX_PENDING` |
| Ingestion | `INGEST_MAX_CHUNK_CHARS`, `INGEST_MIN_CHUNK_CHARS`, `INGEST_OVERLAP_CHARS` |
| Tests only | `MEMIBRIUM_TEST_DSN` (a disposable Postgres; enables the DB-backed cases in `test_retain_idempotency.py` and `test_hybrid_retrieval_tiebreak_db.py`) |
| Edge (Caddy) | `AZURE_GATEWAY_API_KEY` |
