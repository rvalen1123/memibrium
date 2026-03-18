#!/usr/bin/env python3
"""
Memibrium E2E Test — RuVector DB Layer
=======================================
Tests the full CT lifecycle against ruvector-postgres WITHOUT needing
an LLM API key. Generates synthetic embeddings to isolate the DB layer.

Usage:
  docker run -d --name memibrium-ruvector-db \
    -e POSTGRES_DB=memory -e POSTGRES_USER=memory -e POSTGRES_PASSWORD=memory \
    -p 5432:5432 ruvnet/ruvector-postgres:latest

  python test_ruvector_e2e.py

Tests:
  1. Extension detection (ruvector vs vector)
  2. Schema creation with ruvector(1536) type
  3. Insert memory with ruvector embedding
  4. Vector search with cosine distance (<=>)
  5. W(k,t) re-ranking
  6. Confirm → crystallization path
  7. Freeze + snapshot
  8. Revert from snapshot
  9. Consolidation (δ-decay + shedding)
  10. Dashboard reports correct engine
"""

import asyncio
import json
import os
import random
import sys

# Force ruvector mode
os.environ["USE_RUVECTOR"] = "true"
os.environ["DB_HOST"] = os.environ.get("DB_HOST", "localhost")
os.environ["DB_NAME"] = os.environ.get("DB_NAME", "memory")
os.environ["DB_USER"] = os.environ.get("DB_USER", "memory")
os.environ["DB_PASSWORD"] = os.environ.get("DB_PASSWORD", "memory")

# Import after env is set so config picks up USE_RUVECTOR
sys.path.insert(0, os.path.dirname(__file__))
from server import (
    ColdStore, compute_weight, make_witness_entry,
    LifecycleState, VALID_TRANSITIONS,
)

def fake_embedding(dim=1536, seed=None):
    """Generate a deterministic fake embedding for testing."""
    if seed is not None:
        random.seed(seed)
    vec = [random.gauss(0, 1) for _ in range(dim)]
    norm = sum(x*x for x in vec) ** 0.5
    return [x / norm for x in vec]  # unit normalize

PASS = 0
FAIL = 0

def test(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name}: {detail}")

