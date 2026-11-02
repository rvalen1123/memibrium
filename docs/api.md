# Memibrium HTTP / MCP API

> Relocated verbatim from the root `README.md` in the MED-242 docs pass (2026-11-02). The [README](../README.md) is now the short entry point; this file keeps the full text.

Sections: MCP Tools (the README tables) · Idempotent retain · Additional routes present in `server.py` · Prompts to Try.

---

## MCP Tools (16 endpoints)

### Core Memory (8 tools)

| Endpoint | Method | What | Patent |
|---|---|---|---|
| `/mcp/retain` | POST | Ingest → score → embed → store in hot tier | CT lifecycle |
| `/mcp/recall` | POST | Dual-tier search: hot first, cold fallback, topic expansion | CT W(k,t) |
| `/mcp/reflect` | POST | Synthesize memories, crystallized weighted highest | — |
| `/mcp/confirm` | POST | **Human validation — ONLY path to crystallization** | STG Claim 1 |
| `/mcp/freeze` | POST | Snapshot + exempt from decay | STG Claim 7 |
| `/mcp/revert` | POST | Restore from snapshot | STG Claim 7 |
| `/mcp/consolidate` | POST | Manual trigger: δ-decay + shed + auto-promote | CT δ-decay |
| `/mcp/dashboard` | GET | Lifecycle counts, CT parameters, architecture | — |
| `/mcp/tools` | GET | MCP tool manifest for auto-discovery | — |

### Ingestion Engine (8 tools)

| Endpoint | Method | What |
|---|---|---|
| `/mcp/ingest/file` | POST | Ingest a single file: read → chunk → classify → embed → CT lifecycle |
| `/mcp/ingest/directory` | POST | Scan directory, ingest all supported files (.md, .txt, .json, .csv, .pdf) |
| `/mcp/ingest/jsonl` | POST | Ingest Claude conversation JSONL with auto-classification into 30 knowledge categories |
| `/mcp/ingest/status` | GET | Ingestion engine stats: hashes seen, taxonomy breakdown, config |
| `/mcp/ingest/compile` | POST | Compile wiki index from ingested memories — generates topic articles + backlinks |
| `/mcp/ingest/taxonomy` | GET | View the 30-category knowledge taxonomy with CT tier assignments |
| `/mcp/ingest/taxonomy` | POST | Update taxonomy categories at runtime |
| `/mcp/wiki` | GET | List compiled wiki files or read a specific file's content |

#### Ingestion Pipeline

```
Raw Sources
  │
  ├─ Files (.md, .txt, .json, .csv, .pdf)
  │   └─ /mcp/ingest/file or /mcp/ingest/directory
  │       ├─ Semantic chunking (by headers for .md, paragraphs for .txt, rows for .csv)
  │       ├─ Provenance hash per chunk (STG Claim 6 alignment)
  │       ├─ Content dedup (SHA-256, skip already-seen hashes)
  │       └─ Each chunk → IngestAgent → CT lifecycle
  │
  ├─ Claude Conversations (.jsonl)
  │   └─ /mcp/ingest/jsonl
  │       ├─ Parse {"messages": [...]} format
  │       ├─ 30-category keyword classifier → domain assignment
  │       ├─ CT tier mapping (crystallize | hot | archive)
  │       ├─ Skip list (dead projects filtered out)
  │       ├─ Length + dedup filters
  │       └─ Each conversation → IngestAgent → CT lifecycle
  │
  └─ Wiki Compilation
      └─ /mcp/ingest/compile
          ├─ Query all active memories by domain
          ├─ Group by topic → generate topic articles (.md)
          ├─ Generate index.md with backlinks
          └─ Output to configurable directory (Obsidian-compatible)
              └─ /mcp/wiki?file=index.md → read compiled articles via MCP
```

#### Knowledge Taxonomy (30 categories)

The ingestion engine ships with a 30-category taxonomy that maps content to CT lifecycle tiers:

| Tier | Count | Examples |
|---|---|---|
| **crystallize** | 16 | Patents (CT/KEOS/STG, Forward Design, Visiting AI), Architecture (Memibrium, Azure, WordPress), IP Deals, Legal/Compliance |
| **hot** | 13 | Business (Medvinci, LRS, Peptide Ops), Projects (Music, WhaleWatch), Strategy, Fine-Tuning |
| **archive** | 1 | General Coding / Debugging |

