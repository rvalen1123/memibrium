# Memibrium HTTP / MCP API

> Relocated from the root `README.md` in the MED-242 docs pass (2026-11-02) and corrected against `server.py`. The [README](../README.md) is the short entry point.

Sections: Counts · MCP endpoint · Core memory routes · Ingestion routes · Idempotent retain · Other routes · Prompts to Try.

This page gives one line per route. It documents request fields only for idempotent retain and the two list routes; for every tool's input fields, read the `inputSchema` entries served by `GET /mcp/tools` (`handle_mcp_manifest` in `server.py`).

---

## Counts

- **27 HTTP routes** are registered in `app = Starlette(routes=[...])`: the MCP protocol endpoint `/mcp` and 26 REST routes (one route, `/mcp/ingest/taxonomy`, accepts both GET and POST).
- **18 MCP tools** are listed by `GET /mcp/tools`. Each maps to one route: `retain`, `recall`, `reflect`, `confirm`, `freeze`, `revert`, `consolidate`, `dashboard` (the eight core governance tools), `prefetch` → `/mcp/prefetch`, `self_model_observe` → `/mcp/self_model/observe`, `context_packet` → `/mcp/context_packet`, `decision_trace` → `/mcp/decision_trace`, `ingest_file`, `ingest_directory`, `ingest_jsonl`, `ingest_status` → `/mcp/ingest/{file,directory,jsonl,status}`, `compile_wiki` → `/mcp/ingest/compile`, `wiki_read` → `/mcp/wiki`.
- The other 9 routes have no manifest entry: `/mcp` (the MCP endpoint itself), `/health`, `/mcp/tools`, `/mcp/test_embeddings`, `/mcp/retain/diagnostics`, `/mcp/graph`, `/mcp/self_model/observations`, `/mcp/decision_traces`, `/mcp/ingest/taxonomy`.
- **10 of the 18 tools are served over MCP** at `POST /mcp` by default: `confirm`, `revert`, `consolidate` and `freeze` are always withheld, and the four path tools (`ingest_file`, `ingest_directory`, `ingest_jsonl`, `compile_wiki`) are served only when `MCP_INGEST_ROOTS` is set (see [MCP endpoint](#mcp-endpoint)).

---

## MCP endpoint

`POST /mcp` is the endpoint the plugin's `.mcp.json` points MCP clients (Claude Code, Codex, other hosts) at. It speaks MCP over stateless streamable HTTP and replies with JSON (`handle_mcp_protocol` / `mcp_dispatch` in `server.py`, MED-254):

- **Protocol versions.** `2026-07-28` (per-request `params._meta` with `io.modelcontextprotocol/protocolVersion` and `io.modelcontextprotocol/clientCapabilities`, `server/discover`, and the `MCP-Protocol-Version` / `Mcp-Method` / `Mcp-Name` headers, which must match the body), plus the legacy `initialize` handshake for `2025-11-25`, `2025-06-18` and `2025-03-26`. An unknown legacy version negotiates `2025-11-25`.
- **Methods.** `initialize`, `notifications/initialized` (and any other notification: HTTP 202, empty body), `ping`, `tools/list`, `tools/call`, and `server/discover` for 2026-07-28 clients. Anything else is JSON-RPC `-32601`.
- **Stateless.** No `Mcp-Session-Id`, no server-initiated streams. `GET /mcp` and `DELETE /mcp` return 405 with `Allow: POST`.
- **Transport refusals.** A request with an `Origin` header gets 403 (MCP clients send none; a browser page always does, so this blocks DNS-rebinding pages). A body that is not `application/json` gets 415; invalid JSON gets 400 with JSON-RPC `-32700`; a batch (JSON array) gets 400 with `-32600`; an unsupported `MCP-Protocol-Version` gets 400 with `-32022`.
- **Tools.** `tools/list` returns the `GET /mcp/tools` manifest entries (same names, descriptions and `inputSchema`s, except that `compile_wiki` has no `output_dir` over MCP) with MCP `annotations`, minus the withheld and ungated path tools. `tools/call` checks the arguments against that `inputSchema` before dispatch: an undeclared argument, a missing required one, or a value of the wrong JSON type, outside an `enum`, outside `minimum`/`maximum`, or with array items of the wrong type is JSON-RPC `-32602` (so `skip_duplicates: "false"` is refused, not read as true). `top_k` is bounded to 1–50 (`TOOL_TOP_K_MAX`) on `recall`, `reflect`, `prefetch` and `context_packet`, and `confidence` to 0–1; the REST routes do not enforce these bounds. Then it runs the tool's REST handler with the arguments as its JSON body (or query parameters for the GET routes `dashboard`, `ingest_status`, `wiki_read`). The handler's JSON comes back as a `text` content item, and as `structuredContent` when it is an object; a handler status ≥ 400 or an exception sets `isError: true`.

**Served by default (10):** `retain`, `recall`, `reflect`, `dashboard`, `prefetch`, `self_model_observe`, `context_packet`, `decision_trace`, `ingest_status`, `wiki_read`.

**Path tools, default-deny (4):** `ingest_file`, `ingest_directory`, `ingest_jsonl` and `compile_wiki`. Over MCP an agent that reads untrusted content could otherwise ingest any file the server can read (`.env`, keys) and read it back through `recall`. With `MCP_INGEST_ROOTS` unset or empty (the default), they are not in `tools/list` and `tools/call` refuses them with `-32602` and the reason. With `MCP_INGEST_ROOTS` set (an `os.pathsep`-separated list of directories, canonicalised with `realpath` at import), they are served, and:

- `filepath` (`ingest_file`, `ingest_jsonl`) and `directory` (`ingest_directory`) must resolve, after `realpath` (symlinks and `..` followed), to a root or a path under one; otherwise `-32602`.
- For `ingest_directory`, every file it would ingest (the same `rglob`/`glob` selection the engine uses) must also resolve inside the roots, so a symlink inside an allowed directory that points outside it refuses the whole call. The check runs just before the ingest; a process that can write inside a root could still swap a file between the check and the read.
- `compile_wiki` does not accept `output_dir` over MCP (`-32602`), because that argument re-points the shared `wiki_compiler.output_dir` for every later client. Over MCP the wiki is compiled to its configured location.

The REST routes are not affected by `MCP_INGEST_ROOTS`.

**Withheld (4), the human-only governance tools:** three can move a memory to `crystallized` without a human, and `freeze` would let an agent protect and boost its own memories. They are not in `tools/list`, `tools/call` refuses them with `-32602` and the reason, and they have no entry in the dispatch table (`MCP_TOOL_DISPATCH`). Their REST routes are unchanged for humans and human-operated tools.

| Tool | Why it is not offered to agents |
|---|---|
| `confirm` | The human validation signal and the only path to crystallization. An agent calling it would be confirming its own output. |
| `consolidate` | `ConsolidateAgent.run_cycle` moves `accepted` memories that have reached `CRYSTALLIZE_CONFIRMATIONS` to `crystallized`. It already runs every `CONSOLIDATE_INTERVAL_MIN`. |
| `revert` | `ColdStore.revert` writes the snapshot's `state` back, which can be `crystallized`, without a confirmation and without a witness entry. |
| `freeze` | `ColdStore.freeze` sets `frozen = TRUE`, which takes the memory out of `get_active_memories` and so out of decay and shedding, and `handle_freeze` records ranking feedback with weight 2.0. An agent could protect and boost its own memories. Freeze and revert are a paired governance action; freeze stays human-only until Ricky decides otherwise. |

Arguments outside a tool's schema are refused rather than passed through. This matters for `self_model_observe`, whose REST body would also accept `lifecycle_state` and `user_state` (for example `user_state: "confirmed"`): over MCP those fields cannot be set. `test_mcp_endpoint.py` (in CI, no database) covers the handshake, `tools/list`, a read-only `tools/call`, both eras' header rules, the transport refusals, value validation, the path-tool gate (unset, out-of-root, `..`, symlink escapes, in-root) and the withheld tools in both `tools/list` and `tools/call`.

**No inbound authentication.** `/mcp` inherits the same no-auth exposure as every `/mcp/*` route (MED-234): anyone who can reach the port can call the served tools. Withholding a tool from MCP does not protect its REST route: `POST /mcp/confirm`, `/mcp/freeze`, `/mcp/revert`, `/mcp/consolidate` and the ingest routes check no caller, so any process with HTTP access to the port can still call them directly. Keep the server on loopback or a private network.

---

## Core memory routes

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
| `/mcp` | POST | MCP protocol endpoint for plugin clients (see [MCP endpoint](#mcp-endpoint)); GET and DELETE return 405 | — |
| `/mcp/tools` | GET | MCP tool manifest for auto-discovery (not itself a tool) | — |

## Ingestion routes

Seven routes, six of them manifest tools (`/mcp/ingest/taxonomy` is not).

| Endpoint | Method | What |
|---|---|---|
| `/mcp/ingest/file` | POST | Ingest a single file: read → chunk → classify → embed → CT lifecycle |
| `/mcp/ingest/directory` | POST | Scan directory, ingest all supported files (.md, .txt, .json, .csv, .pdf; PDF needs the optional library below) |
| `/mcp/ingest/jsonl` | POST | Ingest Claude conversation JSONL with auto-classification into 30 knowledge categories |
| `/mcp/ingest/status` | GET | Ingestion engine stats: hashes seen, taxonomy breakdown, config |
| `/mcp/ingest/compile` | POST | Compile wiki index from ingested memories — generates topic articles + backlinks |
| `/mcp/ingest/taxonomy` | GET, POST | GET: view the 30-category knowledge taxonomy with CT tier assignments. POST: update taxonomy categories at runtime. |
| `/mcp/wiki` | GET | List compiled wiki files or read a specific file's content |

**PDF files need an optional dependency.** `requirements.txt` does not install a PDF library. `ingest_engine._extract_pdf_text` tries PyMuPDF (`import fitz`), then `pypdf`; with neither it logs `No PDF library available. Install PyMuPDF or pypdf.` and returns empty text, so the PDF produces zero chunks rather than an error. Install one with `pip install pymupdf` or `pip install pypdf` (the Docker image installs neither).

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

`python test_retain_idempotency.py` covers the request path and the migration's statement order without a database; set `MEMIBRIUM_TEST_DSN` to a disposable Postgres to also run the migration for real (CI does this against a digest-pinned `pgvector/pgvector:0.8.7-pg16` service and fails on any skip; local recipe in [operations.md](operations.md#testing)).

---

## Other routes

The routes not listed above, with a one-line description taken from each handler's docstring or body. Four of them are also manifest tools, marked "(tool)".

| Endpoint | Method | What |
|---|---|---|
| `/health` | GET | Liveness probe; returns `{"status": "ok", "engine": "memibrium"}`. Used by the Dockerfile `HEALTHCHECK` and the Caddy `/health` handle. |
| `/mcp/test_embeddings` | POST | Diagnostic: embed one text with the configured embedder and with an Azure deployment, and compare. The Azure half is legacy and returns an error now that the subscription is closed ([operations](operations.md#legacy-azure-subscription-closed-not-maintained)). |
| `/mcp/retain/diagnostics` | GET, POST | Snapshot of retain requests still in flight (`memibrium.retain.pending_diagnostics.v1`). |
| `/mcp/graph` | GET | Memory graph topology: nodes, edges, analytics (from `memory_edges`). |
| `/mcp/prefetch` | POST | (tool) Predictive memory pre-fetching from a recent `context_query`. |
| `/mcp/self_model/observe` | POST | (tool) Create a source-backed Ethos/Disposition/DNA self-model observation. |
| `/mcp/self_model/observations` | GET, POST | List self-model observations. Filters (`engine`, `entity_ids`, `include_rejected`, `limit`) are read only from a POST JSON body; GET ignores query parameters and returns the unfiltered default (top 20 by confidence, then recency; rejected excluded). |
| `/mcp/decision_trace` | POST | (tool) Persist an auditable decision/evidence trace for reward-aware memory. |
| `/mcp/decision_traces` | GET, POST | List decision traces. Filters (`status`, `limit`) are read only from a POST JSON body; GET ignores query parameters and returns the unfiltered default (newest 10 traces, any status). |
| `/mcp/context_packet` | POST | (tool) Compose a grounded context packet from episodic, graph and self-model evidence (`query`, `top_k`, `include_source_attribution`, `include_recall_telemetry`). Used by the LongMemEval retrieval bridge (see `docs/eval/`). |

Request bodies are JSON. Handlers return HTTP 400 with `{"error": ...}` when a required field is missing (`content`, `query`, `topic`, `memory_id`). This page has no per-route field tables; the manifest served at `GET /mcp/tools` is the authoritative list of tool names and input schemas.

**Inbound authentication:** none of these routes (nor `POST /mcp`) check a credential today; the server trusts the network it is bound to (`0.0.0.0:9999` when started with `python server.py`; `127.0.0.1:9999` from the compose stack unless `MEMIBRIUM_BIND` is set). Tracked as MED-234.

---

## Prompts to Try

Once the plugin is installed, try prompts like these:

- `Remember that our API rate limit is 1000 req/min.`
- `What do you know about the deployment architecture?`
- `Is the rate limit information confirmed yet?` (the agent reports the memory's state; confirming it is yours to do with `POST /mcp/confirm`, which is not an MCP tool)
- `Which memories should I freeze before we change the deployment architecture?` (freezing them is yours to do with `POST /mcp/freeze`, which is not an MCP tool)
- `Show me the memory dashboard.`
- `What's the lifecycle state of what you know about our auth system?`
