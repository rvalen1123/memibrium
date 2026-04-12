#!/usr/bin/env python3
"""
Memibrium Production E2E Test Suite
=====================================
Tests all 8 MCP endpoints against a live Memibrium server.
Runs the full CT lifecycle: retain → recall → reflect → confirm(×3)
→ crystallize → freeze → revert → consolidate → dashboard.

Usage:
  python test_production_e2e.py                                    # default: localhost:9999
  python test_production_e2e.py https://memibrium-prod.eastus2.cloudapp.azure.com  # production

Requires: httpx (pip install httpx)
"""

import asyncio
import httpx
import json
import sys
import time
from datetime import datetime

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:9999"
PASS = 0
FAIL = 0
MEMORY_IDS = []

def test(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name}: {detail}")
    return condition

def pp(data):
    """Pretty-print JSON response (compact)."""
    if isinstance(data, dict):
        return json.dumps(data, indent=None, default=str)[:200]
    return str(data)[:200]

async def run_tests():
    global PASS, FAIL, MEMORY_IDS
    timeout = httpx.Timeout(30.0, connect=10.0)
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=timeout) as c:

        print(f"\nMemibrium Production E2E Test")
        print(f"Target: {BASE_URL}")
        print(f"Time:   {datetime.now().isoformat()}")
        print(f"{'='*60}")

        # ── 1. Health Check ──
        print("\n--- 1. Health Check ---")
        r = await c.get("/health")
        test("Health status 200", r.status_code == 200)
        d = r.json()
        test("Engine is memibrium", d.get("engine") == "memibrium")

        # ── 2. MCP Tool Manifest ──
        print("\n--- 2. MCP Tool Manifest ---")
        r = await c.get("/mcp/tools")
        test("Tools status 200", r.status_code == 200)
        tools = r.json().get("tools", [])
        tool_names = [t["name"] for t in tools]
        test("8+ tools listed", len(tools) >= 8, f"got {len(tools)}")
        for name in ["retain", "recall", "reflect", "confirm",
                      "freeze", "revert", "consolidate", "dashboard"]:
            test(f"Tool '{name}' present", name in tool_names)

        # ── 3. Dashboard (baseline) ──
        print("\n--- 3. Dashboard (baseline) ---")
        r = await c.get("/mcp/dashboard")
        test("Dashboard status 200", r.status_code == 200)
        dash = r.json()
        test("Has lifecycle_counts", "lifecycle_counts" in dash)
        test("Has architecture", "architecture" in dash)
        arch = dash.get("architecture", {})
        test("Reports vector extension", "vector_extension" in arch)
        test("Reports hot tier", "hot_tier" in arch)
        test("Reports cold tier", "cold_tier" in arch)
        test("Reports LEANN status", "leann_available" in arch)
        test("Reports sovereignty", "sovereignty" in arch)
        baseline_total = dash.get("total_memories", 0)
        print(f"    Baseline: {baseline_total} memories, engine={arch.get('vector_extension')}")
        print(f"    Hot: {arch.get('hot_tier')}, Cold: {arch.get('cold_tier')}")

        # ── 4. Retain (ingest 3 memories) ──
        print("\n--- 4. Retain (ingest 3 memories) ---")
        test_memories = [
            {"content": "E2E test: API rate limit is 5000 req/min on Enterprise plan",
             "source": "e2e_test", "domain": "test-api"},
            {"content": "E2E test: Auth uses SAML SSO with Azure AD for enterprise",
             "source": "e2e_test", "domain": "test-auth"},
            {"content": "E2E test: Deployment pipeline runs through GitHub Actions to AKS",
             "source": "e2e_test", "domain": "test-deploy"},
        ]
        for i, mem in enumerate(test_memories):
            r = await c.post("/mcp/retain", json=mem)
            test(f"Retain #{i+1} status 200", r.status_code == 200,
                 f"got {r.status_code}: {r.text[:100]}")
            if r.status_code == 200:
                d = r.json()
                mid = d.get("id", "")
                MEMORY_IDS.append(mid)
                test(f"Retain #{i+1} has ID", bool(mid))
                test(f"Retain #{i+1} state", d.get("state") in ["observation", "accepted"],
                     f"got {d.get('state')}")
                test(f"Retain #{i+1} importance scored", d.get("importance", 0) > 0)
                test(f"Retain #{i+1} entities extracted", isinstance(d.get("entities"), list))
                test(f"Retain #{i+1} witness chain", d.get("witness_count", 0) >= 1)
                print(f"    -> {mid} state={d.get('state')} imp={d.get('importance')}")

        # ── 5. Recall (vector search) ──
        print("\n--- 5. Recall (vector search) ---")
        r = await c.post("/mcp/recall", json={
            "query": "API rate limit enterprise", "top_k": 5})
        test("Recall status 200", r.status_code == 200)
        if r.status_code == 200:
            d = r.json()
            results = d.get("results", [])
            test("Recall returns results", len(results) > 0, f"got {len(results)}")
            if results:
                top = results[0]
                test("Top result has cosine_score", "cosine_score" in top)
                test("Top result has w_kt", "w_kt" in top)
                test("Top result has combined_score", "combined_score" in top)
                test("Top result has witness_chain", "witness_chain" in top)
                test("Cosine > 0.3", top.get("cosine_score", 0) > 0.3,
                     f"got {top.get('cosine_score')}")
                print(f"    Top: {top.get('id')} score={top.get('combined_score')} "
                      f"state={top.get('state')}")

        # Domain-filtered recall
        r2 = await c.post("/mcp/recall", json={
            "query": "authentication SAML", "top_k": 3, "domain": "test-auth"})
        test("Domain recall status 200", r2.status_code == 200)

        # ── 6. Reflect (synthesis) ──
        print("\n--- 6. Reflect (synthesis) ---")
        r = await c.post("/mcp/reflect", json={
            "topic": "enterprise infrastructure", "top_k": 5})
        test("Reflect status 200", r.status_code == 200)
        if r.status_code == 200:
            d = r.json()
            test("Synthesis returned", bool(d.get("synthesis")))
            test("Memory count", d.get("memory_count", 0) > 0)
            print(f"    Synthesized {d.get('memory_count')} memories, "
                  f"tier={d.get('tier')}")

        # ── 7. Confirm (3x → crystallization) ──
        print("\n--- 7. Confirm (3x -> crystallization) ---")
        if MEMORY_IDS:
            target_id = MEMORY_IDS[0]
            for i in range(3):
                r = await c.post("/mcp/confirm", json={
                    "memory_id": target_id, "weight": 1.0})
                test(f"Confirm #{i+1} status 200", r.status_code == 200)
                if r.status_code == 200:
                    d = r.json()
                    print(f"    Confirm #{i+1}: count={d.get('confirmation_count')} "
                          f"state={d.get('state')} W={d.get('w_kt')}")

            # Final state check
            if r.status_code == 200:
                d = r.json()
                test("Crystallized after 3 confirms",
                     d.get("state") == "crystallized" or d.get("crystallized") is True,
                     f"state={d.get('state')}")
                test("W(k,t) increased", d.get("w_kt", 0) > 0.5,
                     f"got {d.get('w_kt')}")
        else:
            test("Confirm (skipped - no memory IDs)", False, "retain failed")

        # ── 8. Freeze + Snapshot ──
        print("\n--- 8. Freeze + Snapshot ---")
        if MEMORY_IDS:
            target_id = MEMORY_IDS[0]
            r = await c.post("/mcp/freeze", json={
                "memory_id": target_id, "reason": "e2e_test pre-migration"})
            test("Freeze status 200", r.status_code == 200)
            if r.status_code == 200:
                d = r.json()
                snap_id = d.get("snapshot_id", "")
                test("Snapshot created", bool(snap_id), f"got {d}")
                test("Frozen flag", d.get("frozen") is True)
                print(f"    Snapshot: {snap_id}")

                # ── 9. Revert from Snapshot ──
                print("\n--- 9. Revert from Snapshot ---")
                r = await c.post("/mcp/revert", json={
                    "memory_id": target_id, "snapshot_id": snap_id})
                test("Revert status 200", r.status_code == 200)
                if r.status_code == 200:
                    d = r.json()
                    test("Reverted to snapshot", d.get("reverted_to") == snap_id)
                    print(f"    Reverted to: {d.get('reverted_to')}")

        # ── 10. Consolidate (manual trigger) ──
        print("\n--- 10. Consolidate ---")
        r = await c.post("/mcp/consolidate", json={})
        test("Consolidate status 200", r.status_code == 200)
        if r.status_code == 200:
            d = r.json()
            test("Reports total", "total" in d)
            test("Reports decayed", "decayed" in d)
            print(f"    Stats: {pp(d)}")

        # ── 11. Dashboard (final state) ──
        print("\n--- 11. Dashboard (final state) ---")
        r = await c.get("/mcp/dashboard")
        test("Dashboard status 200", r.status_code == 200)
        if r.status_code == 200:
            d = r.json()
            final_total = d.get("total_memories", 0)
            test("Memories increased", final_total > baseline_total,
                 f"baseline={baseline_total} final={final_total}")
            counts = d.get("lifecycle_counts", {})
            print(f"    Final: {final_total} memories, states={counts}")

        # ── 12. Error handling ──
        print("\n--- 12. Error Handling ---")
        r = await c.post("/mcp/retain", json={})
        test("Empty retain returns 400", r.status_code == 400)

        r = await c.post("/mcp/confirm", json={"memory_id": "nonexistent_xyz"})
        test("Confirm nonexistent returns 404", r.status_code == 404)

        r = await c.post("/mcp/recall", json={})
        test("Empty recall returns 400", r.status_code == 400)

        r = await c.post("/mcp/freeze", json={})
        test("Empty freeze returns 400", r.status_code == 400)

    # ── Summary ──
    print(f"\n{'='*60}")
    print(f"  TARGET:  {BASE_URL}")
    print(f"  RESULTS: {PASS} passed, {FAIL} failed")
    print(f"  IDS:     {MEMORY_IDS}")
    print(f"  TIME:    {datetime.now().isoformat()}")
    print(f"{'='*60}")

    return FAIL == 0

if __name__ == "__main__":
    success = asyncio.run(run_tests())
    sys.exit(0 if success else 1)