Taxonomy is configurable at runtime via `/mcp/ingest/taxonomy` (GET/POST) or by editing `knowledge_taxonomy.py`.

---

## Idempotent retain

`POST /mcp/retain` accepts `refs.idempotency_key`; `refs.event_id` is used as the key only when no explicit `idempotency_key` is given. The chosen key is trimmed, bounded to 256 chars (longer → HTTP 400), and materialized into the stored `refs.idempotency_key`, so a retry with the same key in the same `domain` returns the existing memory with `"duplicate": true` and performs no embedding, insert or background scoring. A UNIQUE partial index on `(domain, refs->>'idempotency_key')` makes this atomic: two concurrent identical retains yield one memory, and the loser returns it as a duplicate. Without a key, behaviour is unchanged.

Rows written before the unique index existed are migrated at startup, once, inside one transaction, before the index is built (`migrate_idempotency_keys` in `server.py`): stored keys are trimmed and blank/null keys dropped; rows carrying only `refs.event_id` get `refs.idempotency_key = trim(event_id)`; and where more than one row in a domain holds the same key, the earliest row keeps it and the others lose the key and record `refs.idempotency_duplicate_of = <winner id>` plus `refs.idempotency_key_retired`. Nothing is deleted. Rows whose `refs` is not a JSON object are left alone. To preview what the dedupe step would touch on a database:

```sql
SELECT domain, refs->>'idempotency_key' AS key, count(*)
FROM memories
WHERE jsonb_typeof(refs) = 'object' AND refs ? 'idempotency_key'
GROUP BY 1, 2 HAVING count(*) > 1;
```

`python test_retain_idempotency.py` covers the request path and the migration's statement order without a database; set `MEMIBRIUM_TEST_DSN` to a disposable Postgres to also run the migration for real (CI does this with a `postgres:16` service).

---

## Additional routes in `server.py`

The tables above are the README's view (16 MCP tools). `server.py` registers 26 routes in total. The ones not listed above, with a one-line description taken from each handler's docstring or body (`server.py`, `app = Starlette(routes=[...])`):

| Endpoint | Method | What |
|---|---|---|
| `/health` | GET | Liveness probe; returns `{"status": "ok", "engine": "memibrium"}`. Used by the Dockerfile `HEALTHCHECK` and the Caddy `/health` handle. |
| `/mcp/test_embeddings` | POST | Test both the Ollama and Azure embedding endpoints on one text and compare (diagnostic). |
| `/mcp/retain/diagnostics` | GET, POST | Snapshot of retain requests still in flight (`memibrium.retain.pending_diagnostics.v1`). |
| `/mcp/graph` | GET | Memory graph topology: nodes, edges, analytics (from `memory_edges`). |
| `/mcp/prefetch` | POST | Predictive memory pre-fetching from a recent `context_query`. |
| `/mcp/self_model/observe` | POST | Create a source-backed Ethos/Disposition/DNA self-model observation. |
| `/mcp/self_model/observations` | GET, POST | List self-model observations (`engine`, `entity_ids`, `include_rejected`, `limit`). |
| `/mcp/decision_trace` | POST | Persist an auditable decision/evidence trace for reward-aware memory. |
| `/mcp/decision_traces` | GET, POST | List decision traces (`status`, `limit`). |
| `/mcp/context_packet` | POST | Compose a grounded context packet from episodic, graph and self-model evidence (`query`, `top_k`, `include_source_attribution`, `include_recall_telemetry`). Used by the LongMemEval retrieval bridge (see `docs/eval/`). |

Request bodies are JSON. Handlers return HTTP 400 with `{"error": ...}` when a required field is missing (`content`, `query`, `topic`, `memory_id`). The MCP tool manifest served at `GET /mcp/tools` is the authoritative list of tool names and input schemas for MCP clients.

**Inbound authentication:** none of these routes check a credential today; the server trusts the network it is bound to (`0.0.0.0:9999` when started with `python server.py`). Tracked as MED-234.

---

## Prompts to Try

Once the plugin is installed, try prompts like these:

- `Remember that our API rate limit is 1000 req/min.`
- `What do you know about the deployment architecture?`
- `Confirm that the rate limit information is correct.`
- `Freeze the deployment architecture memories before we change things.`
- `Show me the memory dashboard.`
- `What's the lifecycle state of what you know about our auth system?`
