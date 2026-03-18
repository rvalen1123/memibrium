#!/usr/bin/env python3
"""
Memibrium E2E Test — LEANN Cold Tier (Phase 3)
================================================
Tests LEANN integration for cold tier compression.

Usage:
  docker run -d --name memibrium-ruvector-db \
    -e POSTGRES_DB=memory -e POSTGRES_USER=memory -e POSTGRES_PASSWORD=memory \
    -p 5432:5432 ruvnet/ruvector-postgres:latest

  pip install leann
  python test_leann_e2e.py
"""

import asyncio
import json
import os
import sys

os.environ["USE_RUVECTOR"] = "true"
os.environ["USE_LEANN"] = "true"
os.environ["LEANN_INDEX_DIR"] = "./data/leann_test"
os.environ["DB_HOST"] = os.environ.get("DB_HOST", "localhost")
os.environ["DB_NAME"] = os.environ.get("DB_NAME", "memory")
os.environ["DB_USER"] = os.environ.get("DB_USER", "memory")
os.environ["DB_PASSWORD"] = os.environ.get("DB_PASSWORD", "memory")

sys.path.insert(0, os.path.dirname(__file__))
from server import LEANNColdTier, ColdStore

PASS = 0
FAIL = 0

def test(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name}: {detail}")

async def run_tests():
    global PASS, FAIL

    # --- Test 1: LEANN tier initializes ---
    print("\n=== Test 1: LEANN Initialization ===")
    tier = LEANNColdTier()
    await tier.initialize()
    test("LEANN available", tier.available,
         "leann not importable")
    test("Index path created",
         os.path.exists(tier.index_path))

    if not tier.available:
        print("FATAL: LEANN not available, cannot continue")
        print(f"\n  RESULTS: {PASS} passed, {FAIL} failed")
        return False

    # --- Test 2: Stage memories ---
    print("\n=== Test 2: Stage Memories for LEANN ===")
    await tier.index_memory("cold_1",
        "The API rate limit was changed to 2000 req/min in Q3 2025")
    await tier.index_memory("cold_2",
        "Deployment architecture uses Azure Container Apps with Caddy reverse proxy")
    await tier.index_memory("cold_3",
        "Authentication uses OAuth2 PKCE flow with Azure AD B2C")

    staging = os.path.join(tier.index_path, "staging.jsonl")
    test("Staging file created", os.path.exists(staging))
    test("Dirty flag set", tier._dirty is True)

    if os.path.exists(staging):
        with open(staging, "r") as f:
            lines = [l for l in f if l.strip()]
        test("3 entries staged", len(lines) == 3,
             f"got {len(lines)}")

    # --- Test 3: Build LEANN index ---
    print("\n=== Test 3: Build LEANN Index ===")
    await tier.rebuild_index()
    test("Dirty flag cleared", tier._dirty is False)
    test("Searcher initialized", tier.searcher is not None)

    index_file = os.path.join(tier.index_path, "cold.leann")
    index_meta = index_file + ".meta.json"
    test("Index files exist",
         os.path.exists(index_meta) or os.path.exists(index_file),
         f"looking at {index_file}")
    test("Staging cleared", not os.path.exists(staging))

    # --- Test 4: Search LEANN cold tier ---
    print("\n=== Test 4: LEANN Cold Search ===")
    results = await tier.search("rate limit", top_k=3)
    test("Search returns results", len(results) > 0,
         f"got {len(results)}")
    if results:
        test("Top result has text",
             "text" in results[0] and len(results[0]["text"]) > 0)
        test("Top result has score",
             "score" in results[0])
        test("Source is leann_cold",
             results[0].get("source") == "leann_cold")
        print(f"    Top result: score={results[0].get('score', 0):.3f}"
              f" text={results[0].get('text', '')[:80]}...")

    # --- Test 5: Search different queries ---
    print("\n=== Test 5: Multi-Query Search ===")
    r2 = await tier.search("authentication OAuth", top_k=2)
    test("Auth query returns results", len(r2) > 0)
    r3 = await tier.search("deployment container", top_k=2)
    test("Deploy query returns results", len(r3) > 0)

    # --- Test 6: No-result query ---
    print("\n=== Test 6: Edge Cases ===")
    r4 = await tier.search("quantum physics black hole", top_k=2)
    test("Irrelevant query returns something",
         isinstance(r4, list))  # LEANN may still return low-score results

    # --- Cleanup ---
    print("\n=== Cleanup ===")
    import shutil
    if os.path.exists(tier.index_path):
        shutil.rmtree(tier.index_path)
        print("  Cleaned up test index")

    print(f"\n{'='*50}")
    print(f"  RESULTS: {PASS} passed, {FAIL} failed")
    print(f"  LEANN: available={tier.available}")
    print(f"{'='*50}")

    return FAIL == 0

if __name__ == "__main__":
    success = asyncio.run(run_tests())
    sys.exit(0 if success else 1)
