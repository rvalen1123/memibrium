"""Shared bearer-token setup for in-process tests that exercise other guards (MED-234).

Tests of the host allowlist, cross-site refusal and the MCP endpoint are not about authentication, so they run
with one configured human token (accepted on every route) and send it on every request. test_bearer_auth.py
covers the authentication itself.
"""

from unittest.mock import patch

import server

TEST_TOKEN = "memibrium-test-token-" + "0" * 24  # 45 characters, above MIN_AUTH_TOKEN_CHARS
AUTH = {"authorization": f"Bearer {TEST_TOKEN}"}


def install_test_token(testcase) -> None:
    """Configure TEST_TOKEN as the only (human) token for the duration of `testcase`."""
    for name, value in (("MEMIBRIUM_API_TOKENS", ()), ("MEMIBRIUM_HUMAN_TOKENS", (TEST_TOKEN.encode("utf-8"),))):
        p = patch.object(server, name, value)
        p.start()
        testcase.addCleanup(p.stop)
