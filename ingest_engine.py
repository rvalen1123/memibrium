#!/usr/bin/env python3
"""
Memibrium Ingestion Engine
=========================================================

Bulk document ingestion with semantic chunking, provenance tracking,
and wiki compilation. Extends Memibrium's single-string IngestAgent
into a full knowledge pipeline.

Pipeline:
  raw files → chunk → provenance hash → IngestAgent → CT lifecycle → wiki index

Supported formats: .md, .txt, .json, .csv, .pdf (text extraction)

Patent alignment:
  STG Claim 6 — witness chains: every chunk gets a provenance record
  CT lifecycle — all chunks enter as OBSERVATION, gate to ACCEPTED
  δ-decay     — chunks that aren't confirmed decay like any other memory

Author: Ricky Valentine / Orchard Holdings LLC
"""

import asyncio
import hashlib
import json
import logging
import os
import re
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from knowledge_taxonomy import KnowledgeClassifier, Category, DEFAULT_SKIP_KEYWORDS

log = logging.getLogger("memibrium.ingest_engine")

# ── Configuration ──────────────────────────────────────────────────

MAX_CHUNK_CHARS = int(os.environ.get("INGEST_MAX_CHUNK_CHARS", "2000"))
MIN_CHUNK_CHARS = int(os.environ.get("INGEST_MIN_CHUNK_CHARS", "100"))
OVERLAP_CHARS = int(os.environ.get("INGEST_OVERLAP_CHARS", "200"))
SUPPORTED_EXTENSIONS = {".md", ".txt", ".json", ".csv", ".pdf"}


# ── Data Models ────────────────────────────────────────────────────

@dataclass
class ChunkProvenance:
    """Provenance record for a single chunk — STG Claim 6 alignment."""
    source_file: str
    chunk_index: int
    total_chunks: int
    content_hash: str
    heading_path: list[str]  # e.g. ["# Architecture", "## Hot Tier"]
    char_offset: int
    char_length: int
    ingested_at: str = ""

    def __post_init__(self):
        if not self.ingested_at:
            self.ingested_at = datetime.now(timezone.utc).isoformat()


@dataclass
class IngestResult:
    source_file: str
    chunks_total: int
    chunks_ingested: int
    chunks_skipped: int
    memory_ids: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    duration_ms: float = 0.0


@dataclass
class DirectoryIngestResult:
    directory: str
    files_scanned: int
    files_ingested: int
    files_skipped: int
    total_chunks: int
    total_memories: int
    file_results: list[dict] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    duration_ms: float = 0.0


# ── Chunking Strategies ───────────────────────────────────────────

def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def chunk_markdown(text: str, max_chars: int = MAX_CHUNK_CHARS,
                   min_chars: int = MIN_CHUNK_CHARS) -> list[dict]:
    """
    Semantic chunking by markdown headers.
    Splits on H1/H2/H3, preserves heading hierarchy as context.
    Oversized sections get paragraph-split with overlap.
    """
    # Split on headers while keeping the header line
    header_pattern = re.compile(r"^(#{1,3})\s+(.+)$", re.MULTILINE)
    sections = []
    last_end = 0
    heading_stack: list[str] = []

    for match in header_pattern.finditer(text):
        # Capture content before this header
        if last_end < match.start():
            content = text[last_end:match.start()].strip()
            if content and len(content) >= min_chars:
                sections.append({
                    "content": content,
                    "heading_path": list(heading_stack),
                    "char_offset": last_end,
                })

        level = len(match.group(1))
        title = match.group(0).strip()

        # Maintain heading stack by level
        heading_stack = [h for h in heading_stack
                         if h.count("#") < title.count("#")]
        heading_stack.append(title)
        last_end = match.start()

    # Capture trailing content
    if last_end < len(text):
        content = text[last_end:].strip()
        if content and len(content) >= min_chars:
            sections.append({
                "content": content,
                "heading_path": list(heading_stack),
                "char_offset": last_end,
            })

    # If no headers found, fall back to paragraph chunking
    if not sections:
        return chunk_plaintext(text, max_chars, min_chars)

    # Split oversized sections by paragraphs
    final_chunks = []
    for section in sections:
        content = section["content"]
        if len(content) <= max_chars:
            final_chunks.append(section)
        else:
            sub_chunks = _split_by_paragraphs(
                content, max_chars,
                heading_path=section["heading_path"],
                base_offset=section["char_offset"],
            )
            final_chunks.extend(sub_chunks)

    return final_chunks


