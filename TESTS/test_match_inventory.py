#!/usr/bin/env python3
"""Tests for catalog-to-inventory matching."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from typing import Any

from match_inventory import match_catalog


class MatchInventoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog: dict[str, Any] = {"tools": [
            {"id": "git", "name": "Git", "record": "TOOLS/git.md"},
            {"id": "playwright", "name": "Playwright", "record": "TOOLS/playwright.md"},
            {"id": "hummingbot", "name": "Hummingbot", "record": "TOOLS/hummingbot.md"},
            {"id": "future-tool", "name": "Future tool", "record": "TOOLS/future.md"},
        ]}
        self.report: dict[str, Any] = {
            "scope": "current_process_environment_only",
            "generated_at": "2026-11-27T00:00:00+00:00",
            "commands": {"git": {"installed": True}, "hummingbot": {"installed": False}},
            "python_modules": {"playwright": {"available": False}},
            "node_packages": {"playwright": {"available": True}},
        }

    def test_matches_detected_tool(self) -> None:
        result = match_catalog(self.catalog, self.report)
        self.assertEqual(result["tools"][0]["availability"], "available")

    def test_alternative_probes_are_or_conditions(self) -> None:
        result = match_catalog(self.catalog, self.report)
        self.assertEqual(result["tools"][1]["availability"], "available")
        self.assertEqual(len(result["tools"][1]["evidence"]), 2)

    def test_missing_requires_known_probe(self) -> None:
        result = match_catalog(self.catalog, self.report)
        self.assertEqual(result["tools"][2]["availability"], "missing")

    def test_unconfigured_probe_is_not_probed_not_missing(self) -> None:
        result = match_catalog(self.catalog, self.report)
        self.assertEqual(result["tools"][3]["availability"], "not_probed")

    def test_counts_and_scope_are_reported(self) -> None:
        result = match_catalog(self.catalog, self.report)
        self.assertEqual(result["catalog_match"]["counts"], {
            "available": 2, "missing": 1, "not_probed": 1,
        })
        self.assertEqual(result["inventory_scope"], "current_process_environment_only")


if __name__ == "__main__":
    unittest.main()
