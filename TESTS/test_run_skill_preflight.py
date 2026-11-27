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
        self.assertFalse(report["safety"]["network_access"])
        self.assertFalse(report["safety"]["installation_attempted"])

    def test_unknown_skill_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown Skill ID"):
            run_preflight(["not-a-real-skill"])


if __name__ == "__main__":
    unittest.main()