def chunk_plaintext(text: str, max_chars: int = MAX_CHUNK_CHARS,
                    min_chars: int = MIN_CHUNK_CHARS) -> list[dict]:
    """Paragraph-based chunking with overlap for plain text."""
    return _split_by_paragraphs(text, max_chars, heading_path=[], base_offset=0)


def _split_by_paragraphs(text: str, max_chars: int,
                          heading_path: list[str],
                          base_offset: int) -> list[dict]:
    """Split text into chunks at paragraph boundaries."""
    paragraphs = re.split(r"\n\s*\n", text)
    chunks = []
    current = ""
    current_offset = base_offset

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        if len(current) + len(para) + 2 > max_chars and current:
            chunks.append({
                "content": current.strip(),
                "heading_path": list(heading_path),
                "char_offset": current_offset,
            })
            # Overlap: keep tail of previous chunk
            overlap = current[-OVERLAP_CHARS:] if len(current) > OVERLAP_CHARS else ""
            current_offset = current_offset + len(current) - len(overlap)
            current = overlap + "\n\n" + para if overlap else para
        else:
            if not current:
                current_offset = base_offset
            current = current + "\n\n" + para if current else para

    if current.strip():
        chunks.append({
            "content": current.strip(),
            "heading_path": list(heading_path),
            "char_offset": current_offset,
        })

    return chunks


