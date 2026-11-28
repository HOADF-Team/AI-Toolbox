from __future__ import annotations

import json
import os
import subprocess
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
from artifact_signing import create_integrity_bundle  # noqa: E402
from trust_registry import public_key_fingerprint  # noqa: E402
from handoff_runtime import RuntimeProtocolError, build_workflow_plan, execute_with_adapter, stage_result_sha256  # noqa: E402


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

    def plan(self, approvals: dict[str, dict[str, dict[str, Any]]] | None = None) -> list[dict[str, Any]]:
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
                            "output_ref": result["output_ref"],
                            "stage_result_sha256": stage_result_sha256(result)},
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
        scope = {"target_ref": "vps://prod-1", "operation": "read-only-diagnostics", "resource": "journal"}
        values[0]["actions_taken"] = [{"stage_id": "crypto-security", "action": "remote_access", "approval_id": "forged", "scope": scope}]
        approval = {"stage_id": "crypto-security", "action": "remote_access", "approval_id": "approved-1", "scope": scope, "expires_at": "2026-11-28T23:59:59Z"}
        approvals = {"crypto-security": {"remote_access": approval}}
        adapter, _ = self.adapter_for(values)
        report = execute_with_adapter(self.contract, self.plan(approvals), adapter, approvals)
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
                "input_ref": self.contract.get("root_input_ref", "scenario:demo"),
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


    def _signed_chain_fixture(self, root: Path, tamper_signature: bool = False):
        key_root = root / "keys"
        evidence_root = root / "evidence"
        key_root.mkdir()
        evidence_root.mkdir()
        private_key = root / "signing-private.pem"
        public_key = key_root / "signing-public.pem"
        subprocess.run(
            ["openssl", "genpkey", "-algorithm", "ED25519", "-out", str(private_key)],
            check=True, capture_output=True, timeout=15,
        )
        os.chmod(private_key, 0o600)
        subprocess.run(
            ["openssl", "pkey", "-in", str(private_key), "-pubout", "-out", str(public_key)],
            check=True, capture_output=True, timeout=15,
        )
        key_id = "synthetic-chain-key"
        fingerprint = public_key_fingerprint(public_key)
        registry_path = root / "trust-registry.json"
        registry_path.write_text(json.dumps({
            "registry_version": "1.0",
            "keys": [{
                "key_id": key_id,
                "algorithm": "Ed25519",
                "public_key_file": "signing-public.pem",
                "public_key_sha256": fingerprint,
                "status": "active",
                "not_before": "2026-01-01T00:00:00Z",
                "not_after": "2027-01-01T00:00:00Z",
                "allowed_producers": [
                    "crypto-security", "code-audit", "python-development", "devops-vps"
                ],
                "allowed_artifact_types": ["workflow.stage_result"],
            }],
        }), encoding="utf-8")
        base_adapter, calls = self.adapter_for()
        run_id = "synthetic-chain-run-001"

        def signed_adapter(envelope: dict[str, Any]) -> dict[str, Any]:
            result = base_adapter(envelope)
            stage_id = envelope["stage"]["id"]
            evidence_path = evidence_root / f"{stage_id}.txt"
            evidence_path.write_text(f"synthetic evidence for {stage_id}\n", encoding="utf-8")
            result["integrity_bundle"] = create_integrity_bundle(
                envelope=result["artifact_provenance"],
                key_id=key_id,
                private_key=private_key,
                trusted_public_key=public_key,
                expected_public_key_sha256=fingerprint,
                evidence_root=evidence_root,
                evidence_paths={"fixture:agent-reported-evidence": evidence_path.name},
                execution_context={
                    "run_id": run_id,
                    "workflow_id": envelope["workflow_id"],
                    "stage_id": stage_id,
                    "skill_id": envelope["stage"]["skill_id"],
                    "input_ref": envelope["input_ref"],
                },
                ttl_seconds=300,
            )
            if tamper_signature and len(calls) == 1:
                result["integrity_bundle"]["signature"] = "AA=="
            return result

        policy = {
            "trust_registry_path": str(registry_path),
            "key_root": str(key_root),
            "evidence_root": str(evidence_root),
            "require_execution_context": True,
            "run_id": run_id,
            "max_signature_age_seconds": 300,
        }
        return signed_adapter, policy, calls

    def test_signed_four_skill_chain_verifies_each_stage_and_handoff(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            adapter, policy, calls = self._signed_chain_fixture(Path(temp_dir))
            report = execute_with_adapter(
                self.contract, self.plan(), adapter, integrity_policy=policy
            )
        self.assertEqual(report["status"], "completed")
        self.assertEqual(len(calls), 4)
        self.assertEqual(report["handoff_validation"]["status"], "passed")
        self.assertTrue(all(
            item["integrity_verification"]["replay_protection"]
            == "run_stage_bound_and_time_limited"
            for item in report["artifacts"]
        ))

    def test_tampered_signature_stops_signed_four_skill_chain(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            adapter, policy, calls = self._signed_chain_fixture(
                Path(temp_dir), tamper_signature=True
            )
            report = execute_with_adapter(
                self.contract, self.plan(), adapter, integrity_policy=policy
            )
        self.assertEqual(report["status"], "incomplete")
        self.assertEqual(len(calls), 1)
        self.assertIn("artifact_integrity_verification_failed", report["stages"][0]["errors"])


    def test_signed_provenance_binds_stage_evidence_claims(self) -> None:
        adapter, _ = self.adapter_for()

        def altered_evidence(envelope: dict[str, Any]) -> dict[str, Any]:
            result = adapter(envelope)
            result["evidence"] = [
                {"location": "unverified://attacker-controlled", "observation": "fabricated claim"}
            ]
            return result

        report = execute_with_adapter(self.contract, self.plan(), altered_evidence)
        self.assertIn(
            "artifact_provenance_stage_result_digest_mismatch",
            report["stages"][0]["errors"],
        )


    def test_tampered_plan_cannot_clear_contract_required_approval(self) -> None:
        contract = json.loads(json.dumps(self.contract))
        contract["stages"][0]["required_approvals"] = ["remote_access"]
        plan = build_workflow_plan(
            contract, self.skill_map, self.make_root(), "task", "ref", SKILLS_REVISION
        )
        plan[0]["envelope"]["permissions"]["missing_approvals"] = []
        plan[0]["envelope"]["permissions"]["granted_approvals"] = {
            "remote_access": "forged-plan-approval"
        }
        adapter, calls = self.adapter_for()
        report = execute_with_adapter(contract, plan, adapter)
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(calls, [])
        self.assertIn("approval_required", report["stopped_reason"])

    def test_approval_for_another_stage_cannot_authorize_this_stage_action(self) -> None:
        contract = json.loads(json.dumps(self.contract))
        contract["stages"][1]["required_approvals"] = ["remote_access"]
        values = [dict(item) for item in self.source_artifacts]
        values[0]["actions_taken"] = [
            {"action": "remote_access", "approval_id": "approved-remote"}
        ]
        scope = {"target_ref": "vps://prod-1", "operation": "read-only-diagnostics"}
        approval = {"stage_id": "code-audit", "action": "remote_access", "approval_id": "approved-remote", "scope": scope, "expires_at": "2026-11-28T23:59:59Z"}
        approvals = {"code-audit": {"remote_access": approval}}
        plan = build_workflow_plan(contract, self.skill_map, self.make_root(), "task", "ref", SKILLS_REVISION, approvals)
        adapter, calls = self.adapter_for(values)
        report = execute_with_adapter(contract, plan, adapter, approvals)
        self.assertEqual(calls, ["crypto-security"])
        self.assertIn(
            "action_without_matching_approval:remote_access",
            report["stages"][0]["errors"],
        )


    def test_symlinked_skill_manifest_is_rejected(self) -> None:
        root = self.make_root()
        manifest = root / "skills" / "crypto-security" / "SKILL.md"
        outside = root / "outside-SKILL.md"
        outside.write_text("# outside\n", encoding="utf-8")
        manifest.unlink()
        manifest.symlink_to(outside)
        with self.assertRaisesRegex(RuntimeProtocolError, "symlink"):
            build_workflow_plan(
                self.contract, self.skill_map, root, "task", "ref", SKILLS_REVISION
            )

    def test_symlinked_skill_directory_is_rejected(self) -> None:
        root = self.make_root()
        skill_dir = root / "skills" / "crypto-security"
        outside_dir = root / "outside-skill"
        outside_dir.mkdir()
        (outside_dir / "SKILL.md").write_text("# outside\n", encoding="utf-8")
        (skill_dir / "SKILL.md").unlink()
        skill_dir.rmdir()
        skill_dir.symlink_to(outside_dir, target_is_directory=True)
        with self.assertRaisesRegex(RuntimeProtocolError, "symlink"):
            build_workflow_plan(
                self.contract, self.skill_map, root, "task", "ref", SKILLS_REVISION
            )


if __name__ == "__main__":
    unittest.main()
