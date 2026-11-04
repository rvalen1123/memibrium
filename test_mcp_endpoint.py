#!/usr/bin/env python3
"""POST /mcp: the MCP protocol endpoint the shipped plugin connects to (MED-254).

Runs against the Starlette app in-process with no database, server, LLM or network: the
TestClient is not entered as a context manager, so the startup hook (schema migration,
embedding probe) never runs. Tool calls that would touch the database use patched handlers.
"""

import base64
import json
import unittest
from unittest.mock import patch

from starlette.testclient import TestClient

import server

LEGACY = "2025-06-18"
MODERN = "2026-07-28"
META = {
    "io.modelcontextprotocol/protocolVersion": MODERN,
    "io.modelcontextprotocol/clientInfo": {"name": "t", "version": "1"},
    "io.modelcontextprotocol/clientCapabilities": {},
}
WITHHELD = {"confirm", "consolidate", "revert"}


class McpEndpointTest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(server.app)  # no `with`: startup (DB, embedder) does not run

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
        self.assertEqual(len(names), 15)
        self.assertIn("recall", names)
        self.assertIn("retain", names)

        # The names and inputSchemas are the REST manifest's own.
        manifest = {t["name"]: t for t in server.mcp_manifest_tools()}
        for tool in tools:
            self.assertEqual(tool["inputSchema"], manifest[tool["name"]]["inputSchema"], tool["name"])
            self.assertEqual(tool["description"], manifest[tool["name"]]["description"], tool["name"])

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
        r = self.call("ingest_file", {"filepath": "/nonexistent/memibrium-mcp-test.md"})
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
        self.assertIn("pool not initialized", result["content"][0]["text"])

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

    def test_consolidate_and_revert_are_refused(self):
        async def must_not_run(*a, **k):
            raise AssertionError("withheld tool reached the store through MCP")

        with patch.object(server.consolidate_agent, "run_cycle", must_not_run), \
                patch.object(server.store, "revert", must_not_run):
            for name, args in (("consolidate", {}), ("revert", {"memory_id": "mem_1"})):
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
