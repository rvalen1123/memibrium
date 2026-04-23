#!/usr/bin/env python3
import asyncio
from datetime import datetime, timezone

from memory_hierarchy import parse_temporal_expressions
from hybrid_retrieval import parse_temporal_window, HybridRetriever
from server import IngestAgent


class DummyStore:
    def __init__(self):
        self.insert_calls = []

    async def insert_memory(self, *args, **kwargs):
        self.insert_calls.append((args, kwargs))


class DummyExecutor:
    pass


class DummyEmbedder:
    def __init__(self):
        self._executor = DummyExecutor()

    def embed(self, content):
        return [0.1, 0.2, 0.3]


class DummyChat:
    pass


async def _run_ingest(agent, event_at, refs=None):
    original_hierarchy = __import__('server').hierarchy_manager
    __import__('server').hierarchy_manager = None
    try:
        await agent.ingest(
            "[1:56 pm on 8 May, 2023] John called Maria",
            domain="locomo-test",
            event_at=event_at,
            refs=refs or {},
        )
    finally:
        __import__('server').hierarchy_manager = original_hierarchy


def test_absolute_date_expression_sets_time_bounds():
    expressions = parse_temporal_expressions("Meeting happened on 2023-05-08.")
    assert expressions, "expected at least one temporal expression"
    expr = expressions[0]
    assert expr["kind"] == "absolute_date"
    assert expr["start_time"] is not None
    assert expr["end_time"] is not None
    assert expr["start_time"].isoformat().startswith("2023-05-08T00:00:00")
    assert expr["end_time"].isoformat().startswith("2023-05-09T00:00:00")


def test_locomo_style_datetime_expression_sets_time_bounds():
    expressions = parse_temporal_expressions("[1:56 pm on 8 May, 2023] John called Maria")
    assert expressions, "expected LOCOMO date-time to be extracted"
    expr = expressions[0]
    assert expr["start_time"] is not None
    assert expr["end_time"] is not None
    assert expr["start_time"].year == 2023
    assert expr["start_time"].month == 5
    assert expr["start_time"].day == 8
    assert expr["start_time"].hour == 13
    assert expr["start_time"].minute == 56


def test_before_after_queries_get_temporal_window():
    before_window = parse_temporal_window("What happened before 2023-05-08?", now=datetime(2026, 1, 1, tzinfo=timezone.utc))
    after_window = parse_temporal_window("What happened after 2023-05-08?", now=datetime(2026, 1, 1, tzinfo=timezone.utc))
    assert before_window is not None
    assert after_window is not None
    before_start, before_end = before_window
    after_start, after_end = after_window
    assert before_end.isoformat().startswith("2023-05-08T00:00:00")
    assert after_start.isoformat().startswith("2023-05-09T00:00:00")
    assert before_start < before_end
    assert after_start < after_end


def test_ingest_can_store_event_time_and_refs():
    store = DummyStore()
    agent = IngestAgent(store, DummyEmbedder(), DummyChat())

    async def fake_run_in_executor(executor, func, *args):
        return func(*args)

    loop = asyncio.new_event_loop()
    original_run_in_executor = loop.run_in_executor
    loop.run_in_executor = fake_run_in_executor
    try:
        asyncio.set_event_loop(loop)
        event_at = "2023-05-08T13:56:00+00:00"
        refs = {"session_index": 1, "turn_start": 0, "turn_end": 2, "chunk_index": 0}
        loop.run_until_complete(_run_ingest(agent, event_at, refs=refs))
    finally:
        loop.run_in_executor = original_run_in_executor
        loop.close()
        asyncio.set_event_loop(None)

    assert store.insert_calls, "expected insert_memory to be called"
    args, kwargs = store.insert_calls[0]
    assert kwargs.get("event_at") == event_at
    assert kwargs.get("refs") == refs


def test_chronology_sort_prefers_event_time_then_turn_order():
    retriever = HybridRetriever(pool=None)
    memories = [
        {"id": "b", "created_at": "2023-05-08T13:56:00+00:00", "refs": {"turn_start": 10}},
        {"id": "c", "created_at": "2023-05-09T09:00:00+00:00", "refs": {"turn_start": 0}},
        {"id": "a", "created_at": "2023-05-08T13:56:00+00:00", "refs": {"turn_start": 1}},
    ]
    ordered = retriever.sort_by_chronology(memories)
    assert [m["id"] for m in ordered] == ["a", "b", "c"]


