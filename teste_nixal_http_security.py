from __future__ import annotations

import unittest

from nixal_http_security import (
    DEFAULT_BROWSER_ORIGINS,
    cors_response_origin,
    normalize_origin,
    origin_is_allowed,
    parse_allowed_origins,
)


class TestNyxalHttpSecurity(unittest.TestCase):
    def test_default_origins_are_loopback_only(self) -> None:
        self.assertIn("http://127.0.0.1:3000", DEFAULT_BROWSER_ORIGINS)
        self.assertIn("http://localhost:8010", DEFAULT_BROWSER_ORIGINS)
        self.assertFalse(origin_is_allowed("https://attacker.example", parse_allowed_origins()))

    def test_explicit_origins_are_added_as_exact_origins(self) -> None:
        allowed = parse_allowed_origins("https://nyxos.example.com, https://admin.example.com/")
        self.assertTrue(origin_is_allowed("https://nyxos.example.com", allowed))
        self.assertTrue(origin_is_allowed("https://admin.example.com", allowed))
        self.assertFalse(origin_is_allowed("https://evil-nyxos.example.com", allowed))

    def test_wildcard_and_opaque_origins_are_not_allowed(self) -> None:
        allowed = parse_allowed_origins("*")
        self.assertFalse(origin_is_allowed("https://attacker.example", allowed))
        self.assertFalse(origin_is_allowed("null", allowed))
        self.assertIsNone(cors_response_origin("https://attacker.example", allowed))

    def test_malformed_or_path_origins_are_rejected(self) -> None:
        allowed = parse_allowed_origins()
        self.assertIsNone(normalize_origin("https://example.com/path"))
        self.assertIsNone(normalize_origin("file://"))
        self.assertIsNone(normalize_origin("http://user:pass@example.com"))
        self.assertFalse(origin_is_allowed("not-an-origin", allowed))

    def test_loopback_origin_is_echoed_exactly_after_normalization(self) -> None:
        allowed = parse_allowed_origins()
        self.assertEqual(cors_response_origin("http://LOCALHOST:3000/", allowed), "http://localhost:3000")

    def test_non_browser_clients_without_origin_remain_supported(self) -> None:
        allowed = parse_allowed_origins()
        self.assertTrue(origin_is_allowed(None, allowed))
        self.assertTrue(origin_is_allowed("", allowed))
        self.assertIsNone(cors_response_origin(None, allowed))


if __name__ == "__main__":
    unittest.main(verbosity=2)
