from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from trust_registry import (  # noqa: E402
    TrustRegistryError,
    public_key_fingerprint,
    resolve_trusted_key,
)


class TrustRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.key_root = self.root / "keys"
        self.key_root.mkdir()
        self.private_key = self.root / "private.pem"
        self.public_key = self.key_root / "approved.pub"
        subprocess.run(
            ["openssl", "genpkey", "-algorithm", "ED25519", "-out", str(self.private_key)],
            check=True, capture_output=True, timeout=15,
        )
        subprocess.run(
            ["openssl", "pkey", "-in", str(self.private_key), "-pubout", "-out", str(self.public_key)],
            check=True, capture_output=True, timeout=15,
        )
        self.registry_path = self.root / "trust-registry.json"
        self.now = datetime(2026, 11, 28, 12, 0, tzinfo=timezone.utc)
        self.entry = {
            "key_id": "runtime-signing-2026-01",
            "algorithm": "Ed25519",
            "public_key_file": "approved.pub",
            "public_key_sha256": public_key_fingerprint(self.public_key),
            "status": "active",
            "not_before": "2026-01-01T00:00:00Z",
            "not_after": "2027-01-01T00:00:00Z",
            "allowed_producers": ["crypto-security"],
            "allowed_artifact_types": ["security.review"],
        }
        self.write_registry([self.entry])

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write_registry(self, entries) -> None:
        self.registry_path.write_text(
            json.dumps({"registry_version": "1.0", "keys": entries}),
            encoding="utf-8",
        )

    def resolve(self, key_id="runtime-signing-2026-01", producer="crypto-security", artifact="security.review"):
        return resolve_trusted_key(
            self.registry_path, self.key_root, key_id, producer, artifact, self.now
        )

    def test_active_key_with_matching_fingerprint_and_scope_passes(self) -> None:
        result = self.resolve()
        self.assertEqual(result["status"], "active")
        self.assertEqual(result["public_key_sha256"], self.entry["public_key_sha256"])

    def test_revoked_key_is_rejected(self) -> None:
        entry = {**self.entry, "status": "revoked"}
        self.write_registry([entry])
        with self.assertRaisesRegex(TrustRegistryError, "signing_key_not_active"):
            self.resolve()

    def test_retired_key_is_rejected(self) -> None:
        self.write_registry([{**self.entry, "status": "retired"}])
        with self.assertRaisesRegex(TrustRegistryError, "signing_key_not_active"):
            self.resolve()

    def test_expired_key_is_rejected(self) -> None:
        self.write_registry([{**self.entry, "not_after": "2026-11-28T11:59:59Z"}])
        with self.assertRaisesRegex(TrustRegistryError, "signing_key_outside_validity_window"):
            self.resolve()

    def test_not_yet_valid_key_is_rejected(self) -> None:
        self.write_registry([{**self.entry, "not_before": "2026-11-28T12:00:01Z"}])
        with self.assertRaisesRegex(TrustRegistryError, "signing_key_outside_validity_window"):
            self.resolve()

    def test_wrong_fingerprint_is_rejected(self) -> None:
        self.write_registry([{**self.entry, "public_key_sha256": "0" * 64}])
        with self.assertRaisesRegex(TrustRegistryError, "trusted_public_key_fingerprint_mismatch"):
            self.resolve()

    def test_unauthorized_producer_is_rejected(self) -> None:
        with self.assertRaisesRegex(TrustRegistryError, "producer_not_authorized_for_key"):
            self.resolve(producer="devops-vps")

    def test_unauthorized_artifact_type_is_rejected(self) -> None:
        with self.assertRaisesRegex(TrustRegistryError, "artifact_type_not_authorized_for_key"):
            self.resolve(artifact="deployment.change")

    def test_duplicate_key_id_is_rejected(self) -> None:
        self.write_registry([self.entry, self.entry])
        with self.assertRaisesRegex(TrustRegistryError, "key_id_missing_or_duplicated"):
            self.resolve()

    def test_path_traversal_is_rejected(self) -> None:
        self.write_registry([{**self.entry, "public_key_file": "../private.pem"}])
        with self.assertRaisesRegex(TrustRegistryError, "public_key_path_must_be_relative"):
            self.resolve()

    def test_changed_public_key_is_rejected(self) -> None:
        other_private = self.root / "other-private.pem"
        other_public = self.key_root / "other.pub"
        subprocess.run(
            ["openssl", "genpkey", "-algorithm", "ED25519", "-out", str(other_private)],
            check=True, capture_output=True, timeout=15,
        )
        subprocess.run(
            ["openssl", "pkey", "-in", str(other_private), "-pubout", "-out", str(other_public)],
            check=True, capture_output=True, timeout=15,
        )
        other_public.replace(self.public_key)
        with self.assertRaisesRegex(TrustRegistryError, "trusted_public_key_fingerprint_mismatch"):
            self.resolve()


if __name__ == "__main__":
    unittest.main()
