from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
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


if __name__ == "__main__":
    unittest.main()
