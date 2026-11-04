#!/usr/bin/env python3
"""POST /mcp: the MCP protocol endpoint the shipped plugin connects to (MED-254).

Runs against the Starlette app in-process with no database, server, LLM or network: the
TestClient is not entered as a context manager, so the startup hook (schema migration,
embedding probe) never runs. Tool calls that would touch the database use patched handlers.
"""

import base64
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from starlette.testclient import TestClient

import server
from ingest_engine import DirectoryIngestResult, IngestResult

LEGACY = "2025-06-18"
MODERN = "2026-07-28"
META = {
    "io.modelcontextprotocol/protocolVersion": MODERN,
    "io.modelcontextprotocol/clientInfo": {"name": "t", "version": "1"},
    "io.modelcontextprotocol/clientCapabilities": {},
}
WITHHELD = {"confirm", "consolidate", "revert", "freeze"}
PATH_TOOLS = {"ingest_file", "ingest_directory", "ingest_jsonl", "compile_wiki"}
DEFAULT_SERVED = {"retain", "recall", "reflect", "dashboard", "prefetch", "self_model_observe", "context_packet",
                  "decision_trace", "ingest_status", "wiki_read"}


class McpEndpointTest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(server.app)  # no `with`: startup (DB, embedder) does not run
        # Every test starts with MCP_INGEST_ROOTS unset (the default), whatever the environment says.
        roots = patch.object(server, "MCP_INGEST_ROOTS", ())
        roots.start()
        self.addCleanup(roots.stop)

    def tools_list(self):
        r = self.rpc({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        return {t["name"]: t for t in r.json()["result"]["tools"]}

    def rpc(self, body, headers=None):
        h = {"content-type": "application/json", "accept": "application/json, text/event-stream"}
        h.update(headers or {})
        return self.client.post("/mcp", content=json.dumps(body), headers=h)

    def call(self, name, arguments=None, msg_id=10):
        params = {"name": name}
        if arguments is not None:
            params["arguments"] = arguments
        return self.rpc({"jsonrpc": "2.0", "id": msg_id, "method": "tools/call", "params": params},
                        {"mcp-protocol-version": LEGACY})

    # ── the legacy handshake a plugin client performs ──

    def test_legacy_initialize_list_and_read_only_call(self):
        init = self.rpc({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": LEGACY, "capabilities": {}, "clientInfo": {"name": "claude-code", "version": "2"}}})
        self.assertEqual(init.status_code, 200)
        self.assertIsNone(init.headers.get("mcp-session-id"))  # stateless: no sessions
        result = init.json()["result"]
        self.assertEqual(result["protocolVersion"], LEGACY)
        self.assertEqual(result["serverInfo"]["name"], "memibrium")
        self.assertIn("tools", result["capabilities"])

        note = self.rpc({"jsonrpc": "2.0", "method": "notifications/initialized"}, {"mcp-protocol-version": LEGACY})
        self.assertEqual(note.status_code, 202)
        self.assertEqual(note.text, "")

        listed = self.rpc({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, {"mcp-protocol-version": LEGACY})
        self.assertEqual(listed.status_code, 200)
        tools = listed.json()["result"]["tools"]
        names = [t["name"] for t in tools]
        self.assertEqual(set(names), DEFAULT_SERVED)
        self.assertIn("recall", names)
        self.assertIn("retain", names)

        # The names and inputSchemas are the REST manifest's own.
        manifest = {t["name"]: t for t in server.mcp_manifest_tools()}
        for tool in tools:
            expected = manifest[tool["name"]]["inputSchema"]
            overrides = server.MCP_SCHEMA_OVERRIDES.get(tool["name"], {})
            if overrides:
                expected = {**expected, "properties": {**expected["properties"], **overrides}}
            self.assertEqual(tool["inputSchema"], expected, tool["name"])
            self.assertEqual(tool["description"], manifest[tool["name"]]["description"], tool["name"])
        # Over MCP a decision trace can only be proposed.
        trace = next(t for t in tools if t["name"] == "decision_trace")
        self.assertEqual(trace["inputSchema"]["properties"]["status"]["enum"], ["proposed"])

        status = self.call("ingest_status", {})
        self.assertEqual(status.status_code, 200)
        body = status.json()["result"]
        self.assertNotIn("isError", body)
        self.assertEqual(body["structuredContent"]["taxonomy_categories"], 30)
        self.assertEqual(json.loads(body["content"][0]["text"]), body["structuredContent"])

    def test_unknown_legacy_version_negotiates_newest_legacy(self):
        init = self.rpc({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05"}})
        self.assertEqual(init.json()["result"]["protocolVersion"], "2025-11-25")

    def test_tool_call_dispatches_arguments_to_the_rest_handler(self):
        seen = {}

        async def fake_recall(query, **kwargs):
            seen["query"], seen["kwargs"] = query, kwargs
            return {"results": [{"id": "m1", "state": "accepted", "content": "rate limit 1000/min"}]}

        with patch.object(server, "recall_memories", fake_recall):
            r = self.call("recall", {"query": "rate limit", "top_k": 3, "domain": "proj"})
        result = r.json()["result"]
        self.assertNotIn("isError", result)
        self.assertEqual(seen["query"], "rate limit")
        self.assertEqual(seen["kwargs"]["top_k"], 3)
        self.assertEqual(seen["kwargs"]["domain"], "proj")
        self.assertEqual(json.loads(result["content"][0]["text"])[0]["id"], "m1")
        self.assertNotIn("structuredContent", result)  # a list is not a structuredContent object

    def test_handler_error_status_becomes_a_tool_error(self):
        root, _ = self._roots()
        r = self.call("ingest_file", {"filepath": str(root / "missing.md")})
        self.assertEqual(r.status_code, 200)
        result = r.json()["result"]
        self.assertTrue(result["isError"])
        self.assertIn("File not found", result["structuredContent"]["error"])

    def test_handler_exception_becomes_a_tool_error(self):
        async def boom(request):
            raise RuntimeError("pool not initialized")

        dispatch = dict(server.MCP_TOOL_DISPATCH)
        _, method, path, ann = dispatch["dashboard"]
        dispatch["dashboard"] = (boom, method, path, ann)
        with patch.object(server, "MCP_TOOL_DISPATCH", dispatch):
            result = self.call("dashboard", {}).json()["result"]
        self.assertTrue(result["isError"])
        # The client gets the exception type, not its message (which stays in the server log).
        self.assertIn("RuntimeError", result["content"][0]["text"])
        self.assertNotIn("pool not initialized", result["content"][0]["text"])

    # ── CT authority: nothing reachable over MCP can confirm or crystallize ──

    def test_withheld_tools_are_not_listed(self):
        names = {t["name"] for t in self.rpc({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}).json()["result"]["tools"]}
        self.assertFalse(names & WITHHELD, names & WITHHELD)
        self.assertEqual(set(server.MCP_WITHHELD_TOOLS), WITHHELD)
        self.assertFalse(set(server.MCP_TOOL_DISPATCH) & WITHHELD)

    def test_confirm_is_refused_and_never_reaches_the_store(self):
        async def must_not_run(*a, **k):
            raise AssertionError("confirm reached the store through MCP")

        with patch.object(server.store, "get_memory", must_not_run), \
                patch.object(server.store, "update_memory", must_not_run), \
                patch.object(server.store, "add_feedback", must_not_run):
            r = self.call("confirm", {"memory_id": "mem_1", "weight": 1.0})
        self.assertEqual(r.status_code, 200)
        err = r.json()["error"]
        self.assertEqual(err["code"], -32602)
        self.assertIn("not available over MCP", err["message"])
        self.assertIn("human", err["data"]["reason"])
        self.assertNotIn("result", r.json())

    def test_consolidate_revert_and_freeze_are_refused(self):
        async def must_not_run(*a, **k):
            raise AssertionError("withheld tool reached the store through MCP")

        with patch.object(server.consolidate_agent, "run_cycle", must_not_run), \
                patch.object(server.store, "revert", must_not_run), \
                patch.object(server.store, "freeze", must_not_run), \
                patch.object(server.store, "add_feedback", must_not_run):
            for name, args in (("consolidate", {}), ("revert", {"memory_id": "mem_1"}),
                               ("freeze", {"memory_id": "mem_1", "reason": "agent wants it kept"})):
                err = self.call(name, args).json()["error"]
                self.assertEqual(err["code"], -32602, name)
                self.assertIn("not available over MCP", err["message"], name)

    def test_every_manifest_tool_is_either_served_or_withheld(self):
        # A tool added to the REST manifest must be classified here before it can be offered to agents.
        manifest = {t["name"] for t in server.mcp_manifest_tools()}
        self.assertEqual(manifest, set(server.MCP_TOOL_DISPATCH) | set(server.MCP_WITHHELD_TOOLS))

    def test_arguments_outside_the_schema_are_refused(self):
        # self_model_observe's REST body would accept lifecycle_state / user_state; the MCP schema does not.
        r = self.call("self_model_observe", {"engine": "manual", "observation_type": "x", "claim_text": "y",
                                             "evidence_memory_ids": ["m1"], "user_state": "confirmed",
                                             "lifecycle_state": "crystallized"})
        err = r.json()["error"]
        self.assertEqual(err["code"], -32602)
        self.assertIn("lifecycle_state", err["message"])
        self.assertIn("user_state", err["message"])
        err = self.call("retain", {"content": "x", "benchmark_fast_path": True}).json()["error"]
        self.assertIn("benchmark_fast_path", err["message"])

    # ── argument values are checked against the schema before dispatch ──

    def test_argument_values_are_validated(self):
        obs = {"engine": "manual", "observation_type": "x", "claim_text": "y"}
        cases = [
            ("recall", {"query": "q", "top_k": 51}, "top_k must be <= 50"),
            ("recall", {"query": "q", "top_k": 0}, "top_k must be >= 1"),
            ("recall", {"query": "q", "top_k": "5"}, "top_k must be of type integer"),
            ("recall", {"query": "q", "top_k": True}, "top_k must be of type integer"),
            ("recall", {"query": "q", "expand": "false"}, "expand must be of type boolean"),
            ("recall", {"query": ["q"]}, "query must be of type string"),
            ("reflect", {"topic": "t", "top_k": 1000}, "top_k must be <= 50"),
            ("context_packet", {"query": "q", "top_k": 99}, "top_k must be <= 50"),
            ("prefetch", {"top_k": -1}, "top_k must be >= 1"),
            ("retain", {"content": "x", "refs": "not-an-object"}, "refs must be of type object"),
            ("self_model_observe", {**obs, "engine": "astrology"}, "engine must be one of"),
            ("self_model_observe", {**obs, "evidence_memory_ids": ["m1", 2]}, "evidence_memory_ids[1] must be of type string"),
            ("self_model_observe", {**obs, "confidence": 2}, "confidence must be <= 1"),
            ("self_model_observe", {**obs, "sensitivity": "public"}, "sensitivity must be one of"),
            ("decision_trace", {"query": "q", "answer": "a", "status": "confirmed"}, "status must be one of"),
        ]
        for name, args, expected in cases:
            err = self.call(name, args).json()["error"]
            self.assertEqual(err["code"], -32602, (name, args))
            self.assertIn(expected, err["message"], (name, args))

    def test_valid_values_still_dispatch(self):
        async def fake_recall(query, **kwargs):
            return {"results": []}

        with patch.object(server, "recall_memories", fake_recall):
            result = self.call("recall", {"query": "q", "top_k": 50, "expand": False}).json()["result"]
        self.assertNotIn("isError", result)

    # ── path tools: default-deny, then confined to MCP_INGEST_ROOTS ──

    def _roots(self):
        base = tempfile.TemporaryDirectory()
        self.addCleanup(base.cleanup)
        root, outside = Path(base.name, "allowed"), Path(base.name, "outside")
        root.mkdir()
        outside.mkdir()
        (root / "notes.md").write_text("# notes\nfine to ingest\n")
        (root / "chat.jsonl").write_text("{}\n")
        (outside / "secret.md").write_text("SECRET\n")
        p = patch.object(server, "MCP_INGEST_ROOTS", (os.path.realpath(root),))
        p.start()
        self.addCleanup(p.stop)
        return root, outside

    def _fake_ingest(self):
        calls = []

        def result(path):
            return IngestResult(source_file=path, chunks_total=1, chunks_ingested=1, chunks_skipped=0)

        async def ingest_file(filepath, **kwargs):
            calls.append("file")
            return result(filepath)

        async def ingest_jsonl(filepath, **kwargs):
            calls.append("jsonl")
            return result(filepath)

        async def ingest_directory(dirpath, **kwargs):
            calls.append("directory")
            return DirectoryIngestResult(directory=dirpath, files_scanned=1, files_ingested=1, files_skipped=0,
                                         total_chunks=1, total_memories=1)

        for name, fn in (("ingest_file", ingest_file), ("ingest_jsonl", ingest_jsonl),
                         ("ingest_directory", ingest_directory)):
            p = patch.object(server.doc_engine, name, fn)
            p.start()
            self.addCleanup(p.stop)
        return calls

    def test_path_tools_are_withheld_when_roots_are_unset(self):
        self.assertFalse(set(self.tools_list()) & PATH_TOOLS)
        for name, args in (("ingest_file", {"filepath": "/etc/hostname"}), ("ingest_directory", {"directory": "/etc"}),
                           ("ingest_jsonl", {"filepath": "/etc/hostname"}), ("compile_wiki", {})):
            err = self.call(name, args).json()["error"]
            self.assertEqual(err["code"], -32602, name)
            self.assertIn("not available over MCP", err["message"], name)
            self.assertIn("MCP_INGEST_ROOTS", err["data"]["reason"], name)

    def test_path_tools_listed_when_roots_are_set(self):
        self._roots()
        tools = self.tools_list()
        self.assertEqual(set(tools), DEFAULT_SERVED | PATH_TOOLS)
        self.assertNotIn("output_dir", tools["compile_wiki"]["inputSchema"]["properties"])

    def test_in_root_paths_work(self):
        root, _ = self._roots()
        calls = self._fake_ingest()
        for name, args in (("ingest_file", {"filepath": str(root / "notes.md"), "skip_duplicates": False}),
                           ("ingest_jsonl", {"filepath": str(root / "chat.jsonl")}),
                           ("ingest_directory", {"directory": str(root), "recursive": True})):
            self.assertNotIn("isError", self.call(name, args).json()["result"], name)
        self.assertEqual(calls, ["file", "jsonl", "directory"])

    def test_out_of_root_and_dotdot_paths_are_refused(self):
        root, outside = self._roots()
        calls = self._fake_ingest()
        for name, args in (("ingest_file", {"filepath": str(outside / "secret.md")}),
                           ("ingest_file", {"filepath": str(root / ".." / "outside" / "secret.md")}),
                           ("ingest_jsonl", {"filepath": "/etc/hostname"}),
                           ("ingest_directory", {"directory": str(outside)}),
                           ("ingest_directory", {"directory": str(root) + "-sibling"})):
            err = self.call(name, args).json()["error"]
            self.assertEqual(err["code"], -32602, (name, args))
            self.assertIn("outside MCP_INGEST_ROOTS", err["message"], (name, args))
        self.assertEqual(calls, [])

    def test_symlink_escapes_are_refused(self):
        root, outside = self._roots()
        calls = self._fake_ingest()
        (root / "link.md").symlink_to(outside / "secret.md")
        (root / "linkdir").symlink_to(outside, target_is_directory=True)
        for name, args in (("ingest_file", {"filepath": str(root / "link.md")}),
                           ("ingest_directory", {"directory": str(root / "linkdir")})):
            err = self.call(name, args).json()["error"]
            self.assertEqual(err["code"], -32602, name)
            self.assertIn("outside MCP_INGEST_ROOTS", err["message"], name)
        # A directory inside the roots that holds a symlink to a file outside them is refused as a whole.
        (root / "linkdir").unlink()
        err = self.call("ingest_directory", {"directory": str(root)}).json()["error"]
        self.assertIn("resolves outside MCP_INGEST_ROOTS", err["message"])
        self.assertIn("link.md", err["message"])
        self.assertEqual(calls, [])

    def test_skip_duplicates_string_is_refused_not_truthy(self):
        root, _ = self._roots()
        calls = self._fake_ingest()
        err = self.call("ingest_file", {"filepath": str(root / "notes.md"), "skip_duplicates": "false"}).json()["error"]
        self.assertIn("skip_duplicates must be of type boolean", err["message"])
        self.assertEqual(calls, [])

    def test_compile_wiki_cannot_repoint_the_shared_output_dir(self):
        self._roots()
        before = server.wiki_compiler.output_dir
        with tempfile.TemporaryDirectory() as elsewhere:
            err = self.call("compile_wiki", {"output_dir": elsewhere}).json()["error"]
        self.assertEqual(err["code"], -32602)
        self.assertIn("not accepted over MCP", err["message"])
        self.assertEqual(server.wiki_compiler.output_dir, before)

    def test_missing_required_argument_and_unknown_tool(self):
        self.assertIn("query", self.call("recall", {}).json()["error"]["message"])
        self.assertIn("unknown tool", self.call("drop_tables", {}).json()["error"]["message"])
        self.assertIn("must be an object", self.call("recall", ["q"]).json()["error"]["message"])

    # ── 2026-07-28 ──

    def test_modern_discover_list_and_call(self):
        h = {"mcp-protocol-version": MODERN}
        d = self.rpc({"jsonrpc": "2.0", "id": "d", "method": "server/discover", "params": {"_meta": META}},
                     {**h, "mcp-method": "server/discover"})
        self.assertEqual(d.status_code, 200)
        self.assertEqual(d.json()["result"]["supportedVersions"], [MODERN])
        tl = self.rpc({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {"_meta": META}},
                      {**h, "mcp-method": "tools/list"}).json()["result"]
        self.assertEqual(tl["resultType"], "complete")
        self.assertFalse({t["name"] for t in tl["tools"]} & WITHHELD)
        encoded = "=?base64?" + base64.b64encode(b"ingest_status").decode() + "?="
        c = self.rpc({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                      "params": {"name": "ingest_status", "arguments": {}, "_meta": META}},
                     {**h, "mcp-method": "tools/call", "mcp-name": encoded}).json()["result"]
        self.assertEqual(c["resultType"], "complete")
        self.assertEqual(c["_meta"]["io.modelcontextprotocol/serverInfo"]["name"], "memibrium")
        self.assertEqual(c["structuredContent"]["taxonomy_categories"], 30)

    def test_modern_header_rules(self):
        h = {"mcp-protocol-version": MODERN}
        # initialize is not part of 2026-07-28
        r = self.rpc({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"_meta": META}},
                     {**h, "mcp-method": "initialize"})
        self.assertEqual(r.status_code, 404)
        # missing _meta
        r = self.rpc({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, {**h, "mcp-method": "tools/list"})
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (400, -32602))
        # Mcp-Method mismatch
        r = self.rpc({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {"_meta": META}},
                     {**h, "mcp-method": "tools/call"})
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (400, -32020))
        # Mcp-Name mismatch
        r = self.rpc({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                      "params": {"name": "recall", "arguments": {"query": "q"}, "_meta": META}},
                     {**h, "mcp-method": "tools/call", "mcp-name": "dashboard"})
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (400, -32020))
        # a withheld tool is refused in the modern era too
        r = self.rpc({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                      "params": {"name": "confirm", "arguments": {"memory_id": "m"}, "_meta": META}},
                     {**h, "mcp-method": "tools/call", "mcp-name": "confirm"})
        self.assertIn("not available over MCP", r.json()["error"]["message"])

    # ── transport ──

    # ── review follow-ups: S1, S2, N1-N3, N7 ──

    def test_notification_shaped_confirm_executes_nothing(self):
        async def must_not_run(*a, **k):
            raise AssertionError("a notification reached the store")

        with patch.object(server.store, "get_memory", must_not_run), \
                patch.object(server.store, "update_memory", must_not_run), \
                patch.object(server.store, "add_feedback", must_not_run):
            for name in ("confirm", "freeze", "recall"):
                r = self.rpc({"jsonrpc": "2.0", "method": "tools/call",
                              "params": {"name": name, "arguments": {"memory_id": "m", "query": "q"}}})
                self.assertEqual(r.status_code, 202, name)
                self.assertEqual(r.text, "", name)

    def test_withheld_name_variants_are_unknown_tools(self):
        async def must_not_run(*a, **k):
            raise AssertionError("a confirm variant reached the store")

        with patch.object(server.store, "get_memory", must_not_run), \
                patch.object(server.store, "update_memory", must_not_run):
            for name in ("Confirm", "CONFIRM", "confirm ", " confirm", "confirm\u0000", "mcp__memibrium__confirm",
                         "memibrium.confirm", "memibrium/confirm", "/mcp/confirm", "Freeze", "REVERT", "consolidate\n"):
                err = self.call(name, {"memory_id": "m"}).json()["error"]
                self.assertEqual(err["code"], -32602, repr(name))
                self.assertIn("unknown tool", err["message"], repr(name))
            for bad in (None, 1, ["confirm"], {"name": "confirm"}):
                err = self.call(bad, {"memory_id": "m"}).json()["error"]
                self.assertEqual(err["code"], -32602, repr(bad))

    def test_decision_trace_status_other_than_proposed_is_refused(self):
        for status in ("accepted", "rejected", "corrected", "superseded"):
            err = self.call("decision_trace", {"query": "q", "answer": "a", "status": status}).json()["error"]
            self.assertEqual(err["code"], -32602, status)
            self.assertIn("status must be one of proposed", err["message"], status)

    def test_nul_byte_paths_are_refused_not_500(self):
        root, _ = self._roots()
        calls = self._fake_ingest()
        for name, args in (("ingest_file", {"filepath": str(root / "a\x00b.md")}),
                           ("ingest_jsonl", {"filepath": "\x00"}),
                           ("ingest_directory", {"directory": str(root) + "\x00"})):
            r = self.call(name, args)
            self.assertEqual(r.status_code, 200, name)
            err = r.json()["error"]
            self.assertEqual(err["code"], -32602, name)
            self.assertIn("NUL byte", err["message"], name)
        self.assertEqual(calls, [])
        self.assertFalse(server._mcp_path_inside_roots("a\x00b"))

    def test_directory_scan_errors_are_refused_not_500(self):
        root, _ = self._roots()
        calls = self._fake_ingest()

        def boom(directory, recursive):
            raise PermissionError("scan denied")

        with patch.object(server, "_mcp_directory_escapes", boom):
            err = self.call("ingest_directory", {"directory": str(root)}).json()["error"]
        self.assertEqual(err["code"], -32602)
        self.assertIn("could not be scanned (PermissionError)", err["message"])
        self.assertEqual(calls, [])

    def test_nan_and_infinity_are_refused(self):
        for literal in ("NaN", "Infinity", "-Infinity"):
            body = ('{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"self_model_observe",'
                    '"arguments":{"engine":"manual","observation_type":"x","claim_text":"y","confidence":%s}}}' % literal)
            r = self.client.post("/mcp", content=body, headers={"content-type": "application/json"})
            self.assertEqual((r.status_code, r.json()["error"]["code"]), (400, -32700), literal)
        # The validator refuses them as well, should a non-finite number ever reach it.
        for value in (float("nan"), float("inf"), float("-inf")):
            self.assertIn("finite", server._mcp_schema_error({"type": "number", "minimum": 0, "maximum": 1}, value, "c"))

    def test_empty_origin_and_json_lookalike_media_types_are_refused(self):
        ping = '{"jsonrpc":"2.0","id":1,"method":"ping"}'
        r = self.client.post("/mcp", content=ping, headers={"content-type": "application/json", "origin": ""})
        self.assertEqual(r.status_code, 403)
        for ctype in ("application/json-evil", "application/jsonp", "text/json", "application/json5"):
            r = self.client.post("/mcp", content=ping, headers={"content-type": ctype})
            self.assertEqual(r.status_code, 415, ctype)
        for ctype in ("application/json; charset=utf-8", "Application/JSON"):
            r = self.client.post("/mcp", content=ping, headers={"content-type": ctype})
            self.assertEqual(r.status_code, 200, ctype)

    def test_ingest_roots_are_stripped_and_relative_entries_ignored(self):
        with tempfile.TemporaryDirectory() as d:
            raw = os.pathsep.join([f"  {d}  ", "relative/notes", "", "   "])
            self.assertEqual(server._parse_mcp_ingest_roots(raw), (os.path.realpath(d),))
        self.assertEqual(server._parse_mcp_ingest_roots(""), ())

    def test_dispatch_failure_is_a_generic_internal_error(self):
        async def broken(*a, **k):
            raise RuntimeError("secret detail /etc/memibrium.key")

        with patch.object(server, "mcp_dispatch", broken):
            r = self.rpc({"jsonrpc": "2.0", "id": 7, "method": "tools/list"})
        self.assertEqual(r.status_code, 500)
        self.assertEqual(r.json(), {"jsonrpc": "2.0", "id": 7, "error": {"code": -32603, "message": "Internal error"}})

    def test_reviewed_rows_are_kept_by_the_upsert_sql(self):
        # S1: the ids are content hashes, so a re-submission hits ON CONFLICT; the guards must keep reviewed rows.
        captured = []

        class Conn:
            async def execute(self, sql, *args):
                captured.append(sql)

        class Acquire:
            async def __aenter__(self):
                return Conn()

            async def __aexit__(self, *exc):
                return False

        class Pool:
            def acquire(self):
                return Acquire()

        import asyncio
        store = server.ColdStore.__new__(server.ColdStore)
        store.pool = Pool()
        asyncio.run(store.create_self_model_observation(
            {"engine": "manual", "observation_type": "x", "claim_text": "y", "evidence_memory_ids": ["m1"]}))
        asyncio.run(store.create_decision_trace({"query": "q", "answer": "a"}))
        obs_sql, trace_sql = captured
        kept = server.SELF_MODEL_REVIEW_KEPT_SQL
        for column in ("confidence", "evidence_memory_ids", "evidence_artifact_ids", "entity_ids",
                       "lifecycle_state", "user_state", "metadata"):
            self.assertIn(f"{column} = CASE WHEN {kept} THEN self_model_observations.{column}", obs_sql, column)
        for column in ("status", "outcome_signal", "metadata"):
            self.assertIn(f"{column} = CASE WHEN {server.DECISION_TRACE_REVIEW_KEPT_SQL} THEN decision_traces.{column}",
                          trace_sql, column)

    def test_get_and_delete_are_405(self):
        for method in ("GET", "DELETE"):
            r = self.client.request(method, "/mcp")
            self.assertEqual(r.status_code, 405, method)
            self.assertEqual(r.headers.get("allow"), "POST", method)

    def test_transport_refusals(self):
        self.assertEqual(self.rpc({"jsonrpc": "2.0", "id": 1, "method": "ping"},
                                  {"origin": "http://evil.example"}).status_code, 403)
        self.assertEqual(self.client.post("/mcp", content="{}", headers={"content-type": "text/plain"}).status_code, 415)
        bad = self.client.post("/mcp", content="{not json", headers={"content-type": "application/json"})
        self.assertEqual((bad.status_code, bad.json()["error"]["code"]), (400, -32700))
        self.assertEqual(self.rpc([{"jsonrpc": "2.0", "id": 1, "method": "ping"}]).status_code, 400)
        r = self.rpc({"jsonrpc": "2.0", "id": 1, "method": "ping"}, {"mcp-protocol-version": "1999-01-01"})
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (400, -32022))
        self.assertEqual(self.rpc({"jsonrpc": "2.0", "id": 1, "method": "ping"}).json()["result"], {})
        self.assertEqual(self.rpc({"jsonrpc": "2.0", "id": 9, "method": "resources/list"}).json()["error"]["code"], -32601)

    def test_rest_manifest_is_unchanged(self):
        r = self.client.get("/mcp/tools")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()["tools"]), 18)
        self.assertIn("confirm", {t["name"] for t in r.json()["tools"]})


if __name__ == "__main__":
    unittest.main(verbosity=2)
