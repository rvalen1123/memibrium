# Memibrium — Sovereign AI Memory with Crystallization Theory

> **"It gets smarter without getting wiser."** — That's the problem this stack is built to solve.

A sovereign, self-hosted memory infrastructure implementing **Crystallization Theory** as a knowledge governance layer over tiered vector search. No cloud memory dependencies.

Adapted from [Google's Always-On Memory Agent](https://research.google/blog/) research pattern, with [RuVector](https://github.com/ruvnet/ruvector) (rUv) as the target hot-tier engine and [LEANN](https://github.com/yichuan-w/LEANN) (Berkeley SkyLab, MLSys 2026) for cold-tier compression.

**Patent POC:** CT #63/953,509 · KEOS #63/962,609 · STG (pending)

[![Status](https://img.shields.io/badge/status-production-green)]()
[![MCP](https://img.shields.io/badge/protocol-MCP-blue)]()
[![LLM](https://img.shields.io/badge/LLM-any%20OpenAI--compatible-orange)]()
[![Sovereign](https://img.shields.io/badge/sovereignty-full-darkgreen)]()

---

## Architecture

![Technical Architecture](assets/technical-architecture.png)

```
MCP Clients → Caddy TLS → Memibrium (server.py)
  → CT Lifecycle Engine (the patent layer)
  → pgvector dual-tier (hot=working, cold=crystallized)
  → Any OpenAI-compatible LLM provider
```

**Tiering policy = lifecycle state.** That's the paper.

| Tier | States | Engine | Latency |
|---|---|---|---|
| **Hot** | observation, consideration, accepted | pgvector → [RuVector](https://github.com/ruvnet/ruvector) (Phase 2.5) | <1ms target |
| **Cold** | crystallized, shed | pgvector → [LEANN](https://github.com/yichuan-w/LEANN) compression (Phase 3) | 2-5s acceptable |

**Why RuVector for hot:** Rust-native HNSW with sub-millisecond search, built-in witness chains, SONA self-learning re-ranking, and a direct path to [Cognitum](https://cognitum.ai) hardware deployment. Created by [rUv](https://github.com/ruvnet) — the same team building the agentic chip. MIT licensed.

**Why LEANN for cold:** 97% storage compression by recomputing vectors on-the-fly instead of storing pre-built indexes. 100GB of embeddings → ~5GB on disk. Makes years of crystallized history viable on constrained hardware. From Berkeley SkyLab (MLSys 2026).

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

**Score** | 4/19 | 4/19 | 5/19 | 5/19 | 10/19 | **15/19** |

> ¹ memU stores everything then auto-organizes — no LLM gate on ingest. "Self-Evolution" is [labeled "Coming Soon"](https://memu.pro/docs) as of March 2026.
> ² memU supports `llm_profiles` for provider switching, not per-operation model routing.
> ³ memU self-hosted requires Python 3.13+, PostgreSQL + pgvector. [Import mismatch bug](https://github.com/NevaMind-AI/memU/issues/329) still open Feb 2026.
> ⁴ Roadmap. Proactive prediction = Phase 4. Hierarchical memory maps to CT crystallization layers = Phase 5.

### The CT Distinction

Every other memory system in this table stores everything and hopes retrieval sorts it out. This stack implements **principled pruning** via Crystallization Theory:

- **W(k,t) = (C × R × V) / A** — mathematical weight function drives ranking AND shedding
- **δ-decay** — recency degrades every 30 minutes. Memories must earn survival through human confirmation.
- **Human-gated crystallization** — the `confirm` endpoint is the ONLY path from `accepted` → `crystallized`. No ML confidence score can crystallize a memory. (STG Claim 1: negative limitation)
- **Witness chains** — every state transition is hash-linked, append-only, tamper-evident. Full provenance from observation to crystallization to shed. (STG Claim 6)
- **Freeze/revert** — COW snapshots let you freeze a memory (exempt from decay) and revert to any prior state. (STG Claim 7)

> *"Pruning is where most memory systems fall apart. Without decay or relevance scoring, you end up with a dense context of outdated state that can mislead the model worse than no memory at all."*

This stack doesn't just store memories. It governs knowledge.

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

## Deploy

### Local (any machine)

```bash
# Requires: Python 3.11+, PostgreSQL with pgvector extension
pip install asyncpg openai starlette uvicorn

# Configure any OpenAI-compatible provider (OpenAI, Azure, Ollama, etc.)
export OPENAI_API_KEY="your-key"
export OPENAI_BASE_URL="https://api.openai.com/v1"  # or your provider
export EMBEDDING_MODEL="text-embedding-3-small"
export CHAT_MODEL="gpt-4.1-mini"

# Database
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

The VM bootstraps via cloud-init: Python, Caddy, PostgreSQL + pgvector, Memibrium. Caddy handles TLS termination.

### Supported LLM Providers

Any OpenAI-compatible API works out of the box:

| Provider | `OPENAI_BASE_URL` | Notes |
|---|---|---|
| OpenAI | `https://api.openai.com/v1` | Default |
| Azure OpenAI / Foundry | `https://your-resource.openai.azure.com/` | Use `AzureOpenAI` client |
| Ollama | `http://localhost:11434/v1` | Local, no API key needed |
| OpenRouter | `https://openrouter.ai/api/v1` | Multi-model access |
| vLLM / TGI | `http://localhost:8000/v1` | Self-hosted inference |

---

## Files

| File | What |
|---|---|
| `server.py` | CT memory server — lifecycle engine, W(k,t), δ-decay, witness chains, 8 MCP endpoints |
| `Caddyfile` | TLS termination + local `:9999` proxy with Foundry auth injection |
| `main.tf` | Root Terraform — VM + network + cognitive modules |
| `modules/vm/cloud-init.yaml` | Full bootstrap: server, Caddy, PostgreSQL, hardening, systemd |
| `modules/cognitive/main.tf` | LLM provider config (Azure Foundry example, swap for your provider) |
| `modules/network/main.tf` | VNet, subnet, NSG (443/80/22) |

---

## Design Decisions

1. **Crystallization Theory as governance.** The CT lifecycle engine sits ABOVE the vector store. The innovation is in the governance — W(k,t), δ-decay, human-gated crystallization — not the storage engine. Swap pgvector for RuVector, the claims still hold.

2. **Human consensus, not ML confidence.** STG Claim 1 negative limitation: `confirm` is the ONLY path to crystallization. The LLM importance score is stored for observability but does NOT drive lifecycle transitions. This is the architectural distinction from every competitor.

3. **Tiering = lifecycle state.** Observation/consideration/accepted → hot tier (fast, recent). Crystallized/shed → cold tier (deep, historical). No separate config or manual routing. The state machine IS the tiering policy.

4. **Entity graph as world state.** "I moved to Berlin" updates a Location entity, doesn't just store a new vector. The `entities` table enables contradiction detection during consolidation.

5. **Fully sovereign.** No cloud memory services. PostgreSQL + pgvector + any OpenAI-compatible LLM provider for embeddings and synthesis. Everything runs on your infrastructure. Future: RuVector + LEANN on Cognitum hardware when available.

6. **Witness chains everywhere.** Every state transition — ingest, decay, shed, crystallize, freeze, revert — produces a hash-linked provenance entry. Tamper-evident. Append-only. This is how you prove a memory's lineage in a regulated environment (healthcare, finance).

---

## Roadmap

| Phase | What | Status |
|---|---|---|
| **1** | LEANN + Foundry + MCP (v1) | ✅ Shipped |
| **2** | CT lifecycle engine + pgvector dual-tier + entity graph | ✅ Shipped |
| **2.5** | Swap hot tier pgvector → [RuVector](https://github.com/ruvnet/ruvector) (Rust HNSW, <1ms, SONA self-learning) | Next |
| **3** | [LEANN](https://github.com/yichuan-w/LEANN) compression on cold tier (97% storage savings) | Planned |
| **4** | Proactive intent prediction (memU-style dual-agent loop) | Planned |
| **5** | Hierarchical memory with CT crystallization layers | Planned |
| **6** | Multimodal ingestion (docs, images, audio) | Planned |
| **7** | [Cognitum](https://cognitum.ai) edge deploy — sovereign, <15W, no cloud dependency | Waiting on hardware |

---

## Patent ↔ Code Map

| Patent Claim | Implementation | Lines |
|---|---|---|
| CT: 5-stage lifecycle | `LifecycleState` enum, `VALID_TRANSITIONS`, state machine | §1 |
| CT: W(k,t) = (C×R×V)/A | `compute_weight()` — drives ranking AND shedding | §1 |
| CT: δ-decay | `ConsolidateAgent.run_cycle()` — R(t+1) = R(t)×(1-δ) | §4 |
| STG Claim 1: negative limitation | `confirm` is ONLY crystallization path, NOT ML confidence | §5 |
| STG Claim 6: witness chains | `make_witness_entry()` — hash-linked, append-only | §1 |
| STG Claim 7: freeze/revert | `ColdStore.freeze()` / `revert()` — COW snapshots | §2 |
| Entity graph | `entities` table + `upsert_entity()` — world state management | §2 |

---

*Adapted from [Google's Always-On Memory Agent](https://research.google/blog/) research.*
*Hot tier: [RuVector](https://github.com/ruvnet/ruvector) by [rUv](https://github.com/ruvnet) · Cold tier: [LEANN](https://github.com/yichuan-w/LEANN) by Berkeley SkyLab.*
*Memibrium — Crystallization Theory by Richard "Ricky" Valentine*

> "The system gets wiser—not merely smarter—because the wisdom is human wisdom, accumulated through deliberate consensus and preserved through sovereign governance."
