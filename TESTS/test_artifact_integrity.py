from __future__ import annotations

import base64
import copy
import json
import subprocess
import tempfile
import unittest
from datetime import datetime, timezone
from unittest.mock import patch
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



    def test_published_canonical_json_golden_vectors(self) -> None:
        vector_path = ROOT / "TESTS" / "fixtures" / "canonical-json-vectors.json"
        fixture = json.loads(vector_path.read_text(encoding="utf-8"))
        self.assertEqual(fixture["profile_id"], "hoadf-python-json-v1")
        for vector in fixture["vectors"]:
            with self.subTest(vector=vector["id"]):
                encoded = canonical_json_bytes(vector["value"])
                self.assertEqual(encoded.decode("utf-8"), vector["canonical_utf8"])
                self.assertEqual(sha256_bytes(encoded), vector["sha256"])

    def test_canonical_json_rejects_non_string_object_keys(self) -> None:
        with self.assertRaisesRegex(
            IntegrityVerificationError, "canonical_json_object_keys_must_be_strings"
        ):
            canonical_json_bytes({1: "value"})

    def test_canonical_json_rejects_python_only_container_types(self) -> None:
        with self.assertRaisesRegex(
            IntegrityVerificationError, "value_is_not_json_data"
        ):
            canonical_json_bytes({"values": ("not", "a", "json-array")})


    def test_required_trusted_timestamp_cannot_be_omitted(self) -> None:
        with self.assertRaisesRegex(IntegrityVerificationError, "trusted_timestamp_required"):
            verify_integrity_bundle(
                self.envelope, self.bundle, self.public_key,
                "ci-ephemeral-test-key", self.evidence_root,
                require_trusted_timestamp=True,
            )

    def test_rfc3161_timestamp_verifies_exact_raw_ed25519_signature(self) -> None:
        response = self.root / "artifact.tsr"
        ca_bundle = self.root / "tsa-ca.pem"
        response.write_bytes(b"synthetic timestamp response fixture")
        ca_bundle.write_text("synthetic host trust bundle fixture\n", encoding="utf-8")
        generation_time = "2026-11-28T11:00:00+00:00"
        with patch(
            "trust_registry_history.verify_rfc3161_timestamp",
            return_value={
                "status": "verified",
                "gen_time": generation_time,
                "verification": "openssl_ts_verify_with_host_supplied_ca",
            },
        ) as timestamp_verifier:
            report = verify_integrity_bundle(
                self.envelope, self.bundle, self.public_key,
                "ci-ephemeral-test-key", self.evidence_root,
                timestamp_response=response,
                timestamp_ca_file=ca_bundle,
                require_trusted_timestamp=True,
                now=datetime(2026, 11, 28, 12, 0, tzinfo=timezone.utc),
            )
        self.assertEqual(report["trusted_timestamp"]["gen_time"], generation_time)
        self.assertEqual(
            timestamp_verifier.call_args.args[0],
            base64.b64decode(self.bundle["signature"], validate=True),
        )
        self.assertEqual(report["status"], "verified")

    def test_future_rfc3161_timestamp_is_rejected(self) -> None:
        response = self.root / "future.tsr"
        ca_bundle = self.root / "tsa-ca.pem"
        response.write_bytes(b"synthetic timestamp response fixture")
        ca_bundle.write_text("synthetic host trust bundle fixture\n", encoding="utf-8")
        with patch(
            "trust_registry_history.verify_rfc3161_timestamp",
            return_value={
                "status": "verified",
                "gen_time": "2026-11-28T13:00:00+00:00",
                "verification": "openssl_ts_verify_with_host_supplied_ca",
            },
        ):
            with self.assertRaisesRegex(
                IntegrityVerificationError, "trusted_timestamp_from_future"
            ):
                verify_integrity_bundle(
                    self.envelope, self.bundle, self.public_key,
                    "ci-ephemeral-test-key", self.evidence_root,
                    timestamp_response=response,
                    timestamp_ca_file=ca_bundle,
                    require_trusted_timestamp=True,
                    now=datetime(2026, 11, 28, 12, 0, tzinfo=timezone.utc),
                )

    def test_timestamp_response_and_ca_must_be_paired(self) -> None:
        response = self.root / "unpaired.tsr"
        response.write_bytes(b"fixture")
        with self.assertRaisesRegex(
            IntegrityVerificationError, "timestamp_response_and_ca_must_be_supplied_together"
        ):
            verify_integrity_bundle(
                self.envelope, self.bundle, self.public_key,
                "ci-ephemeral-test-key", self.evidence_root,
                timestamp_response=response,
            )


if __name__ == "__main__":
    unittest.main()
