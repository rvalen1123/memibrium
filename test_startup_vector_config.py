#!/usr/bin/env python3
"""Tests for vector runtime configuration helpers."""

import asyncio
import unittest
from unittest.mock import patch

import server


class StartupVectorConfigTests(unittest.TestCase):
    def test_embedding_dimension_match_passes(self):
        result = server.validate_embedding_dimension([0.1, 0.2, 0.3], expected_dim=3, allow_mismatch=False)
        self.assertTrue(result["matches"])
        self.assertEqual(result["actual_dim"], 3)

    def test_embedding_dimension_mismatch_fails_unless_allowed(self):
        with self.assertRaises(RuntimeError):
            server.validate_embedding_dimension([0.1, 0.2], expected_dim=3, allow_mismatch=False)

        allowed = server.validate_embedding_dimension([0.1, 0.2], expected_dim=3, allow_mismatch=True)
        self.assertFalse(allowed["matches"])
        self.assertTrue(allowed["allow_mismatch"])

    def test_require_ruvector_flag_is_tracked_on_store(self):
        store = server.ColdStore()
        self.assertEqual(store.require_ruvector, server.REQUIRE_RUVECTOR)
        self.assertEqual(store.vector_extension_requested, server.VECTOR_EXTENSION)
        self.assertFalse(store.vector_fallback_occurred)

    def test_vector_extension_identifier_is_restricted_to_known_safe_values(self):
        store = server.ColdStore()
        self.assertIn(store.vtype, {"vector", "ruvector"})
        self.assertIn(store.vector_ext, {"vector", "ruvector"})

    def test_verify_startup_embedding_dimension_updates_store_and_validates(self):
        asyncio.run(self._run_verify_startup_embedding_dimension_updates_store_and_validates())

    async def _run_verify_startup_embedding_dimension_updates_store_and_validates(self):
        test_vector = [0.1] * server.EMBEDDING_DIM

        class DummyStore:
            def __init__(self):
                self.embedding_dim_actual = None

        def embed_stub(*_args, **_kwargs):
            return test_vector

        original_store = server.store
        original_embedder = server.embedder
        try:
            class DummyEmbedder:
                _executor = None
                embed = staticmethod(embed_stub)

            server.store = DummyStore()
            server.embedder = DummyEmbedder()

            result = await server.verify_startup_embedding_dimension()

            self.assertEqual(server.store.embedding_dim_actual, len(test_vector))
            expected = server.validate_embedding_dimension(
                test_vector,
                expected_dim=server.EMBEDDING_DIM,
                allow_mismatch=server.ALLOW_EMBEDDING_DIM_MISMATCH,
            )
            self.assertEqual(result, expected)
        finally:
            server.store = original_store
            server.embedder = original_embedder

    def test_substrate_readiness_reports_local_embedding_and_leann_fallback(self):
        class DummyStore:
            embedding_dim_actual = 1536

        with patch.object(server, "store", DummyStore()), patch.object(
            server, "AZURE_EMBEDDING_ENDPOINT", ""
        ), patch.object(server, "AZURE_EMBEDDING_DEPLOYMENT", ""), patch.object(
            server, "AZURE_EMBEDDING_API_KEY", ""
        ), patch.object(server, "EMBED_BASE", "http://ollama:11434/v1"), patch.object(
            server, "EMBED_MODEL", "nomic-embed-text"
        ), patch.object(server, "USE_LEANN", False), patch.object(server, "leann_tier", None):
            readiness = server._substrate_readiness()

        self.assertEqual(readiness["schema"], "memibrium.substrate_readiness.v1")
        self.assertEqual(readiness["embedding"]["provider"], "ollama_openai_compatible")
        self.assertEqual(readiness["embedding"]["model"], "nomic-embed-text")
        self.assertFalse(readiness["embedding"]["azure_embedding_configured"])
        self.assertEqual(
            readiness["leann"]["cold_tier_status"],
            "candidates_leann_not_installed_or_disabled",
        )

    def test_substrate_readiness_reports_api_embedding_and_leann_ready(self):
        class DummyStore:
            embedding_dim_actual = 1536

        class DummyLeannTier:
            available = True
            searcher = object()

        with patch.object(server, "store", DummyStore()), patch.object(
            server, "AZURE_EMBEDDING_ENDPOINT", "https://example.openai.azure.com/"
        ), patch.object(server, "AZURE_EMBEDDING_DEPLOYMENT", "text-embedding-3-small"), patch.object(
            server, "AZURE_EMBEDDING_API_KEY", "[REDACTED]"
        ), patch.object(server, "USE_LEANN", True), patch.object(server, "leann_tier", DummyLeannTier()):
            readiness = server._substrate_readiness()

        self.assertEqual(readiness["embedding"]["provider"], "azure_openai")
        self.assertEqual(readiness["embedding"]["model"], "text-embedding-3-small")
        self.assertTrue(readiness["embedding"]["azure_embedding_configured"])
        self.assertEqual(readiness["embedding"]["endpoint_host"], "example.openai.azure.com")
        self.assertEqual(readiness["leann"]["cold_tier_status"], "leann_ready")


if __name__ == "__main__":
    unittest.main()
