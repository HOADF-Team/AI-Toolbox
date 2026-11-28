from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from artifact_provenance import validate_provenance_envelope  # noqa: E402

SHA = "a" * 40
VALID = {
    "envelope_version": "1.0",
    "artifact_id": "artifact.security-risk-001",
    "artifact_type": "security.risk_assessment",
    "producer": {"kind": "skill", "id": "crypto-security", "version": "1.0", "revision": SHA},
    "source": {"repository": "HOADF-Team/Personal-AI-Library", "revision": SHA},
    "created_at": "2026-11-28T10:00:00Z",
    "inputs": [{"ref": "task.request", "artifact_type": "task.request"}],
    "payload": {"risk": "high"},
    "evidence": ["fixture:credential-log-observation"],
    "verification": {"status": "structurally_validated", "method": "unit-test",
                     "checked_at": "2026-11-28T10:01:00Z",
                     "limitations": ["synthetic fixture; no live system checked"]},
}


class ArtifactProvenanceTests(unittest.TestCase):
    def test_valid_envelope_passes(self):
        self.assertEqual(validate_provenance_envelope(VALID)["status"], "passed")

    def test_non_object_fails(self):
        self.assertIn("envelope_must_be_object", validate_provenance_envelope([])["errors"])

    def test_full_git_revision_required(self):
        bad = copy.deepcopy(VALID)
        bad["producer"]["revision"] = "abc123"
        self.assertIn("producer_revision_must_be_full_git_sha", validate_provenance_envelope(bad)["errors"])

    def test_timezone_aware_iso_timestamp_required(self):
        bad = copy.deepcopy(VALID)
        bad["created_at"] = "not-a-date"
        self.assertIn("created_at_must_be_iso8601_timestamp", validate_provenance_envelope(bad)["errors"])

    def test_duplicate_input_refs_fail(self):
        bad = copy.deepcopy(VALID)
        bad["inputs"].append(copy.deepcopy(bad["inputs"][0]))
        self.assertIn("inputs_1_duplicate_ref", validate_provenance_envelope(bad)["errors"])

    def test_independent_verification_requires_verifier_and_evidence(self):
        bad = copy.deepcopy(VALID)
        bad["verification"]["status"] = "independently_verified"
        self.assertIn("independent_verification_requires_verifier", validate_provenance_envelope(bad)["errors"])

    def test_bad_payload_digest_fails(self):
        bad = copy.deepcopy(VALID)
        bad["payload_sha256"] = "not-a-digest"
        self.assertIn("payload_sha256_must_be_64_lowercase_hex", validate_provenance_envelope(bad)["errors"])

    def test_unknown_verification_state_fails(self):
        bad = copy.deepcopy(VALID)
        bad["verification"]["status"] = "trusted"
        self.assertIn("invalid_verification_status", validate_provenance_envelope(bad)["errors"])


if __name__ == "__main__":
    unittest.main()
