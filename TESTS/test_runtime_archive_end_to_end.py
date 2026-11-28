from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "TESTS"))

from artifact_integrity import canonical_json_bytes  # noqa: E402
from artifact_signing import create_integrity_bundle  # noqa: E402
from handoff_runtime import build_workflow_plan, execute_with_adapter  # noqa: E402
from local_tsa_fixture import LocalRfc3161TSA  # noqa: E402
from runtime_archive_export import create_cryptographic_runtime_archive  # noqa: E402
from runtime_archive_verification import (  # noqa: E402
    verify_runtime_archive_cryptographically,
)
from trust_registry import public_key_fingerprint  # noqa: E402
from trust_registry_history import (  # noqa: E402
    build_history_anchor_statement,
    build_history_checkpoint,
    build_history_record,
    registry_snapshot_sha256,
)
from test_handoff_runtime import RuntimeAdapterProtocolTests  # noqa: E402


class RuntimeArchiveEndToEndTests(unittest.TestCase):
    """Exercise four signed stages through export and independent offline verification."""

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        RuntimeAdapterProtocolTests.setUpClass()
        self.fixture = RuntimeAdapterProtocolTests()
        self.contract = self.fixture.contract
        self.skill_map = self.fixture.skill_map
        self.source_artifacts = self.fixture.source_artifacts

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _keypair(self, private_key: Path, public_key: Path) -> None:
        subprocess.run(
            ["openssl", "genpkey", "-algorithm", "ED25519", "-out", str(private_key)],
            check=True, capture_output=True, timeout=15,
        )
        os.chmod(private_key, 0o600)
        subprocess.run(
            ["openssl", "pkey", "-in", str(private_key), "-pubout", "-out", str(public_key)],
            check=True, capture_output=True, timeout=15,
        )

    def _run_and_export(self) -> tuple[Path, Path, Path, dict[str, Any]]:
        now = datetime.now(timezone.utc)
        key_id = "synthetic-chain-key"
        run_id = "synthetic-archive-run-001"
        private_key = self.root / "stage-signing-private.pem"
        public_key = self.root / "stage-signing-public.pem"
        self._keypair(private_key, public_key)
        fingerprint = public_key_fingerprint(public_key)

        tsa = LocalRfc3161TSA(self.root / "local-tsa")
        evidence_root = self.root / "live-evidence"
        evidence_root.mkdir()
        registry_path = self.root / "live-registry.json"
        registry = {
            "registry_version": "1.0",
            "keys": [{
                "key_id": key_id,
                "algorithm": "Ed25519",
                "public_key_file": public_key.name,
                "public_key_sha256": fingerprint,
                "status": "active",
                "not_before": "2020-01-01T00:00:00Z",
                "not_after": "2035-01-01T00:00:00Z",
                "allowed_producers": [
                    "crypto-security", "code-audit", "python-development", "devops-vps"
                ],
                "allowed_artifact_types": ["workflow.stage_result"],
            }],
        }
        registry_path.write_text(json.dumps(registry), encoding="utf-8")

        base_adapter, calls = self.fixture.adapter_for()
        timestamp_responses: dict[str, str] = {}

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
            signature = base64.b64decode(
                result["integrity_bundle"]["signature"], validate=True
            )
            timestamp_responses[stage_id] = str(tsa.issue(signature))
            return result

        skill_root = self.root / "skills"
        for stage in self.contract["stages"]:
            path = skill_root / "skills" / stage["id"] / "SKILL.md"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"# {stage['id']}\n", encoding="utf-8")
        plan = build_workflow_plan(
            self.contract,
            self.skill_map,
            skill_root,
            "Synthetic end-to-end archive test",
            "fixture:root-input",
            "a" * 40,
        )
        runtime_policy = {
            "trust_registry_path": str(registry_path),
            "key_root": str(self.root),
            "evidence_root": str(evidence_root),
            "require_execution_context": True,
            "run_id": run_id,
            "max_signature_age_seconds": 300,
            "require_trusted_timestamp": True,
            "timestamp_responses": timestamp_responses,
            "timestamp_ca_file": str(tsa.ca_cert),
            "timestamp_untrusted_chain_file": str(tsa.tsa_cert),
        }
        run_report = execute_with_adapter(
            self.contract, plan, signed_adapter, integrity_policy=runtime_policy
        )
        self.assertEqual(run_report["status"], "completed", run_report)
        self.assertEqual(len(calls), 4)
        self.assertEqual(run_report["handoff_validation"]["status"], "passed")

        stage_public_key = public_key
        snapshot_digest = registry_snapshot_sha256(registry)
        history_event = {
            "event_id": "synthetic-stage-key-added",
            "action": "key_added",
            "key_id": key_id,
            "effective_at": "2020-01-01T00:00:00Z",
            "registry_sha256": snapshot_digest,
        }
        history = [build_history_record(history_event, 1)]
        checkpoint = build_history_checkpoint(history)

        anchor_private = self.root / "history-anchor-private.pem"
        anchor_public = self.root / "history-anchor-public.pem"
        self._keypair(anchor_private, anchor_public)
        anchor_key_id = "synthetic-history-anchor"
        anchored_at = now.isoformat().replace("+00:00", "Z")
        statement = build_history_anchor_statement(
            "synthetic-stage-key-history", checkpoint, anchored_at, anchor_key_id
        )
        statement_path = self.root / "history-anchor-statement.json"
        signature_path = self.root / "history-anchor-signature.bin"
        statement_path.write_bytes(canonical_json_bytes(statement))
        subprocess.run(
            [
                "openssl", "pkeyutl", "-sign", "-inkey", str(anchor_private),
                "-rawin", "-in", str(statement_path), "-out", str(signature_path),
            ],
            check=True, capture_output=True, timeout=15,
        )
        anchor_signature = signature_path.read_bytes()
        anchor = {
            **statement,
            "signature": base64.b64encode(anchor_signature).decode("ascii"),
        }
        anchor_timestamp = tsa.issue(anchor_signature)

        staging = self.root / "staging"
        (staging / "workflow").mkdir(parents=True)
        (staging / "trust" / "keys").mkdir(parents=True)
        (staging / "trust" / "registry-snapshots").mkdir(parents=True)
        (staging / "trust" / "registry.json").write_text(
            json.dumps(registry), encoding="utf-8"
        )
        (staging / "trust" / "history.json").write_text(
            json.dumps(history), encoding="utf-8"
        )
        (staging / "trust" / "history-checkpoint.json").write_text(
            json.dumps(checkpoint), encoding="utf-8"
        )
        (staging / "trust" / "history-anchor.json").write_text(
            json.dumps(anchor), encoding="utf-8"
        )
        shutil.copyfile(anchor_timestamp, staging / "trust" / "history-anchor.tsr")
        shutil.copyfile(
            stage_public_key, staging / "trust" / "keys" / public_key.name
        )
        (staging / "trust" / "registry-snapshots" / f"{snapshot_digest}.json").write_text(
            json.dumps(registry), encoding="utf-8"
        )
        (staging / "workflow" / "contract.json").write_text(
            json.dumps(self.contract), encoding="utf-8"
        )

        files: dict[str, str] = {
            "workflow/contract.json": "workflow/contract.json",
            "trust/registry.json": "trust/registry.json",
            "trust/history.json": "trust/history.json",
            "trust/history-checkpoint.json": "trust/history-checkpoint.json",
            "trust/history-anchor.json": "trust/history-anchor.json",
            "trust/history-anchor.tsr": "trust/history-anchor.tsr",
            f"trust/keys/{public_key.name}": f"trust/keys/{public_key.name}",
            f"trust/registry-snapshots/{snapshot_digest}.json":
                f"trust/registry-snapshots/{snapshot_digest}.json",
        }
        stage_ids = [stage["id"] for stage in self.contract["stages"]]
        skill_ids = [stage.get("skill_id", stage["id"]) for stage in self.contract["stages"]]
        personal_revision = run_report["artifacts"][0]["artifact_provenance"]["source"]["revision"]

        for result in run_report["artifacts"]:
            stage_id = result["stage"]
            stage_dir = staging / "workflow" / "stages" / stage_id
            evidence_dir = stage_dir / "evidence"
            evidence_dir.mkdir(parents=True)
            evidence_name = f"{stage_id}.txt"
            shutil.copyfile(evidence_root / evidence_name, evidence_dir / evidence_name)
            shutil.copyfile(
                timestamp_responses[stage_id], stage_dir / "timestamp.tsr"
            )
            result_path = staging / "workflow" / "stages" / f"{stage_id}.json"
            result_path.write_text(json.dumps(result), encoding="utf-8")
            files[f"workflow/stages/{stage_id}.json"] = (
                f"workflow/stages/{stage_id}.json"
            )
            files[f"workflow/stages/{stage_id}/timestamp.tsr"] = (
                f"workflow/stages/{stage_id}/timestamp.tsr"
            )
            files[
                f"workflow/stages/{stage_id}/evidence/{evidence_name}"
            ] = f"workflow/stages/{stage_id}/evidence/{evidence_name}"

        metadata = {
            "run_id": run_id,
            "workflow_id": self.contract["workflow_id"],
            "stage_ids": stage_ids,
            "skill_ids": skill_ids,
            "personal_ai_library_revision": personal_revision,
            "ai_toolbox_revision": "b" * 40,
            "created_at": now.isoformat().replace("+00:00", "Z"),
            "run_status": "completed",
            "verification_policy": {"require_trusted_timestamp": True},
        }
        archive = self.root / "portable-archive"
        create_cryptographic_runtime_archive(staging, archive, metadata, files)
        host_trust = {
            "history_anchor_public_key": anchor_public,
            "history_anchor_key_id": anchor_key_id,
            "timestamp_ca_file": tsa.ca_cert,
            "timestamp_untrusted_chain_file": tsa.tsa_cert,
            "require_trusted_timestamps": True,
        }
        return archive, anchor_public, tsa.ca_cert, {
            "trust_policy": host_trust,
            "timestamp_chain": tsa.tsa_cert,
            "run_report": run_report,
        }

    def test_four_stage_run_exports_and_verifies_offline(self) -> None:
        archive, anchor_public, tsa_ca, context = self._run_and_export()
        report = verify_runtime_archive_cryptographically(
            archive, context["trust_policy"]
        )
        self.assertEqual(report["status"], "runtime_archive_cryptographically_verified")
        self.assertEqual(report["verification_scope"], "offline_audit_only")
        self.assertEqual(len(report["stages"]), 4)
        self.assertEqual(report["handoff_validation"]["status"], "passed")
        self.assertTrue(all(
            item["verification"]["trusted_timestamp"]["status"] == "verified"
            for item in report["stages"]
        ))
        self.assertTrue(anchor_public.is_file())
        self.assertTrue(tsa_ca.is_file())

    def test_tampered_archived_stage_signature_fails_closed(self) -> None:
        archive, _, _, context = self._run_and_export()
        stage_path = archive / "workflow" / "stages" / "crypto-security.json"
        stage = json.loads(stage_path.read_text(encoding="utf-8"))
        stage["integrity_bundle"]["signature"] = base64.b64encode(b"tampered").decode("ascii")
        stage_path.write_text(json.dumps(stage), encoding="utf-8")
        from runtime_run_archive import MANIFEST_NAME
        import hashlib
        manifest_path = archive / MANIFEST_NAME
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        data = stage_path.read_bytes()
        entry = next(item for item in manifest["entries"] if item["path"] == "workflow/stages/crypto-security.json")
        entry["size"] = len(data)
        entry["sha256"] = hashlib.sha256(data).hexdigest()
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaises(ValueError):
            verify_runtime_archive_cryptographically(archive, context["trust_policy"])


if __name__ == "__main__":
    unittest.main()
