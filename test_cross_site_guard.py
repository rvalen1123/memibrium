#!/usr/bin/env python3
"""Cross-site request refusal on every state-changing route (MED-271).

A web page can POST to localhost:9999 with a `text/plain` body and no CORS preflight. `CrossSiteRequestGuard`
refuses every request a route would hand to a handler with a method other than GET, HEAD or OPTIONS when it
carries an Origin that is not allowlisted (403), a cross-site Sec-Fetch-Site (403) or a body that is not
declared application/json (415).

Runs in-process with no database, server, LLM or network: the TestClient is not entered as a context manager,
so the startup hook never runs. "The handler is never called" is shown on a copy of the real route table whose
endpoints are spies, behind the same middleware stack as `server.app`.
"""

import unittest
from unittest.mock import patch

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

import server

UNSAFE = ("POST", "PUT", "PATCH", "DELETE")
JSON = {"content-type": "application/json"}

# The routes that change state, or run work on the server's behalf, through a method other than GET.
# Pinned so that adding a POST/PUT/PATCH/DELETE route is a visible, reviewed change to this list.
EXPECTED_UNSAFE_ROUTES = {
    ("/mcp", "POST"),
    ("/mcp/test_embeddings", "POST"),
    ("/mcp/retain", "POST"),
    ("/mcp/retain/diagnostics", "POST"),
    ("/mcp/recall", "POST"),
    ("/mcp/reflect", "POST"),
    ("/mcp/confirm", "POST"),
    ("/mcp/freeze", "POST"),
    ("/mcp/revert", "POST"),
    ("/mcp/consolidate", "POST"),
    ("/mcp/prefetch", "POST"),
    ("/mcp/self_model/observe", "POST"),
    ("/mcp/self_model/observations", "POST"),
    ("/mcp/decision_trace", "POST"),
    ("/mcp/decision_traces", "POST"),
    ("/mcp/context_packet", "POST"),
    ("/mcp/ingest/file", "POST"),
    ("/mcp/ingest/directory", "POST"),
    ("/mcp/ingest/jsonl", "POST"),
    ("/mcp/ingest/compile", "POST"),
    ("/mcp/ingest/taxonomy", "POST"),
}


def unsafe_routes(app):
    """Every (path, method) of `app` whose method is not GET, HEAD or OPTIONS."""
    return {(r.path, m) for r in app.routes for m in (r.methods or ()) if m not in server.SAFE_METHODS}


class SpyApp:
    """The real route table with every endpoint replaced by a spy, behind the real middleware stack."""

    def __init__(self):
        self.calls = []

        def spy_for(path):
            async def spy(request):
                self.calls.append((request.method, path))
                return JSONResponse({"spy": path})
            return spy

        routes = [Route(r.path, spy_for(r.path), methods=sorted(r.methods or ())) for r in server.app.routes]
        self.client = TestClient(Starlette(routes=routes, middleware=server.app.user_middleware))


