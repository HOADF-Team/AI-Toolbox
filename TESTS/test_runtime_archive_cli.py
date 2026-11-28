from __future__ import annotations

import json
import tempfile
import unittest
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from runtime_archive_cli import (
    RuntimeArchiveCLIError,
    export_from_request,
    load_trust_policy,
    main,
)


class RuntimeArchiveCLITests(unittest.TestCase):
    def test_trust_config_resolves_paths_relative_to_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "anchor.pub").write_text("PUBLIC KEY FIXTURE", encoding="utf-8")
            (root / "tsa.pem").write_text("TSA CERTIFICATE FIXTURE", encoding="utf-8")
            config = root / "trust.json"
            config.write_text(json.dumps({
                "history_anchor_public_key": "anchor.pub",
                "history_anchor_key_id": "anchor-01",
                "timestamp_ca_file": "tsa.pem",
            }), encoding="utf-8")
            policy = load_trust_policy(config)
            self.assertEqual(policy["history_anchor_public_key"], root / "anchor.pub")
            self.assertEqual(policy["timestamp_ca_file"], root / "tsa.pem")
            self.assertTrue(policy["require_trusted_timestamps"])

    def test_trust_config_loads_paired_tsa_crls_for_strict_revocation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name in ("anchor.pub", "tsa.pem", "historical.crl", "current.crl"):
                (root / name).write_text("PUBLIC TRUST MATERIAL", encoding="utf-8")
            config = root / "trust.json"
            config.write_text(json.dumps({
                "history_anchor_public_key": "anchor.pub",
                "history_anchor_key_id": "anchor-01",
                "timestamp_ca_file": "tsa.pem",
                "historical_tsa_crl_file": "historical.crl",
                "current_tsa_crl_file": "current.crl",
                "require_tsa_revocation": True,
            }), encoding="utf-8")
            policy = load_trust_policy(config)
            self.assertTrue(policy["require_tsa_revocation"])
            self.assertEqual(policy["historical_tsa_crl_file"], root / "historical.crl")
            self.assertEqual(policy["current_tsa_crl_file"], root / "current.crl")

    def test_trust_config_requires_both_crls_when_revocation_is_required(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "anchor.pub").write_text("public", encoding="utf-8")
            (root / "tsa.pem").write_text("certificate", encoding="utf-8")
            config = root / "trust.json"
            config.write_text(json.dumps({
                "history_anchor_public_key": "anchor.pub",
                "history_anchor_key_id": "anchor",
                "timestamp_ca_file": "tsa.pem",
                "require_tsa_revocation": True,
            }), encoding="utf-8")
            with self.assertRaisesRegex(
                RuntimeArchiveCLIError, "trust_config_tsa_revocation_crls_required"
            ):
                load_trust_policy(config)

    def test_trust_config_rejects_unknown_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "anchor.pub").write_text("public", encoding="utf-8")
            (root / "tsa.pem").write_text("certificate", encoding="utf-8")
            config = root / "trust.json"
            config.write_text(json.dumps({
                "history_anchor_public_key": "anchor.pub",
                "history_anchor_key_id": "anchor",
                "timestamp_ca_file": "tsa.pem",
                "trust_archive_key": True,
            }), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeArchiveCLIError, "trust_config_unknown_fields"):
                load_trust_policy(config)

    def test_trust_config_rejects_private_key_material(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "anchor.pem").write_text(
                "-----BEGIN PRIVATE KEY-----\\nsecret\\n", encoding="utf-8"
            )
            (root / "tsa.pem").write_text("certificate", encoding="utf-8")
            config = root / "trust.json"
            config.write_text(json.dumps({
                "history_anchor_public_key": "anchor.pem",
                "history_anchor_key_id": "anchor",
                "timestamp_ca_file": "tsa.pem",
            }), encoding="utf-8")
            with self.assertRaisesRegex(
                RuntimeArchiveCLIError, "history_anchor_public_key_private_key_material"
            ):
                load_trust_policy(config)

    def test_export_request_requires_exact_explicit_file_map_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            request = root / "request.json"
            request.write_text(json.dumps({
                "source_root": ".",
                "destination": "archive",
                "metadata": {},
                "files": {},
                "discover_files": True,
            }), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeArchiveCLIError, "export_request_unknown_fields"):
                export_from_request(request)

    def test_export_delegates_to_existing_explicit_allowlist_exporter(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            request = root / "request.json"
            request.write_text(json.dumps({
                "source_root": ".",
                "destination": "archive",
                "metadata": {"run_id": "fixture"},
                "files": {"a.txt": "a.txt"},
            }), encoding="utf-8")
            expected = {"status": "archive_integrity_verified"}
            with patch("runtime_archive_cli.create_cryptographic_runtime_archive", return_value=expected) as exporter:
                report = export_from_request(request)
            self.assertEqual(report, expected)
            self.assertEqual(exporter.call_args.args[0], root)
            self.assertEqual(exporter.call_args.args[1], root / "archive")
            self.assertEqual(exporter.call_args.args[3], {"a.txt": "a.txt"})

    def test_cli_returns_nonzero_for_invalid_trust_configuration(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = root / "trust.json"
            config.write_text("{}", encoding="utf-8")
            result = main([
                "verify", "--archive", str(root / "archive"),
                "--trust-config", str(config),
            ])
            self.assertEqual(result, 2)


if __name__ == "__main__":
    unittest.main()
