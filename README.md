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

Prerequisites: Python 3.11+, PostgreSQL with the `vector` extension (or [ruvector-postgres](https://github.com/ruvnet/ruvector)), any OpenAI-compatible LLM endpoint for embeddings and chat.

```bash
pip install -r requirements.txt
cp .env.example .env            # fill in values, or export the variables directly
python server.py                # listens on 0.0.0.0:9999
curl http://localhost:9999/health
```

Configuration is read from the environment (names, not values — see [docs/operations.md](docs/operations.md) for the full list):

- LLM: `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `CHAT_MODEL`, `EMBEDDING_MODEL`, `EMBEDDING_BASE_URL`, `EMBEDDING_DIM`
- Database: `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
- Engines: `USE_RUVECTOR`, `USE_LEANN`; CT tuning: `IMPORTANCE_THRESHOLD`, `SHEDDING_THRESHOLD`, `CONSOLIDATE_INTERVAL_MIN`, `DECAY_RATE`, `CRYSTALLIZE_CONFIRMATIONS`

Schema is created and migrated at startup (`ColdStore.initialize`: additive `IF NOT EXISTS` statements plus the one-shot `migrate_idempotency_keys`). Pointing the server at a database is itself a migration.

Other ways to run: `docker compose -f docker-compose.ruvector.yml up -d` (ruvector-postgres + Ollama + server), Terraform for an Azure VM under `deploy/`, and `Caddyfile` for the TLS edge. All in [docs/operations.md](docs/operations.md).

Install the agent plugin (skill + MCP wiring): `claude plugin marketplace add rvalen1123/memibrium && claude plugin install memibrium@memibrium`. Other hosts: [DISTRIBUTION.md](DISTRIBUTION.md).

## API at a glance

All routes take and return JSON. Full reference, including request fields and the routes not listed here: [docs/api.md](docs/api.md).

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
| `GET /mcp/tools` · `GET /health` | MCP tool manifest · liveness. |

## Status and caveats

- **No inbound authentication on `/mcp/*`.** The server trusts whatever network it is bound to; Caddy only terminates TLS. Tracked as **MED-234**. Do not expose port 9999 publicly.
- **Gateway key rotation pending.** `Caddyfile` now reads the Azure gateway key from the environment variable `AZURE_GATEWAY_API_KEY`; the value that was previously committed must be rotated. Tracked as **MED-233**.
- Idempotent retain (PR #11, hardened in PR #12): keys are trimmed, bounded to 256 chars, materialized into `refs.idempotency_key`, and enforced by the unique partial index `memories_domain_idempotency_uidx`. Details and the pre-index migration: [docs/api.md](docs/api.md#idempotent-retain).
- The `consideration` state exists in the schema and transition table but is not yet used by `IngestAgent`.
- Benchmark numbers in older notes were measured against a degraded database and are flagged as such; see [docs/benchmarks.md](docs/benchmarks.md) and the dated records under [docs/eval/](docs/eval/README.md).

## Tests

```bash
python test_taxonomy.py              # 40 tests, no DB or LLM
python test_ingest_unit.py           # 34 tests, no DB or LLM
python test_retain_idempotency.py    # 18 tests; one is skipped unless MEMIBRIUM_TEST_DSN points at a disposable Postgres
```

These three are what CI runs (`.github/workflows/ci.yml`, Python 3.11–3.13, with a `postgres:16` service for the DSN-backed case). End-to-end tests that need a running server are listed in [docs/operations.md](docs/operations.md#testing).

## Where the docs are

| Path | Contents |
|---|---|
| [AGENTS.md](AGENTS.md) | Working instructions for coding agents (commands, conventions, boundaries). `CLAUDE.md` points here. |
| [docs/README.md](docs/README.md) | Index of every document in `docs/` with its status. |
| [docs/architecture.md](docs/architecture.md) | Skill + MCP layering, tiering, lifecycle flow, design decisions, patent ↔ code map, repo layout. |
| [docs/api.md](docs/api.md) | Every route, the ingestion pipeline and taxonomy, idempotent retain, example prompts. |
| [docs/operations.md](docs/operations.md) | Install, deploy (local, Docker, Terraform), LLM providers, env vars, Caddy, tests. |
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
