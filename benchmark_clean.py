#!/usr/bin/env python3
"""Clean benchmark — single-threaded, no parallel overload. Tests what matters."""

import json
import time
import urllib.request

BASE = "http://localhost:9999"

def api(path, payload=None, timeout=30):
    data = json.dumps(payload).encode() if payload else None
    req = urllib.request.Request(f"{BASE}{path}", data=data, headers={"Content-Type": "application/json"}, method="POST" if payload else "GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {"error": str(e)}

def benchmark():
    print("=" * 60)
    print("MEMIBRIUM CONTROLLED BENCHMARK")
    print("=" * 60)
    
    # Baseline stats
    d = api("/mcp/dashboard")
    arch = d.get("architecture", {})
    print(f"\nEngine: {arch.get('vector_extension', '?')}")
    print(f"Synthesis: {arch.get('synthesis', '?')}")
    print(f"Provider: {arch.get('provider', '?')}")
    print(f"Total memories: {d.get('total_memories', 0)}")
    print(f"Memory edges: {d.get('memory_edges', 0)}")
    
    # --- Embedding latency (isolated) ---
    print("\n" + "-" * 60)
    print("EMBEDDING LATENCY (isolated)")
    print("-" * 60)
    
    texts = [
        "Short text.",
        "The quick brown fox jumps over the lazy dog.",
        "PostgreSQL is a powerful open source relational database system with over 35 years of active development.",
    ]
    
    for text in texts:
        t0 = time.perf_counter()
        r = api("/mcp/test_embeddings", {"text": text})
        t1 = time.perf_counter()
        lat_ms = (t1 - t0) * 1000
        ollama = r.get("ollama", {})
        print(f"  {len(text):3} chars  {ollama.get('latency_ms', '?'):>8} ms  dims={ollama.get('dimensions', '?')}")
    
    # --- Write latency (isolated, no background tasks) ---
    print("\n" + "-" * 60)
    print("WRITE LATENCY (single, isolated)")
    print("-" * 60)
    
    t0 = time.perf_counter()
    r = api("/mcp/retain", {"content": "Benchmark memory about quantum computing and superposition.", "source": "bench"})
    t1 = time.perf_counter()
    lat_ms = (t1 - t0) * 1000
    print(f"  retain: {lat_ms:.2f} ms  id={r.get('id', '?')[:20]} state={r.get('state', '?')}")
    
    # --- Recall latency (isolated) ---
    print("\n" + "-" * 60)
    print("RECALL LATENCY (hybrid search)")
    print("-" * 60)
    
    queries = [
        "quantum computing",
        "artificial intelligence",
        "Docker containers",
    ]
    
    for query in queries:
        t0 = time.perf_counter()
        r = api("/mcp/recall", {"query": query, "top_k": 5})
        t1 = time.perf_counter()
        lat_ms = (t1 - t0) * 1000
        results = r.get("results", [])
        print(f"  '{query[:25]:25}' {len(results)} results  {lat_ms:7.2f} ms")
    
    # --- Recall with top_k=20 (cross-encoder test) ---
    print("\n" + "-" * 60)
    print("RECALL LATENCY top_k=20 (cross-encoder candidate set)")
    print("-" * 60)
    
    t0 = time.perf_counter()
    r = api("/mcp/recall", {"query": "artificial intelligence", "top_k": 20})
    t1 = time.perf_counter()
    lat_ms = (t1 - t0) * 1000
    results = r.get("results", [])
    has_ce = any("ce_score" in m for m in results)
    print(f"  top_k=20  {len(results)} results  {lat_ms:7.2f} ms  cross-encoder active={has_ce}")
    if results and has_ce:
        for m in results[:3]:
            print(f"    {m.get('id', '?')[:20]}  ce_score={m.get('ce_score', 'N/A'):>6}  rrf={m.get('rrf_score', 'N/A'):>6}")
    
    # --- Sequential throughput (10 items) ---
    print("\n" + "-" * 60)
    print("SEQUENTIAL THROUGHPUT (10 retains)")
    print("-" * 60)
    
    t0 = time.perf_counter()
    for i in range(10):
        api("/mcp/retain", {"content": f"Throughput test memory {i} about distributed systems.", "source": "bench"})
    t1 = time.perf_counter()
    total_ms = (t1 - t0) * 1000
    print(f"  Total: {total_ms:.2f} ms  Per-item: {total_ms/10:.2f} ms  Throughput: {10/(total_ms/1000):.1f} ops/sec")
    
    print("\n" + "=" * 60)
    print("DONE")
    print("=" * 60)

if __name__ == "__main__":
    benchmark()
