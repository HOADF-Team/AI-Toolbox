from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "TESTS" / "fixtures" / "inter-skill-demo"
sys.path.insert(0, str(ROOT / "scripts"))
from handoff_runtime import RuntimeProtocolError, build_workflow_plan, execute_with_adapter  # noqa: E402


class RuntimeAdapterProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract: dict[str, Any] = json.loads(
            (FIXTURE / "workflow-contract.json").read_text(encoding="utf-8")
        )
        cls.skill_map = json.loads(
            (ROOT / "CATALOG" / "skill-tools.json").read_text(encoding="utf-8")
        )
        cls.source_artifacts = [
            json.loads((FIXTURE / "handoffs" / f"{stage['id']}.json").read_text(encoding="utf-8"))
            for stage in cls.contract["stages"]
        ]

    def make_root(self, skill_ids: list[str] | None = None) -> Path:
        root = Path(tempfile.mkdtemp())
        for skill_id in skill_ids or [stage["id"] for stage in self.contract["stages"]]:
            path = root / "skills" / skill_id / "SKILL.md"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"# {skill_id}\n", encoding="utf-8")
        return root

    def plan(self, approvals: dict[str, str] | None = None) -> list[dict[str, Any]]:
        return build_workflow_plan(
            self.contract, self.skill_map, self.make_root(),
            "Review the synthetic security fixture", "scenario:demo", approvals,
        )

    def adapter_for(self, artifacts: list[dict[str, Any]] | None = None):
        values = artifacts or self.source_artifacts
        calls: list[str] = []

        def adapter(envelope: dict[str, Any]) -> dict[str, Any]:
            calls.append(envelope["stage"]["id"])
            index = len(calls) - 1
            result = dict(values[index])
            result["input_ref"] = envelope["input_ref"]
            result["status"] = "completed"
            result["skill_id"] = envelope["stage"]["skill_id"]
            result["provenance"] = {
                "execution_mode": "mock",
                "skill_manifest_ref": envelope["skill"]["manifest_path"],
                "agent": "test-adapter",
            }
            result.setdefault("actions_taken", [])
            return result
        return adapter, calls

    def test_builds_ordered_envelopes_from_catalog_and_manifests(self) -> None:
        plan = self.plan()
        self.assertEqual([x["envelope"]["stage"]["skill_id"] for x in plan],
                         ["crypto-security", "code-audit", "python-development", "devops-vps"])
        self.assertEqual(plan[1]["envelope"]["prior_stage_output_ref"], "stage-output:crypto-security")

    def test_unknown_skill_id_is_rejected(self) -> None:
        bad = json.loads(json.dumps(self.contract))
        bad["stages"][0]["skill_id"] = "not-a-real-skill"
        with self.assertRaisesRegex(RuntimeProtocolError, "unknown Skill ID"):
            build_workflow_plan(bad, self.skill_map, self.make_root(), "task", "ref")

    def test_missing_manifest_is_rejected(self) -> None:
        with self.assertRaisesRegex(RuntimeProtocolError, "manifest unavailable"):
            build_workflow_plan(self.contract, self.skill_map, self.make_root([]), "task", "ref")

    def test_mock_adapter_executes_full_sequence_and_validates_handoffs(self) -> None:
        adapter, calls = self.adapter_for()
        report = execute_with_adapter(self.contract, self.plan(), adapter)
        self.assertEqual(report["status"], "completed")
        self.assertEqual(len(calls), 4)
        self.assertEqual(report["handoff_validation"]["status"], "passed")

    def test_failed_stage_stops_following_stages(self) -> None:
        values = [dict(x) for x in self.source_artifacts]
        values[1]["status"] = "failed"
        adapter, calls = self.adapter_for(values)
        report = execute_with_adapter(self.contract, self.plan(), adapter)
        self.assertEqual(report["status"], "incomplete")
        self.assertEqual(len(calls), 2)

    def test_required_approval_blocks_before_adapter(self) -> None:
        contract = json.loads(json.dumps(self.contract))
        contract["stages"][0]["required_approvals"] = ["remote_access"]
        plan = build_workflow_plan(contract, self.skill_map, self.make_root(), "task", "ref")
        adapter, calls = self.adapter_for()
        report = execute_with_adapter(contract, plan, adapter)
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(calls, [])

    def test_action_without_matching_approval_is_rejected(self) -> None:
        values = [dict(x) for x in self.source_artifacts]
        values[0]["actions_taken"] = [{"action": "remote_access", "approval_id": "forged"}]
        adapter, _ = self.adapter_for(values)
        report = execute_with_adapter(self.contract, self.plan(), adapter, {"remote_access": "approved-1"})
        self.assertEqual(report["status"], "incomplete")
        self.assertIn("invalid_stage_result", report["stopped_reason"])

    def test_invalid_provenance_is_rejected(self) -> None:
        adapter, _ = self.adapter_for()
        def invalid(envelope: dict[str, Any]) -> dict[str, Any]:
            result = adapter(envelope)
            result["provenance"] = {"execution_mode": "mock"}
            return result
        report = execute_with_adapter(self.contract, self.plan(), invalid)
        self.assertIn("invalid_stage_result", report["stopped_reason"])

    def test_stage_output_cannot_claim_wrong_skill(self) -> None:
        adapter, _ = self.adapter_for()
        def wrong(envelope: dict[str, Any]) -> dict[str, Any]:
            result = adapter(envelope)
            result["skill_id"] = "other-skill"
            return result
        report = execute_with_adapter(self.contract, self.plan(), wrong)
        self.assertIn("invalid_stage_result", report["stopped_reason"])


if __name__ == "__main__":
    unittest.main()
