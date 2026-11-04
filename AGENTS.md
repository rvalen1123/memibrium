# AGENTS.md — working in the Memibrium repo

Memibrium is a single-process Python/Starlette memory server (`server.py`) over PostgreSQL + pgvector that implements the Crystallization Theory (CT) lifecycle; `/mcp/confirm` is the only route that can crystallize a memory, and nothing you write may change that. Read [README.md](README.md) first, then the file this section points you to.

## Repo map

| Path | What it is |
|---|---|
| `server.py` | The whole server: config from env, `ColdStore` (schema + migrations + queries), `IngestAgent`, `ConsolidateAgent`, recall/ranking, all 27 routes (the MCP endpoint `POST /mcp` and 26 REST routes), `app = Starlette(...)`. ~4000 lines. |
| `hybrid_retrieval.py`, `ct_ranker.py`, `ct_scoring.py`, `memory_hierarchy.py` | Retrieval candidate generation, CT re-ranking, `compute_weight()` (W(k,t)), hierarchy processing. Imported by `server.py`. |
| `ingest_engine.py`, `knowledge_taxonomy.py` | Bulk file/JSONL ingestion, wiki compiler, 30-category classifier. |
| `test_*.py` | Tests. CI runs 14 dependency-free files plus 2 against Postgres + pgvector (see Commands); the E2E files need a running server, RuVector or LEANN. |
| `benchmark*.py`, `benchmark_scripts/`, `scripts/` | LOCOMO/LongMemEval harnesses and audit scripts. They write under `docs/eval/results/`. |
| `docs/` | Human docs (`architecture.md`, `api.md`, `operations.md`, `benchmarks.md`, `roadmap.md`), indexed in `docs/README.md`. |
| `docs/eval/` | Dated preregistrations, results and handoffs for the LOCOMO and LongMemEval studies. Records, not working docs. Indexed in `docs/eval/README.md`. |
| `plugins/memibrium/` | The shipped plugin: `.mcp.json` and `skills/crystallization-memory/SKILL.md` (the governance skill agents load). `skills/` at the root is a redirect stub to it. |
| `Dockerfile`, `docker-compose.ruvector.yml` | Container image and the compose stack (ruvector-postgres + Ollama + server): the supported non-local way to run. |
| `Caddyfile`, `deploy/`, `main.tf` + `variables.tf` + `outputs.tf` + `modules/` | Legacy Azure config (the Caddy gateway header and both Terraform trees). The Azure subscription was closed on 2026-11-02; none of it works. Slated for removal under MED-233, "Remove dead Azure config from Memibrium (Caddy gateway header, Terraform trees)". Do not extend it or document it as a current path. |
| `.github/workflows/ci.yml` | CI: Python 3.11/3.12/3.13 matrix, every step `shell: bash` (pipefail), digest-pinned `pgvector/pgvector:0.8.7-pg16` service, the test commands below; fails if a DB-backed test skips. |

## Commands

Install once:

```bash
pip install -r requirements.txt
```

Run the CI tests that need no database, server, LLM or network (CI runs each of these; all must pass):

```bash
python test_taxonomy.py
python test_ingest_unit.py
for t in test_coldstore_vector_candidates.py test_context_graph_v0.py test_ct_ranker.py \
         test_hybrid_retrieval_ruvector.py test_recall_hybrid_ct.py test_server_recall_telemetry.py \
         test_startup_vector_config.py test_temporal_memory.py test_locomo_context_packet_canary.py \
         test_locomo_query_expansion.py test_longmemeval_oracle_canary.py test_mcp_endpoint.py; do
  python "$t" || break
done
```

Run one test (pytest is available; the files are plain `unittest`/script style and also run under it):

```bash
python -m pytest test_retain_idempotency.py -k test_second_retain_with_same_event_id_is_a_duplicate
```

Run the database-backed tests against a disposable Postgres + pgvector, the same image CI uses (the tests create and drop objects, so the database must be throwaway). CI runs them with `-v` and fails the job on any skip; without `MEMIBRIUM_TEST_DSN` they skip instead:

```bash
docker run --rm -d --name memibrium-test-pg -p 5432:5432 \
  -e POSTGRES_USER=memibrium -e POSTGRES_PASSWORD=memibrium -e POSTGRES_DB=memibrium_test \
  pgvector/pgvector:0.8.7-pg16
export MEMIBRIUM_TEST_DSN=postgresql://memibrium:memibrium@localhost:5432/memibrium_test
python test_retain_idempotency.py -v           # 18 tests, 0 skipped
python test_hybrid_retrieval_tiebreak_db.py -v # 4 tests, 0 skipped
docker stop memibrium-test-pg
```

Start the server locally (needs a reachable Postgres with the `vector` extension and a keyless OpenAI-compatible endpoint, Ollama by default; see `docs/operations.md` for which variables each LLM client reads). `server.py` does not load `.env`; export it first:

```bash
cp .env.example .env              # names only below; never commit values
set -a; . ./.env; set +a          # export .env into this shell
python server.py                  # 0.0.0.0:9999 — startup creates/migrates the schema in the database it points at
curl http://localhost:9999/health
```

End-to-end tests that need the running server: `python test_production_e2e.py`, `python test_ingest_e2e.py` (see `docs/operations.md`).

## Conventions that change behaviour

