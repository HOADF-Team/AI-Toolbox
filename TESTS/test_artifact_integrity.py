from __future__ import annotations

import base64
import copy
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from artifact_integrity import (  # noqa: E402
    IntegrityVerificationError,
    canonical_json_bytes,
    sha256_bytes,
    verify_integrity_bundle,
)

SHA = "a" * 40


class ArtifactIntegrityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.evidence_root = self.root / "evidence"
        self.evidence_root.mkdir()
        (self.evidence_root / "scan.txt").write_text("clean fixture\n", encoding="utf-8")
        self.private_key = self.root / "private.pem"
        self.public_key = self.root / "public.pem"
        subprocess.run(
            ["openssl", "genpkey", "-algorithm", "ED25519", "-out", str(self.private_key)],
            check=True, capture_output=True, timeout=15,
        )
        subprocess.run(
            ["openssl", "pkey", "-in", str(self.private_key), "-pubout", "-out", str(self.public_key)],
            check=True, capture_output=True, timeout=15,
        )
        payload = {"result": "synthetic-clean"}
        self.envelope = {
            "envelope_version": "1.0",
            "artifact_id": "artifact.integrity-test",
            "artifact_type": "test.result",
            "producer": {"kind": "tool", "id": "test-tool", "version": "1", "revision": SHA},
            "source": {"repository": "HOADF-Team/AI-Toolbox", "revision": SHA},
            "created_at": "2026-11-28T10:00:00Z",
            "inputs": [{"ref": "fixture:input", "artifact_type": "test.input"}],
            "payload": payload,
            "evidence": ["evidence:scan"],
            "verification": {
                "status": "structurally_validated", "method": "test",
                "checked_at": "2026-11-28T10:01:00Z", "limitations": ["synthetic fixture"],
            },
            "payload_sha256": sha256_bytes(canonical_json_bytes(payload)),
        }
        evidence_item = {
            "ref": "evidence:scan",
            "path": "scan.txt",
            "sha256": sha256_bytes((self.evidence_root / "scan.txt").read_bytes()),
        }
        statement = {
            "statement_version": "1.0",
            "envelope_sha256": sha256_bytes(canonical_json_bytes(self.envelope)),
            "evidence": [evidence_item],
        }
        statement_file = self.root / "statement.json"
        signature_file = self.root / "statement.sig"
        statement_file.write_bytes(canonical_json_bytes(statement))
        subprocess.run(
            ["openssl", "pkeyutl", "-sign", "-inkey", str(self.private_key),
             "-rawin", "-in", str(statement_file), "-out", str(signature_file)],
            check=True, capture_output=True, timeout=15,
        )
        self.bundle = {
            "bundle_version": "1.0",
            "algorithm": "Ed25519",
            "key_id": "ci-ephemeral-test-key",
            "statement": statement,
            "signature": base64.b64encode(signature_file.read_bytes()).decode("ascii"),
        }

    def tearDown(self) -> None:
        self.temp.cleanup()

    def verify(self, envelope=None, bundle=None, key=None, key_id="ci-ephemeral-test-key"):
        return verify_integrity_bundle(
            envelope or self.envelope,
            bundle or self.bundle,
            key or self.public_key,
            key_id,
            self.evidence_root,
        )

    def test_valid_signature_and_evidence_pass(self) -> None:
        report = self.verify()
        self.assertEqual(report["status"], "verified")
        self.assertEqual(report["verified_evidence"], ["evidence:scan"])

    def test_modified_payload_is_rejected(self) -> None:
        bad = copy.deepcopy(self.envelope)
        bad["payload"]["result"] = "tampered"
        with self.assertRaisesRegex(IntegrityVerificationError, "artifact_envelope_digest_mismatch"):
            self.verify(envelope=bad)

    def test_payload_hash_mismatch_is_rejected(self) -> None:
        bad = copy.deepcopy(self.envelope)
        bad["payload"]["result"] = "tampered"
        with self.assertRaisesRegex(IntegrityVerificationError, "payload_digest_mismatch"):
            self.verify(envelope=bad, bundle={
                **self.bundle,
                "statement": {
                    **self.bundle["statement"],
                    "envelope_sha256": sha256_bytes(canonical_json_bytes(bad)),
                },
            })

    def test_modified_evidence_file_is_rejected(self) -> None:
        (self.evidence_root / "scan.txt").write_text("changed\n", encoding="utf-8")
        with self.assertRaisesRegex(IntegrityVerificationError, "evidence_digest_mismatch"):
            self.verify()

    def test_wrong_trust_key_id_is_rejected(self) -> None:
        with self.assertRaisesRegex(IntegrityVerificationError, "untrusted_signing_key_id"):
            self.verify(key_id="unexpected-key")

    def test_tampered_signature_is_rejected(self) -> None:
        bad = copy.deepcopy(self.bundle)
        bad["signature"] = base64.b64encode(b"not-a-valid-signature").decode("ascii")
        with self.assertRaisesRegex(IntegrityVerificationError, "signature_verification_failed"):
            self.verify(bundle=bad)

    def test_changed_statement_without_resigning_is_rejected(self) -> None:
        bad = copy.deepcopy(self.bundle)
        bad["statement"]["evidence"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(IntegrityVerificationError, "evidence_digest_mismatch"):
            self.verify(bundle=bad)

    def test_path_traversal_is_rejected(self) -> None:
        bad = copy.deepcopy(self.bundle)
        bad["statement"]["evidence"][0]["path"] = "../outside.txt"
        with self.assertRaisesRegex(IntegrityVerificationError, "evidence_path_must_be_relative"):
            self.verify(bundle=bad)


    def test_duplicate_envelope_evidence_references_are_rejected(self) -> None:
        bad = {**self.envelope, "evidence": ["evidence:scan", "evidence:scan"]}
        bad_bundle = copy.deepcopy(self.bundle)
        bad_bundle["statement"]["envelope_sha256"] = sha256_bytes(canonical_json_bytes(bad))
        with self.assertRaisesRegex(
            IntegrityVerificationError, "duplicate_envelope_evidence_reference"
        ):
            self.verify(envelope=bad, bundle=bad_bundle)

    def test_duplicate_manifest_evidence_references_are_rejected(self) -> None:
        bad = copy.deepcopy(self.bundle)
        bad["statement"]["evidence"].append(dict(bad["statement"]["evidence"][0]))
        with self.assertRaisesRegex(
            IntegrityVerificationError, "duplicate_evidence_manifest_reference"
        ):
            self.verify(bundle=bad)

    def test_manifest_entry_with_unknown_field_is_rejected(self) -> None:
        bad = copy.deepcopy(self.bundle)
        bad["statement"]["evidence"][0]["untrusted_path_hint"] = "../outside"
        with self.assertRaisesRegex(
            IntegrityVerificationError, "invalid_evidence_manifest_entry_fields"
        ):
            self.verify(bundle=bad)

    def test_malformed_manifest_digest_is_rejected(self) -> None:
        bad = copy.deepcopy(self.bundle)
        bad["statement"]["evidence"][0]["sha256"] = "not-a-digest"
        with self.assertRaisesRegex(
            IntegrityVerificationError, "invalid_evidence_sha256"
        ):
            self.verify(bundle=bad)


if __name__ == "__main__":
    unittest.main()