class CrossSiteGuardTest(unittest.TestCase):
    def setUp(self):
        allow = patch.object(server, "MEMIBRIUM_ALLOWED_ORIGINS", ())
        allow.start()
        self.addCleanup(allow.stop)
        self.spy = SpyApp()
        self.client = TestClient(server.app)  # no `with`: startup (DB, embedder) does not run

    def post(self, path, headers, body='{"memory_id": "m1"}'):
        return self.spy.client.post(path, content=body, headers=headers)

    # ── the route inventory ──

    def test_guard_is_installed_on_the_app(self):
        self.assertIn(server.CrossSiteRequestGuard, [m.cls for m in server.app.user_middleware])

    def test_unsafe_route_inventory_is_pinned(self):
        # A new POST/PUT/PATCH/DELETE route fails here until it is added above; the per-route tests below then
        # show the guard refuses it.
        self.assertEqual(unsafe_routes(server.app), EXPECTED_UNSAFE_ROUTES)

    def test_every_unsafe_route_refuses_text_plain_on_the_real_app(self):
        for path, method in sorted(unsafe_routes(server.app)):
            with self.subTest(route=f"{method} {path}"):
                r = self.client.request(method, path, content='{"x": 1}', headers={"content-type": "text/plain"})
                self.assertEqual(r.status_code, 415)

    def test_every_unsafe_route_refuses_a_foreign_origin_on_the_real_app(self):
        for path, method in sorted(unsafe_routes(server.app)):
            with self.subTest(route=f"{method} {path}"):
                r = self.client.request(method, path, content="{}",
                                        headers={**JSON, "origin": "http://evil.example"})
                self.assertEqual(r.status_code, 403)

    def test_every_unsafe_route_refuses_without_calling_its_handler_and_passes_json(self):
        for path, method in sorted(unsafe_routes(server.app)):
            with self.subTest(route=f"{method} {path}"):
                self.spy.calls.clear()
                for headers, status in (({"content-type": "text/plain"}, 415),
                                        ({**JSON, "origin": "https://evil.example"}, 403),
                                        ({**JSON, "origin": ""}, 403),
                                        ({**JSON, "sec-fetch-site": "cross-site"}, 403)):
                    r = self.spy.client.request(method, path, content="{}", headers=headers)
                    self.assertEqual(r.status_code, status, headers)
                self.assertEqual(self.spy.calls, [])
                r = self.spy.client.request(method, path, content="{}", headers=JSON)
                self.assertEqual(r.status_code, 200)
                self.assertEqual(self.spy.calls, [(method, path)])

    # ── the refusals, on POST /mcp/confirm ──

    def test_text_plain_to_confirm_is_415_and_the_handler_never_runs(self):
        r = self.post("/mcp/confirm", {"content-type": "text/plain"})
        self.assertEqual(r.status_code, 415)
        self.assertEqual(self.spy.calls, [])

    def test_missing_content_type_and_json_lookalikes_are_415(self):
        for ctype in (None, "", "application/x-www-form-urlencoded", "multipart/form-data; boundary=x",
                      "application/json-evil", "text/json", "application/jsonp"):
            headers = {} if ctype is None else {"content-type": ctype}
            self.assertEqual(self.post("/mcp/confirm", headers).status_code, 415, ctype)
        self.assertEqual(self.spy.calls, [])

    def test_foreign_origin_to_confirm_is_403_and_the_handler_never_runs(self):
        r = self.post("/mcp/confirm", {**JSON, "origin": "http://evil.example"})
        self.assertEqual(r.status_code, 403)
        self.assertEqual(self.spy.calls, [])

    def test_empty_origin_is_403(self):
        self.assertEqual(self.post("/mcp/confirm", {**JSON, "origin": ""}).status_code, 403)
        self.assertEqual(self.post("/mcp/confirm", {**JSON, "origin": "null"}).status_code, 403)
        self.assertEqual(self.spy.calls, [])

    def test_cross_site_fetch_metadata_without_origin_is_403(self):
        for site in ("cross-site", "same-site", "Cross-Site"):
            self.assertEqual(self.post("/mcp/confirm", {**JSON, "sec-fetch-site": site}).status_code, 403, site)
        for site in ("same-origin", "none"):
            self.assertEqual(self.post("/mcp/confirm", {**JSON, "sec-fetch-site": site}).status_code, 200, site)

    def test_normal_json_client_passes(self):
        for ctype in ("application/json", "application/json; charset=utf-8", "Application/JSON"):
            self.assertEqual(self.post("/mcp/confirm", {"content-type": ctype}).status_code, 200, ctype)
        self.assertEqual(len(self.spy.calls), 3)

    # ── the allowlist ──

    def test_allowlisted_origin_passes(self):
        with patch.object(server, "MEMIBRIUM_ALLOWED_ORIGINS", ("http://localhost:3000",)):
            for origin in ("http://localhost:3000", "HTTP://LOCALHOST:3000"):
                r = self.post("/mcp/confirm", {**JSON, "origin": origin, "sec-fetch-site": "cross-site"})
                self.assertEqual(r.status_code, 200, origin)
            for origin in ("http://localhost:3001", "https://localhost:3000", "http://localhost:3000.evil.example",
                           ""):
                self.assertEqual(self.post("/mcp/confirm", {**JSON, "origin": origin}).status_code, 403, origin)
            # An allowlisted origin still has to send JSON.
            r = self.post("/mcp/confirm", {"content-type": "text/plain", "origin": "http://localhost:3000"})
            self.assertEqual(r.status_code, 415)
        self.assertEqual(len(self.spy.calls), 2)

    def test_duplicate_origin_headers_are_refused(self):
        with patch.object(server, "MEMIBRIUM_ALLOWED_ORIGINS", ("http://localhost:3000",)):
            r = self.spy.client.post("/mcp/confirm", content="{}", headers=[
                ("content-type", "application/json"), ("origin", "http://localhost:3000"),
                ("origin", "http://evil.example")])
        self.assertEqual(r.status_code, 403)
        self.assertEqual(self.spy.calls, [])

    def test_the_mcp_endpoint_ignores_the_allowlist(self):
        ping = '{"jsonrpc":"2.0","id":1,"method":"ping"}'
        with patch.object(server, "MEMIBRIUM_ALLOWED_ORIGINS", ("http://localhost:3000",)):
            r = self.client.post("/mcp", content=ping, headers={**JSON, "origin": "http://localhost:3000"})
        self.assertEqual(r.status_code, 403)
        self.assertEqual(self.client.post("/mcp", content=ping, headers=JSON).status_code, 200)

    def test_allowlist_parsing(self):
        parse = server._parse_allowed_origins
        self.assertEqual(parse(""), ())
        self.assertEqual(parse(" http://localhost:3000/ , HTTPS://Console.Example "),
                         ("http://localhost:3000", "https://console.example"))
        with self.assertLogs(server.log, "WARNING"):
            self.assertEqual(parse("null,*,localhost:3000,ftp://x.example,http://x.example/path,http://u@x.example"),
                             ())

    # ── what the guard leaves alone ──

    def test_safe_methods_are_not_checked(self):
        for path, method in (("/health", "GET"), ("/health", "HEAD"), ("/mcp/tools", "GET")):
            r = self.client.request(method, path, headers={"origin": "http://evil.example",
                                                           "content-type": "text/plain"})
            self.assertEqual(r.status_code, 200, f"{method} {path}")
        r = self.spy.client.get("/mcp/ingest/taxonomy", headers={"origin": "http://evil.example"})
        self.assertEqual((r.status_code, self.spy.calls), (200, [("GET", "/mcp/ingest/taxonomy")]))

    def test_wrong_method_and_unknown_path_keep_the_router_answer(self):
        self.assertEqual(self.client.post("/health", content="x", headers={"content-type": "text/plain"}).status_code,
                         405)
        self.assertEqual(self.client.delete("/mcp").status_code, 405)
        self.assertEqual(self.client.post("/nope", content="x").status_code, 404)

    def test_no_cors_headers_are_served(self):
        r = self.client.get("/mcp/tools", headers={"origin": "http://evil.example"})
        self.assertNotIn("access-control-allow-origin", r.headers)
        r = self.client.options("/mcp/confirm", headers={"origin": "http://evil.example",
                                                          "access-control-request-method": "POST"})
        self.assertNotEqual(r.status_code, 200)
        self.assertNotIn("access-control-allow-origin", r.headers)


if __name__ == "__main__":
    unittest.main(verbosity=2)
