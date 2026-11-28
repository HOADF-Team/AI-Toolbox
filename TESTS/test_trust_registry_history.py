from __future__ import annotations

import base64
import copy
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from trust_registry_history import (  # noqa: E402
    GENESIS_HASH,
    RegistryHistoryError,
    build_history_checkpoint,
    build_history_record,
    build_history_anchor_statement,
    registry_snapshot_sha256,
    verify_registry_history,
    verify_history_anchor,
    verify_rfc3161_timestamp,
)


class TrustRegistryHistoryTests(unittest.TestCase):
    def event(self, event_id, action, key_id="signing-key-2026", **extra):
        return {
            "event_id": event_id,
            "action": action,
            "key_id": key_id,
            "effective_at": "2026-06-01T12:00:00Z",
            "registry_sha256": "a" * 64,
            **extra,
        }

    def chain(self):
        first = build_history_record(self.event("evt-1", "key_added"), 1)
        second = build_history_record(
            self.event("evt-2", "key_retired"), 2, first["event_sha256"]
        )
        records = [first, second]
        return records, build_history_checkpoint(records)


    def _signed_anchor(self, root: Path):
        private_key = root / "anchor-private.pem"
        public_key = root / "anchor-public.pem"
        subprocess.run(
            ["openssl", "genpkey", "-algorithm", "ED25519", "-out", str(private_key)],
            check=True, capture_output=True, timeout=15,
        )
        subprocess.run(
            ["openssl", "pkey", "-in", str(private_key), "-pubout", "-out", str(public_key)],
            check=True, capture_output=True, timeout=15,
        )
        records, checkpoint = self.chain()
        statement = build_history_anchor_statement(
            "security-key-lifecycle", checkpoint, "2026-11-28T12:00:00Z", "external-anchor-2026"
        )
        statement_path = root / "anchor.json"
        signature_path = root / "anchor.sig"
        from artifact_integrity import canonical_json_bytes
        statement_path.write_bytes(canonical_json_bytes(statement))
        subprocess.run(
            ["openssl", "pkeyutl", "-sign", "-inkey", str(private_key), "-rawin",
             "-in", str(statement_path), "-out", str(signature_path)],
            check=True, capture_output=True, timeout=15,
        )
        anchor = {
            **statement,
            "signature": base64.b64encode(signature_path.read_bytes()).decode("ascii"),
        }
        return records, anchor, public_key

    def test_signed_external_anchor_authenticates_history_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            records, anchor, public_key = self._signed_anchor(Path(temp_dir))
            report = verify_history_anchor(records, anchor, public_key, "external-anchor-2026")
        self.assertEqual(report["status"], "signed_checkpoint_verified")
        self.assertEqual(report["history"]["event_count"], 2)
        self.assertEqual(report["log_id"], "security-key-lifecycle")

    def test_signed_external_anchor_rejects_tampered_history(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            records, anchor, public_key = self._signed_anchor(Path(temp_dir))
            changed = copy.deepcopy(records)
            changed[0]["event"]["reason"] = "tampered"
            with self.assertRaisesRegex(RegistryHistoryError, "history_event_hash_mismatch"):
                verify_history_anchor(changed, anchor, public_key, "external-anchor-2026")

    def test_signed_external_anchor_rejects_wrong_anchor_key_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            records, anchor, public_key = self._signed_anchor(Path(temp_dir))
            with self.assertRaisesRegex(RegistryHistoryError, "untrusted_history_anchor_key_id"):
                verify_history_anchor(records, anchor, public_key, "other-anchor")

    def test_signed_external_anchor_rejects_changed_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            records, anchor, public_key = self._signed_anchor(Path(temp_dir))
            changed = copy.deepcopy(anchor)
            changed["checkpoint"]["head_sha256"] = "f" * 64
            with self.assertRaisesRegex(RegistryHistoryError, "history_anchor_signature_verification_failed"):
                verify_history_anchor(records, changed, public_key, "external-anchor-2026")



    def test_rfc3161_timestamp_end_to_end_with_ephemeral_local_tsa(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            ca_key = root / "ca.key"
            ca_cert = root / "ca.pem"
            tsa_key = root / "tsa.key"
            tsa_csr = root / "tsa.csr"
            tsa_cert = root / "tsa.pem"
            tsa_ext = root / "tsa.ext"
            config = root / "tsa.cnf"
            serial = root / "tsa.srl"
            data_path = root / "statement.json"
            request_path = root / "request.tsq"
            response_path = root / "response.tsr"
            data = b'{"checkpoint":{"event_count":1,"head_sha256":"abc"}}'
            data_path.write_bytes(data)

            def run_openssl(*args: str) -> None:
                subprocess.run(
                    ["openssl", *args], check=True, capture_output=True, text=True, timeout=30
                )

            run_openssl(
                "req", "-x509", "-newkey", "rsa:2048", "-nodes",
                "-keyout", str(ca_key), "-out", str(ca_cert),
                "-subj", "/CN=HOADF Ephemeral Test Root", "-days", "2",
                "-addext", "basicConstraints=critical,CA:TRUE",
                "-addext", "keyUsage=critical,keyCertSign,cRLSign",
            )
            run_openssl(
                "req", "-new", "-newkey", "rsa:2048", "-nodes",
                "-keyout", str(tsa_key), "-out", str(tsa_csr),
                "-subj", "/CN=HOADF Ephemeral Test TSA",
            )
            tsa_ext.write_text(
                "basicConstraints=critical,CA:FALSE\\n"
                "keyUsage=critical,digitalSignature,nonRepudiation\\n"
                "extendedKeyUsage=critical,timeStamping\\n"
                "subjectKeyIdentifier=hash\\n"
                "authorityKeyIdentifier=keyid,issuer\\n",
                encoding="utf-8",
            )
            run_openssl(
                "x509", "-req", "-in", str(tsa_csr), "-CA", str(ca_cert),
                "-CAkey", str(ca_key), "-CAcreateserial", "-out", str(tsa_cert),
                "-days", "1", "-sha256", "-extfile", str(tsa_ext),
            )
            serial.write_text("01\\n", encoding="ascii")
            config.write_text(
                "[ tsa ]\\n"
                "default_tsa = tsa_config1\\n"
                "[ tsa_config1 ]\\n"
                f"serial = {serial}\\n"
                "crypto_device = builtin\\n"
                f"signer_cert = {tsa_cert}\\n"
                f"certs = {ca_cert}\\n"
                f"signer_key = {tsa_key}\\n"
                "signer_digest = sha256\\n"
                "default_policy = 1.2.3.4.1\\n"
                "digests = sha256, sha384, sha512\\n"
                "accuracy = secs:1\\n"
                "ordering = yes\\n"
                "tsa_name = yes\\n"
                "ess_cert_id_chain = no\\n",
                encoding="utf-8",
            )
            run_openssl(
                "ts", "-query", "-data", str(data_path), "-sha256", "-cert",
                "-out", str(request_path),
            )
            run_openssl(
                "ts", "-reply", "-config", str(config), "-queryfile",
                str(request_path), "-out", str(response_path),
            )
            report = verify_rfc3161_timestamp(
                data, response_path, ca_cert, tsa_cert
            )
            self.assertEqual(report["status"], "verified")
            self.assertTrue(report["gen_time"].endswith("+00:00"))

    def test_rfc3161_timestamp_requires_valid_response_and_trusted_ca(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            response = root / "response.tsr"
            ca_file = root / "trusted-ca.pem"
            response.write_bytes(b"synthetic timestamp response")
            ca_file.write_text("synthetic trusted CA", encoding="utf-8")
            verified = subprocess.CompletedProcess(
                args=["openssl"], returncode=0, stdout="Verification: OK", stderr=""
            )
            details = subprocess.CompletedProcess(
                args=["openssl"], returncode=0,
                stdout="Time Stamp: Nov 28 11:22:33 2026 GMT", stderr=""
            )
            with patch("trust_registry_history.subprocess.run", side_effect=[verified, details]) as run:
                report = verify_rfc3161_timestamp(b"exact signed statement", response, ca_file)
            self.assertEqual(report["status"], "verified")
            self.assertEqual(report["gen_time"], "2026-11-28T11:22:33+00:00")
            self.assertEqual(run.call_count, 2)
            self.assertIn("-CAfile", run.call_args_list[0].args[0])

    def test_rfc3161_timestamp_rejects_untrusted_or_invalid_response(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            response = root / "response.tsr"
            ca_file = root / "trusted-ca.pem"
            response.write_bytes(b"synthetic timestamp response")
            ca_file.write_text("synthetic trusted CA", encoding="utf-8")
            failed = subprocess.CompletedProcess(
                args=["openssl"], returncode=1, stdout="", stderr="verification failure"
            )
            with patch("trust_registry_history.subprocess.run", return_value=failed):
                with self.assertRaisesRegex(
                    RegistryHistoryError, "rfc3161_signature_or_trust_verification_failed"
                ):
                    verify_rfc3161_timestamp(b"exact signed statement", response, ca_file)

    def test_history_anchor_requires_timestamp_response_and_ca_together(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            records, anchor, public_key = self._signed_anchor(Path(temp_dir))
            with self.assertRaisesRegex(
                RegistryHistoryError, "timestamp_response_and_ca_must_be_supplied_together"
            ):
                verify_history_anchor(
                    records, anchor, public_key, "external-anchor-2026",
                    timestamp_response=Path(temp_dir) / "missing.tsr",
                )

    def test_valid_add_and_retirement_chain_passes_checkpoint(self) -> None:
        records, checkpoint = self.chain()
        report = verify_registry_history(records, checkpoint)
        self.assertEqual(report["status"], "verified")
        self.assertEqual(report["event_count"], 2)
        self.assertEqual(report["key_lifecycle"]["signing-key-2026"], "retired")

    def test_modified_event_is_detected(self) -> None:
        records, checkpoint = self.chain()
        changed = copy.deepcopy(records)
        changed[1]["event"]["effective_at"] = "2026-06-02T12:00:00Z"
        with self.assertRaisesRegex(RegistryHistoryError, "history_event_hash_mismatch"):
            verify_registry_history(changed, checkpoint)

    def test_reordered_events_are_rejected(self) -> None:
        records, checkpoint = self.chain()
        with self.assertRaisesRegex(RegistryHistoryError, "history_sequence_mismatch"):
            verify_registry_history(list(reversed(records)), checkpoint)

    def test_truncated_history_is_detected_by_external_checkpoint(self) -> None:
        records, checkpoint = self.chain()
        with self.assertRaisesRegex(
            RegistryHistoryError, "history_event_count_checkpoint_mismatch"
        ):
            verify_registry_history(records[:1], checkpoint)

    def test_changed_checkpoint_head_is_rejected(self) -> None:
        records, checkpoint = self.chain()
        bad = {**checkpoint, "head_sha256": "0" * 64}
        with self.assertRaisesRegex(
            RegistryHistoryError, "history_head_checkpoint_mismatch"
        ):
            verify_registry_history(records, bad)

    def test_wrong_previous_hash_is_rejected(self) -> None:
        first = build_history_record(self.event("evt-1", "key_added"), 1)
        second = build_history_record(
            self.event("evt-2", "key_retired"), 2, "f" * 64
        )
        records = [first, second]
        with self.assertRaisesRegex(
            RegistryHistoryError, "history_previous_hash_mismatch"
        ):
            verify_registry_history(records, build_history_checkpoint(records))

    def test_retirement_requires_prior_key_registration(self) -> None:
        record = build_history_record(self.event("evt-1", "key_retired"), 1)
        records = [record]
        with self.assertRaisesRegex(
            RegistryHistoryError, "key_retired_without_active_key"
        ):
            verify_registry_history(records, build_history_checkpoint(records))

    def test_revocation_after_retirement_is_terminal(self) -> None:
        first = build_history_record(self.event("evt-1", "key_added"), 1)
        second = build_history_record(
            self.event("evt-2", "key_retired"), 2, first["event_sha256"]
        )
        third = build_history_record(
            self.event("evt-3", "key_revoked", reason="suspected compromise"),
            3,
            second["event_sha256"],
        )
        report = verify_registry_history(
            [first, second, third],
            build_history_checkpoint([first, second, third]),
        )
        self.assertEqual(report["key_lifecycle"]["signing-key-2026"], "revoked")

    def test_duplicate_event_id_is_rejected(self) -> None:
        first = build_history_record(self.event("same-id", "key_added"), 1)
        second = build_history_record(
            self.event("same-id", "key_retired"), 2, first["event_sha256"]
        )
        records = [first, second]
        with self.assertRaisesRegex(RegistryHistoryError, "duplicate_history_event_id"):
            verify_registry_history(records, build_history_checkpoint(records))

    def test_rotation_event_requires_replacement_and_reason(self) -> None:
        event = self.event("evt-rotation", "key_rotated", replacement_key_id="next-key", reason="planned rotation")
        record = build_history_record(event, 1)
        with self.assertRaisesRegex(
            RegistryHistoryError, "key_rotated_without_active_key"
        ):
            verify_registry_history([record], build_history_checkpoint([record]))

    def test_first_record_requires_genesis_hash(self) -> None:
        with self.assertRaisesRegex(
            RegistryHistoryError, "first_event_must_use_genesis_hash"
        ):
            build_history_record(self.event("evt-1", "key_added"), 1, "1" * 64)

    def test_empty_history_uses_genesis_checkpoint(self) -> None:
        checkpoint = build_history_checkpoint([])
        self.assertEqual(checkpoint["head_sha256"], GENESIS_HASH)
        report = verify_registry_history([], checkpoint)
        self.assertEqual(report["status"], "verified")


    def test_registry_snapshot_digest_is_canonical(self) -> None:
        first = {"registry_version": "1.0", "keys": []}
        second = {"keys": [], "registry_version": "1.0"}
        self.assertEqual(registry_snapshot_sha256(first), registry_snapshot_sha256(second))


    def test_rotation_atomically_retires_old_key_and_activates_replacement(self) -> None:
        first = build_history_record(
            self.event("old-key-added", "key_added", key_id="old-key"), 1
        )
        rotation = build_history_record(
            self.event(
                "old-key-rotated",
                "key_rotated",
                key_id="old-key",
                replacement_key_id="new-key",
                reason="planned key rotation",
            ),
            2,
            first["event_sha256"],
        )
        records = [first, rotation]
        report = verify_registry_history(records, build_history_checkpoint(records))
        self.assertEqual(report["key_lifecycle"]["old-key"], "retired")
        self.assertEqual(report["key_lifecycle"]["new-key"], "active")

    def test_replacement_key_cannot_be_activated_twice(self) -> None:
        first = build_history_record(
            self.event("old-key-added", "key_added", key_id="old-key"), 1
        )
        rotation = build_history_record(
            self.event(
                "old-key-rotated",
                "key_rotated",
                key_id="old-key",
                replacement_key_id="new-key",
                reason="planned key rotation",
            ),
            2,
            first["event_sha256"],
        )
        duplicate = build_history_record(
            self.event("new-key-added-again", "key_added", key_id="new-key"),
            3,
            rotation["event_sha256"],
        )
        records = [first, rotation, duplicate]
        with self.assertRaisesRegex(
            RegistryHistoryError, "key_added_after_existing_lifecycle"
        ):
            verify_registry_history(records, build_history_checkpoint(records))


if __name__ == "__main__":
    unittest.main()
