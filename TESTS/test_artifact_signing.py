from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "TESTS"))
from local_tsa_fixture import issue_local_rfc3161_timestamp  # noqa: E402
from artifact_integrity import IntegrityVerificationError, verify_integrity_bundle  # noqa: E402
from artifact_signing import create_integrity_bundle  # noqa: E402
from trust_registry import public_key_fingerprint  # noqa: E402


class ArtifactSigningTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.evidence_root = self.root / "evidence"
        self.evidence_root.mkdir()
        (self.evidence_root / "scan.txt").write_text("synthetic evidence\n", encoding="utf-8")
        self.private_key = self.root / "private.pem"
        self.public_key = self.root / "public.pem"
        subprocess.run(
            ["openssl", "genpkey", "-algorithm", "ED25519", "-out", str(self.private_key)],
            check=True, capture_output=True, timeout=15,
        )
        os.chmod(self.private_key, 0o600)
        subprocess.run(
            ["openssl", "pkey", "-in", str(self.private_key), "-pubout", "-out", str(self.public_key)],
            check=True, capture_output=True, timeout=15,
        )
        self.fingerprint = public_key_fingerprint(self.public_key)
        self.envelope = {
            "envelope_version": "1.0",
            "artifact_id": "artifact.signing-test",
            "artifact_type": "test.result",
            "producer": {"kind": "tool", "id": "test-tool", "version": "1", "revision": "a" * 40},
            "source": {"repository": "HOADF-Team/AI-Toolbox", "revision": "a" * 40},
            "created_at": "2026-11-28T10:00:00Z",
            "inputs": [{"ref": "fixture:input", "artifact_type": "test.input"}],
            "payload": {"result": "synthetic"},
            "evidence": ["evidence:scan"],
            "verification": {
                "status": "structurally_validated", "method": "test",
                "checked_at": "2026-11-28T10:01:00Z", "limitations": ["synthetic fixture"],
            },
        }

    def tearDown(self) -> None:
        self.temp.cleanup()

    def sign(self, **overrides):
        args = {
            "envelope": self.envelope,
            "key_id": "test-signing-key",
            "private_key": self.private_key,
            "trusted_public_key": self.public_key,
            "expected_public_key_sha256": self.fingerprint,
            "evidence_root": self.evidence_root,
            "evidence_paths": {"evidence:scan": "scan.txt"},
        }
        args.update(overrides)
        return create_integrity_bundle(**args)

    def test_created_bundle_passes_existing_verifier(self) -> None:
        bundle = self.sign()
        report = verify_integrity_bundle(
            self.envelope, bundle, self.public_key, "test-signing-key", self.evidence_root
        )
        self.assertEqual(report["status"], "verified")
        self.assertEqual(report["verified_evidence"], ["evidence:scan"])

    def test_wrong_private_key_is_rejected(self) -> None:
        other = self.root / "other.pem"
        subprocess.run(
            ["openssl", "genpkey", "-algorithm", "ED25519", "-out", str(other)],
            check=True, capture_output=True, timeout=15,
        )
        os.chmod(other, 0o600)
        with self.assertRaisesRegex(
            IntegrityVerificationError, "signing_private_key_does_not_match_registered_key"
        ):
            self.sign(private_key=other)

    def test_private_key_with_open_permissions_is_rejected(self) -> None:
        os.chmod(self.private_key, 0o644)
        with self.assertRaisesRegex(
            IntegrityVerificationError, "signing_private_key_permissions_too_open"
        ):
            self.sign()

    def test_evidence_mapping_must_match_refs_exactly(self) -> None:
        with self.assertRaisesRegex(
            IntegrityVerificationError, "evidence_paths_must_match_envelope_refs_exactly"
        ):
            self.sign(evidence_paths={})

    def test_evidence_path_traversal_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            IntegrityVerificationError, "evidence_path_must_be_relative_and_confined"
        ):
            self.sign(evidence_paths={"evidence:scan": "../outside.txt"})

    def test_evidence_symlink_is_rejected(self) -> None:
        link = self.evidence_root / "linked.txt"
        link.symlink_to(self.evidence_root / "scan.txt")
        with self.assertRaisesRegex(IntegrityVerificationError, "evidence_symlink_not_allowed"):
            self.sign(evidence_paths={"evidence:scan": "linked.txt"})

    def test_envelope_change_invalidates_created_bundle(self) -> None:
        bundle = self.sign()
        changed = {**self.envelope, "payload": {"result": "tampered"}}
        with self.assertRaisesRegex(
            IntegrityVerificationError, "artifact_envelope_digest_mismatch"
        ):
            verify_integrity_bundle(
                changed, bundle, self.public_key, "test-signing-key", self.evidence_root
            )


    def test_run_bound_signature_verifies_for_exact_context(self) -> None:
        context = {
            "run_id": "run-2026-11-28-001",
            "workflow_id": "security-review-four-skill-chain",
            "stage_id": "crypto-security",
            "skill_id": "crypto-security",
            "input_ref": "scenario:demo",
        }
        bundle = self.sign(execution_context=context, ttl_seconds=300)
        report = verify_integrity_bundle(
            self.envelope, bundle, self.public_key, "test-signing-key", self.evidence_root,
            expected_execution_context=context, max_age_seconds=300,
        )
        self.assertEqual(report["replay_protection"], "run_stage_bound_and_time_limited")

    def test_artifact_verifier_accepts_real_local_rfc3161_signature_timestamp(self) -> None:
        bundle = self.sign()
        signature = base64.b64decode(bundle["signature"], validate=True)
        response, ca_bundle, tsa_cert = issue_local_rfc3161_timestamp(
            signature, self.root / "local-tsa"
        )
        report = verify_integrity_bundle(
            self.envelope,
            bundle,
            self.public_key,
            "test-signing-key",
            self.evidence_root,
            timestamp_response=response,
            timestamp_ca_file=ca_bundle,
            timestamp_untrusted_chain_file=tsa_cert,
            require_trusted_timestamp=True,
        )
        self.assertEqual(report["status"], "verified")
        self.assertEqual(report["trusted_timestamp"]["status"], "verified")
        self.assertTrue(report["trusted_timestamp"]["gen_time"].endswith("+00:00"))

    def test_trusted_timestamp_must_fall_inside_signed_execution_window(self) -> None:
        context = {
            "run_id": "run-timestamp-window",
            "workflow_id": "workflow-a",
            "stage_id": "stage-a",
            "skill_id": "skill-a",
            "input_ref": "input-a",
        }
        bundle = self.sign(execution_context=context, ttl_seconds=300)
        issued = datetime.fromisoformat(
            bundle["statement"]["execution_context"]["issued_at"].replace("Z", "+00:00")
        )
        response = self.root / "artifact.tsr"
        ca_bundle = self.root / "tsa-ca.pem"
        response.write_bytes(b"synthetic timestamp response")
        ca_bundle.write_text("synthetic TSA trust fixture\n", encoding="utf-8")
        with patch(
            "trust_registry_history.verify_rfc3161_timestamp",
            return_value={
                "status": "verified",
                "gen_time": (issued - timedelta(seconds=1)).isoformat(),
                "verification": "openssl_ts_verify_with_host_supplied_ca",
            },
        ):
            with self.assertRaisesRegex(
                IntegrityVerificationError, "trusted_timestamp_outside_execution_context_window"
            ):
                verify_integrity_bundle(
                    self.envelope, bundle, self.public_key, "test-signing-key",
                    self.evidence_root,
                    expected_execution_context=context,
                    timestamp_response=response,
                    timestamp_ca_file=ca_bundle,
                    require_trusted_timestamp=True,
                    now=issued + timedelta(seconds=10),
                )

    def test_signature_replay_in_another_run_is_rejected(self) -> None:
        context = {
            "run_id": "run-original",
            "workflow_id": "workflow-a",
            "stage_id": "stage-a",
            "skill_id": "skill-a",
            "input_ref": "input-a",
        }
        bundle = self.sign(execution_context=context)
        replay_context = {**context, "run_id": "run-replay"}
        with self.assertRaisesRegex(
            IntegrityVerificationError, "signed_execution_context_mismatch:run_id"
        ):
            verify_integrity_bundle(
                self.envelope, bundle, self.public_key, "test-signing-key", self.evidence_root,
                expected_execution_context=replay_context,
            )

    def test_signature_replay_for_another_stage_is_rejected(self) -> None:
        context = {
            "run_id": "run-a",
            "workflow_id": "workflow-a",
            "stage_id": "stage-a",
            "skill_id": "skill-a",
            "input_ref": "input-a",
        }
        bundle = self.sign(execution_context=context)
        replay_context = {**context, "stage_id": "stage-b"}
        with self.assertRaisesRegex(
            IntegrityVerificationError, "signed_execution_context_mismatch:stage_id"
        ):
            verify_integrity_bundle(
                self.envelope, bundle, self.public_key, "test-signing-key", self.evidence_root,
                expected_execution_context=replay_context,
            )

    def test_expired_run_bound_signature_is_rejected(self) -> None:
        context = {
            "run_id": "run-expired",
            "workflow_id": "workflow-a",
            "stage_id": "stage-a",
            "skill_id": "skill-a",
            "input_ref": "input-a",
        }
        bundle = self.sign(execution_context=context, ttl_seconds=60)
        with self.assertRaisesRegex(IntegrityVerificationError, "signed_execution_context_expired"):
            verify_integrity_bundle(
                self.envelope, bundle, self.public_key, "test-signing-key", self.evidence_root,
                expected_execution_context=context,
                now=datetime.now(timezone.utc) + timedelta(seconds=61),
            )

    def test_run_bound_signature_rejects_ttl_above_verifier_policy(self) -> None:
        context = {
            "run_id": "run-long",
            "workflow_id": "workflow-a",
            "stage_id": "stage-a",
            "skill_id": "skill-a",
            "input_ref": "input-a",
        }
        bundle = self.sign(execution_context=context, ttl_seconds=1200)
        with self.assertRaisesRegex(
            IntegrityVerificationError, "execution_context_ttl_exceeds_policy"
        ):
            verify_integrity_bundle(
                self.envelope, bundle, self.public_key, "test-signing-key", self.evidence_root,
                expected_execution_context=context, max_age_seconds=900,
            )


if __name__ == "__main__":
    unittest.main()
