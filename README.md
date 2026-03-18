# Memibrium — Sovereign AI Memory with Crystallization Theory

> **"It gets smarter without getting wiser."** — That's the problem this stack is built to solve.

Sovereign, self-hosted memory infrastructure implementing **Crystallization Theory** as a knowledge governance layer over tiered vector search. Ships as a plugin: one skill + one MCP server = governed memory for any agent.

**Patent POC:** CT #63/953,509 · KEOS #63/962,609 · STG (pending)

[![Status](https://img.shields.io/badge/status-production-green)]()
[![Plugin](https://img.shields.io/badge/distribution-plugin-purple)]()
[![MCP](https://img.shields.io/badge/protocol-MCP-blue)]()
[![LLM](https://img.shields.io/badge/LLM-any%20OpenAI--compatible-orange)]()
[![Sovereign](https://img.shields.io/badge/sovereignty-full-darkgreen)]()
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.18150324.svg)](https://doi.org/10.5281/zenodo.18150324)

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

**Cursor / other MCP clients:** See [DISTRIBUTION.md](DISTRIBUTION.md)

### 3. Verify

Ask your agent: *"What do you know about my project?"*

You should get a governed memory response with lifecycle states — not a generic "I don't have memory" answer.

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

The plugin wires in the **Memibrium MCP Server**, which gives your agent **8 tools** for governed memory operations. That is the execution layer for storing, retrieving, confirming, freezing, and reverting knowledge.

### Why this plugin is different

This is not a prompt pack. It is a packaged knowledge governance layer:

- **The skill** teaches the agent when to store, when to cite, and what to avoid.
- **The MCP tools** let the agent act on live memory with lifecycle guarantees.
- **The plugin** keeps the guidance layer and execution layer aligned in one install.
- **Multi-host support** lets you use the same governed memory across Claude Code, Copilot CLI, Cursor, and other compatible hosts.

---

## Architecture

![Technical Architecture](assets/technical-architecture.png)

```
Plugin Install
  ├─ Skill (SKILL.md) → loaded into agent system prompt
  │   "How the agent should think about memory"
  │
  └─ MCP Server (.mcp.json → server.py on :9999)
      └─ CT Lifecycle Engine (the patent layer)
          └─ pgvector dual-tier (hot=working, cold=crystallized)
              └─ Any OpenAI-compatible LLM provider
```

**Tiering policy = lifecycle state.** That's the paper.

| Tier | States | Engine | Latency |
|---|---|---|---|
| **Hot** | observation, consideration, accepted | pgvector → [RuVector](https://github.com/ruvnet/ruvector) (Phase 2.5) | <1ms target |
| **Cold** | crystallized, shed | pgvector → [LEANN](https://github.com/yichuan-w/LEANN) compression (Phase 3) | 2-5s acceptable |

---

## What You Get

| Component | What it adds | Examples |
|---|---|---|
| **Crystallization skill** | Memory governance, behavioral rules, guardrails | 8 rules: cite by state, never auto-crystallize, freeze before destructive changes |
| **Memibrium MCP** | Live memory tooling with lifecycle guarantees | retain, recall, reflect, confirm, freeze, revert, consolidate, dashboard |

---

## MCP Tools (8 endpoints)

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

### Lifecycle Flow

![Lifecycle Flow](assets/lifecycle-flow.png)

```
Content arrives
  │
  ├─ IngestAgent: score importance (LLM, informational only)
  ├─ Embed via configured LLM provider (OpenAI-compatible)
  ├─ Store as OBSERVATION → gate → ACCEPTED (or stay in observation)
  ├─ Extract entities → update world-state graph
  │
  ▼ (every 30 minutes)
ConsolidateAgent:
  ├─ Apply δ-decay: R(t+1) = R(t) × (1 - δ)
  ├─ W(k,t) < 0.15 → SHED (archived, removed from hot)
  ├─ confirmation_count ≥ 3 AND validation ≥ 0.5 → CRYSTALLIZED
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

## Competitive Landscape (March 2026)

| Capability | mem0 | supermemory | Google Agent | Hindsight | memU | **This** |
|---|---|---|---|---|---|---|
| Importance scoring (LLM-gated writes) | ❌ | ❌ | ✅ | ❌ | ⚠️¹ | ✅ |
| Entity extraction + world state | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Background consolidation (δ-decay) | ❌ | ❌ | ✅ | ❌ | ✅ | ✅ |
| Vector search (real cosine scores) | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ |
| Hot/cold tiered storage | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| MCP endpoint | ✅ | ✅ | ❌ | ✅ | ❌ | ✅ |
| Sovereign (self-hosted, no cloud deps) | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ |
| Multi-model routing | ❌ | ❌ | ❌ | ❌ | ✅² | ✅ |
| One-command deploy | ❌ | ✅ | ❌ | ✅ | ⚠️³ | ✅ |
| LLM-generated summaries | ❌ | ❌ | ✅ | ❌ | ✅ | ✅ |
| Topic expansion | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Proactive intent prediction | ❌ | ❌ | ❌ | ❌ | ✅ | ❌⁴ |
| Hierarchical memory (3-layer) | ❌ | ❌ | ❌ | ❌ | ✅ | ❌⁴ |
| Multimodal ingestion | ❌ | ❌ | ❌ | ❌ | ✅ | ❌⁴ |
| Benchmark published (Locomo) | ❌ | ❌ | ❌ | ❌ | ✅ | ❌⁴ |
| **Human-gated crystallization** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Witness chain provenance** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Freeze / revert (COW snapshots)** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| **W(k,t) mathematical scoring** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Plugin distribution (skill + MCP)** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |

**Score** | 4/20 | 4/20 | 5/20 | 5/20 | 10/20 | **16/20** |

> ¹ memU stores everything then auto-organizes — no LLM gate on ingest.
> ² memU supports `llm_profiles` for provider switching, not per-operation model routing.
> ³ memU self-hosted requires Python 3.13+, PostgreSQL + pgvector.
> ⁴ Roadmap. Proactive prediction = Phase 4. Hierarchical memory = Phase 5.

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

python server.py
```

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

## Repository Layout

```
memibrium/
├── .claude-plugin/
│   └── marketplace.json                    # Marketplace registry
├── plugins/
│   └── memibrium/
│       ├── .claude-plugin/
│       │   └── plugin.json                 # Plugin manifest
│       ├── .mcp.json                       # MCP config (auto-wired on install)
│       └── skills/
│           └── crystallization-memory/
│               └── SKILL.md                # Governance skill (8 rules)
├── server.py                               # CT memory server (8 MCP endpoints)
├── Caddyfile                               # TLS termination + reverse proxy
├── deploy/                                 # Terraform (Azure VM)
│   ├── main.tf
│   ├── modules/vm/cloud-init.yaml
│   ├── modules/cognitive/main.tf
│   └── modules/network/main.tf
├── assets/                                 # Architecture diagrams
├── DISTRIBUTION.md                         # Plugin architecture + install paths
├── SECURITY.md
└── README.md                               # This file
```

---

## Design Decisions

1. **Plugin-first distribution.** The skill teaches the agent *how to think about memory*. The MCP handles execution. The plugin keeps both aligned in one install. Follows the [microsoft/azure-skills](https://github.com/microsoft/azure-skills) pattern.

2. **Crystallization Theory as governance.** The CT lifecycle engine sits ABOVE the vector store. The innovation is in the governance — W(k,t), δ-decay, human-gated crystallization — not the storage engine. Swap pgvector for RuVector, the claims still hold.

3. **Human consensus, not ML confidence.** STG Claim 1 negative limitation: `confirm` is the ONLY path to crystallization. The LLM importance score is informational, not authoritative.

4. **Tiering = lifecycle state.** Observation/consideration/accepted → hot tier. Crystallized/shed → cold tier. The state machine IS the tiering policy.

5. **Entity graph as world state.** "I moved to Berlin" updates a Location entity, doesn't just store a new vector.

6. **Fully sovereign.** No cloud memory services. Everything runs on your infrastructure.

7. **Witness chains everywhere.** Every state transition produces a hash-linked provenance entry. Tamper-evident. Append-only.

---

## Roadmap

| Phase | What | Status |
|---|---|---|
| **1** | LEANN + Foundry + MCP (v1) | ✅ Shipped |
| **2** | CT lifecycle engine + pgvector dual-tier + entity graph | ✅ Shipped |
| **2.5** | Plugin architecture (azure-skills pattern) | ✅ Shipped |
| **3** | Swap hot tier pgvector → [RuVector](https://github.com/ruvnet/ruvector) (Rust HNSW, <1ms) | Next |
| **4** | [LEANN](https://github.com/yichuan-w/LEANN) compression on cold tier (97% storage savings) | Planned |
| **5** | Proactive intent prediction | Planned |
| **6** | Hierarchical memory with CT crystallization layers | Planned |
| **7** | Multimodal ingestion (docs, images, audio) | Planned |
| **8** | [Cognitum](https://cognitum.ai) edge deploy — sovereign, <15W | Waiting on hardware |

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

---

## Prompts to Try

Once the plugin is installed, try prompts like these:

- `Remember that our API rate limit is 1000 req/min.`
- `What do you know about the deployment architecture?`
- `Confirm that the rate limit information is correct.`
- `Freeze the deployment architecture memories before we change things.`
- `Show me the memory dashboard.`
- `What's the lifecycle state of what you know about our auth system?`

---

## Learn More

- [DISTRIBUTION.md](DISTRIBUTION.md) — Plugin architecture, all install paths, MemSkill comparison
- [SECURITY.md](SECURITY.md) — Security policy
- [Crystallization Theory paper](https://doi.org/10.5281/zenodo.18150324)

---

*Adapted from [Google's Always-On Memory Agent](https://research.google/blog/) research.*
*Hot tier: [RuVector](https://github.com/ruvnet/ruvector) by [rUv](https://github.com/ruvnet) · Cold tier: [LEANN](https://github.com/yichuan-w/LEANN) by Berkeley SkyLab.*
*Memibrium — Crystallization Theory by Richard "Ricky" Valentine / [Orchard Holdings LLC](https://github.com/rvalen1123)*

> "The system gets wiser—not merely smarter—because the wisdom is human wisdom, accumulated through deliberate consensus and preserved through sovereign governance."
