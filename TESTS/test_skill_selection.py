from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "TESTS" / "fixtures" / "inter-skill-demo"
sys.path.insert(0, str(ROOT / "scripts"))
from skill_selection import validate_skill_selection  # noqa: E402


class SkillSelectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract: dict[str, Any] = json.loads(
            (FIXTURE / "workflow-contract.json").read_text(encoding="utf-8")
        )
        cls.selection: dict[str, Any] = json.loads(
            (FIXTURE / "skill-selection.json").read_text(encoding="utf-8")
        )
        cls.skill_map = json.loads(
            (ROOT / "CATALOG" / "skill-tools.json").read_text(encoding="utf-8")
        )

    def validate(self, selection: dict[str, Any] | None = None):
        return validate_skill_selection(selection or self.selection, self.contract, self.skill_map)

    def test_valid_selection_passes(self) -> None:
        self.assertEqual(self.validate()["status"], "passed")

    def test_unknown_skill_is_rejected(self) -> None:
        bad = json.loads(json.dumps(self.selection))
        bad["selected_skills"][0]["skill_id"] = "unknown-skill"
        self.assertIn("unknown_skill:unknown-skill", self.validate(bad)["errors"])

    def test_missing_stage_is_rejected(self) -> None:
        bad = json.loads(json.dumps(self.selection))
        bad["selected_skills"].pop()
        self.assertIn("stage_order_or_membership_mismatch", self.validate(bad)["errors"])

    def test_wrong_order_is_rejected(self) -> None:
        bad = json.loads(json.dumps(self.selection))
        bad["selected_skills"][0], bad["selected_skills"][1] = (
            bad["selected_skills"][1], bad["selected_skills"][0]
        )
        self.assertIn("stage_order_or_membership_mismatch", self.validate(bad)["errors"])

    def test_missing_stage_rationale_is_rejected(self) -> None:
        bad = json.loads(json.dumps(self.selection))
        bad["selected_skills"][1]["rationale"] = ""
        self.assertIn("stage_1_missing_rationale", self.validate(bad)["errors"])

    def test_forward_or_unknown_dependency_is_rejected(self) -> None:
        bad = json.loads(json.dumps(self.selection))
        bad["selected_skills"][0]["depends_on"] = ["code-audit"]
        self.assertIn("stage_0_dependency_not_prior:code-audit", self.validate(bad)["errors"])

    def test_contract_skill_substitution_is_rejected(self) -> None:
        bad = json.loads(json.dumps(self.selection))
        bad["selected_skills"][0]["skill_id"] = "code-audit"
        self.assertIn("contract_skill_mismatch:crypto-security", self.validate(bad)["errors"])

    def test_workflow_mismatch_is_rejected(self) -> None:
        bad = json.loads(json.dumps(self.selection))
        bad["workflow_id"] = "different-workflow"
        self.assertIn("workflow_id_mismatch", self.validate(bad)["errors"])


if __name__ == "__main__":
    unittest.main()