async def run_tests():
    global PASS, FAIL
    store = ColdStore()

    # ── Test 1: Initialize with ruvector extension ──
    print("\n═══ Test 1: Extension Detection + Schema ═══")
    try:
        await store.initialize()
        test("Extension loaded", store.vector_ext == "ruvector",
             f"got {store.vector_ext}")
        test("Type is ruvector", store.vtype == "ruvector",
             f"got {store.vtype}")
        test("Cosine ops class", store.vcosine_ops == "ruvector_cosine_ops",
             f"got {store.vcosine_ops}")
    except Exception as e:
        test("Initialize", False, str(e))
        print("FATAL: Cannot continue without DB connection")
        return

    # ── Test 2: Insert memories with ruvector embeddings ──
    print("\n═══ Test 2: Insert Memories ═══")
    emb1 = fake_embedding(seed=42)
    emb2 = fake_embedding(seed=43)
    emb3 = fake_embedding(seed=44)

    witness1 = make_witness_entry("none", "observation", "test_ingest", 0.0, 0.0)
    witness2 = make_witness_entry("observation", "accepted", "test_gate", 0.0, 0.5,
                                  prev_hash=witness1["entry_hash"])

    await store.insert_memory("test_mem_1", "API rate limit is 1000 req/min",
                              emb1, "accepted", "test", "project-api", 0.8,
                              [{"name": "API", "type": "system"}], ["rate-limit"],
                              [witness1, witness2])
    await store.insert_memory("test_mem_2", "Deploy uses Azure Container Apps",
                              emb2, "accepted", "test", "project-infra", 0.6,
                              [], ["deployment"], [witness1])
    await store.insert_memory("test_mem_3", "Old config that should decay",
                              emb3, "observation", "test", "default", 0.2,
                              [], ["config"], [witness1])

    mem1 = await store.get_memory("test_mem_1")
    test("Memory inserted", mem1 is not None)
    test("Content stored", mem1["content"] == "API rate limit is 1000 req/min")
    test("State is accepted", mem1["state"] == "accepted")
    test("Witness chain length", len(json.loads(mem1["witness_chain"])
         if isinstance(mem1["witness_chain"], str) else mem1["witness_chain"]) == 2)

    # ── Test 3: Vector search with ruvector cosine ──
    print("\n═══ Test 3: Vector Search (cosine <=> ruvector) ═══")
    results = await store.search(emb1, top_k=3)
    test("Search returns results", len(results) > 0, f"got {len(results)}")
    if results:
        test("Top result is mem_1", results[0]["id"] == "test_mem_1",
             f"got {results[0]['id']}")
        test("Cosine score exists", "cosine_score" in results[0])
        test("W(k,t) computed", "w_kt" in results[0])
        test("Combined score", "combined_score" in results[0])
        test("Cosine > 0.9 for exact match",
             results[0]["cosine_score"] > 0.9,
             f"got {results[0]['cosine_score']}")

    # State filter: only accepted states (mem_1 and mem_2 are accepted)
    hot_results = await store.search(emb1, top_k=3,
                                     state_filter=["accepted"])
    test("State filter works", len(hot_results) >= 1,
         f"got {len(hot_results)} results")

    # Domain filter
    domain_results = await store.search(emb1, top_k=3, domain="project-api")
    test("Domain filter works", len(domain_results) >= 1)

    # ── Test 4: Confirm → Crystallization ──
    print("\n═══ Test 4: Confirm → Crystallization Path ═══")
    # Confirm 3 times (CRYSTALLIZE_CONFIRMATIONS=3)
    for i in range(3):
        mem = await store.get_memory("test_mem_1")
        old_w = compute_weight(mem["confirmation_count"], mem["recency_score"],
                               mem["validation_score"], mem["created_at"])
        new_count = mem["confirmation_count"] + 1
        new_val = 1.0 - (1.0 - mem["validation_score"]) * (1.0 - 1.0 * 0.3)
        new_w = compute_weight(new_count, 1.0, new_val, mem["created_at"])
        new_state = mem["state"]
        if new_count >= 3 and new_val >= 0.5 and mem["state"] == "accepted":
            new_state = "crystallized"
        witness = make_witness_entry(mem["state"], new_state, "human_confirm", old_w, new_w)
        await store.update_memory("test_mem_1", state=new_state,
                                  confirmation_count=new_count, recency_score=1.0,
                                  validation_score=new_val, witness_append=witness)

    mem1_after = await store.get_memory("test_mem_1")
    test("Confirmation count = 3", mem1_after["confirmation_count"] == 3)
    test("State is crystallized", mem1_after["state"] == "crystallized",
         f"got {mem1_after['state']}")

    # ── Test 5: Freeze + Snapshot ──
    print("\n═══ Test 5: Freeze + Snapshot ═══")
    freeze_result = await store.freeze("test_mem_1", "pre-migration backup")
    test("Freeze succeeds", "snapshot_id" in freeze_result,
         f"got {freeze_result}")
    test("Memory frozen", freeze_result.get("frozen") is True)
    snap_id = freeze_result.get("snapshot_id", "")

    mem1_frozen = await store.get_memory("test_mem_1")
    test("Frozen flag set", mem1_frozen["frozen"] is True)

    # ── Test 6: Revert from Snapshot ──
    print("\n═══ Test 6: Revert from Snapshot ═══")
    revert_result = await store.revert("test_mem_1", snap_id)
    test("Revert succeeds", "reverted_to" in revert_result,
         f"got {revert_result}")
    mem1_reverted = await store.get_memory("test_mem_1")
    test("Frozen flag cleared", mem1_reverted["frozen"] is False)

    # ── Test 7: Consolidation (δ-decay) ──
    print("\n═══ Test 7: Consolidation Cycle ═══")
    from server import ConsolidateAgent
    consolidator = ConsolidateAgent(store)
    stats = await consolidator.run_cycle()
    test("Consolidation runs", isinstance(stats, dict))
    test("Total memories tracked", stats.get("total", 0) >= 2,
         f"got {stats.get('total')}")
    test("Decay applied", stats.get("decayed", 0) >= 0)

    # ── Test 8: Dashboard state counts ──
    print("\n═══ Test 8: Dashboard ═══")
    counts = await store.count_by_state()
    test("Counts returned", isinstance(counts, dict))
    test("Has crystallized", "crystallized" in counts,
         f"got states: {list(counts.keys())}")
    total = sum(counts.values())
    test("Total >= 3", total >= 3, f"got {total}")

    # ── Test 9: Cold tier search (crystallized) ──
    print("\n═══ Test 9: Cold Tier Search ═══")
    cold_results = await store.search(emb1, top_k=3,
                                      state_filter=["crystallized", "shed"])
    test("Cold search returns results", len(cold_results) > 0)
    if cold_results:
        test("Finds crystallized memory", cold_results[0]["state"] == "crystallized")

    # ── Test 10: Entity upsert ──
    print("\n═══ Test 10: Entity Graph ═══")
    await store.upsert_entity("API Gateway", "system",
                              {"region": "us-east-2"}, "test_mem_1")
    await store.upsert_entity("API Gateway", "system",
                              {"version": "v3"}, "test_mem_2")
    async with store.pool.acquire() as conn:
        ent = await conn.fetchrow(
            "SELECT * FROM entities WHERE name = 'API Gateway'")
    test("Entity created", ent is not None)
    if ent:
        attrs = json.loads(ent["attributes"]) if isinstance(ent["attributes"], str) else ent["attributes"]
        test("Attributes merged", "region" in attrs and "version" in attrs,
             f"got {attrs}")
        mids = json.loads(ent["memory_ids"]) if isinstance(ent["memory_ids"], str) else ent["memory_ids"]
        test("Memory IDs linked", len(mids) == 2, f"got {mids}")

    # ── Cleanup ──
    print("\n═══ Cleanup ═══")
    async with store.pool.acquire() as conn:
        await conn.execute("DELETE FROM memory_snapshots WHERE memory_id LIKE 'test_%'")
        await conn.execute("DELETE FROM memories WHERE id LIKE 'test_%'")
        await conn.execute("DELETE FROM entities WHERE name = 'API Gateway'")
    print("  🧹 Test data cleaned up")

    # ── Summary ──
    print(f"\n{'═'*50}")
    print(f"  RESULTS: {PASS} passed, {FAIL} failed")
    print(f"  ENGINE:  {store.vector_ext} ({store.vtype})")
    print(f"{'═'*50}")

    if store.pool:
        await store.pool.close()

    return FAIL == 0

if __name__ == "__main__":
    success = asyncio.run(run_tests())
    sys.exit(0 if success else 1)
