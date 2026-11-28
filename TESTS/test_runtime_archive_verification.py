from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from runtime_archive_verification import (  # noqa: E402
    RuntimeArchiveVerificationError,
    verify_runtime_archive_cryptographically,
)
from runtime_run_archive import create_runtime_archive  # noqa: E402


class RuntimeArchiveCryptographicVerificationTests(unittest.TestCase):
    def make_archive(self, root: Path, *, bad_context: bool = False) -> tuple[Path, Path, Path]:
        source = root / "source"
        source.mkdir()
        (source / "workflow" / "stages" / "alpha" / "evidence").mkdir(parents=True)
        (source / "trust" / "keys").mkdir(parents=True)
        (source / "trust").mkdir(exist_ok=True)
        (source / "workflow" / "stages" / "alpha" / "evidence" / "proof.txt").write_text(
            "synthetic evidence\n", encoding="utf-8"
        )
        contract = {
            "workflow_id": "archive-test",
            "root_input_ref": "root",
            "stages": [{"id": "alpha", "skill_id": "alpha", "required_fields": ["decision"]}],
        }
        revision = "a" * 40
        result = {
            "stage": "alpha",
            "skill_id": "alpha",
            "input_ref": "root",
            "output_ref": "out:alpha",
            "status": "completed",
            "decision": "synthetic-pass",
            "evidence": [{"location": "fixture:proof", "observation": "synthetic only"}],
            "artifact_provenance": {
                "producer": {"id": "alpha", "revision": revision},
                "source": {"revision": revision},
                "payload": {
                    "stage": "alpha",
                    "skill_id": "alpha",
                    "output_ref": "out:alpha",
                    "stage_result_sha256": "b" * 64,
                },
            },
            "integrity_bundle": {
                "key_id": "test-key",
                "statement": {
                    "execution_context": {
                        "run_id": "run-001",
                        "workflow_id": "archive-test",
                        "stage_id": "alpha",
                        "skill_id": "alpha",
                        "input_ref": "wrong" if bad_context else "root",
                        "issued_at": "2026-11-28T10:00:00Z",
                        "expires_at": "2026-11-28T10:05:00Z",
                    }
                },
            },
        }
        files = {
            "workflow/contract.json": "workflow/contract.json",
            "workflow/stages/alpha.json": "workflow/stages/alpha.json",
            "workflow/stages/alpha/evidence/proof.txt": "workflow/stages/alpha/evidence/proof.txt",
            "workflow/stages/alpha/timestamp.tsr": "workflow/stages/alpha/timestamp.tsr",
            "trust/registry.json": "trust/registry.json",
            "trust/keys/test.pub": "trust/keys/test.pub",
            "trust/history.json": "trust/history.json",
            "trust/history-checkpoint.json": "trust/history-checkpoint.json",
            "trust/history-anchor.json": "trust/history-anchor.json",
            "trust/history-anchor.tsr": "trust/history-anchor.tsr",
        }
        source_files = {
            "workflow/contract.json": contract,
            "workflow/stages/alpha.json": result,
            "trust/registry.json": {"registry_version": "1.0", "keys": []},
            "trust/history.json": [],
            "trust/history-checkpoint.json": {"event_count": 0, "head_sha256": "0" * 64},
            "trust/history-anchor.json": {"anchor_version": "1.0", "signature": "fixture"},
        }
        for relative, value in source_files.items():
            path = source / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(value), encoding="utf-8")
        for relative in (
            "workflow/stages/alpha/timestamp.tsr",
            "trust/keys/test.pub",
            "trust/history-anchor.tsr",
        ):
            path = source / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"synthetic fixture bytes")
        registry_key = root / "history-anchor.pub"
        registry_key.write_text("external public trust anchor fixture", encoding="utf-8")
        tsa_ca = root / "tsa-ca.pem"
        tsa_ca.write_text("external TSA trust root fixture", encoding="utf-8")

        archive = root / "archive"
        create_runtime_archive(
            source,
            archive,
            {
                "run_id": "run-001",
                "workflow_id": "archive-test",
                "stage_ids": ["alpha"],
                "skill_ids": ["alpha"],
                "personal_ai_library_revision": revision,
                "ai_toolbox_revision": "c" * 40,
                "created_at": "2026-11-28T10:06:00Z",
                "run_status": "completed",
                "verification_policy": {"require_trusted_timestamp": True},
            },
            files,
        )
        return archive, registry_key, tsa_ca

    def verify_with_fixtures(self, archive: Path, anchor_key: Path, tsa_ca: Path):
        checkpoint = {"event_count": 0, "head_sha256": "0" * 64}
        policy = {
            "history_anchor_public_key": anchor_key,
            "history_anchor_key_id": "external-anchor",
            "timestamp_ca_file": tsa_ca,
            "require_trusted_timestamps": True,
        }
        with (
            patch(
                "runtime_archive_verification.verify_history_anchor",
                return_value={
                    "status": "signed_checkpoint_verified",
                    "checkpoint": checkpoint,
                    "timestamp": {"status": "verified"},
                },
            ) as anchor_verifier,
            patch(
                "runtime_archive_verification.verify_archived_bundle",
                return_value={
                    "status": "archived_verified",
                    "trusted_timestamp": {"status": "verified"},
                },
            ) as stage_verifier,
            patch(
                "runtime_archive_verification.validate_provenance_envelope",
                return_value={"status": "passed", "errors": []},
            ),
            patch("runtime_archive_verification.stage_result_sha256", return_value="b" * 64),
        ):
            report = verify_runtime_archive_cryptographically(archive, policy)
        return report, anchor_verifier, stage_verifier

    def test_complete_archive_is_verified_with_external_trust_roots(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            archive, anchor_key, tsa_ca = self.make_archive(Path(temp))
            report, anchor_verifier, stage_verifier = self.verify_with_fixtures(
                archive, anchor_key, tsa_ca
            )
        self.assertEqual(report["status"], "runtime_archive_cryptographically_verified")
        self.assertEqual(report["verification_scope"], "offline_audit_only")
        self.assertEqual(anchor_verifier.call_args.args[2], anchor_key)
        self.assertEqual(stage_verifier.call_count, 1)
        self.assertTrue(report["limitations"])

    def test_external_trust_anchor_is_mandatory(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            archive, _, tsa_ca = self.make_archive(Path(temp))
            with self.assertRaisesRegex(RuntimeArchiveVerificationError, "external_trust_anchors_required"):
                verify_runtime_archive_cryptographically(archive, {"timestamp_ca_file": tsa_ca})

    def test_signed_execution_context_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            archive, anchor_key, tsa_ca = self.make_archive(Path(temp), bad_context=True)
            with (
                patch(
                    "runtime_archive_verification.verify_history_anchor",
                    return_value={
                        "status": "signed_checkpoint_verified",
                        "checkpoint": {"event_count": 0, "head_sha256": "0" * 64},
                        "timestamp": {"status": "verified"},
                    },
                ),
                patch(
                    "runtime_archive_verification.validate_provenance_envelope",
                    return_value={"status": "passed", "errors": []},
                ),
            ):
                with patch("runtime_archive_verification.verify_archived_bundle") as stage_verifier:
                    with self.assertRaisesRegex(
                        RuntimeArchiveVerificationError, "signed_execution_context_mismatch"
                    ):
                        verify_runtime_archive_cryptographically(
                            archive,
                            {
                                "history_anchor_public_key": anchor_key,
                                "history_anchor_key_id": "external-anchor",
                                "timestamp_ca_file": tsa_ca,
                            },
                        )
                    stage_verifier.assert_not_called()

    def test_incomplete_run_cannot_be_reported_as_verified(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            archive, anchor_key, tsa_ca = self.make_archive(Path(temp))
            metadata_path = archive / "archive.json"
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            metadata["run_status"] = "incomplete"
            metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
            from runtime_run_archive import MANIFEST_NAME
            manifest_path = archive / MANIFEST_NAME
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            import hashlib
            data = metadata_path.read_bytes()
            entry = next(item for item in manifest["entries"] if item["path"] == "archive.json")
            entry["size"] = len(data)
            entry["sha256"] = hashlib.sha256(data).hexdigest()
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeArchiveVerificationError, "archive_run_not_completed"):
                verify_runtime_archive_cryptographically(archive, {
                    "history_anchor_public_key": anchor_key,
                    "history_anchor_key_id": "external-anchor",
                    "timestamp_ca_file": tsa_ca,
                })


if __name__ == "__main__":
    unittest.main()
