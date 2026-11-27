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
            {"id": "gitleaks", "name": "Gitleaks", "record": "TOOLS/gitleaks.md"},
            {"id": "pip-audit", "name": "pip-audit", "record": "TOOLS/pip-audit.md"},
            {"id": "openssh-client", "name": "OpenSSH client", "record": "TOOLS/openssh-client.md"},
        ]}
        self.report: dict[str, Any] = {
            "scope": "current_process_environment_only",
            "generated_at": "2026-11-27T00:00:00+00:00",
            "commands": {"git": {"installed": True}, "hummingbot": {"installed": False}, "gitleaks": {"installed": True}, "ssh": {"installed": True}},
            "python_modules": {"playwright": {"available": False}, "pip_audit": {"available": True}},
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

    def test_security_tool_probes_are_mapped(self) -> None:
        result = match_catalog(self.catalog, self.report)
        by_id = {item["id"]: item for item in result["tools"]}
        self.assertEqual(by_id["gitleaks"]["availability"], "available")
        self.assertEqual(by_id["pip-audit"]["availability"], "available")

    def test_openssh_client_is_matched_from_local_ssh_probe(self) -> None:
        result = match_catalog(self.catalog, self.report)
        by_id = {item["id"]: item for item in result["tools"]}
        self.assertEqual(by_id["openssh-client"]["availability"], "available")
        self.assertEqual(
            by_id["openssh-client"]["evidence"],
            [{"source": "commands", "key": "ssh", "available": True}],
        )

    def test_counts_and_scope_are_reported(self) -> None:
        result = match_catalog(self.catalog, self.report)
        self.assertEqual(result["catalog_match"]["counts"], {
            "available": 5, "missing": 1, "not_probed": 1,
        })
        self.assertEqual(result["inventory_scope"], "current_process_environment_only")


if __name__ == "__main__":
    unittest.main()
