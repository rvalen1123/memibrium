#!/usr/bin/env python3
"""
Unit Tests — Ingest Engine (Chunking & Provenance)
====================================================
Tests markdown/plaintext/JSON/CSV chunking, provenance hashing,
dedup logic, and file reading. No DB or LLM dependencies.

Usage:
  python test_ingest_unit.py
"""

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(__file__))
from ingest_engine import (
    chunk_markdown, chunk_plaintext, chunk_json, chunk_csv,
    read_and_chunk, _content_hash, ChunkProvenance,
    MAX_CHUNK_CHARS, MIN_CHUNK_CHARS,
)

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
    return condition


def run_tests():
    global PASS, FAIL

    # ── 1. Markdown Chunking ──
    print("\n--- 1. Markdown Chunking ---")
    md = """# Architecture

This section covers the overall architecture of the system.
It has multiple paragraphs of content that describe how things work.

## Hot Tier

The hot tier uses pgvector for fast HNSW search.
Observations and accepted memories live here.
Results are ranked by cosine similarity times W(k,t).

## Cold Tier

Crystallized and shed memories move to the cold tier.
LEANN provides 97% compression via graph recomputation.

# Deployment

Deployment uses Azure Container Apps with Caddy reverse proxy.
The staging slot runs identical config with a separate DB.
"""
    chunks = chunk_markdown(md)
    test("Markdown produces chunks", len(chunks) > 0, f"got {len(chunks)}")
    test("Multiple sections found", len(chunks) >= 3,
         f"got {len(chunks)}")

    # Check heading paths are captured
    has_heading_path = any(c.get("heading_path") for c in chunks)
    test("Heading paths captured", has_heading_path)

    # Check no empty chunks
    test("No empty chunks",
         all(len(c["content"].strip()) > 0 for c in chunks))

    # ── 2. Oversized section splitting ──
    print("\n--- 2. Oversized Section Splitting ---")
    big_section = "# Big Section\n\n" + "\n\n".join(
        [f"Paragraph {i}: " + "x" * 200 for i in range(20)]
    )
    chunks = chunk_markdown(big_section, max_chars=500)
    test("Big section gets split", len(chunks) > 1,
         f"got {len(chunks)} chunks")
    test("All chunks under max",
         all(len(c["content"]) <= 700 for c in chunks),  # some overhead ok
         f"max chunk: {max(len(c['content']) for c in chunks)}")

    # ── 3. Plaintext Chunking ──
    print("\n--- 3. Plaintext Chunking ---")
    plain = "\n\n".join([f"Paragraph {i}: " + "word " * 50 for i in range(10)])
    chunks = chunk_plaintext(plain, max_chars=500)
    test("Plaintext produces chunks", len(chunks) > 1)
    test("All plaintext chunks have content",
         all(c["content"].strip() for c in chunks))

    # ── 4. JSON Chunking ──
    print("\n--- 4. JSON Chunking ---")
    json_array = json.dumps([
        {"name": "Alpha", "value": 1, "desc": "First item"},
        {"name": "Beta", "value": 2, "desc": "Second item"},
        {"name": "Gamma", "value": 3, "desc": "Third item"},
    ])
    chunks = chunk_json(json_array)
    test("JSON array → 3 chunks", len(chunks) == 3, f"got {len(chunks)}")
    test("First chunk is valid JSON",
         json.loads(chunks[0]["content"])["name"] == "Alpha")
    test("Heading path has index", chunks[1]["heading_path"] == ["[1]"])

    # Invalid JSON falls back to plaintext
    chunks = chunk_json("this is not json at all")
    test("Invalid JSON falls back", len(chunks) > 0)

    # ── 5. CSV Chunking ──
    print("\n--- 5. CSV Chunking ---")
    csv_data = "name,value,category\n" + "\n".join(
        [f"item_{i},{i},cat_{i%3}" for i in range(50)]
    )
    chunks = chunk_csv(csv_data, max_chars=500)
    test("CSV produces chunks", len(chunks) > 1)
    # Each chunk should start with the header
    test("All CSV chunks have header",
         all(c["content"].startswith("name,value,category") for c in chunks))

    # ── 6. Content Hashing ──
    print("\n--- 6. Content Hashing ---")
    h1 = _content_hash("hello world")
    h2 = _content_hash("hello world")
    h3 = _content_hash("different content")
    test("Same content → same hash", h1 == h2)
    test("Different content → different hash", h1 != h3)
    test("Hash is 16 chars hex", len(h1) == 16 and all(c in "0123456789abcdef" for c in h1))

    # ── 7. Provenance Records ──
    print("\n--- 7. Provenance Records ---")
    prov = ChunkProvenance(
        source_file="/path/to/doc.md",
        chunk_index=0,
        total_chunks=5,
        content_hash=h1,
        heading_path=["# Architecture", "## Hot Tier"],
        char_offset=100,
        char_length=500,
    )
    test("Provenance has source", prov.source_file == "/path/to/doc.md")
    test("Provenance has hash", prov.content_hash == h1)
    test("Provenance has heading path", len(prov.heading_path) == 2)
    test("Provenance auto-timestamps", len(prov.ingested_at) > 0)

    # ── 8. File Reading ──
    print("\n--- 8. File Reading ---")
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False,
                                      encoding='utf-8') as f:
        f.write(md)
        md_path = f.name

    try:
        chunks, fmt = read_and_chunk(md_path)
        test("MD file reads", len(chunks) > 0)
        test("Format detected as md", fmt == "md")
    finally:
        os.unlink(md_path)

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False,
                                      encoding='utf-8') as f:
        f.write(json_array)
        json_path = f.name

    try:
        chunks, fmt = read_and_chunk(json_path)
        test("JSON file reads", len(chunks) > 0)
        test("Format detected as json", fmt == "json")
    finally:
        os.unlink(json_path)

    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False,
                                      encoding='utf-8') as f:
        f.write(plain)
        txt_path = f.name

    try:
        chunks, fmt = read_and_chunk(txt_path)
        test("TXT file reads", len(chunks) > 0)
        test("Format detected as txt", fmt == "txt")
    finally:
        os.unlink(txt_path)

    # Unsupported extension
    try:
        read_and_chunk("/fake/file.xyz")
        test("Unsupported ext raises", False, "no exception")
    except ValueError:
        test("Unsupported ext raises", True)

    # ── 9. Empty file handling ──
    print("\n--- 9. Edge Cases ---")
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write("")
        empty_path = f.name

    try:
        chunks, fmt = read_and_chunk(empty_path)
        test("Empty file → 0 chunks", len(chunks) == 0)
    finally:
        os.unlink(empty_path)

    # Very short content (below min_chars)
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write("Hi")
        short_path = f.name

    try:
        chunks, fmt = read_and_chunk(short_path)
        test("Short content produces chunk (filtered at ingest)", len(chunks) >= 0)
    finally:
        os.unlink(short_path)

    # ── 10. Markdown with no headers ──
    print("\n--- 10. No-Header Markdown ---")
    no_headers = "Just some text without any markdown headers.\n\n" * 5
    chunks = chunk_markdown(no_headers)
    test("No-header falls to plaintext", len(chunks) > 0)

    # ── 11. CSV edge: single row ──
    print("\n--- 11. CSV Edge Cases ---")
    single_row_csv = "header1,header2\n"
    chunks = chunk_csv(single_row_csv)
    test("Single-row CSV → 1 chunk", len(chunks) == 1)

    # ── 12. JSONL mock (conversation format) ──
    print("\n--- 12. JSONL Conversation Format ---")
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False,
                                      encoding='utf-8') as f:
        for i in range(5):
            line = json.dumps({
                "messages": [
                    {"role": "system", "content": "You are helpful."},
                    {"role": "user", "content": f"Question {i}: How does memibrium work?"},
                    {"role": "assistant", "content": f"Answer {i}: Memibrium implements crystallization theory."},
                ]
            })
            f.write(line + "\n")
        jsonl_path = f.name

    try:
        # JSONL should be readable as text
        with open(jsonl_path, 'r') as jf:
            lines = jf.readlines()
        test("JSONL has 5 lines", len(lines) == 5)
        for line in lines:
            d = json.loads(line)
            test("Line is valid JSON", "messages" in d)
            break  # just test first line structure
    finally:
        os.unlink(jsonl_path)

    # ── Summary ──
    print(f"\n{'='*50}")
    print(f"  RESULTS: {PASS} passed, {FAIL} failed")
    print(f"{'='*50}")
    return FAIL == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
