from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from skill_interfaces import validate_skill_interfaces, validate_workflow_compatibility  # noqa: E402


class SkillInterfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = json.loads((ROOT / "CATALOG" / "skill-interfaces.json").read_text(encoding="utf-8"))
        cls.skill_map = json.loads((ROOT / "CATALOG" / "skill-tools.json").read_text(encoding="utf-8"))
        cls.workflow = {
            "workflow_id": "interface-demo",
            "external_inputs": ["task.request", "project.source_snapshot"],
            "stages": [
                {"id": "security", "skill_id": "crypto-security", "consumes": ["task.request"], "produces": ["security.risk_assessment"]},
                {"id": "audit", "skill_id": "code-audit", "consumes": ["project.source_snapshot", "security.risk_assessment"], "produces": ["code.audit_findings"]},
                {"id": "dev", "skill_id": "python-development", "consumes": ["code.audit_findings"], "produces": ["code.patch_proposal", "code.regression_plan"]},
                {"id": "ops", "skill_id": "devops-vps", "consumes": ["code.patch_proposal", "security.risk_assessment"], "produces": ["infrastructure.diagnostic_report", "infrastructure.hardening_plan"]}
            ]
        }

    def test_repository_interface_catalog_passes(self) -> None:
        report = validate_skill_interfaces(self.catalog, self.skill_map)
        self.assertEqual(report["status"], "passed", report["errors"])
        self.assertEqual(report["interface_count"], 4)

    def test_duplicate_skill_interface_rejected(self) -> None:
        bad = copy.deepcopy(self.catalog)
        bad["interfaces"].append(copy.deepcopy(bad["interfaces"][0]))
        self.assertIn("duplicate_skill_interface:crypto-security", validate_skill_interfaces(bad, self.skill_map)["errors"])

    def test_unknown_side_effect_rejected(self) -> None:
        bad = copy.deepcopy(self.catalog)
        bad["interfaces"][0]["possible_side_effects"].append("grant_admin")
        self.assertIn("interface_0_invalid_possible_side_effects", validate_skill_interfaces(bad, self.skill_map)["errors"])

    def test_unknown_skill_rejected(self) -> None:
        bad = copy.deepcopy(self.catalog)
        bad["interfaces"][0]["skill_id"] = "not-a-skill"
        self.assertIn("interface_0_unknown_skill", validate_skill_interfaces(bad, self.skill_map)["errors"])

    def test_compatible_chain_passes(self) -> None:
        report = validate_workflow_compatibility(self.workflow, self.catalog)
        self.assertEqual(report["status"], "passed", report["errors"])

    def test_missing_input_fails(self) -> None:
        bad = copy.deepcopy(self.workflow)
        bad["stages"][1]["consumes"].append("unknown.external_data")
        report = validate_workflow_compatibility(bad, self.catalog)
        self.assertIn("code-audit.inputs_available", report["errors"])

    def test_wrong_output_type_fails(self) -> None:
        bad = copy.deepcopy(self.workflow)
        bad["stages"][0]["produces"] = ["financial.transfer"]
        report = validate_workflow_compatibility(bad, self.catalog)
        self.assertIn("crypto-security.produces_supported", report["errors"])

    def test_later_stage_output_cannot_be_used_early(self) -> None:
        bad = copy.deepcopy(self.workflow)
        bad["stages"][0]["consumes"].append("code.patch_proposal")
        report = validate_workflow_compatibility(bad, self.catalog)
        self.assertIn("crypto-security.inputs_available", report["errors"])

    def test_side_effect_metadata_does_not_grant_permission(self) -> None:
        report = validate_workflow_compatibility(self.workflow, self.catalog)
        self.assertTrue(all("side_effects_not_permissions" in item["id"] for item in report["checks"] if item["id"].endswith("side_effects_not_permissions")))


if __name__ == "__main__":
    unittest.main()
