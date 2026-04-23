#!/usr/bin/env python3
"""Benchmark Memibrium memory stack — write latency, recall latency, throughput."""

import json
import time
import urllib.request
import urllib.error

BASE = "http://localhost:9999"

def api_call(method, path, payload=None):
    url = f"{BASE}{path}"
    data = json.dumps(payload).encode() if payload else None
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method=method)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())

def retain(content, source="benchmark"):
    return api_call("POST", "/mcp/retain", {"content": content, "source": source})

def recall(query, top_k=5):
    return api_call("POST", "/mcp/recall", {"query": query, "top_k": top_k})

def dashboard():
    return api_call("GET", "/mcp/dashboard")

def benchmark():
    print("=" * 60)
    print("MEMIBRIUM MEMORY STACK BENCHMARK")
    print("=" * 60)
    
    d = dashboard()
    arch = d.get("architecture", {})
    print(f"\nEngine: {arch.get('vector_extension', 'unknown')}")
    print(f"Hot tier: {arch.get('hot_tier', 'unknown')}")
    print(f"Synthesis model: {arch.get('synthesis', 'unknown')}")
    print(f"Provider: {arch.get('provider', 'unknown')}")
    print(f"Total memories: {d.get('total_memories', 0)}")
    print(f"Memory edges: {d.get('memory_edges', 0)}")
    print(f"Unresolved contradictions: {d.get('unresolved_contradictions', 0)}")
    
    # --- Write latency ---
    print("\n" + "-" * 60)
    print("WRITE LATENCY (single retain)")
    print("-" * 60)
    
    test_contents = [
        "Docker containers are lightweight virtualized environments.",
        "PostgreSQL supports full-text search via tsvector and ts_rank_cd.",
        "The quick brown fox jumps over the lazy dog.",
        "Machine learning models require large datasets for training.",
        "Ollama runs large language models locally without cloud dependencies.",
    ]
    
    latencies = []
    for content in test_contents:
        t0 = time.perf_counter()
        result = retain(content)
        t1 = time.perf_counter()
        lat_ms = (t1 - t0) * 1000
        latencies.append(lat_ms)
        mem_id = result.get("id", "?")
        state = result.get("state", "?")
        print(f"  {mem_id[:20]:20} state={state:12} {lat_ms:7.2f} ms")
    
    print(f"\n  Average write latency: {sum(latencies)/len(latencies):.2f} ms")
    print(f"  Min: {min(latencies):.2f} ms  Max: {max(latencies):.2f} ms")
    
    # --- Recall latency ---
    print("\n" + "-" * 60)
    print("RECALL LATENCY (hybrid search: semantic + BM25 + RRF)")
    print("-" * 60)
    
    queries = [
        "Docker containers",
        "PostgreSQL full-text search",
        "quick brown fox",
        "machine learning datasets",
        "Ollama local LLM",
    ]
    
    recall_lats = []
    for query in queries:
        t0 = time.perf_counter()
        result = recall(query, top_k=5)
        t1 = time.perf_counter()
        lat_ms = (t1 - t0) * 1000
        recall_lats.append(lat_ms)
        results = result.get("results", [])
        print(f"  '{query[:30]:30}' {len(results)} results  {lat_ms:7.2f} ms")
    
    print(f"\n  Average recall latency: {sum(recall_lats)/len(recall_lats):.2f} ms")
    print(f"  Min: {min(recall_lats):.2f} ms  Max: {max(recall_lats):.2f} ms")
    
    # --- Throughput test ---
    print("\n" + "-" * 60)
    print("WRITE THROUGHPUT (batch of 20 sequential)")
    print("-" * 60)
    
    batch_contents = [
        f"Benchmark memory number {i} about artificial intelligence and neural networks."
        for i in range(20)
    ]
    
    t0 = time.perf_counter()
    for c in batch_contents:
        retain(c)
    t1 = time.perf_counter()
    
    total_ms = (t1 - t0) * 1000
    per_item_ms = total_ms / len(batch_contents)
    throughput = len(batch_contents) / (total_ms / 1000)
    
    print(f"  Total time: {total_ms:.2f} ms")
    print(f"  Per-item: {per_item_ms:.2f} ms")
    print(f"  Throughput: {throughput:.1f} retains/second")
    
    # --- Summary ---
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Write latency (avg):  {sum(latencies)/len(latencies):7.2f} ms")
    print(f"  Recall latency (avg): {sum(recall_lats)/len(recall_lats):7.2f} ms")
    print(f"  Write throughput:     {throughput:.1f} ops/sec")
    print("=" * 60)

if __name__ == "__main__":
    benchmark()
