from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from archival_verification import verify_archived_bundle  # noqa: E402
from artifact_integrity import IntegrityVerificationError  # noqa: E402
from artifact_signing import create_integrity_bundle  # noqa: E402
from trust_registry import public_key_fingerprint  # noqa: E402
from trust_registry_history import (  # noqa: E402
    build_history_checkpoint, build_history_record, registry_snapshot_sha256,
)


class ArchivalVerificationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.key_root = self.root / "keys"
        self.key_root.mkdir()
        self.evidence_root = self.root / "evidence"
        self.evidence_root.mkdir()
        (self.evidence_root / "scan.txt").write_text("archived fixture\n", encoding="utf-8")
        self.private_key = self.root / "private.pem"
        self.public_key = self.key_root / "archived.pub"
        subprocess.run(
            ["openssl", "genpkey", "-algorithm", "ED25519", "-out", str(self.private_key)],
            check=True, capture_output=True, timeout=15,
        )
        os.chmod(self.private_key, 0o600)
        subprocess.run(
            ["openssl", "pkey", "-in", str(self.private_key), "-pubout", "-out", str(self.public_key)],
            check=True, capture_output=True, timeout=15,
        )
        self.registry_path = self.root / "registry.json"
        self.entry = {
            "key_id": "archive-key-2026",
            "algorithm": "Ed25519",
            "public_key_file": "archived.pub",
            "public_key_sha256": public_key_fingerprint(self.public_key),
            "status": "retired",
            "retired_at": "2026-12-01T00:00:00Z",
            "not_before": "2026-01-01T00:00:00Z",
            "not_after": "2027-01-01T00:00:00Z",
            "allowed_producers": ["crypto-security"],
            "allowed_artifact_types": ["security.review"],
        }
        self.write_registry(self.entry)
        self.envelope = {
            "envelope_version": "1.0",
            "artifact_id": "archived.security.review.001",
            "artifact_type": "security.review",
            "producer": {
                "kind": "skill", "id": "crypto-security", "version": "1",
                "revision": "a" * 40,
            },
            "source": {"repository": "HOADF-Team/Personal-AI-Library", "revision": "a" * 40},
            "created_at": "2026-06-01T12:00:00Z",
            "inputs": [{"ref": "fixture:input", "artifact_type": "task"}],
            "payload": {"decision": "synthetic-pass"},
            "evidence": ["evidence:scan"],
            "verification": {
                "status": "structurally_validated", "method": "fixture",
                "checked_at": "2026-06-01T12:01:00Z", "limitations": ["synthetic archive"],
            },
        }

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write_registry(self, entry) -> None:
        self.registry_path.write_text(
            json.dumps({"registry_version": "1.0", "keys": [entry]}),
            encoding="utf-8",
        )

    def sign(self, envelope=None, execution_context=None):
        return create_integrity_bundle(
            envelope=envelope or self.envelope,
            key_id="archive-key-2026",
            private_key=self.private_key,
            trusted_public_key=self.public_key,
            expected_public_key_sha256=self.entry["public_key_sha256"],
            evidence_root=self.evidence_root,
            evidence_paths={"evidence:scan": "scan.txt"},
            execution_context=execution_context,
            ttl_seconds=300,
        )

    def verify(
        self, envelope=None, bundle=None, history_records=None,
        history_checkpoint=None, require_history=False, registry_snapshots=None,
    ):
        return verify_archived_bundle(
            envelope or self.envelope,
            bundle or self.sign(),
            self.registry_path,
            self.key_root,
            self.evidence_root,
            history_records,
            history_checkpoint,
            require_history,
            registry_snapshots,
        )

    def valid_history(self, retired_at=None):
        effective_retirement = retired_at or self.entry["retired_at"]
        active_entry = {**self.entry, "status": "active"}
        active_entry.pop("retired_at", None)
        retired_entry = {**self.entry, "retired_at": effective_retirement}
        added_snapshot = {"registry_version": "1.0", "keys": [active_entry]}
        retired_snapshot = {"registry_version": "1.0", "keys": [retired_entry]}
        added_digest = registry_snapshot_sha256(added_snapshot)
        retired_digest = registry_snapshot_sha256(retired_snapshot)
        added = build_history_record({
            "event_id": "archive-key-added",
            "action": "key_added",
            "key_id": "archive-key-2026",
            "effective_at": "2026-01-01T00:00:00Z",
            "registry_sha256": added_digest,
        }, 1)
        retired = build_history_record({
            "event_id": "archive-key-retired",
            "action": "key_retired",
            "key_id": "archive-key-2026",
            "effective_at": effective_retirement,
            "registry_sha256": retired_digest,
        }, 2, added["event_sha256"])
        records = [added, retired]
        snapshots = {added_digest: added_snapshot, retired_digest: retired_snapshot}
        return records, build_history_checkpoint(records), snapshots

    def test_retired_key_verifies_artifact_signed_before_retirement(self) -> None:
        report = self.verify()
        self.assertEqual(report["status"], "archived_verified")
        self.assertEqual(report["trust_resolution"]["status"], "retired")
        self.assertEqual(report["trust_resolution"]["verification_mode"], "historical")

    def test_revoked_key_is_never_accepted_for_archive(self) -> None:
        self.write_registry({
            **self.entry, "status": "revoked",
            "revoked_at": "2026-09-01T00:00:00Z",
            "revocation_reason": "suspected_compromise",
        })
        with self.assertRaisesRegex(ValueError, "signing_key_revoked"):
            self.verify()

    def test_artifact_signed_after_retirement_is_rejected(self) -> None:
        self.write_registry({
            **self.entry, "retired_at": "2026-05-01T00:00:00Z"
        })
        with self.assertRaisesRegex(ValueError, "historical_signature_after_key_retirement"):
            self.verify()

    def test_archived_signature_with_run_context_uses_signed_issue_time(self) -> None:
        context = {
            "run_id": "archived-run-001",
            "workflow_id": "security-review-four-skill-chain",
            "stage_id": "crypto-security",
            "skill_id": "crypto-security",
            "input_ref": "fixture:input",
        }
        bundle = self.sign(execution_context=context)
        report = self.verify(bundle=bundle)
        self.assertEqual(report["status"], "archived_verified")

    def test_tampered_envelope_is_rejected(self) -> None:
        bundle = self.sign()
        changed = {**self.envelope, "payload": {"decision": "tampered"}}
        with self.assertRaisesRegex(IntegrityVerificationError, "artifact_envelope_digest_mismatch"):
            self.verify(envelope=changed, bundle=bundle)


    def test_strict_archive_verification_requires_external_history_checkpoint(self) -> None:
        with self.assertRaisesRegex(
            ValueError, "authenticated_registry_history_and_snapshots_required"
        ):
            self.verify(require_history=True)

    def test_retired_key_passes_with_matching_authenticated_history(self) -> None:
        records, checkpoint, snapshots = self.valid_history()
        report = self.verify(
            history_records=records,
            history_checkpoint=checkpoint,
            require_history=True,
            registry_snapshots=snapshots,
        )
        self.assertEqual(report["status"], "archived_verified")
        self.assertEqual(report["history_verification"]["status"], "verified")

    def test_retirement_timestamp_must_match_history(self) -> None:
        records, checkpoint, snapshots = self.valid_history("2026-11-30T00:00:00Z")
        with self.assertRaisesRegex(ValueError, "registry_history_retirement_mismatch"):
            self.verify(
                history_records=records,
                history_checkpoint=checkpoint,
                require_history=True,
                registry_snapshots=snapshots,
            )

    def test_revocation_record_blocks_archival_verification(self) -> None:
        records, _, snapshots = self.valid_history()
        revoked = build_history_record({
            "event_id": "archive-key-revoked",
            "action": "key_revoked",
            "key_id": "archive-key-2026",
            "effective_at": "2026-12-02T00:00:00Z",
            "registry_sha256": "c" * 64,
            "reason": "compromise discovered",
        }, 3, records[-1]["event_sha256"])
        records.append(revoked)
        checkpoint = build_history_checkpoint(records)
        with self.assertRaisesRegex(ValueError, "registry_history_key_revoked"):
            self.verify(
                history_records=records,
                history_checkpoint=checkpoint,
                require_history=True,
                registry_snapshots=snapshots,
            )

    def test_tampered_history_checkpoint_blocks_archival_verification(self) -> None:
        records, checkpoint, snapshots = self.valid_history()
        bad_checkpoint = {**checkpoint, "head_sha256": "0" * 64}
        with self.assertRaisesRegex(ValueError, "history_head_checkpoint_mismatch"):
            self.verify(
                history_records=records,
                history_checkpoint=bad_checkpoint,
                require_history=True,
                registry_snapshots=snapshots,
            )


    def test_tampered_historical_registry_snapshot_is_rejected(self) -> None:
        records, checkpoint, snapshots = self.valid_history()
        digest = records[0]["event"]["registry_sha256"]
        snapshots[digest]["keys"][0]["status"] = "revoked"
        with self.assertRaisesRegex(ValueError, "registry_history_snapshot_digest_mismatch"):
            self.verify(
                history_records=records,
                history_checkpoint=checkpoint,
                require_history=True,
                registry_snapshots=snapshots,
            )


    def test_strict_archival_verification_accepts_old_key_with_rotation_history(self) -> None:
        replacement_private = self.root / "replacement-private.pem"
        replacement_public = self.key_root / "replacement.pub"
        subprocess.run(
            ["openssl", "genpkey", "-algorithm", "ED25519", "-out", str(replacement_private)],
            check=True, capture_output=True, timeout=15,
        )
        subprocess.run(
            ["openssl", "pkey", "-in", str(replacement_private), "-pubout", "-out", str(replacement_public)],
            check=True, capture_output=True, timeout=15,
        )
        replacement = {
            "key_id": "replacement-key-2026",
            "algorithm": "Ed25519",
            "public_key_file": "replacement.pub",
            "public_key_sha256": public_key_fingerprint(replacement_public),
            "status": "active",
            "not_before": "2026-12-01T00:00:00Z",
            "not_after": "2027-12-01T00:00:00Z",
            "allowed_producers": ["crypto-security"],
            "allowed_artifact_types": ["security.review"],
        }
        active_old = {**self.entry, "status": "active"}
        active_old.pop("retired_at", None)
        added_snapshot = {"registry_version": "1.0", "keys": [active_old]}
        rotated_old = {**self.entry, "status": "retired"}
        rotation_snapshot = {
            "registry_version": "1.0",
            "keys": [rotated_old, replacement],
        }
        added_digest = registry_snapshot_sha256(added_snapshot)
        rotation_digest = registry_snapshot_sha256(rotation_snapshot)
        added = build_history_record({
            "event_id": "old-key-added",
            "action": "key_added",
            "key_id": "archive-key-2026",
            "effective_at": "2026-01-01T00:00:00Z",
            "registry_sha256": added_digest,
        }, 1)
        rotated = build_history_record({
            "event_id": "old-key-rotated",
            "action": "key_rotated",
            "key_id": "archive-key-2026",
            "replacement_key_id": "replacement-key-2026",
            "reason": "planned rotation",
            "effective_at": self.entry["retired_at"],
            "registry_sha256": rotation_digest,
        }, 2, added["event_sha256"])
        records = [added, rotated]
        snapshots = {added_digest: added_snapshot, rotation_digest: rotation_snapshot}
        checkpoint = build_history_checkpoint(records)
        report = self.verify(
            history_records=records,
            history_checkpoint=checkpoint,
            require_history=True,
            registry_snapshots=snapshots,
        )
        self.assertEqual(report["status"], "archived_verified")
        self.assertEqual(
            report["history_verification"]["key_lifecycle"]["archive-key-2026"],
            "retired",
        )
        self.assertEqual(
            report["history_verification"]["key_lifecycle"]["replacement-key-2026"],
            "active",
        )


if __name__ == "__main__":
    unittest.main()