def test_multihop_query_detection():
    retriever = HybridRetriever(pool=None)
    assert retriever.is_multihop_query("How did John get from Berlin to Paris after meeting Maria?") is True
    assert retriever.is_multihop_query("What is John's favorite color?") is False


def test_session_adjacency_expansion_adds_neighboring_chunks():
    retriever = HybridRetriever(pool=None)
    base = [
        {"id": "m2", "created_at": "2023-05-08T13:56:00+00:00", "refs": {"session_index": 1, "chunk_index": 2, "turn_start": 6, "turn_end": 8}, "content": "middle"}
    ]
    candidates = [
        {"id": "m1", "created_at": "2023-05-08T13:55:00+00:00", "refs": {"session_index": 1, "chunk_index": 1, "turn_start": 3, "turn_end": 5}, "content": "before"},
        {"id": "m3", "created_at": "2023-05-08T13:57:00+00:00", "refs": {"session_index": 1, "chunk_index": 3, "turn_start": 9, "turn_end": 11}, "content": "after"},
        {"id": "m9", "created_at": "2023-05-09T13:57:00+00:00", "refs": {"session_index": 2, "chunk_index": 3, "turn_start": 9, "turn_end": 11}, "content": "other session"},
    ]
    expanded = retriever.expand_with_session_adjacency(base, candidates, window=1)
    assert [m["id"] for m in expanded] == ["m1", "m2", "m3"]


def test_bridge_terms_extract_entities_and_refs():
    retriever = HybridRetriever(pool=None)
    memories = [
        {"content": "John met Maria in Berlin and later flew to Paris.", "entities": [{"name": "John"}, {"name": "Maria"}], "refs": {"session_index": 1}},
        {"content": "They discussed the conference venue.", "entities": [], "refs": {"session_index": 2}},
    ]
    terms = retriever.extract_bridge_terms("How did John get from Berlin to Paris after meeting Maria?", memories)
    assert "John" in terms
    assert "Maria" in terms
    assert "Berlin" not in terms and "Paris" not in terms


def test_second_hop_merge_includes_bridge_matches():
    retriever = HybridRetriever(pool=None)
    first_hop = [
        {"id": "m2", "created_at": "2023-05-08T13:56:00+00:00", "refs": {"session_index": 1, "chunk_index": 2, "turn_start": 6, "turn_end": 8}, "content": "John met Maria in Berlin.", "entities": [{"name": "John"}, {"name": "Maria"}]}
    ]
    second_hop = [
        {"id": "m5", "created_at": "2023-05-08T14:10:00+00:00", "refs": {"session_index": 1, "chunk_index": 4, "turn_start": 12, "turn_end": 14}, "content": "Later they flew to Paris.", "entities": [{"name": "Maria"}]},
        {"id": "m8", "created_at": "2023-05-08T15:10:00+00:00", "refs": {"session_index": 3, "chunk_index": 1, "turn_start": 0, "turn_end": 2}, "content": "Unrelated side story.", "entities": [{"name": "Deborah"}]},
    ]
    merged = retriever.merge_multihop_results(first_hop, second_hop)
    assert [m["id"] for m in merged] == ["m2", "m5"]


def test_second_hop_filter_requires_entity_overlap_or_session_match():
    retriever = HybridRetriever(pool=None)
    first_hop = [
        {"id": "m2", "created_at": "2023-05-08T13:56:00+00:00", "refs": {"session_index": 1}, "entities": [{"name": "John"}, {"name": "Maria"}], "content": "John met Maria."}
    ]
    second_hop = [
        {"id": "keep-session", "created_at": "2023-05-08T14:00:00+00:00", "refs": {"session_index": 1}, "entities": [{"name": "Nobody"}], "content": "same session"},
        {"id": "keep-entity", "created_at": "2023-05-08T14:01:00+00:00", "refs": {"session_index": 2}, "entities": [{"name": "Maria"}], "content": "entity overlap"},
        {"id": "drop", "created_at": "2023-05-08T14:02:00+00:00", "refs": {"session_index": 3}, "entities": [{"name": "Deborah"}], "content": "unrelated"},
    ]
    filtered = retriever.filter_second_hop_candidates(first_hop, second_hop)
    assert [m["id"] for m in filtered] == ["keep-session", "keep-entity"]
