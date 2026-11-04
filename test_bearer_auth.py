#!/usr/bin/env python3
"""Inbound bearer-token authentication on every route except GET/HEAD /health (MED-234).

Two token sets: MEMIBRIUM_API_TOKENS for clients and agents, MEMIBRIUM_HUMAN_TOKENS for the human approval path.
The human-only governance routes (confirm, freeze, revert, consolidate) accept only human tokens. With no token
of the required kind configured a route answers 503: the server fails closed.

Runs in-process with no database, server, LLM or network (the TestClient is not entered, so startup never runs).
Handlers are spies behind the real middleware stack, so "the handler never ran" is checked directly.
"""

import unittest
from unittest.mock import patch

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

import server

API_TOKEN = "api-token-" + "a" * 32
HUMAN_TOKEN = "human-token-" + "h" * 32
JSON = {"content-type": "application/json"}


def encoded(token: str) -> bytes:
    return token.encode("utf-8")


def bearer(token: str) -> dict:
    return {"authorization": f"Bearer {token}"}


class BearerAuthTest(unittest.TestCase):
    def configure(self, api=(API_TOKEN,), human=(HUMAN_TOKEN,)):
        for name, tokens in (("MEMIBRIUM_API_TOKENS", api), ("MEMIBRIUM_HUMAN_TOKENS", human)):
            p = patch.object(server, name, tuple(encoded(t) for t in tokens))
            p.start()
            self.addCleanup(p.stop)

    def setUp(self):
        for name, value in (("MEMIBRIUM_ALLOWED_HOSTS", server.DEFAULT_ALLOWED_HOSTS),
                            ("MEMIBRIUM_ALLOWED_ORIGINS", ())):
            p = patch.object(server, name, value)
            p.start()
            self.addCleanup(p.stop)
        self.configure()
        self.calls = []

        async def spy(request):
            self.calls.append((request.method, request.url.path))
            return JSONResponse({"ok": True})

        paths = ["/health", "/mcp", "/mcp/recall", "/mcp/graph", *sorted(server.HUMAN_ONLY_PATHS)]
        routes = [Route(p, spy, methods=["GET"] if p in ("/health", "/mcp/graph") else ["POST"]) for p in paths]
        self.spy = TestClient(Starlette(routes=routes, middleware=server.app.user_middleware),
                              base_url="http://localhost:9999")

    def post(self, path, headers=None):
        return self.spy.post(path, content="{}", headers={**JSON, **(headers or {})})

    # ── installation ──

    def test_guard_sits_between_host_allowlist_and_cross_site_refusal(self):
        self.assertEqual([m.cls for m in server.app.user_middleware],
                         [server.HostAllowlistGuard, server.BearerAuthGuard, server.CrossSiteRequestGuard])

    def test_human_only_paths_match_the_routes_withheld_from_mcp(self):
        self.assertEqual({p.rsplit("/", 1)[1] for p in server.HUMAN_ONLY_PATHS}, set(server.MCP_WITHHELD_TOOLS))

    # ── missing, malformed, wrong ──

    def test_missing_token_is_401_with_challenge_and_handler_never_runs(self):
        for path in ("/mcp", "/mcp/recall", "/mcp/confirm"):
            with self.subTest(path=path):
                r = self.post(path)
                self.assertEqual(r.status_code, 401)
                self.assertEqual(r.headers["www-authenticate"], 'Bearer realm="memibrium"')
        r = self.spy.get("/mcp/graph")
        self.assertEqual(r.status_code, 401)
        self.assertEqual(self.calls, [])

    def test_malformed_authorization_is_401(self):
        for value in ("", "Bearer", "Bearer   ", f"Basic {API_TOKEN}", API_TOKEN, f"Token {API_TOKEN}"):
            with self.subTest(value=value):
                self.assertEqual(self.post("/mcp/recall", {"authorization": value}).status_code, 401)
        self.assertEqual(self.calls, [])

    def test_repeated_authorization_header_is_401(self):
        r = self.spy.post("/mcp/recall", content="{}",
                          headers=[("content-type", "application/json"),
                                   ("authorization", f"Bearer {API_TOKEN}"),
                                   ("authorization", f"Bearer {API_TOKEN}")])
        self.assertEqual(r.status_code, 401)
        self.assertEqual(self.calls, [])

    def test_wrong_token_is_403(self):
        for token in ("x" * 40, API_TOKEN + "x", API_TOKEN[:-1]):
            with self.subTest(token=token[:8]):
                self.assertEqual(self.post("/mcp/recall", bearer(token)).status_code, 403)
        self.assertEqual(self.calls, [])

    # ── accepted ──

    def test_api_token_reaches_agent_routes(self):
        self.assertEqual(self.post("/mcp", bearer(API_TOKEN)).status_code, 200)
        self.assertEqual(self.post("/mcp/recall", bearer(API_TOKEN)).status_code, 200)
        self.assertEqual(self.spy.get("/mcp/graph", headers=bearer(API_TOKEN)).status_code, 200)
        self.assertEqual(self.calls, [("POST", "/mcp"), ("POST", "/mcp/recall"), ("GET", "/mcp/graph")])

    def test_scheme_is_case_insensitive(self):
        self.assertEqual(self.post("/mcp/recall", {"authorization": f"bearer {API_TOKEN}"}).status_code, 200)

    def test_human_token_reaches_every_route(self):
        for path in ("/mcp/recall", *sorted(server.HUMAN_ONLY_PATHS)):
            with self.subTest(path=path):
                self.assertEqual(self.post(path, bearer(HUMAN_TOKEN)).status_code, 200)

    # ── the human-only governance routes ──

    def test_api_token_cannot_call_human_only_routes(self):
        for path in sorted(server.HUMAN_ONLY_PATHS):
            with self.subTest(path=path):
                r = self.post(path, bearer(API_TOKEN))
                self.assertEqual(r.status_code, 403)
                self.assertIn("human-only", r.json()["error"])
        self.assertEqual(self.calls, [])

    def test_trailing_slash_does_not_bypass_human_only(self):
        r = self.post("/mcp/confirm/", bearer(API_TOKEN))
        self.assertEqual(r.status_code, 403)
        self.assertEqual(self.calls, [])

    # ── fails closed ──

    def test_no_tokens_configured_is_503_everywhere_but_health(self):
        self.configure(api=(), human=())
        for path in ("/mcp", "/mcp/recall", "/mcp/confirm"):
            with self.subTest(path=path):
                r = self.post(path, bearer(API_TOKEN))
                self.assertEqual(r.status_code, 503)
                self.assertIn("not configured", r.json()["error"])
        self.assertEqual(self.spy.get("/health").status_code, 200)
        self.assertEqual(self.calls, [("GET", "/health")])

    def test_no_human_tokens_means_human_only_routes_are_503(self):
        self.configure(api=(API_TOKEN,), human=())
        self.assertEqual(self.post("/mcp/confirm", bearer(API_TOKEN)).status_code, 503)
        self.assertEqual(self.post("/mcp/recall", bearer(API_TOKEN)).status_code, 200)

    # ── /health and unknown paths ──

    def test_health_get_is_exempt_but_not_other_methods(self):
        self.assertEqual(self.spy.get("/health").status_code, 200)
        self.assertEqual(self.spy.head("/health").status_code, 200)
        self.assertEqual(self.spy.post("/health", content="{}", headers=JSON).status_code, 401)

    def test_unknown_path_without_token_is_401_not_404(self):
        self.assertEqual(self.spy.get("/mcp/does-not-exist").status_code, 401)
        self.assertEqual(self.spy.get("/mcp/does-not-exist", headers=bearer(API_TOKEN)).status_code, 404)

    # ── ordering against the other guards ──

    def test_host_refusal_comes_before_auth(self):
        r = self.post("/mcp/recall", {"host": "evil.example"})
        self.assertEqual(r.status_code, 421)

    def test_auth_comes_before_cross_site_refusal(self):
        self.assertEqual(self.post("/mcp/recall", {"origin": "https://evil.example"}).status_code, 401)
        r = self.post("/mcp/recall", {**bearer(API_TOKEN), "origin": "https://evil.example"})
        self.assertEqual(r.status_code, 403)
        self.assertIn("cross-origin", r.json()["error"])
        self.assertEqual(self.calls, [])

    # ── configuration parsing ──

    def test_parse_ignores_short_and_blank_entries_and_dedupes(self):
        with self.assertLogs(server.log, level="WARNING") as logs:
            parsed = server._parse_auth_tokens(f" {API_TOKEN} ,, tinytok , {API_TOKEN},{HUMAN_TOKEN}", "VAR")
        self.assertEqual(parsed, (encoded(API_TOKEN), encoded(HUMAN_TOKEN)))
        self.assertTrue(any("entry 3" in line for line in logs.output))
        self.assertFalse(any("tinytok" in line for line in logs.output), "the log must never echo a token entry")

    def test_comparison_is_constant_time_over_every_token(self):
        calls = []
        real = server.hmac.compare_digest

        def spy(a, b):
            calls.append(b)
            return real(a, b)

        with patch.object(server.hmac, "compare_digest", spy):
            server._token_matches(encoded(API_TOKEN), (encoded(API_TOKEN), encoded(HUMAN_TOKEN)))
        self.assertEqual(calls, [encoded(API_TOKEN), encoded(HUMAN_TOKEN)], "no early exit on the first match")

    def test_real_app_refuses_without_token(self):
        client = TestClient(server.app, base_url="http://localhost:9999")
        r = client.post("/mcp", content="{}", headers=JSON)
        self.assertEqual(r.status_code, 401)


if __name__ == "__main__":
    unittest.main()