- **CT lifecycle.** States: `observation → accepted → crystallized → shed` (`consideration` is defined but unused). `confirmation_count` is incremented only by `POST /mcp/confirm` (`handle_confirm`). A memory becomes `crystallized` only when that count reaches `CRYSTALLIZE_CONFIRMATIONS` with `validation_score ≥ 0.5`, applied either in `handle_confirm` or in `ConsolidateAgent.run_cycle` on the next cycle. No LLM score, importance value or retrieval signal may set `state = 'crystallized'`. Agents never call `confirm` on their own output; that call represents a human. The MCP endpoint (`POST /mcp`) therefore never offers `confirm`, `revert`, `consolidate` or `freeze` (`MCP_WITHHELD_TOOLS`); a new manifest tool must be classified there or in `MCP_TOOL_DISPATCH` before it is served, and `test_mcp_endpoint.py` fails until it is.
- **Schema changes.** All DDL lives in `ColdStore.initialize` and is additive: `CREATE TABLE IF NOT EXISTS`, `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`. Append new statements after the existing ones. Do not edit, reorder or remove an existing statement or the semantics of `migrate_idempotency_keys` (its SQL in `IDEMPOTENCY_MIGRATION_SQL` ran once on real databases). A data migration must be idempotent and must run before any index that depends on it, inside one transaction, the way `migrate_idempotency_keys` does.
- **Idempotent retain.** `refs.idempotency_key` wins; `refs.event_id` is the fallback alias. The key is trimmed, must be ≤ `IDEMPOTENCY_KEY_MAX_CHARS` (256; longer → HTTP 400 via `IdempotencyKeyError`), is materialized into `refs.idempotency_key` by `_normalize_refs` before insert, and is unique per `(domain, key)` through the partial index `memories_domain_idempotency_uidx`. A blank key is never persisted. A duplicate returns the existing memory with `"duplicate": true` and performs no embedding, insert or background scoring. Keep `FakeStore` in `test_retain_idempotency.py` mirroring the real index semantics when you touch this.
- **Embeddings.** `EMBEDDING_DIM` (default 1536) fixes the width of `memories.embedding` at table creation and is checked at startup by `verify_startup_embedding_dimension`. Changing the model to a different dimension requires a new database or `reembed.py`; `ALLOW_EMBEDDING_DIM_MISMATCH` only downgrades the check, it does not resize the column.
- **Witness chains.** Every state transition appends a `make_witness_entry(...)` record to `witness_chain`. New transitions must do the same.
- **Config.** Settings are module-level constants read from `os.environ` at import time, with a default. Server settings live in `server.py`; settings owned by the CT ranker (`CT_RANKER_*`) are read in `ct_ranker.py`, and the ingestion chunk sizes (`INGEST_*`) in `ingest_engine.py`. Add a new setting in the module that owns it, and list the name in `.env.example` and `docs/operations.md`. Nothing loads `.env` automatically. Tests that need a different value patch the module attribute (see `setUp` in `test_retain_idempotency.py`).
- **Style.** Python 3.11+ syntax, type hints on new functions, `asyncpg` for all database access, no blocking I/O inside handlers. Keep the single-file layout of `server.py`; do not split it into a package in a drive-by change.

## Boundaries

**Always**
- Run the CI test commands under Commands after any change to `server.py` or a test file.
- Keep `docs/api.md` and `docs/operations.md` in step when you add a route or an environment variable.
- Reference Linear issues by ID (`MED-###`) in commits and PR bodies.

**Ask first**
- Any change to the state machine, `VALID_TRANSITIONS`, `compute_weight`, decay or crystallization thresholds.
- Any new DDL beyond an additive `IF NOT EXISTS` statement, or any statement that rewrites existing rows.
- Changes to `Caddyfile`, `Dockerfile`, `docker-compose.ruvector.yml` or anything under `deploy/` or `modules/`.
- Adding inbound authentication to `/mcp/*` (wanted, tracked as MED-234, but it changes every client).
- Moving or deleting anything under `docs/eval/`.
- Merging your own PR: only with Ricky's explicit go-ahead, and only once its required checks are green.

**Never**
- Commit secrets, keys, DSNs with passwords or `.env` files. Name environment variables; never write their values into code, docs, tests or commit messages. (The Azure gateway key once committed in `Caddyfile` is dead with the closed subscription; the config itself goes under MED-233.)
- Weaken CT authority: no code path other than human confirmation may crystallize, and `confirm` must never be invoked automatically.
- Run `python server.py`, a test with `MEMIBRIUM_TEST_DSN`, `reembed.py` or `scripts/clear_locomo_domains.sh` against a production database without explicit confirmation. Startup migrates whatever database it is pointed at.
- Edit the contents of `docs/eval/**` records (preregistrations, results, handoffs). Add a new dated file instead; `docs/eval/locked_plan.md` is also read by `test_locomo_query_expansion.py`.
- Rewrite history on `main`.

## Before you finish

1. `python test_taxonomy.py` — passes (40).
2. `python test_ingest_unit.py` — passes (34).
3. The 12 dependency-free test files in the loop under Commands — each passes.
4. With `MEMIBRIUM_TEST_DSN` set to the disposable pgvector container: `python test_retain_idempotency.py -v` (18) and `python test_hybrid_retrieval_tiebreak_db.py -v` (4) pass with no skips. If you cannot run Postgres locally, say so; CI runs them.
5. `git status` shows no `.env`, no key material, nothing under `wiki/` or `data/`.
6. If you added a route, env var or doc: `docs/api.md`, `docs/operations.md` and `docs/README.md` updated.
