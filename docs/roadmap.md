# Roadmap and competitive landscape

> Relocated verbatim from the root `README.md` in the MED-242 docs pass (2026-11-02). The [README](../README.md) is now the short entry point; this file keeps the full text.


---

## Roadmap

| Phase | What | Status |
|---|---|---|
| **1** | LEANN + Foundry + MCP (v1) | ✅ Shipped |
| **2** | CT lifecycle engine + pgvector dual-tier + entity graph | ✅ Shipped |
| **2.5** | Plugin architecture (azure-skills pattern) | ✅ Shipped |
| **2.5** | RuVector hot tier (GNN re-ranking, SONA self-learning) | ✅ Shipped |
| **3** | [LEANN](https://github.com/yichuan-w/LEANN) cold tier compression (97% storage savings) | ✅ Shipped |
| **3.5** | Ingestion engine: bulk file/JSONL ingest, 30-category taxonomy, wiki compiler | ✅ Shipped |
| **3.5** | Docker container, CI/CD, `.env.example` | ✅ Shipped |
| **4** | Proactive intent prediction | Planned |
| **5** | Hierarchical memory with CT crystallization layers | Planned |
| **6** | Full multimodal ingestion (images, audio, video transcripts) | Planned |
| **7** | [Cognitum](https://cognitum.ai) edge deploy — sovereign, <15W | Waiting on hardware |

---

## Competitive Landscape (April 2026)

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
| Bulk document/conversation ingestion | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Knowledge taxonomy + auto-classification | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Wiki compilation from memory | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Proactive intent prediction | ❌ | ❌ | ❌ | ❌ | ✅ | ❌⁴ |
| Hierarchical memory (3-layer) | ❌ | ❌ | ❌ | ❌ | ✅ | ❌⁴ |
| Multimodal ingestion | ❌ | ❌ | ❌ | ❌ | ✅ | ⚠️⁵ |
| Benchmark published (Locomo) | ❌ | ❌ | ❌ | ❌ | ✅ | ❌⁴ |
| **Human-gated crystallization** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Witness chain provenance** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Freeze / revert (COW snapshots)** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| **W(k,t) mathematical scoring** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Plugin distribution (skill + MCP)** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |

**Score** | 4/23 | 4/23 | 5/23 | 5/23 | 10/23 | **19/23** |

> ¹ memU stores everything then auto-organizes — no LLM gate on ingest.
> ² memU supports `llm_profiles` for provider switching, not per-operation model routing.
> ³ memU self-hosted requires Python 3.13+, PostgreSQL + pgvector.
> ⁴ Roadmap. Proactive prediction = Phase 4. Hierarchical memory = Phase 5.
> ⁵ Text-based formats (MD, TXT, JSON, CSV, PDF text extraction). Image/audio ingestion planned.
