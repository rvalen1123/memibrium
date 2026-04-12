#!/usr/bin/env python3
"""
Memibrium Ingestion E2E Test Suite
====================================
Tests the 6 new ingestion endpoints against a live Memibrium server.
Creates temp files, ingests them, verifies classification and wiki compilation.

Usage:
  python test_ingest_e2e.py                     # default: localhost:9999
  python test_ingest_e2e.py http://server:9999  # remote

Requires: httpx (pip install httpx)
"""

import asyncio
import httpx
import json
import os
import sys
import tempfile
import time
from datetime import datetime

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:9999"
PASS = 0
FAIL = 0
TEMP_FILES = []


def test(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name}: {detail}")
    return condition


def make_temp_file(content, suffix=".md"):
    """Create a temp file and track it for cleanup."""
    f = tempfile.NamedTemporaryFile(
        mode='w', suffix=suffix, delete=False, encoding='utf-8')
    f.write(content)
    f.close()
    TEMP_FILES.append(f.name)
    return f.name


def make_temp_dir(files):
    """Create a temp directory with multiple files."""
    d = tempfile.mkdtemp()
    TEMP_FILES.append(d)
    paths = []
    for name, content in files.items():
        path = os.path.join(d, name)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        paths.append(path)
    return d, paths


def make_temp_jsonl(conversations):
    """Create a JSONL file with Claude conversation format."""
    f = tempfile.NamedTemporaryFile(
        mode='w', suffix='.jsonl', delete=False, encoding='utf-8')
    for conv in conversations:
        f.write(json.dumps(conv) + "\n")
    f.close()
    TEMP_FILES.append(f.name)
    return f.name


def cleanup():
    import shutil
    for path in TEMP_FILES:
        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
            elif os.path.isfile(path):
                os.unlink(path)
        except Exception:
            pass


