from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "TESTS" / "fixtures" / "inter-skill-demo"
sys.path.insert(0, str(ROOT / "scripts"))
from check_skill_tools import check_skill  # noqa: E402


class InterSkillWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.scenario: dict[str, Any] = json.loads(
            (FIXTURE / "scenario.json").read_text(encoding="utf-8")
        )
        cls.mapping: dict[str, Any] = json.loads(
            (ROOT / "CATALOG" / "skill-tools.json").read_text(encoding="utf-8")
        )
        cls.skills = {item["id"]: item for item in cls.mapping["skills"]}

    def test_all_expected_skills_exist_in_the_catalog_map(self) -> None:
        expected = self.scenario["expected_skill_order"]
        self.assertEqual(len(expected), 4)
        self.assertEqual(len(set(expected)), 4)
        self.assertTrue(set(expected).issubset(self.skills))

    def test_preflight_checks_all_four_skills(self) -> None:
        # Synthetic inventory: Python is available; no other capability is asserted.
        matches = {
            "inventory_scope": "synthetic_test_data_only",
            "tools": [{"id": "python", "availability": "available"}],
        }
        results = [check_skill(self.skills[skill_id], matches)
                   for skill_id in self.scenario["expected_skill_order"]]
        self.assertEqual([item["skill"] for item in results],
                         self.scenario["expected_skill_order"])
        self.assertTrue(all(item["readiness"] == "ready" for item in results))
        # Readiness is prerequisite matching only, never proof of workflow execution.
        self.assertTrue(all("not proof" in item["note"] for item in results))

    def test_scenario_enforces_credential_and_trading_safety(self) -> None:
        safeguards = self.scenario["safeguards"]
        for control in (
            "never_print_secret_values",
            "never_execute_fixture_code",
            "never_connect_to_ssh_or_remote_hosts",
            "ssh_binary_does_not_prove_remote_access",
            "revoke_exposed_credential_before_host_isolation",
            "never_auto_close_open_positions",
            "production_changes_require_explicit_approval",
        ):
            with self.subTest(control=control):
                self.assertIs(safeguards[control], True)

        findings = self.scenario["findings"]
        self.assertEqual(findings[0]["id"], "exposed-credential")
        self.assertIn("revoke credential immediately", findings[0]["expected_action"])
        self.assertIn("simulation only", findings[0]["expected_action"])

    def test_fixture_contains_only_a_placeholder_and_no_live_secret(self) -> None:
        source = (FIXTURE / "demo_bot.py").read_text(encoding="utf-8")
        scenario_text = (FIXTURE / "scenario.json").read_text(encoding="utf-8")
        self.assertIn("EXCHANGE_API_KEY", source)
        self.assertNotIn("DEMO-ONLY-KEY-", source + scenario_text)
        self.assertNotIn("-----BEGIN", source + scenario_text)

    def test_fixture_is_marked_non_executable_and_remote_scope_is_unchecked(self) -> None:
        self.assertIs(self.scenario["synthetic_only"], True)
        evidence = self.scenario["expected_evidence"]
        self.assertEqual(evidence["remote_access"], "not_checked")
        self.assertEqual(evidence["production_system"], "not_accessed")
        self.assertEqual(evidence["credential_revocation"], "not_performed_simulation_only")
        source = (FIXTURE / "README.md").read_text(encoding="utf-8")
        self.assertIn("must never be deployed or executed", source)


if __name__ == "__main__":
    unittest.main()
