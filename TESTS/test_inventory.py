#!/usr/bin/env python3
"""Smoke tests for the read-only environment inventory."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "scripts" / "inventory.py"


class InventorySmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        result = subprocess.run(
            [sys.executable, str(INVENTORY)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if result.returncode != 0:
            raise AssertionError(
                f"inventory.py exited {result.returncode}: {result.stderr}"
            )
        try:
            cls.report: dict[str, Any] = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise AssertionError("inventory.py did not emit valid JSON") from exc

    def test_report_has_environment_scope_and_timestamp(self) -> None:
        report = self.report
        self.assertEqual(report.get("schema_version"), "1.1")
        self.assertEqual(report.get("scope"), "current_process_environment_only")
        timestamp = datetime.fromisoformat(report["generated_at"])
        self.assertIsNotNone(timestamp.tzinfo)

        environment = report["environment"]
        for key in (
            "os",
            "os_release",
            "architecture",
            "python_executable",
            "python_version",
        ):
            self.assertIsInstance(environment.get(key), str)
            self.assertTrue(environment[key])

    def test_command_entries_are_consistent(self) -> None:
        commands = self.report["commands"]
        self.assertIsInstance(commands, dict)
        self.assertIn("python", commands)
        for security_command in ("gitleaks", "pip-audit", "trivy", "age", "restic"):
            self.assertIn(security_command, commands)
        self.assertIn("pip_audit", self.report["python_modules"])

        for name, item in commands.items():
            with self.subTest(command=name):
                self.assertIsInstance(item["installed"], bool)
                self.assertTrue(
                    item["path"] is None or isinstance(item["path"], str)
                )
                self.assertTrue(
                    item["version_or_help"] is None
                    or isinstance(item["version_or_help"], str)
                )
                self.assertEqual(item["installed"], item["path"] is not None)

    def test_module_and_node_package_entries_are_well_formed(self) -> None:
        modules = self.report["python_modules"]
        packages = self.report["node_packages"]
        self.assertIsInstance(modules, dict)
        self.assertIsInstance(packages, dict)

        for name, item in modules.items():
            with self.subTest(python_module=name):
                self.assertIsInstance(item["available"], bool)

        for name, item in packages.items():
            with self.subTest(node_package=name):
                self.assertIsInstance(item["available"], bool)
                self.assertTrue(
                    item["resolved_path"] is None
                    or isinstance(item["resolved_path"], str)
                )
                self.assertEqual(
                    item["available"], item["resolved_path"] is not None
                )

    def test_inventory_is_non_mutating_offline_and_reports_command_probes(self) -> None:
        safety = self.report["safety"]
        self.assertIs(safety["read_only"], True)
        self.assertIsInstance(safety["commands_executed"], bool)
        self.assertIsInstance(safety["command_probe_count"], int)
        self.assertEqual(safety["commands_executed"], safety["command_probe_count"] > 0)
        self.assertIs(safety["trusted_path_required"], True)
        self.assertIs(safety["network_access"], False)
        self.assertIs(safety["installation_attempted"], False)
        self.assertIn("not sandboxed", safety["note"])


if __name__ == "__main__":
    unittest.main()