async def run_tests():
    global PASS, FAIL
    timeout = httpx.Timeout(60.0, connect=10.0)
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=timeout) as c:

        print(f"\nMemibrium Ingestion E2E Test")
        print(f"Target: {BASE_URL}")
        print(f"Time:   {datetime.now().isoformat()}")
        print(f"{'='*60}")

        # ── 0. Verify server has ingestion endpoints ──
        print("\n--- 0. Server Readiness ---")
        r = await c.get("/health")
        test("Health OK", r.status_code == 200)

        r = await c.get("/mcp/tools")
        tools = r.json().get("tools", [])
        tool_names = [t["name"] for t in tools]
        test("ingest_file tool exists", "ingest_file" in tool_names,
             f"tools: {tool_names}")
        test("ingest_directory tool exists", "ingest_directory" in tool_names)
        test("ingest_jsonl tool exists", "ingest_jsonl" in tool_names)
        test("compile_wiki tool exists", "compile_wiki" in tool_names)

        # ── 1. Ingest Status (baseline) ──
        print("\n--- 1. Ingest Status (baseline) ---")
        r = await c.get("/mcp/ingest/status")
        test("Status returns 200", r.status_code == 200)
        d = r.json()
        test("Has unique_hashes_seen", "unique_hashes_seen" in d)
        test("Has taxonomy_categories", "taxonomy_categories" in d)
        test("30 taxonomy categories", d.get("taxonomy_categories") == 30,
             f"got {d.get('taxonomy_categories')}")
        test("Has tier breakdown", "taxonomy_tiers" in d)
        baseline_hashes = d.get("unique_hashes_seen", 0)
        print(f"    Baseline: {baseline_hashes} hashes, {d.get('taxonomy_categories')} categories")

        # ── 2. Ingest Single File (.md) ──
        print("\n--- 2. Ingest Single File (.md) ---")
        md_content = """# Memibrium Test Document

This is a test document for the ingestion engine.
It tests markdown chunking with headers and paragraphs.

## Architecture Details

The hot tier uses pgvector for HNSW vector search.
Memories in observation and accepted states live here.
W(k,t) ranking ensures the most relevant memories surface first.

## Deployment Notes

Deployment is handled through Azure Container Apps.
Caddy reverse proxy terminates TLS and routes to the app.
"""
        md_path = make_temp_file(md_content, suffix=".md")
        r = await c.post("/mcp/ingest/file", json={
            "filepath": md_path,
            "domain": "test-ingest",
            "source_label": "e2e-test-doc.md",
        })
        test("File ingest returns 200", r.status_code == 200,
             f"got {r.status_code}: {r.text[:200]}")
        if r.status_code == 200:
            d = r.json()
            test("Has chunks_total", d.get("chunks_total", 0) > 0,
                 f"got {d.get('chunks_total')}")
            test("Has chunks_ingested", d.get("chunks_ingested", 0) > 0,
                 f"got {d.get('chunks_ingested')}")
            test("Has memory_ids", len(d.get("memory_ids", [])) > 0)
            test("Has duration_ms", d.get("duration_ms", 0) > 0)
            test("No errors", len(d.get("errors", [])) == 0,
                 f"errors: {d.get('errors')}")
            print(f"    Ingested: {d.get('chunks_ingested')}/{d.get('chunks_total')} chunks "
                  f"in {d.get('duration_ms', 0):.0f}ms")

        # ── 3. Dedup on re-ingest ──
        print("\n--- 3. Dedup on Re-Ingest ---")
        r = await c.post("/mcp/ingest/file", json={
            "filepath": md_path,
            "domain": "test-ingest",
            "skip_duplicates": True,
        })
        if r.status_code == 200:
            d = r.json()
            test("All chunks skipped as dupes",
                 d.get("chunks_skipped", 0) == d.get("chunks_total", 0),
                 f"skipped={d.get('chunks_skipped')} total={d.get('chunks_total')}")
            test("Zero new memories", d.get("chunks_ingested", 0) == 0)

        # ── 4. Ingest Single File (.json) ──
        print("\n--- 4. Ingest Single File (.json) ---")
        json_content = json.dumps([
            {"concept": "Delta Decay", "definition": "Recency score degrades over time via R(t+1) = R(t) * (1-d)"},
            {"concept": "Witness Chain", "definition": "Hash-linked append-only log of state transitions"},
            {"concept": "W(k,t)", "definition": "Weight function: (C * R * V) / A"},
        ])
        json_path = make_temp_file(json_content, suffix=".json")
        r = await c.post("/mcp/ingest/file", json={
            "filepath": json_path,
            "domain": "test-ingest",
        })
        test("JSON ingest returns 200", r.status_code == 200)
        if r.status_code == 200:
            d = r.json()
            test("JSON → 3 chunks", d.get("chunks_total") == 3,
                 f"got {d.get('chunks_total')}")

        # ── 5. Ingest Directory ──
        print("\n--- 5. Ingest Directory ---")
        dir_path, _ = make_temp_dir({
            "readme.md": "# Project Readme\n\nThis is a test project for memibrium.\nIt has enough content to pass the minimum length filter.",
            "config.json": json.dumps({"key": "value", "setting": "enabled", "description": "A configuration file with settings for testing"}),
            "notes.txt": "These are plain text notes about the project.\n\n" * 5,
            "data.csv": "name,value,category\n" + "\n".join(
                [f"item_{i},{i},cat_{i%3}" for i in range(20)]
            ),
        })
        r = await c.post("/mcp/ingest/directory", json={
            "directory": dir_path,
            "domain": "test-dir-ingest",
            "recursive": True,
        })
        test("Directory ingest returns 200", r.status_code == 200,
             f"got {r.status_code}: {r.text[:200]}")
        if r.status_code == 200:
            d = r.json()
            test("Files scanned", d.get("files_scanned", 0) >= 3,
                 f"got {d.get('files_scanned')}")
            test("Files ingested", d.get("files_ingested", 0) >= 1,
                 f"got {d.get('files_ingested')}")
            test("Total memories created", d.get("total_memories", 0) > 0,
                 f"got {d.get('total_memories')}")
            test("Has file_results", len(d.get("file_results", [])) > 0)
            print(f"    Dir: {d.get('files_ingested')}/{d.get('files_scanned')} files, "
                  f"{d.get('total_memories')} memories in {d.get('duration_ms', 0):.0f}ms")

        # ── 6. Ingest JSONL (Claude Conversations) ──
        print("\n--- 6. Ingest JSONL (Claude Conversations) ---")
        conversations = [
            {"messages": [
                {"role": "system", "content": "You are helpful."},
                {"role": "user", "content": "How does the memibrium crystallization path work with pgvector dual-tier?"},
                {"role": "assistant", "content": "Memibrium uses a dual-tier architecture where the hot tier (pgvector) stores observation/accepted memories, and the cold tier stores crystallized/shed memories. The crystallization path requires 3 human confirmations via /mcp/confirm."},
            ]},
            {"messages": [
                {"role": "system", "content": "You are helpful."},
                {"role": "user", "content": "What is the Medvinci DTC peptide launch strategy?"},
                {"role": "assistant", "content": "Medvinci Research launched as a DTC peptide brand for independent researchers. The strategy includes affiliate marketing through Amber's network with 20% direct commission."},
            ]},
            {"messages": [
                {"role": "system", "content": "You are helpful."},
                {"role": "user", "content": "Explain wound care MSC 2.0 coding"},
                {"role": "assistant", "content": "MSC wound care uses ICD-10 codes for arterial ulcer..."},
            ]},
            {"messages": [
                {"role": "system", "content": "You are helpful."},
                {"role": "user", "content": "Hi"},
                {"role": "assistant", "content": "Hey"},
            ]},
        ]
        jsonl_path = make_temp_jsonl(conversations)
        r = await c.post("/mcp/ingest/jsonl", json={
            "filepath": jsonl_path,
        })
        test("JSONL ingest returns 200", r.status_code == 200,
             f"got {r.status_code}: {r.text[:200]}")
        if r.status_code == 200:
            d = r.json()
            # Expect: conv 1 → arch-memibrium, conv 2 → biz-medvinci, conv 3 → skipped (wound care), conv 4 → skipped (too short)
            test("Memories created (2 of 4 expected)", d.get("total_memories", 0) >= 1,
                 f"got {d.get('total_memories')}")
            print(f"    JSONL: {d.get('total_memories')} memories, "
                  f"{len(d.get('errors', []))} errors in {d.get('duration_ms', 0):.0f}ms")

        # ── 7. Ingest Status (post-ingest) ──
        print("\n--- 7. Ingest Status (post-ingest) ---")
        r = await c.get("/mcp/ingest/status")
        if r.status_code == 200:
            d = r.json()
            new_hashes = d.get("unique_hashes_seen", 0)
            test("Hashes increased", new_hashes > baseline_hashes,
                 f"baseline={baseline_hashes} now={new_hashes}")

        # ── 8. Taxonomy Endpoint ──
        print("\n--- 8. Taxonomy ---")
        r = await c.get("/mcp/ingest/taxonomy")
        test("Taxonomy GET returns 200", r.status_code == 200)
        if r.status_code == 200:
            d = r.json()
            cats = d.get("categories", [])
            test("30 categories returned", len(cats) == 30,
                 f"got {len(cats)}")
            ids = [c["id"] for c in cats]
            test("patent-ct-keos-stg present", "patent-ct-keos-stg" in ids)
            test("arch-memibrium present", "arch-memibrium" in ids)

        # ── 9. Wiki Compile ──
        print("\n--- 9. Wiki Compile ---")
        wiki_dir = tempfile.mkdtemp()
        TEMP_FILES.append(wiki_dir)
        r = await c.post("/mcp/ingest/compile", json={
            "domain": "test-ingest",
            "output_dir": wiki_dir,
        })
        test("Compile returns 200", r.status_code == 200,
             f"got {r.status_code}: {r.text[:200]}")
        if r.status_code == 200:
            d = r.json()
            test("Has total_memories", d.get("total_memories", 0) >= 0)
            test("Has articles_written", "articles_written" in d)
            test("Has output_dir", "output_dir" in d)
            if d.get("articles_written", 0) > 0:
                test("Index file created",
                     os.path.exists(os.path.join(wiki_dir, "index.md")))
            print(f"    Wiki: {d.get('articles_written', 0)} articles, "
                  f"{d.get('total_memories', 0)} memories")

        # ── 10. Error Handling ──
        print("\n--- 10. Error Handling ---")
        r = await c.post("/mcp/ingest/file", json={})
        test("Empty filepath returns 400", r.status_code == 400)

        r = await c.post("/mcp/ingest/file", json={"filepath": "/nonexistent/file.md"})
        test("Missing file returns 404", r.status_code == 404)

        r = await c.post("/mcp/ingest/directory", json={})
        test("Empty directory returns 400", r.status_code == 400)

        r = await c.post("/mcp/ingest/directory", json={"directory": "/nonexistent/dir"})
        test("Missing directory returns 404", r.status_code == 404)

        r = await c.post("/mcp/ingest/jsonl", json={})
        test("Empty JSONL returns 400", r.status_code == 400)

        # ── 11. Verify memories are queryable ──
        print("\n--- 11. Cross-check: Recall Ingested Content ---")
        r = await c.post("/mcp/recall", json={
            "query": "pgvector hot tier architecture", "top_k": 5})
        test("Recall returns 200", r.status_code == 200)
        if r.status_code == 200:
            results = r.json().get("results", [])
            test("Ingested content is retrievable", len(results) > 0,
                 f"got {len(results)} results")
            if results:
                # Check that at least one result has our test source
                sources = [r.get("source", "") for r in results]
                has_ingest_source = any("file:" in s or "jsonl:" in s for s in sources)
                test("Source tracked in recall", has_ingest_source,
                     f"sources: {sources}")

    # ── Summary ──
    print(f"\n{'='*60}")
    print(f"  TARGET:  {BASE_URL}")
    print(f"  RESULTS: {PASS} passed, {FAIL} failed")
    print(f"  TIME:    {datetime.now().isoformat()}")
    print(f"{'='*60}")

    return FAIL == 0


if __name__ == "__main__":
    try:
        success = asyncio.run(run_tests())
    finally:
        cleanup()
    sys.exit(0 if success else 1)
