"""End-to-end tests for the one-command Skill preflight."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from run_skill_preflight import run_preflight


class RunSkillPreflightTests(unittest.TestCase):
    def test_selected_security_skill_returns_full_evidence_bundle(self) -> None:
        report = run_preflight(["crypto-security"])
        self.assertEqual(report["scope"], "current_process_environment_only")
        self.assertEqual(report["summary"]["skills_total"], 1)
        self.assertEqual(report["skills"][0]["skill"], "crypto-security")
        self.assertIn(report["skills"][0]["readiness"], {"ready", "blocked", "unknown"})
        self.assertIn("commands", report["inventory"])
        self.assertIn("tools", report["tool_matches"])
        self.assertTrue(report["safety"]["read_only"])
        self.assertIsInstance(report["safety"]["commands_executed"], bool)
        self.assertIsInstance(report["safety"]["command_probe_count"], int)
        self.assertTrue(report["safety"]["trusted_path_required"])
        self.assertFalse(report["safety"]["network_access"])
        self.assertEqual(report["safety"]["external_command_network_access"], "not_controlled")
        self.assertEqual(report["safety"]["external_command_side_effects"], "not_controlled")
        self.assertFalse(report["safety"]["installation_attempted"])

    def test_four_skill_pilot_returns_evidence_for_each_direction(self) -> None:
        skill_ids = [
            "crypto-security",
            "devops-vps",
            "code-audit",
            "python-development",
        ]
        report = run_preflight(skill_ids)
        self.assertEqual(report["summary"]["skills_total"], len(skill_ids))
        self.assertEqual([item["skill"] for item in report["skills"]], skill_ids)
        for item in report["skills"]:
            self.assertIn(item["readiness"], {"ready", "blocked", "unknown"})
            self.assertIsInstance(item["required_groups"], list)
            self.assertIsInstance(item["recommended_tools"], list)

    def test_all_mapped_skills_complete_preflight(self) -> None:
        report = run_preflight()
        self.assertEqual(report["summary"]["skills_total"], 25)
        skill_ids = [item["skill"] for item in report["skills"]]
        self.assertEqual(len(skill_ids), len(set(skill_ids)))
        self.assertEqual(
            sum(report["summary"]["readiness"].values()),
            report["summary"]["skills_total"],
        )
        self.assertEqual(
            set(report["summary"]["readiness"]),
            {"ready", "blocked", "unknown"},
        )

    def test_unknown_skill_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown Skill ID"):
            run_preflight(["not-a-real-skill"])


if __name__ == "__main__":
    unittest.main()
