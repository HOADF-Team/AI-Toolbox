from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "TESTS" / "fixtures" / "inter-skill-demo"
sys.path.insert(0, str(ROOT / "scripts"))
from check_skill_tools import check_skill  # noqa: E402
from validate_inter_skill_workflow import validate  # noqa: E402


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
        cls.handoffs = [
            json.loads((FIXTURE / "handoffs" / f"{stage}.json").read_text(encoding="utf-8"))
            for stage in cls.scenario["expected_skill_order"]
        ]

    def report(self, handoffs: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        return validate(self.scenario, copy.deepcopy(handoffs or self.handoffs))

    def test_all_expected_skills_exist_in_the_catalog_map(self) -> None:
        expected = self.scenario["expected_skill_order"]
        self.assertEqual(len(expected), 4)
        self.assertEqual(len(set(expected)), 4)
        self.assertTrue(set(expected).issubset(self.skills))

    def test_preflight_checks_all_four_skills(self) -> None:
        matches = {"inventory_scope": "synthetic_test_data_only",
                   "tools": [{"id": "python", "availability": "available"}]}
        results = [check_skill(self.skills[s], matches)
                   for s in self.scenario["expected_skill_order"]]
        self.assertEqual([x["skill"] for x in results], self.scenario["expected_skill_order"])
        self.assertTrue(all(x["readiness"] == "ready" for x in results))

    def test_valid_handoff_chain_passes(self) -> None:
        report = self.report()
        self.assertEqual(report["status"], "passed", report["errors"])
        self.assertEqual(len(report["handoff_chain"]), 4)

    def test_missing_stage_fails(self) -> None:
        self.assertIn("required_stages_and_order", self.report(self.handoffs[:-1])["errors"])

    def test_wrong_stage_order_fails(self) -> None:
        bad = copy.deepcopy(self.handoffs)
        bad[0], bad[1] = bad[1], bad[0]
        self.assertIn("required_stages_and_order", self.report(bad)["errors"])

    def test_handoff_link_mismatch_fails(self) -> None:
        bad = copy.deepcopy(self.handoffs)
        bad[2]["input_ref"] = "wrong-artifact"
        self.assertIn("python-development.input_link", self.report(bad)["errors"])

    def test_secret_value_in_secret_field_fails(self) -> None:
        bad = copy.deepcopy(self.handoffs)
        bad[0]["api_key"] = "not-redacted"
        self.assertIn("secret_redaction", self.report(bad)["errors"])

    def test_incident_action_order_is_enforced(self) -> None:
        bad = copy.deepcopy(self.handoffs)
        bad[0]["incident_events"].reverse()
        self.assertIn("incident_recommendation_order", self.report(bad)["errors"])

    def test_automatic_liquidation_is_rejected(self) -> None:
        bad = copy.deepcopy(self.handoffs)
        bad[0]["incident_events"].append({"event": "position_liquidation"})
        self.assertIn("no_automatic_liquidation", self.report(bad)["errors"])

    def test_missing_evidence_fails(self) -> None:
        bad = copy.deepcopy(self.handoffs)
        bad[1]["evidence"] = []
        self.assertIn("code-audit.evidence", self.report(bad)["errors"])

    def test_false_vps_access_claim_fails(self) -> None:
        bad = copy.deepcopy(self.handoffs)
        bad[3]["remote_access"] = "connected"
        self.assertIn("remote_and_production_scope", self.report(bad)["errors"])

    def test_fixture_safeguards_remain_explicit(self) -> None:
        safeguards = self.scenario["safeguards"]
        for key in ("never_print_secret_values", "never_execute_fixture_code",
                    "never_connect_to_ssh_or_remote_hosts",
                    "revoke_exposed_credential_before_host_isolation",
                    "never_auto_close_open_positions",
                    "production_changes_require_explicit_approval"):
            with self.subTest(key=key):
                self.assertIs(safeguards[key], True)
        self.assertIs(self.scenario["synthetic_only"], True)


if __name__ == "__main__":
    unittest.main()
