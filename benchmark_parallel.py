#!/usr/bin/env python3
"""Async parallel benchmark + cross-encoder re-ranking latency test."""

import asyncio
import json
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

BASE = "http://localhost:9999"

def api_call(method, path, payload=None, timeout=30):
    url = f"{BASE}{path}"
    data = json.dumps(payload).encode() if payload else None
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {"error": str(e)}

def retain(content, source="benchmark"):
    return api_call("POST", "/mcp/retain", {"content": content, "source": source})

def recall(query, top_k=5):
    return api_call("POST", "/mcp/recall", {"query": query, "top_k": top_k})

def dashboard():
    return api_call("GET", "/mcp/dashboard")

def test_embeddings():
    return api_call("POST", "/mcp/test_embeddings", {"text": "The quick brown fox jumps over the lazy dog"})

def parallel_retain_batch(contents, max_workers=8):
    """Run retains in parallel using thread pool."""
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        t0 = time.perf_counter()
        futures = [ex.submit(retain, c) for c in contents]
        results = [f.result() for f in futures]
        t1 = time.perf_counter()
    return results, (t1 - t0) * 1000

def benchmark():
    print("=" * 60)
    print("MEMIBRIUM PARALLEL + RE-RANKING BENCHMARK")
    print("=" * 60)
    
    d = dashboard()
    arch = d.get("architecture", {})
    print(f"\nEngine: {arch.get('vector_extension', 'unknown')}")
    print(f"Synthesis model: {arch.get('synthesis', 'unknown')}")
    print(f"Provider: {arch.get('provider', 'unknown')}")
    print(f"Total memories: {d.get('total_memories', 0)}")
    
    # --- Parallel write throughput ---
    print("\n" + "-" * 60)
    print("PARALLEL WRITE THROUGHPUT")
    print("-" * 60)
    
    batch_sizes = [10, 20, 40]
    workers_list = [4, 8, 16]
    
    for batch_size in batch_sizes:
        contents = [
            f"Parallel benchmark memory {i} about distributed systems and concurrency patterns."
            for i in range(batch_size)
        ]
        for workers in workers_list:
            if workers > batch_size:
                continue
            results, total_ms = parallel_retain_batch(contents, max_workers=workers)
            throughput = batch_size / (total_ms / 1000)
            per_item_ms = total_ms / batch_size
            print(f"  batch={batch_size:3} workers={workers:2}  {total_ms:8.1f}ms  {per_item_ms:6.1f}ms/item  {throughput:5.1f} ops/sec")
    
    # --- Embedding endpoint comparison ---
    print("\n" + "-" * 60)
    print("EMBEDDING ENDPOINT LATENCY")
    print("-" * 60)
    
    t0 = time.perf_counter()
    emb_result = test_embeddings()
    t1 = time.perf_counter()
    total_ms = (t1 - t0) * 1000
    
    ollama = emb_result.get("ollama", {})
    azure = emb_result.get("azure", {})
    
    print(f"  Ollama:  success={ollama.get('success', False)}  latency={ollama.get('latency_ms', 'N/A')}ms  dims={ollama.get('dimensions', 'N/A')}")
    print(f"  Azure:   success={azure.get('success', False)}  latency={azure.get('latency_ms', 'N/A')}ms  dims={azure.get('dimensions', 'N/A')}")
    print(f"  Total test time: {total_ms:.2f} ms")
    print(f"  Recommendation: {emb_result.get('recommendation', 'N/A')}")
    
    # --- Cross-encoder re-ranking latency ---
    print("\n" + "-" * 60)
    print("CROSS-ENCODER RE-RANKING LATENCY")
    print("-" * 60)
    
    # The hybrid retriever does cross-encoder re-ranking internally when _CE is available.
    # We can't directly test it via API, but we can check if the module loaded it.
    # Let's do recall with top_k=20 (triggers re-rank on top 2*k=40 candidates)
    
    queries = [
        "artificial intelligence",
        "neural networks",
        "distributed systems",
    ]
    
    for query in queries:
        t0 = time.perf_counter()
        result = recall(query, top_k=20)
        t1 = time.perf_counter()
        lat_ms = (t1 - t0) * 1000
        results = result.get("results", [])
        has_ce = any("ce_score" in r for r in results)
        print(f"  '{query[:25]:25}' top_k=20  {len(results)} results  {lat_ms:7.2f} ms  cross-encoder={has_ce}")
    
    # --- Summary ---
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("  Best parallel throughput seen above")
    print("  Embedding latency: see Ollama vs Azure comparison")
    print("  Cross-encoder: loaded if ce_score present in recall results")
    print("=" * 60)

if __name__ == "__main__":
    benchmark()