def chunk_json(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list[dict]:
    """Chunk JSON: if array of objects, each object is a chunk. Otherwise plaintext."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return chunk_plaintext(text, max_chars)

    if isinstance(data, list):
        chunks = []
        offset = 0
        for i, item in enumerate(data):
            serialized = json.dumps(item, indent=2, ensure_ascii=False)
            chunks.append({
                "content": serialized,
                "heading_path": [f"[{i}]"],
                "char_offset": offset,
            })
            offset += len(serialized)
        return chunks

    return chunk_plaintext(text, max_chars)


def chunk_csv(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list[dict]:
    """Chunk CSV by groups of rows, keeping header on each chunk."""
    lines = text.strip().split("\n")
    if len(lines) < 2:
        return [{"content": text, "heading_path": [], "char_offset": 0}]

    header = lines[0]
    chunks = []
    current_rows = [header]
    current_len = len(header)
    offset = 0

    for line in lines[1:]:
        if current_len + len(line) + 1 > max_chars and len(current_rows) > 1:
            chunks.append({
                "content": "\n".join(current_rows),
                "heading_path": [],
                "char_offset": offset,
            })
            offset += current_len
            current_rows = [header]
            current_len = len(header)

        current_rows.append(line)
        current_len += len(line) + 1

    if len(current_rows) > 1:
        chunks.append({
            "content": "\n".join(current_rows),
            "heading_path": [],
            "char_offset": offset,
        })

    return chunks


# ── File Reading ───────────────────────────────────────────────────

def read_and_chunk(filepath: str) -> tuple[list[dict], str]:
    """
    Read a file, detect type, chunk accordingly.
    Returns (chunks, format_type).
    """
    path = Path(filepath)
    ext = path.suffix.lower()

    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {ext}. Supported: {SUPPORTED_EXTENSIONS}")

    if ext == ".pdf":
        text = _extract_pdf_text(filepath)
        fmt = "pdf"
    else:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
        fmt = ext.lstrip(".")

    if not text.strip():
        return [], fmt

    if ext == ".md":
        chunks = chunk_markdown(text)
    elif ext == ".json":
        chunks = chunk_json(text)
    elif ext == ".csv":
        chunks = chunk_csv(text)
    else:
        chunks = chunk_plaintext(text)

    return chunks, fmt


def _extract_pdf_text(filepath: str) -> str:
    """Best-effort PDF text extraction. Falls back gracefully."""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(filepath)
        pages = [page.get_text() for page in doc]
        doc.close()
        return "\n\n".join(pages)
    except ImportError:
        pass

    try:
        from pypdf import PdfReader
        reader = PdfReader(filepath)
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n\n".join(pages)
    except ImportError:
        pass

    log.warning(f"No PDF library available. Install PyMuPDF or pypdf. Skipping {filepath}")
    return ""


# ── Ingestion Engine ───────────────────────────────────────────────

class DocumentIngestEngine:
    """
    Bulk document ingestion with provenance tracking.

    Pipeline:
      file → read → chunk → provenance → IngestAgent.ingest() → CT lifecycle

    Usage:
      engine = DocumentIngestEngine(ingest_agent)
      result = await engine.ingest_file("/path/to/doc.md", domain="research")
      result = await engine.ingest_directory("/path/to/raw/", domain="research")
    """

    def __init__(self, ingest_agent, store=None, classifier=None):
        """
        Args:
            ingest_agent: The existing Memibrium IngestAgent instance
            store: Optional ColdStore for dedup checks
            classifier: Optional KnowledgeClassifier for tier assignment
        """
        self.agent = ingest_agent
        self.store = store
        self.classifier = classifier or KnowledgeClassifier()
        self._ingested_hashes: set[str] = set()  # in-memory dedup cache

    async def ingest_file(self, filepath: str, domain: str = "default",
                          source_label: Optional[str] = None,
                          skip_duplicates: bool = True) -> IngestResult:
        """
        Ingest a single file: read, chunk, feed through CT lifecycle.

        Args:
            filepath: Path to the file
            domain: Memory domain for partitioning
            source_label: Override source name (default: filename)
            skip_duplicates: Skip chunks whose content hash was already ingested
        """
        import time
        t0 = time.monotonic()

        path = Path(filepath)
        source = source_label or path.name
        result = IngestResult(source_file=str(path), chunks_total=0,
                              chunks_ingested=0, chunks_skipped=0)

        try:
            chunks, fmt = read_and_chunk(str(path))
        except Exception as e:
            result.errors.append(f"Read error: {e}")
            result.duration_ms = (time.monotonic() - t0) * 1000
            return result

        result.chunks_total = len(chunks)

        for i, chunk in enumerate(chunks):
            content = chunk["content"]
            chash = _content_hash(content)

            if skip_duplicates and chash in self._ingested_hashes:
                result.chunks_skipped += 1
                continue

            # Build provenance metadata and prepend to content
            provenance = ChunkProvenance(
                source_file=str(path),
                chunk_index=i,
                total_chunks=len(chunks),
                content_hash=chash,
                heading_path=chunk.get("heading_path", []),
                char_offset=chunk.get("char_offset", 0),
                char_length=len(content),
            )

            # Prefix content with source context for better retrieval
            heading_ctx = " > ".join(chunk.get("heading_path", []))
            prefix = f"[Source: {source}]"
            if heading_ctx:
                prefix += f" [{heading_ctx}]"
            enriched_content = f"{prefix}\n{content}"

            try:
                mem_result = await self.agent.ingest(
                    enriched_content,
                    source=f"file:{source}",
                    domain=domain,
                )
                result.memory_ids.append(mem_result["id"])
                result.chunks_ingested += 1
                self._ingested_hashes.add(chash)
            except Exception as e:
                result.errors.append(f"Chunk {i} error: {e}")

        result.duration_ms = (time.monotonic() - t0) * 1000
        log.info(
            f"Ingested {source}: {result.chunks_ingested}/{result.chunks_total} chunks "
            f"({result.chunks_skipped} skipped, {len(result.errors)} errors) "
            f"in {result.duration_ms:.0f}ms"
        )
        return result

    async def ingest_jsonl(self, filepath: str,
                           skip_short: bool = True,
                           skip_duplicates: bool = True,
                           min_user_len: int = 20,
                           min_asst_len: int = 50) -> DirectoryIngestResult:
        """
        Ingest Claude conversation JSONL (the RV-Brain format).

        Each line is {"messages": [{"role":"system",...}, {"role":"user",...}, {"role":"assistant",...}]}

        Classification determines the domain (category.id) and tier.
        Skip list filters dead projects.
        Dedup by content hash.
        """
        import time
        t0 = time.monotonic()

        result = DirectoryIngestResult(
            directory=filepath, files_scanned=1,
            files_ingested=0, files_skipped=0,
            total_chunks=0, total_memories=0,
        )

        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
        except Exception as e:
            result.errors.append(f"Read error: {e}")
            return result

        result.total_chunks = len(lines)
        skipped_short = 0
        skipped_content = 0
        skipped_dupes = 0

        for line_num, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue

            msgs = data.get("messages", [])
            user_text = ""
            asst_text = ""
            for m in msgs:
                if m.get("role") == "user":
                    user_text = m.get("content", "")
                elif m.get("role") == "assistant":
                    asst_text = m.get("content", "")

            if not user_text or not asst_text:
                continue

            # Length filter
            if skip_short and (len(user_text) < min_user_len or len(asst_text) < min_asst_len):
                skipped_short += 1
                continue

            combined = user_text + " " + asst_text

            # Skip list
            if self.classifier.should_skip(combined):
                skipped_content += 1
                continue

            # Dedup
            chash = _content_hash(combined[:500])
            if skip_duplicates and chash in self._ingested_hashes:
                skipped_dupes += 1
                continue

            # Classify → get domain and tier
            categories, tier = self.classifier.classify_with_tier(combined)
            primary_cat = categories[0]

            # Build content for ingestion
            # Include both Q and A — the knowledge pair
            content = f"[Source: claude-conversation] [{primary_cat.title}]\n\nQ: {user_text}\n\nA: {asst_text}"

            # Truncate oversized assistant responses
            if len(content) > MAX_CHUNK_CHARS * 3:
                content = content[:MAX_CHUNK_CHARS * 3] + "\n\n[...truncated...]"

            try:
                mem_result = await self.agent.ingest(
                    content,
                    source=f"jsonl:{primary_cat.id}",
                    domain=primary_cat.id,
                )
                result.total_memories += 1
                self._ingested_hashes.add(chash)
            except Exception as e:
                result.errors.append(f"Line {line_num}: {e}")

        result.files_ingested = 1
        result.duration_ms = (time.monotonic() - t0) * 1000

        log.info(
            f"JSONL ingest {filepath}: {result.total_memories} memories, "
            f"{skipped_short} short, {skipped_content} skipped, {skipped_dupes} dupes "
            f"in {result.duration_ms:.0f}ms"
        )
        return result

    async def ingest_directory(self, dirpath: str, domain: str = "default",
                               recursive: bool = True,
                               extensions: Optional[set[str]] = None,
                               skip_duplicates: bool = True) -> DirectoryIngestResult:
        """
        Scan a directory and ingest all supported files.

        Args:
            dirpath: Path to directory
            domain: Memory domain
            recursive: Walk subdirectories
            extensions: Filter to specific extensions (default: all supported)
            skip_duplicates: Skip duplicate chunks across files
        """
        import time
        t0 = time.monotonic()

        exts = extensions or SUPPORTED_EXTENSIONS
        dirpath = Path(dirpath)
        result = DirectoryIngestResult(
            directory=str(dirpath), files_scanned=0,
            files_ingested=0, files_skipped=0,
            total_chunks=0, total_memories=0,
        )

        if not dirpath.is_dir():
            result.errors.append(f"Not a directory: {dirpath}")
            return result

        # Collect files
        if recursive:
            files = [f for f in dirpath.rglob("*") if f.suffix.lower() in exts and f.is_file()]
        else:
            files = [f for f in dirpath.glob("*") if f.suffix.lower() in exts and f.is_file()]

        # Sort for deterministic ordering
        files.sort()
        result.files_scanned = len(files)

        for fpath in files:
            try:
                file_result = await self.ingest_file(
                    str(fpath), domain=domain,
                    skip_duplicates=skip_duplicates,
                )
                result.files_ingested += 1
                result.total_chunks += file_result.chunks_total
                result.total_memories += file_result.chunks_ingested
                result.file_results.append(asdict(file_result))
            except Exception as e:
                result.files_skipped += 1
                result.errors.append(f"{fpath.name}: {e}")

        result.duration_ms = (time.monotonic() - t0) * 1000
        log.info(
            f"Directory ingest {dirpath}: {result.files_ingested}/{result.files_scanned} files, "
            f"{result.total_memories} memories in {result.duration_ms:.0f}ms"
        )
        return result

    async def compile_index(self, domain: str = "default",
                            chat_client=None) -> dict:
        """
        Generate a wiki-style index of all ingested knowledge in a domain.

        Queries the store for all active memories, groups by source file,
        and optionally uses the LLM to generate summaries per source.

        Returns dict with index structure suitable for writing to index.md.
        """
        if not self.store:
            return {"error": "No store available for index compilation"}

        memories = await self.store.get_active_memories()

        # Group by source
        by_source: dict[str, list[dict]] = {}
        for mem in memories:
            source = mem.get("source", "unknown")
            if mem.get("domain", "default") != domain and domain != "all":
                continue
            by_source.setdefault(source, []).append(mem)

        index = {
            "domain": domain,
            "compiled_at": datetime.now(timezone.utc).isoformat(),
            "total_memories": len(memories),
            "sources": {},
        }

        for source, mems in sorted(by_source.items()):
            state_counts = {}
            for m in mems:
                st = m.get("lifecycle_state", "unknown")
                state_counts[st] = state_counts.get(st, 0) + 1

            source_entry = {
                "count": len(mems),
                "states": state_counts,
                "topics": list({t for m in mems for t in (m.get("topics") or [])}),
            }

            # Generate summary if chat client available
            if chat_client and len(mems) > 0:
                combined = "\n---\n".join(
                    m.get("content", "")[:500] for m in mems[:10]
                )
                try:
                    summary = chat_client.synthesize(
                        [{"content": m.get("content", ""), "lifecycle_state": m.get("lifecycle_state", "")}
                         for m in mems[:10]],
                        topic=f"Summary of source: {source}",
                    )
                    source_entry["summary"] = summary
                except Exception as e:
                    source_entry["summary"] = f"(summary failed: {e})"

            index["sources"][source] = source_entry

        return index

    def get_stats(self) -> dict:
        """Return ingestion statistics."""
        return {
            "unique_hashes_seen": len(self._ingested_hashes),
            "supported_extensions": list(SUPPORTED_EXTENSIONS),
            "taxonomy_categories": len(self.classifier.categories),
            "taxonomy_tiers": {
                "crystallize": sum(1 for c in self.classifier.categories if c.tier == "crystallize"),
                "hot": sum(1 for c in self.classifier.categories if c.tier == "hot"),
                "archive": sum(1 for c in self.classifier.categories if c.tier == "archive"),
            },
            "config": {
                "max_chunk_chars": MAX_CHUNK_CHARS,
                "min_chunk_chars": MIN_CHUNK_CHARS,
                "overlap_chars": OVERLAP_CHARS,
            },
        }


# ── Wiki Compiler ──────────────────────────────────────────────────

class WikiCompiler:
    """
    Generates markdown wiki files from Memibrium's memory store.

    This is the Karpathy "compile" step: raw data → structured wiki
    with index files, topic articles, and backlinks.
    """

    def __init__(self, store, chat_client, output_dir: str = "./wiki"):
        self.store = store
        self.chat = chat_client
        self.output_dir = Path(output_dir)

    async def compile(self, domain: str = "default") -> dict:
        """
        Full wiki compilation:
        1. Query all active memories
        2. Group by topic
        3. Generate topic articles
        4. Generate index with backlinks
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)

        memories = await self.store.get_active_memories()
        if domain != "all":
            memories = [m for m in memories if m.get("domain", "default") == domain]

        # Group by topic
        by_topic: dict[str, list[dict]] = {}
        for mem in memories:
            for topic in (mem.get("topics") or ["uncategorized"]):
                by_topic.setdefault(topic, []).append(mem)

        articles_written = 0
        topic_index = []

        for topic, mems in sorted(by_topic.items()):
            safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", topic).lower()
            article_path = self.output_dir / f"{safe_name}.md"

            # Build article content
            lines = [
                f"# {topic.title()}",
                "",
                f"*{len(mems)} memories · Compiled {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}*",
                "",
            ]

            # State breakdown
            states = {}
            for m in mems:
                st = m.get("lifecycle_state", "unknown")
                states[st] = states.get(st, 0) + 1
            state_str = " · ".join(f"{k}: {v}" for k, v in sorted(states.items()))
            lines.append(f"**Lifecycle:** {state_str}")
            lines.append("")

            # Memory entries, crystallized first
            sorted_mems = sorted(mems, key=lambda m: (
                0 if m.get("lifecycle_state") == "crystallized" else 1,
                -(m.get("confirmation_count", 0)),
            ))

            for mem in sorted_mems[:20]:  # Cap per article
                state_badge = mem.get("lifecycle_state", "?").upper()
                conf = mem.get("confirmation_count", 0)
                content_preview = (mem.get("content", "")[:300]).replace("\n", " ")
                lines.append(f"### [{state_badge}] (confirmed ×{conf})")
                lines.append(f"{content_preview}")
                lines.append("")

            article_path.write_text("\n".join(lines), encoding="utf-8")
            articles_written += 1
            topic_index.append({
                "topic": topic,
                "file": f"{safe_name}.md",
                "count": len(mems),
                "states": states,
            })

        # Write index
        index_lines = [
            "# Knowledge Wiki Index",
            "",
            f"*Domain: {domain} · {len(memories)} memories · "
            f"{articles_written} articles · "
            f"Compiled {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}*",
            "",
            "## Topics",
            "",
        ]
        for entry in sorted(topic_index, key=lambda e: -e["count"]):
            index_lines.append(
                f"- [[{entry['file']}|{entry['topic'].title()}]] "
                f"({entry['count']} memories)"
            )

        index_path = self.output_dir / "index.md"
        index_path.write_text("\n".join(index_lines), encoding="utf-8")

        return {
            "domain": domain,
            "total_memories": len(memories),
            "articles_written": articles_written,
            "topics": [e["topic"] for e in topic_index],
            "output_dir": str(self.output_dir),
            "index_file": str(index_path),
        }
