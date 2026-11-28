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
from handoff_contract import validate_handoff_chain  # noqa: E402


class GenericHandoffContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract: dict[str, Any] = json.loads(
            (FIXTURE / "workflow-contract.json").read_text(encoding="utf-8")
        )
        cls.artifacts = [
            json.loads((FIXTURE / "handoffs" / f"{stage['id']}.json").read_text(encoding="utf-8"))
            for stage in cls.contract["stages"]
        ]
        cls.context = json.loads((FIXTURE / "scenario.json").read_text(encoding="utf-8"))

    def report(self, artifacts: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        return validate_handoff_chain(
            self.contract, copy.deepcopy(self.artifacts if artifacts is None else artifacts),
            self.context,
        )

    def test_reference_workflow_passes_generic_engine(self) -> None:
        report = self.report()
        self.assertEqual(report["status"], "passed", report["errors"])
        self.assertEqual(len(report["handoff_chain"]), 4)

    def test_missing_stage_fails(self) -> None:
        self.assertIn("stage_sequence", self.report(self.artifacts[:-1])["errors"])

    def test_wrong_order_fails(self) -> None:
        bad = copy.deepcopy(self.artifacts)
        bad[0], bad[1] = bad[1], bad[0]
        self.assertIn("stage_sequence", self.report(bad)["errors"])

    def test_broken_handoff_reference_fails(self) -> None:
        bad = copy.deepcopy(self.artifacts)
        bad[2]["input_ref"] = "disconnected"
        self.assertIn("python-development.input_ref", self.report(bad)["errors"])

    def test_missing_required_field_fails(self) -> None:
        bad = copy.deepcopy(self.artifacts)
        del bad[1]["execution"]
        self.assertIn("code-audit.required.execution", self.report(bad)["errors"])

    def test_missing_evidence_fails(self) -> None:
        bad = copy.deepcopy(self.artifacts)
        bad[0]["evidence"] = []
        self.assertIn("crypto-security.evidence", self.report(bad)["errors"])

    def test_secret_like_field_fails(self) -> None:
        bad = copy.deepcopy(self.artifacts)
        bad[0]["api_key"] = "must-not-be-here"
        self.assertIn("secret_redaction", self.report(bad)["errors"])

    def test_secret_pattern_fails(self) -> None:
        bad = copy.deepcopy(self.artifacts)
        bad[1]["findings"].append("credential marker ghp_12345678901234567890")
        self.assertIn("secret_redaction", self.report(bad)["errors"])

    def test_incident_order_rule_fails(self) -> None:
        bad = copy.deepcopy(self.artifacts)
        bad[0]["incident_events"].reverse()
        self.assertIn("incident_recommendations_ordered", self.report(bad)["errors"])

    def test_forbidden_action_rule_fails(self) -> None:
        bad_contract = copy.deepcopy(self.contract)
        bad_contract["rules"].append({
            "id": "no_position_liquidation_event",
            "stage": "crypto-security",
            "path": "incident_events",
            "type": "forbid_values",
            "item_field": "event",
            "values": ["position_liquidation", "automatic_order_cancellation"],
        })
        bad = copy.deepcopy(self.artifacts)
        bad[0]["incident_events"].append({"event": "position_liquidation"})
        report = validate_handoff_chain(bad_contract, bad, self.context)
        self.assertIn("no_position_liquidation_event", report["errors"])

    def test_false_remote_access_claim_fails(self) -> None:
        bad = copy.deepcopy(self.artifacts)
        bad[3]["remote_access"] = "connected"
        self.assertIn("remote_access_not_checked", self.report(bad)["errors"])

    def test_cli_contract_is_data_driven(self) -> None:
        self.assertEqual(self.contract["workflow_id"], "security-review-four-skill-chain")
        self.assertTrue(all(stage["require_evidence"] for stage in self.contract["stages"]))


if __name__ == "__main__":
    unittest.main()
