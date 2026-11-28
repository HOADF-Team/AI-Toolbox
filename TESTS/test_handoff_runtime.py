from __future__ import annotations

import json
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SKILLS_REVISION = "a" * 40
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
        selected = skill_ids if skill_ids is not None else [stage["id"] for stage in self.contract["stages"]]
        for skill_id in selected:
            path = root / "skills" / skill_id / "SKILL.md"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"# {skill_id}\n", encoding="utf-8")
        return root

    def plan(self, approvals: dict[str, str] | None = None) -> list[dict[str, Any]]:
        return build_workflow_plan(
            self.contract, self.skill_map, self.make_root(),
            "Review the synthetic security fixture", "scenario:demo", SKILLS_REVISION, approvals,
        )

    def adapter_for(self, artifacts: list[dict[str, Any]] | None = None):
        values = artifacts or self.source_artifacts
        calls: list[str] = []

        def adapter(envelope: dict[str, Any]) -> dict[str, Any]:
            calls.append(envelope["stage"]["id"])
            index = len(calls) - 1
            result = dict(values[index])
            result["input_ref"] = envelope["input_ref"]
            result.setdefault("status", "completed")
            result["skill_id"] = envelope["stage"]["skill_id"]
            result["provenance"] = {
                "execution_mode": "mock",
                "skill_manifest_ref": envelope["skill"]["manifest_ref"],
                "agent": "test-adapter",
            }
            result.setdefault("actions_taken", [])
            result["artifact_provenance"] = {
                "envelope_version": "1.0",
                "artifact_id": f"artifact.{envelope['stage']['id']}.result",
                "artifact_type": "workflow.stage_result",
                "producer": {"kind": "skill", "id": envelope["stage"]["skill_id"],
                             "version": "fixture", "revision": envelope["skill"]["manifest_revision"]},
                "source": {"repository": "HOADF-Team/Personal-AI-Library",
                           "revision": envelope["skill"]["manifest_revision"]},
                "created_at": "2026-11-28T10:00:00Z",
                "inputs": [{"ref": envelope["input_ref"], "artifact_type": "workflow.stage_input"}],
                "payload": {"stage": result["stage"], "skill_id": result["skill_id"],
                            "output_ref": result["output_ref"]},
                "evidence": ["fixture:agent-reported-evidence"],
                "verification": {"status": "structurally_validated", "method": "runtime-contract",
                                 "checked_at": "2026-11-28T10:01:00Z",
                                 "limitations": ["synthetic mock; producer and evidence not authenticated"]},
            }
            return result
        return adapter, calls

    def test_builds_ordered_envelopes_from_catalog_and_manifests(self) -> None:
        plan = self.plan()
        self.assertEqual([x["envelope"]["stage"]["skill_id"] for x in plan],
                         ["crypto-security", "code-audit", "python-development", "devops-vps"])
        self.assertEqual(plan[1]["envelope"]["prior_stage_output_ref"], "stage-output:crypto-security")
        self.assertEqual(plan[0]["envelope"]["skill"]["manifest_revision"], SKILLS_REVISION)

    def test_unknown_skill_id_is_rejected(self) -> None:
        bad = json.loads(json.dumps(self.contract))
        bad["stages"][0]["skill_id"] = "not-a-real-skill"
        with self.assertRaisesRegex(RuntimeProtocolError, "unknown Skill ID"):
            build_workflow_plan(bad, self.skill_map, self.make_root(), "task", "ref", SKILLS_REVISION)

    def test_invalid_skill_revision_is_rejected(self) -> None:
        with self.assertRaisesRegex(RuntimeProtocolError, "full 40-character"):
            build_workflow_plan(self.contract, self.skill_map, self.make_root(), "task", "ref", "main")

    def test_missing_manifest_is_rejected(self) -> None:
        with self.assertRaisesRegex(RuntimeProtocolError, "manifest unavailable"):
            build_workflow_plan(self.contract, self.skill_map, self.make_root([]), "task", "ref", SKILLS_REVISION)

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
        plan = build_workflow_plan(contract, self.skill_map, self.make_root(), "task", "ref", SKILLS_REVISION)
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

    def test_wrong_skill_manifest_revision_is_rejected(self) -> None:
        adapter, _ = self.adapter_for()
        def wrong_revision(envelope: dict[str, Any]) -> dict[str, Any]:
            result = adapter(envelope)
            result["provenance"]["skill_manifest_ref"] = "https://github.com/HOADF-Team/Personal-AI-Library/blob/main/skills/crypto-security/SKILL.md"
            return result
        report = execute_with_adapter(self.contract, self.plan(), wrong_revision)
        self.assertIn("skill_manifest_ref_mismatch", report["stages"][0]["errors"])

    def test_missing_artifact_provenance_envelope_is_rejected(self) -> None:
        adapter, _ = self.adapter_for()
        def missing(envelope: dict[str, Any]) -> dict[str, Any]:
            result = adapter(envelope)
            del result["artifact_provenance"]
            return result
        report = execute_with_adapter(self.contract, self.plan(), missing)
        self.assertIn("missing_artifact_provenance_envelope", report["stages"][0]["errors"])

    def test_artifact_provenance_cannot_claim_different_output_ref(self) -> None:
        adapter, _ = self.adapter_for()
        def mismatched(envelope: dict[str, Any]) -> dict[str, Any]:
            result = adapter(envelope)
            result["artifact_provenance"]["payload"]["output_ref"] = "forged:ref"
            return result
        report = execute_with_adapter(self.contract, self.plan(), mismatched)
        self.assertIn("artifact_provenance_output_ref_mismatch", report["stages"][0]["errors"])

    def test_stage_output_cannot_claim_wrong_skill(self) -> None:
        adapter, _ = self.adapter_for()
        def wrong(envelope: dict[str, Any]) -> dict[str, Any]:
            result = adapter(envelope)
            result["skill_id"] = "other-skill"
            return result
        report = execute_with_adapter(self.contract, self.plan(), wrong)
        self.assertIn("invalid_stage_result", report["stopped_reason"])

    def test_integrity_policy_blocks_unsigned_stage_result(self) -> None:
        adapter, _ = self.adapter_for()
        policy = {
            "trusted_public_key": "/tmp/not-a-real-trusted-key.pem",
            "trusted_key_id": "production-trust-anchor",
            "evidence_root": "/tmp/not-a-real-evidence-root",
        }
        report = execute_with_adapter(self.contract, self.plan(), adapter, integrity_policy=policy)
        self.assertIn("missing_integrity_bundle", report["stages"][0]["errors"])


    def test_runtime_binds_signature_to_current_run_and_stage(self) -> None:
        adapter, _ = self.adapter_for()

        def signed_result(envelope: dict[str, Any]) -> dict[str, Any]:
            result = adapter(envelope)
            result["integrity_bundle"] = {"key_id": "test-key"}
            return result

        policy = {
            "trusted_public_key": "/tmp/mock-public-key.pem",
            "trusted_key_id": "test-key",
            "evidence_root": "/tmp/mock-evidence",
            "require_execution_context": True,
            "run_id": "runtime-run-001",
            "max_signature_age_seconds": 600,
        }
        with patch(
            "handoff_runtime.verify_integrity_bundle",
            return_value={"status": "verified"},
        ) as verifier:
            report = execute_with_adapter(
                self.contract, self.plan(), signed_result, integrity_policy=policy
            )
        self.assertEqual(report["status"], "completed")
        self.assertEqual(
            verifier.call_args_list[0].kwargs["expected_execution_context"],
            {
                "run_id": "runtime-run-001",
                "workflow_id": self.contract["workflow_id"],
                "stage_id": "crypto-security",
                "skill_id": "crypto-security",
                "input_ref": "scenario:demo",
            },
        )

    def test_runtime_requires_run_id_when_replay_protection_enabled(self) -> None:
        adapter, _ = self.adapter_for()

        def signed_result(envelope: dict[str, Any]) -> dict[str, Any]:
            result = adapter(envelope)
            result["integrity_bundle"] = {"key_id": "test-key"}
            return result

        policy = {
            "trusted_public_key": "/tmp/mock-public-key.pem",
            "trusted_key_id": "test-key",
            "evidence_root": "/tmp/mock-evidence",
            "require_execution_context": True,
        }
        report = execute_with_adapter(
            self.contract, self.plan(), signed_result, integrity_policy=policy
        )
        self.assertIn("artifact_integrity_verification_failed", report["stages"][0]["errors"])


if __name__ == "__main__":
    unittest.main()
