from __future__ import annotations

import base64
import json
import os
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "TESTS"))
from local_tsa_fixture import issue_local_rfc3161_timestamp  # noqa: E402
from archival_verification import verify_archived_bundle  # noqa: E402
from artifact_integrity import IntegrityVerificationError  # noqa: E402
from artifact_signing import create_integrity_bundle  # noqa: E402
from trust_registry import public_key_fingerprint  # noqa: E402
from trust_registry_history import (  # noqa: E402
    build_history_checkpoint, build_history_record, registry_snapshot_sha256,
    verify_rfc3161_timestamp,
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
        **timestamp_policy,
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
            **timestamp_policy,
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

    def _timestamp_files(self):
        response = self.root / "archive.tsr"
        ca_bundle = self.root / "tsa-ca.pem"
        response.write_bytes(b"synthetic timestamp response")
        ca_bundle.write_text("synthetic TSA trust fixture\n", encoding="utf-8")
        return response, ca_bundle

    def test_required_archive_timestamp_uses_tsa_time_for_key_validity(self) -> None:
        response, ca_bundle = self._timestamp_files()
        timestamp = {
            "status": "verified",
            "gen_time": "2026-06-02T12:00:00+00:00",
            "verification": "openssl_ts_verify_with_host_supplied_ca",
        }
        with patch("archival_verification.verify_rfc3161_timestamp", return_value=timestamp), patch(
            "trust_registry_history.verify_rfc3161_timestamp", return_value=timestamp
        ):
            report = self.verify(
                timestamp_response=response,
                timestamp_ca_file=ca_bundle,
                require_trusted_timestamp=True,
            )
        self.assertEqual(report["status"], "archived_verified")
        self.assertEqual(report["trusted_timestamp"]["gen_time"], timestamp["gen_time"])

    def test_rfc3161_chain_validation_uses_token_generation_time(self) -> None:
        response, ca_bundle = self._timestamp_files()
        generation_time = datetime(2026, 6, 2, 12, 0, 0)
        details = subprocess.CompletedProcess(
            ["openssl", "ts", "-reply"], 0,
            stdout="Time stamp: Jun  2 12:00:00 2026 GMT\\n", stderr="",
        )
        verified = subprocess.CompletedProcess(
            ["openssl", "ts", "-verify"], 0, stdout="Verification: OK\\n", stderr="",
        )
        with patch("trust_registry_history.subprocess.run", side_effect=[details, verified]) as run:
            report = verify_rfc3161_timestamp(
                b"exact signed bytes", response, ca_bundle
            )
        verification_command = run.call_args_list[1].args[0]
        self.assertIn("-attime", verification_command)
        self.assertEqual(
            verification_command[verification_command.index("-attime") + 1],
            str(int(generation_time.replace(tzinfo=timezone.utc).timestamp())),
        )
        self.assertEqual(
            report["verification"],
            "openssl_ts_verify_with_host_supplied_ca_at_authenticated_gen_time",
        )

    def test_archival_verifier_accepts_real_local_rfc3161_timestamp(self) -> None:
        bundle = self.sign()
        signature = base64.b64decode(bundle["signature"], validate=True)
        response, ca_bundle, tsa_cert = issue_local_rfc3161_timestamp(
            signature, self.root / "archive-local-tsa"
        )
        timestamp = verify_rfc3161_timestamp(signature, response, ca_bundle, tsa_cert)
        generation_time = datetime.fromisoformat(
            timestamp["gen_time"].replace("Z", "+00:00")
        )
        self.entry = {
            **self.entry,
            "not_before": (generation_time - timedelta(days=2)).isoformat(),
            "not_after": (generation_time + timedelta(days=2)).isoformat(),
            "retired_at": (generation_time + timedelta(days=1)).isoformat(),
        }
        self.write_registry(self.entry)
        # Keep the exact envelope whose signature was timestamped above.
        report = self.verify(
            timestamp_response=response,
            timestamp_ca_file=ca_bundle,
            timestamp_untrusted_chain_file=tsa_cert,
            require_trusted_timestamp=True,
            now=generation_time + timedelta(seconds=30),
        )
        self.assertEqual(report["status"], "archived_verified")
        self.assertEqual(report["trusted_timestamp"]["gen_time"], timestamp["gen_time"])

    def test_archive_uses_tsa_time_instead_of_signer_created_at(self) -> None:
        response, ca_bundle = self._timestamp_files()
        earlier_envelope = {**self.envelope, "created_at": "2026-02-01T12:00:00Z"}
        self.write_registry({
            **self.entry,
            "retired_at": "2026-05-01T00:00:00Z",
        })
        timestamp = {
            "status": "verified",
            "gen_time": "2026-06-02T12:00:00+00:00",
            "verification": "openssl_ts_verify_with_host_supplied_ca",
        }
        with patch("archival_verification.verify_rfc3161_timestamp", return_value=timestamp), patch(
            "trust_registry_history.verify_rfc3161_timestamp", return_value=timestamp
        ):
            with self.assertRaisesRegex(ValueError, "historical_signature_after_key_retirement"):
                self.verify(
                    envelope=earlier_envelope,
                    bundle=self.sign(envelope=earlier_envelope),
                    timestamp_response=response,
                    timestamp_ca_file=ca_bundle,
                    require_trusted_timestamp=True,
                )

    def test_required_archive_timestamp_cannot_be_omitted(self) -> None:
        with self.assertRaisesRegex(ValueError, "trusted_timestamp_required"):
            self.verify(require_trusted_timestamp=True)

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


    def test_expired_signing_key_is_rejected_using_authenticated_tsa_time(self) -> None:
        bundle = self.sign()
        signature = base64.b64decode(bundle["signature"], validate=True)
        response, ca_bundle, tsa_cert = issue_local_rfc3161_timestamp(
            signature, self.root / "expired-key-local-tsa"
        )
        timestamp = verify_rfc3161_timestamp(signature, response, ca_bundle, tsa_cert)
        generation_time = datetime.fromisoformat(timestamp["gen_time"])
        self.write_registry({
            **self.entry,
            "not_before": (generation_time - timedelta(days=2)).isoformat(),
            "not_after": (generation_time - timedelta(seconds=1)).isoformat(),
            "retired_at": (generation_time + timedelta(days=1)).isoformat(),
        })
        with self.assertRaisesRegex(ValueError, "historical_signature_outside_key_validity"):
            self.verify(
                bundle=bundle,
                timestamp_response=response,
                timestamp_ca_file=ca_bundle,
                timestamp_untrusted_chain_file=tsa_cert,
                require_trusted_timestamp=True,
                now=generation_time + timedelta(seconds=30),
            )

    def test_substituted_tsa_trust_root_rejects_timestamp(self) -> None:
        bundle = self.sign()
        signature = base64.b64decode(bundle["signature"], validate=True)
        response, _, _ = issue_local_rfc3161_timestamp(
            signature, self.root / "original-local-tsa"
        )
        _, substituted_ca, substituted_tsa = issue_local_rfc3161_timestamp(
            b"independent fixture data", self.root / "substituted-local-tsa"
        )
        with self.assertRaisesRegex(ValueError, "rfc3161_signature_or_trust_verification_failed"):
            verify_rfc3161_timestamp(
                signature, response, substituted_ca, substituted_tsa
            )

    def test_missing_archived_evidence_is_rejected(self) -> None:
        bundle = self.sign()
        (self.evidence_root / "scan.txt").unlink()
        with self.assertRaisesRegex(ValueError, "evidence_file_missing_or_outside_root"):
            self.verify(bundle=bundle)


if __name__ == "__main__":
    unittest.main()
