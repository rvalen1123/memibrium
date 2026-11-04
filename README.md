# Memibrium — Sovereign AI Memory with Crystallization Theory

> **"It gets smarter without getting wiser."** — That's the problem this stack is built to solve.

[![Status](https://img.shields.io/badge/status-production-green)]()
[![Plugin](https://img.shields.io/badge/distribution-plugin-purple)]()
[![MCP](https://img.shields.io/badge/protocol-MCP-blue)]()
[![LLM](https://img.shields.io/badge/LLM-any%20OpenAI--compatible-orange)]()
[![Sovereign](https://img.shields.io/badge/sovereignty-full-darkgreen)]()
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.18150324.svg)](https://doi.org/10.5281/zenodo.18150324)

Memibrium is a self-hosted memory server for AI agents. It is a single Python/Starlette process (`server.py`) over PostgreSQL + pgvector that implements **Crystallization Theory (CT)** as a governance layer above vector search: every memory enters as an untrusted *observation*, is ranked and decayed by the weight function W(k,t), and can only become *crystallized* through human confirmation. Lifecycle state doubles as the storage tier (hot = observation/consideration/accepted, cold = crystallized/shed). It ships as a plugin: one governance skill plus one MCP server. Patent POC: CT #63/953,509 · KEOS #63/962,609 · STG (pending).

## Run it

Prerequisites: Python 3.11+, PostgreSQL with the `vector` extension (or [ruvector-postgres](https://github.com/ruvnet/ruvector)), and a keyless OpenAI-compatible endpoint for embeddings and chat (Ollama by default; the clients send the fixed key `ollama`, so hosted providers that need a real key do not work without a code change — see [docs/operations.md](docs/operations.md#how-the-llm-clients-pick-an-endpoint)). PDF ingestion additionally needs `pip install pymupdf` (or `pypdf`).

```bash
pip install -r requirements.txt
cp .env.example .env            # then edit the values
set -a; . ./.env; set +a        # server.py does not load .env itself; export it first
python server.py                # listens on 0.0.0.0:9999
curl http://localhost:9999/health
```

Configuration is read from the environment (names, not values — see [docs/operations.md](docs/operations.md#environment-variables) for the full list with defaults):

- Embeddings: `EMBEDDING_BASE_URL`, `EMBEDDING_MODEL`, `EMBEDDING_DIM` (must match the model's output width; checked at startup)
- Chat and scoring: `OLLAMA_CHAT_BASE`, `CHAT_MODEL`, `SLM_BASE_URL`, `SLM_MODEL`
- Database: `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
- Engines: `USE_RUVECTOR`, `USE_LEANN`; CT tuning: `IMPORTANCE_THRESHOLD`, `SHEDDING_THRESHOLD`, `CONSOLIDATE_INTERVAL_MIN`, `DECAY_RATE`, `CRYSTALLIZE_CONFIRMATIONS`; ranking: `CT_RANKER_*` (read in `ct_ranker.py`)

Schema is created and migrated at startup (`ColdStore.initialize`: additive `IF NOT EXISTS` statements plus the one-shot `migrate_idempotency_keys`). Pointing the server at a database is itself a migration.

The other supported way to run it is the compose stack, `docker compose -f docker-compose.ruvector.yml up -d` (ruvector-postgres + Ollama + server). The first `up` pulls the configured Ollama models before the server starts, `EMBEDDING_DIM` defaults to 768 to match `nomic-embed-text`, and the ports are published on `127.0.0.1` only. Overrides and the upgrade note for an older 1536-wide volume are in [docs/operations.md](docs/operations.md#run-with-the-ruvector-compose-stack). The Terraform trees (`main.tf` + `modules/`, `deploy/`) and the `Caddyfile` are legacy Azure configuration and are not a way to run Memibrium ([Legacy: Azure](docs/operations.md#legacy-azure-subscription-closed-not-maintained)).

Install the agent plugin (skill + MCP wiring): `claude plugin marketplace add rvalen1123/memibrium && claude plugin install memibrium@memibrium`. Other hosts: [DISTRIBUTION.md](DISTRIBUTION.md).

## API at a glance

All routes take and return JSON. [docs/api.md](docs/api.md) lists all 27 routes and the 18 tools in the `GET /mcp/tools` manifest with one line each, and describes the MCP endpoint `POST /mcp` that the plugin connects to (10 of the 18 tools by default; `confirm`, `revert`, `consolidate` and `freeze` are human-only and never offered to agents, and the four path tools need `MCP_INGEST_ROOTS`); it gives request fields only for idempotent retain and the list routes. For per-tool input schemas, read the manifest.

| Route | What it does |
|---|---|
| `POST /mcp/retain` | Store content: score → embed → insert as `observation`. Idempotent when `refs.idempotency_key` (or `refs.event_id`) is set. |
| `POST /mcp/recall` | Dual-tier search (hot first, cold fallback) ranked by cosine × W(k,t). |
| `POST /mcp/reflect` | Synthesize what is known about a topic; crystallized memories weighted highest. |
| `POST /mcp/confirm` | Human validation. **The only path to `crystallized`.** |
| `POST /mcp/freeze` / `POST /mcp/revert` | Snapshot a memory and exempt it from decay / restore a snapshot. |
| `POST /mcp/consolidate` | Run one δ-decay + shed + crystallize cycle now (also runs every `CONSOLIDATE_INTERVAL_MIN`). |
| `GET /mcp/dashboard` · `GET /mcp/graph` | Lifecycle counts and CT parameters · memory graph topology. |
| `POST /mcp/context_packet` · `POST /mcp/prefetch` | Grounded context packet from episodic, graph and self-model evidence · predictive pre-fetch. |
| `POST /mcp/ingest/{file,directory,jsonl}` · `POST /mcp/ingest/compile` · `GET /mcp/wiki` | Bulk ingestion with a 30-category taxonomy; compile a wiki from memory. |
| `POST /mcp` | MCP protocol endpoint (stateless streamable HTTP, JSON replies) the plugin's `.mcp.json` points at. Serves 10 tools by default (14 with `MCP_INGEST_ROOTS` set); never `confirm`, `revert`, `consolidate` or `freeze`. |
| `GET /mcp/tools` · `GET /health` | REST tool manifest (all 18) · liveness. |

## Status and caveats

- **No inbound authentication on `/mcp` or `/mcp/*`.** The server trusts whatever network it is bound to; Caddy only terminates TLS. Tracked as **MED-234**. Do not expose port 9999 publicly.
- **Azure is gone.** The Azure subscription was closed on 2026-11-02, so the gateway key once committed in `Caddyfile` is dead and needs no rotation. The leftover Azure config (Caddy gateway header, both Terraform trees) is unmaintained and slated for removal under **MED-233**.
- Idempotent retain (PR #11, hardened in PR #12): keys are trimmed, bounded to 256 chars, materialized into `refs.idempotency_key`, and enforced by the unique partial index `memories_domain_idempotency_uidx`. Details and the pre-index migration: [docs/api.md](docs/api.md#idempotent-retain).
- The `consideration` state exists in the schema and transition table but is not yet used by `IngestAgent`.
- Benchmark numbers in older notes were measured against a degraded database and are flagged as such; see [docs/benchmarks.md](docs/benchmarks.md) and the dated records under [docs/eval/](docs/eval/README.md).

## Tests

```bash
python test_taxonomy.py              # 40 tests, no DB or LLM
python test_ingest_unit.py           # 34 tests, no DB or LLM
# + 12 more dependency-free test files, including test_mcp_endpoint.py (list in docs/operations.md#testing)
MEMIBRIUM_TEST_DSN=postgresql://memibrium:memibrium@localhost:5432/memibrium_test \
  python test_retain_idempotency.py -v          # 18 tests
MEMIBRIUM_TEST_DSN=... python test_hybrid_retrieval_tiebreak_db.py -v   # 4 tests
MEMIBRIUM_TEST_DSN=... python test_review_preservation_db.py -v         # 3 tests
```

CI (`.github/workflows/ci.yml`, Python 3.11–3.13, `shell: bash` with pipefail) runs all of these against a digest-pinned `pgvector/pgvector:0.8.7-pg16` service and fails if a DB-backed test skips. The `docker run` line for a local test database and the end-to-end tests that need a running server are in [docs/operations.md](docs/operations.md#testing).

## Where the docs are

| Path | Contents |
|---|---|
| [AGENTS.md](AGENTS.md) | Working instructions for coding agents (commands, conventions, boundaries). `CLAUDE.md` points here. |
| [docs/README.md](docs/README.md) | Index of every document in `docs/` with its status. |
| [docs/architecture.md](docs/architecture.md) | Skill + MCP layering, tiering, lifecycle flow, design decisions, patent ↔ code map, repo layout. |
| [docs/api.md](docs/api.md) | Every route and manifest tool (one line each), the ingestion pipeline and taxonomy, idempotent retain, example prompts. |
| [docs/operations.md](docs/operations.md) | Running locally and with the compose stack, how the LLM clients pick endpoints, env vars, tests, and a short legacy-Azure section. |
| [docs/benchmarks.md](docs/benchmarks.md) | LOCOMO benchmark notes and corrections. |
| [docs/roadmap.md](docs/roadmap.md) | Roadmap and competitive landscape. |
| [docs/eval/README.md](docs/eval/README.md) | Index of the dated LOCOMO / LongMemEval preregistrations, results and handoffs. |
| [DISTRIBUTION.md](DISTRIBUTION.md) · [SECURITY.md](SECURITY.md) · [LICENSE.md](LICENSE.md) | Plugin architecture and install paths · security policy · Business Source License 1.1 with patent notice. |
| [Crystallization Theory paper](https://doi.org/10.5281/zenodo.18150324) | The theory this implements. |

---

*Adapted from [Google's Always-On Memory Agent](https://research.google/blog/) research.*
*Hot tier: [RuVector](https://github.com/ruvnet/ruvector) by [rUv](https://github.com/ruvnet) · Cold tier: [LEANN](https://github.com/yichuan-w/LEANN) by Berkeley SkyLab.*
*Memibrium — Crystallization Theory by Richard "Ricky" Valentine / [Orchard Holdings LLC](https://github.com/rvalen1123)*

> "The system gets wiser—not merely smarter—because the wisdom is human wisdom, accumulated through deliberate consensus and preserved through sovereign governance."
