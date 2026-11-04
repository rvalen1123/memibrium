# Memibrium architecture

> Relocated from the root `README.md` in the MED-242 docs pass (2026-11-02); counts, thresholds and the repository layout corrected against the code. The [README](../README.md) is the short entry point.

Sovereign, self-hosted memory infrastructure implementing **Crystallization Theory** as a knowledge governance layer over tiered vector search. Ships as a plugin: one skill + one MCP server = governed memory for any agent.

**Patent POC:** CT #63/953,509 · KEOS #63/962,609 · STG (pending)

Sections: One Install, Two Layers · Architecture · What You Get · Lifecycle Flow · The CT Distinction · Design Decisions · Patent ↔ Code Map · Repository Layout.

---

## One Install, Two Layers

### The skill: the brain

The plugin ships **one governance skill** (`crystallization-memory`) that teaches agents how memory works in this system. It provides 8 behavioral rules, anti-patterns, and interaction patterns:

- All knowledge enters as untrusted (OBSERVATION state)
- Check lifecycle state before citing any memory
- Human confirmation is the ONLY crystallization path
- Contradictions trigger investigation, not overwrites
- Freeze before destructive changes; revert if wrong

### The MCP server: the hands

The plugin wires in the **Memibrium MCP Server**. Its manifest (`GET /mcp/tools`) lists **18 tools**: the 8 core governance tools (retain, recall, reflect, confirm, freeze, revert, consolidate, dashboard), 4 context tools (prefetch, self_model_observe, context_packet, decision_trace) and 6 ingestion tools. The server registers 27 HTTP routes in all; [api.md](api.md#counts) maps each tool to its route. MCP clients connect to `POST /mcp`, which serves 10 of those tools by default, always withholds the human-only governance tools `confirm`, `revert`, `consolidate` and `freeze`, and serves the four path tools only inside `MCP_INGEST_ROOTS` ([api.md](api.md#mcp-endpoint)). That is the execution layer for storing, retrieving, confirming, freezing, and reverting knowledge.

### Why this plugin is different

This is not a prompt pack. It is a packaged knowledge governance layer:

- **The skill** teaches the agent when to store, when to cite, and what to avoid.
- **The MCP tools** let the agent act on live memory with lifecycle guarantees.
- **The plugin** keeps the guidance layer and execution layer aligned in one install.
- **Multi-host support** lets you use the same governed memory across Claude Code, Copilot CLI, Cursor, and other compatible hosts.

---

## Architecture

![Technical Architecture](../assets/technical-architecture.png)

```
Plugin Install
  ├─ Skill (SKILL.md) → loaded into agent system prompt
  │   "How the agent should think about memory"
  │
  └─ MCP Server (.mcp.json → server.py on :9999)
      └─ CT Lifecycle Engine (the patent layer)
          └─ pgvector dual-tier (hot=working, cold=crystallized)
              └─ Keyless OpenAI-compatible endpoints (Ollama by default)
```

**Tiering policy = lifecycle state.** That's the paper.

| Tier | States | Engine | Latency |
|---|---|---|---|
| **Hot** | observation, consideration, accepted | [RuVector](https://github.com/ruvnet/ruvector) HNSW + GNN (or pgvector fallback) | <1ms |
| **Cold** | crystallized, shed | [LEANN](https://github.com/yichuan-w/LEANN) graph recomputation (or pgvector fallback) | ~250ms |

---

## What You Get

| Component | What it adds | Examples |
|---|---|---|
| **Crystallization skill** | Memory governance, behavioral rules, guardrails | 8 rules: cite by state, never auto-crystallize, freeze before destructive changes |
| **Memibrium MCP** | Live memory tooling with lifecycle guarantees | retain, recall, reflect, confirm, freeze, revert, consolidate, dashboard |
| **Ingestion engine** | Bulk document/conversation ingest with classification | File/directory/JSONL ingest, 30-category taxonomy, wiki compilation, provenance tracking |
| **RuVector engine** | GNN re-ranking + SONA self-learning on hot tier | Sub-millisecond HNSW, results improve over time, drop-in pgvector replacement |
| **LEANN cold tier** | 97% storage compression on crystallized memories | Graph-based recomputation, no stored embeddings, ~250ms search |

---

### Lifecycle Flow

![Lifecycle Flow](../assets/lifecycle-flow.png)

```
Content arrives
  │
  ├─ IngestAgent: score importance (LLM, informational only)
  ├─ Embed via configured LLM provider (OpenAI-compatible)
  ├─ Store as OBSERVATION → gate → ACCEPTED (or stay in observation)
  ├─ Extract entities → update world-state graph
  │
  ▼ (every CONSOLIDATE_INTERVAL_MIN, default 30 minutes)
ConsolidateAgent:
  ├─ Apply δ-decay: R(t+1) = R(t) × (1 - δ)   (δ = DECAY_RATE, default 0.02, scaled per memory type)
  ├─ W(k,t) < SHEDDING_THRESHOLD (default 0.05), state ≠ observation → SHED (archived, removed from hot)
  ├─ confirmation_count ≥ CRYSTALLIZE_CONFIRMATIONS (default 3) AND validation ≥ 0.5 → CRYSTALLIZED
  └─ All transitions recorded in witness chain
  │
  ▼ (on query)
QueryAgent:
  ├─ Tier 1: Hot search (observation/consideration/accepted)
  │   Score = cosine × (1 + log(1 + W(k,t)))
  │   ≥ 2 results > 0.6? → return
  └─ Tier 2: Cold search (crystallized/shed) + topic expansion
```

---

## The CT Distinction

Every other memory system stores everything and hopes retrieval sorts it out. This stack implements **principled pruning** via Crystallization Theory:

- **W(k,t) = (C × R × V) / A** — mathematical weight function drives ranking AND shedding
- **δ-decay** — recency degrades every 30 minutes. Memories must earn survival through human confirmation.
- **Human-gated crystallization** — `confirm` is the ONLY path from `accepted` → `crystallized`. No ML confidence score can crystallize a memory. (STG Claim 1: negative limitation)
- **Witness chains** — every state transition is hash-linked, append-only, tamper-evident. (STG Claim 6)
- **Freeze/revert** — COW snapshots let you freeze a memory (exempt from decay) and revert to any prior state. (STG Claim 7)

> *"Pruning is where most memory systems fall apart. Without decay or relevance scoring, you end up with a dense context of outdated state that can mislead the model worse than no memory at all."*

---

## Design Decisions

1. **Plugin-first distribution.** The skill teaches the agent *how to think about memory*. The MCP handles execution. The plugin keeps both aligned in one install. Follows the [microsoft/azure-skills](https://github.com/microsoft/azure-skills) pattern.

2. **Crystallization Theory as governance.** The CT lifecycle engine sits ABOVE the vector store. The innovation is in the governance — W(k,t), δ-decay, human-gated crystallization — not the storage engine. Swap pgvector for RuVector, the claims still hold.

3. **Human consensus, not ML confidence.** STG Claim 1 negative limitation: `confirm` is the ONLY path to crystallization. The LLM importance score is informational, not authoritative.

4. **Tiering = lifecycle state.** Observation/consideration/accepted → hot tier. Crystallized/shed → cold tier. The state machine IS the tiering policy.

    > **Note:** The `consideration` state is defined in the schema and transition table but currently unused in code — `IngestAgent` gates directly from `observation` → `accepted`. This state is reserved for the patent's 5-stage lifecycle claims (CT §4) and will be activated when multi-reviewer confirmation workflows ship in Phase 4.

5. **Entity graph as world state.** "I moved to Berlin" updates a Location entity, doesn't just store a new vector.

6. **Fully sovereign.** No cloud memory services. Everything runs on your infrastructure.

7. **Witness chains everywhere.** Every state transition produces a hash-linked provenance entry. Tamper-evident. Append-only.
8. **Benchmark discipline over feature churn.** For LOCOMO-style temporal and multi-hop regressions, prefer overlap analysis and failure-mode classification before adding broader retrieval or prompt complexity.

---

## Patent ↔ Code Map

| Patent Claim | Implementation | Section |
|---|---|---|
| CT: 5-stage lifecycle | `LifecycleState` enum, `VALID_TRANSITIONS`, state machine | §1 |
| CT: W(k,t) = (C×R×V)/A | `compute_weight()` — drives ranking AND shedding | §1 |
| CT: δ-decay | `ConsolidateAgent.run_cycle()` — R(t+1) = R(t)×(1-δ) | §4 |
| STG Claim 1: negative limitation | `confirm` is ONLY crystallization path, NOT ML confidence | §5 |
| STG Claim 6: witness chains | `make_witness_entry()` — hash-linked, append-only | §1 |
| STG Claim 7: freeze/revert | `ColdStore.freeze()` / `revert()` — COW snapshots | §2 |
| Entity graph | `entities` table + `upsert_entity()` — world state management | §2 |
| **Skill governance** | `SKILL.md` — behavioral rules enforced at agent level | Plugin |
| **LEANN cold tier** | `LEANNColdTier` — graph recomputation, 97% compression | §2b |

---

## Repository Layout

```
memibrium/
├── server.py                               # CT memory server (27 routes, 18 manifest tools)
├── ingest_engine.py                        # Document/JSONL ingestion + wiki compiler
├── knowledge_taxonomy.py                   # 30-category classifier with CT tier mapping
├── plugins/
│   └── memibrium/
│       ├── .mcp.json                       # MCP config (auto-wired on install)
│       └── skills/
│           └── crystallization-memory/
│               └── SKILL.md                # Governance skill (8 rules)
├── test_taxonomy.py                        # 40/40 taxonomy classifier tests
├── test_ingest_unit.py                     # 34/34 chunking + provenance tests
├── test_ingest_e2e.py                      # Ingestion endpoint E2E tests
├── test_production_e2e.py                  # Core endpoint E2E tests
├── test_ruvector_e2e.py                    # RuVector integration tests
├── test_leann_e2e.py                       # LEANN cold tier tests
├── docker-compose.ruvector.yml             # One-command RuVector + Memibrium setup
├── Caddyfile                               # legacy Azure edge config (MED-233)
├── deploy/                                 # legacy Azure Terraform (MED-233)
├── assets/                                 # Architecture diagrams
├── DISTRIBUTION.md                         # Plugin architecture + install paths
└── SECURITY.md
```
