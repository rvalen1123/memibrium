#!/usr/bin/env python3
"""Host-header allowlist on every route, GETs included: DNS-rebinding refusal (MED-276).

A page whose host name re-resolves to 127.0.0.1 is same-origin to the browser, so it could read GET replies.
Its requests still carry its own name in the Host header. `HostAllowlistGuard` answers any Host that is not
loopback or listed in MEMIBRIUM_ALLOWED_HOSTS with 421 Misdirected Request, before routing.

Runs in-process with no database, server, LLM or network (the TestClient is not entered, so startup never
runs). Handlers are spies behind the real middleware stack where "never called" matters.
"""

import asyncio
import unittest
from unittest.mock import patch

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

import server
from auth_test_support import AUTH, install_test_token

JSON = {"content-type": "application/json"}
LOOPBACK_HOSTS = ("localhost", "localhost:9999", "LOCALHOST:9999", "localhost.", "127.0.0.1", "127.0.0.1:9999",
                  "[::1]", "[::1]:9999", "[0:0:0:0:0:0:0:1]:9999")


class HostAllowlistTest(unittest.TestCase):
    def setUp(self):
        for name, value in (("MEMIBRIUM_ALLOWED_HOSTS", server.DEFAULT_ALLOWED_HOSTS),
                            ("MEMIBRIUM_ALLOWED_ORIGINS", ())):
            p = patch.object(server, name, value)
            p.start()
            self.addCleanup(p.stop)
        install_test_token(self)  # MED-234: these tests are not about authentication
        self.calls = []

        async def spy(request):
            self.calls.append((request.method, request.url.path))
            return JSONResponse({"ok": True})

        spy_app = Starlette(routes=[Route("/mcp/graph", spy, methods=["GET"]),
                                    Route("/mcp/confirm", spy, methods=["POST"])],
                            middleware=server.app.user_middleware)
        self.spy = TestClient(spy_app, base_url="http://localhost:9999", headers=AUTH)
        self.client = TestClient(server.app, base_url="http://localhost:9999", headers=AUTH)

    def get(self, host, path="/mcp/graph"):
        return self.spy.get(path, headers={"host": host})

    def post(self, host, path="/mcp/confirm"):
        return self.spy.post(path, content="{}", headers={**JSON, "host": host})

    def test_guard_is_installed_outermost(self):
        self.assertEqual([m.cls for m in server.app.user_middleware],
                         [server.HostAllowlistGuard, server.BearerAuthGuard, server.CrossSiteRequestGuard])

    def test_foreign_host_is_refused_on_get_and_post_without_calling_the_handler(self):
        for host in ("evil.example", "evil.example:9999", "attacker.localhost.evil.example", "127.0.0.1.evil.example",
                     "localhost.evil.example:9999", "192.168.1.5:9999", "[fe80::1]:9999"):
            with self.subTest(host=host):
                r = self.get(host)
                self.assertEqual(r.status_code, 421)
                self.assertIn("MEMIBRIUM_ALLOWED_HOSTS", r.json()["error"])
                self.assertEqual(self.post(host).status_code, 421)
        self.assertEqual(self.calls, [])

    def test_dns_rebinding_read_of_memory_content_is_refused_on_the_real_app(self):
        # A rebinding page sends no Origin on a same-origin GET, so only the Host check stands in its way.
        for path in ("/mcp/graph", "/mcp/wiki", "/mcp/self_model/observations", "/mcp/decision_traces",
                     "/mcp/dashboard", "/mcp/tools", "/health"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path, headers={"host": "rebind.evil.example:9999"}).status_code, 421)

    def test_refusal_comes_before_routing(self):
        self.assertEqual(self.client.get("/nope", headers={"host": "evil.example"}).status_code, 421)
        self.assertEqual(self.client.delete("/mcp", headers={"host": "evil.example"}).status_code, 421)
        self.assertEqual(self.client.get("/nope").status_code, 404)

    def test_loopback_forms_pass(self):
        for host in LOOPBACK_HOSTS:
            with self.subTest(host=host):
                self.assertEqual(self.get(host).status_code, 200)
                self.assertEqual(self.post(host).status_code, 200)
        self.assertEqual(len(self.calls), 2 * len(LOOPBACK_HOSTS))
        self.assertEqual(self.client.get("/health", headers={"host": "127.0.0.1:9999"}).status_code, 200)

    def test_ipv6_with_a_port_passes(self):
        self.assertEqual(self.get("[::1]:9999").status_code, 200)
        self.assertEqual(self.get("[::1]:1").status_code, 200)
        with patch.object(server, "MEMIBRIUM_ALLOWED_HOSTS", server._parse_allowed_hosts("[fd7a:115c:a1e0::1]")):
            self.assertEqual(self.get("[FD7A:115C:A1E0::1]:9999").status_code, 200)

    def test_configured_hosts_pass(self):
        hosts = server._parse_allowed_hosts("memibrium, box.tail1234.ts.net, 192.168.1.5")
        with patch.object(server, "MEMIBRIUM_ALLOWED_HOSTS", hosts):
            for host in ("memibrium:9999", "Box.Tail1234.ts.net", "box.tail1234.ts.net.:443", "192.168.1.5:9999",
                         "localhost:9999"):
                with self.subTest(host=host):
                    self.assertEqual(self.get(host).status_code, 200)
                    self.assertEqual(self.post(host).status_code, 200)
            self.assertEqual(self.get("evil.example").status_code, 421)
        self.assertEqual(self.get("memibrium:9999").status_code, 421)  # not a default

    def test_malformed_missing_and_repeated_host_are_refused(self):
        for host in ("", "::1", "[::1", "[::1]x", "localhost:abc", "localhost:0", "localhost:65536", "a:b:c",
                     "localhost:9999:1", "[evil.example]:9999", "user@localhost"):
            with self.subTest(host=host):
                self.assertEqual(self.get(host).status_code, 421)
        r = self.spy.get("/mcp/graph", headers=[("host", "localhost"), ("host", "evil.example")])
        self.assertEqual(r.status_code, 421)
        self.assertEqual(self.calls, [])

        sent = []

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message):
            sent.append(message)

        scope = {"type": "http", "http_version": "1.0", "method": "GET", "path": "/health", "raw_path": b"/health",
                 "query_string": b"", "headers": [], "scheme": "http", "server": None, "client": None,
                 "root_path": "", "app": server.app}
        asyncio.run(server.HostAllowlistGuard(server.app.router)(scope, receive, send))
        self.assertEqual(sent[0]["status"], 421)  # an HTTP/1.0 request with no Host at all

        # Non-ASCII digits in the port (headers decode as latin-1; '²'.isdigit() is True but int('²') raises):
        # refused with 421, never a 500.
        for raw in (b"localhost:\xb2", b"[::1]:\xb9\xb2", b"127.0.0.1:9\xb3"):
            with self.subTest(host=raw):
                sent.clear()
                asyncio.run(server.HostAllowlistGuard(server.app.router)(
                    {**scope, "http_version": "1.1", "headers": [(b"host", raw)]}, receive, send))
                self.assertEqual(sent[0]["status"], 421)

    def test_cross_site_guard_still_applies_behind_an_allowed_host(self):
        r = self.spy.post("/mcp/confirm", content="{}", headers={"content-type": "text/plain", "host": "localhost"})
        self.assertEqual(r.status_code, 415)
        r = self.spy.post("/mcp/confirm", content="{}", headers={**JSON, "host": "localhost",
                                                                  "origin": "http://localhost:9999"})
        self.assertEqual(r.status_code, 403)

    def test_allowed_hosts_parsing(self):
        parse = server._parse_allowed_hosts
        self.assertEqual(parse(""), ("localhost", "127.0.0.1", "::1"))
        self.assertEqual(parse(" Memibrium , [FE80::1], fe80::1, Bücher.example., localhost "),
                         ("localhost", "127.0.0.1", "::1", "memibrium", "fe80::1", "xn--bcher-kva.example"))
        for entry, reason in (("memibrium:9999", "port"), ("*.ts.net", "wildcard"), ("http://memibrium", "bare host"),
                              ("memibrium/path", "bare host"), ("admin:pw@memibrium", "bare host")):
            with self.subTest(entry=entry), self.assertLogs(server.log, "WARNING") as logs:
                self.assertEqual(parse(entry), server.DEFAULT_ALLOWED_HOSTS)
            self.assertIn(reason, logs.output[0])
            self.assertNotIn("memibrium", logs.output[0].split("MEMIBRIUM_ALLOWED_HOSTS", 1)[1].lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
