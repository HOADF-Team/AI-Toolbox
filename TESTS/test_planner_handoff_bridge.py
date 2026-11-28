from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "TESTS" / "fixtures" / "inter-skill-demo"
REVISION = "a" * 40
sys.path.insert(0, str(ROOT / "scripts"))

from planner_handoff_bridge import (  # noqa: E402
    PlannerHandoffBridgeError,
    prepare_workflow_from_planner,
)


class PlannerHandoffBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract: dict[str, Any] = json.loads(
            (FIXTURE / "workflow-contract.json").read_text(encoding="utf-8")
        )
        cls.skill_map = json.loads(
            (ROOT / "CATALOG" / "skill-tools.json").read_text(encoding="utf-8")
        )

    def make_root(self) -> Path:
        root = Path(tempfile.mkdtemp())
        for stage in self.contract["stages"]:
            skill_id = stage.get("skill_id", stage["id"])
            manifest = root / "skills" / skill_id / "SKILL.md"
            manifest.parent.mkdir(parents=True, exist_ok=True)
            manifest.write_text(f"# {skill_id}\nCanonical test fixture.", encoding="utf-8")
        return root

    def planner_result(self, decision: str = "select", selected: list[str] | None = None) -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "decision": decision,
            "selected_skills": selected if selected is not None else [
                stage.get("skill_id", stage["id"]) for stage in self.contract["stages"]
            ],
            "rationale": "The task requires an ordered security review.",
            "run": {"skills_revision": REVISION},
            "runtime": {"name": "mock-runtime", "planner_version": "test"},
            "limitations": [],
        }

    def prepare(self, result: dict[str, Any] | None = None, contracts: list[dict[str, Any]] | None = None):
        return prepare_workflow_from_planner(
            planner_result=result or self.planner_result(),
            task="Review the synthetic security fixture",
            task_ref="task:fixture-001",
            reviewed_contracts=contracts or [self.contract],
            skill_map=self.skill_map,
            skills_root=self.make_root(),
            skills_revision=REVISION,
        )

    def test_planner_selection_becomes_ordered_validated_plan(self) -> None:
        result = self.prepare()
        self.assertEqual(result["status"], "prepared")
        self.assertEqual(result["workflow_id"], self.contract["workflow_id"])
        self.assertEqual(len(result["plan"]), 4)
        self.assertEqual(
            [item["envelope"]["stage"]["skill_id"] for item in result["plan"]],
            ["crypto-security", "code-audit", "python-development", "devops-vps"],
        )
        self.assertEqual(result["plan"][1]["envelope"]["input_ref"], "stage-output:crypto-security")
        self.assertFalse(result["execution_started"])
        self.assertEqual(result["selection_validation"]["status"], "passed")

    def test_selection_without_reviewed_contract_does_not_invent_workflow(self) -> None:
        result = self.prepare(self.planner_result(selected=["code-audit"]))
        self.assertEqual(result["status"], "no_matching_reviewed_workflow")
        self.assertEqual(result["plan"], [])

    def test_abstain_returns_no_plan(self) -> None:
        result = self.prepare(self.planner_result("abstain", []))
        self.assertEqual(result["status"], "abstain")
        self.assertEqual(result["plan"], [])

    def test_clarify_returns_no_plan(self) -> None:
        result = self.prepare(self.planner_result("clarify", []))
        self.assertEqual(result["status"], "clarify")
        self.assertEqual(result["plan"], [])

    def test_revision_mismatch_is_rejected(self) -> None:
        result = self.planner_result()
        result["run"]["skills_revision"] = "b" * 40
        with self.assertRaisesRegex(PlannerHandoffBridgeError, "revision"):
            self.prepare(result)

    def test_duplicate_selected_skills_are_rejected(self) -> None:
        result = self.planner_result(selected=["crypto-security", "crypto-security"])
        with self.assertRaisesRegex(PlannerHandoffBridgeError, "duplicate"):
            self.prepare(result)

    def test_missing_manifest_stops_preparation(self) -> None:
        root = Path(tempfile.mkdtemp())
        with self.assertRaisesRegex(PlannerHandoffBridgeError, "manifest unavailable"):
            prepare_workflow_from_planner(
                self.planner_result(), "task", "task:1", [self.contract],
                self.skill_map, root, REVISION,
            )

    def test_ambiguous_contract_match_is_rejected(self) -> None:
        with self.assertRaisesRegex(PlannerHandoffBridgeError, "multiple"):
            self.prepare(contracts=[self.contract, dict(self.contract)])

    def test_selection_must_match_exact_order(self) -> None:
        result = self.planner_result(selected=[
            "code-audit", "crypto-security", "python-development", "devops-vps"
        ])
        prepared = self.prepare(result)
        self.assertEqual(prepared["status"], "no_matching_reviewed_workflow")


if __name__ == "__main__":
    unittest.main()
