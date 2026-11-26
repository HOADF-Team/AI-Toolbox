"""Tests for Skill tool dependency preflight."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from check_skill_tools import check_skill


class CheckSkillToolsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.matches: dict[str, Any] = {"inventory_scope": "current_process_environment_only",
            "tools": [
                {"id": "python", "availability": "available"},
                {"id": "nodejs", "availability": "missing"},
                {"id": "playwright", "availability": "not_probed"},
                {"id": "ruff", "availability": "missing"},
            ]}

    def test_all_required_groups_satisfied(self) -> None:
        result = check_skill({"id": "python-development",
            "required_any": [["python"]], "recommended": ["ruff"]}, self.matches)
        self.assertEqual(result["readiness"], "ready")
        self.assertEqual(result["recommended_tools"][0]["availability"], "missing")

    def test_missing_all_alternatives_blocks(self) -> None:
        result = check_skill({"id": "web-development",
            "required_any": [["nodejs"]], "recommended": []}, self.matches)
        self.assertEqual(result["readiness"], "blocked")

    def test_unprobed_alternative_is_unknown_not_blocked(self) -> None:
        result = check_skill({"id": "web-development",
            "required_any": [["nodejs", "playwright"]], "recommended": []}, self.matches)
        self.assertEqual(result["readiness"], "unknown")

    def test_empty_prerequisites_are_ready(self) -> None:
        result = check_skill({"id": "writing", "required_any": [], "recommended": []}, self.matches)
        self.assertEqual(result["readiness"], "ready")


if __name__ == "__main__":
    unittest.main()
