#!/usr/bin/env python3
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from nixal_display_routes import resolve_display_file


class TestNyxalDisplayRoutes(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "index.html").write_text("<html>Nyxal Display</html>", encoding="utf-8")
        (self.root / "assets").mkdir()
        (self.root / "assets" / "app.js").write_text("console.log('Nyxal')", encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def test_display_root_resolves_to_index(self):
        self.assertEqual(resolve_display_file(self.root, "/display/"), self.root / "index.html")
        self.assertEqual(resolve_display_file(self.root, "/display"), self.root / "index.html")

    def test_assets_keep_their_real_path_and_ignore_query(self):
        self.assertEqual(
            resolve_display_file(self.root, "/display/assets/app.js?v=1"),
            self.root / "assets" / "app.js",
        )

    def test_spa_route_falls_back_to_index(self):
        self.assertEqual(resolve_display_file(self.root, "/display/settings/agent"), self.root / "index.html")

    def test_missing_asset_is_not_replaced_by_html(self):
        self.assertIsNone(resolve_display_file(self.root, "/display/assets/missing.js"))

    def test_traversal_and_other_prefix_are_rejected(self):
        self.assertIsNone(resolve_display_file(self.root, "/display/../../secret.txt"))
        self.assertIsNone(resolve_display_file(self.root, "/display-elsewhere/"))

    def test_encoded_traversal_is_rejected(self):
        self.assertIsNone(resolve_display_file(self.root, "/display/%2e%2e/%2e%2e/secret.txt"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
