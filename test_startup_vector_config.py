#!/usr/bin/env python3
"""Tests for vector runtime configuration helpers."""

import unittest

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


if __name__ == "__main__":
    unittest.main()
