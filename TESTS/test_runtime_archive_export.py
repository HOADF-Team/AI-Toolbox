from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from runtime_archive_export import (  # noqa: E402
    RuntimeArchiveExportError,
    create_cryptographic_runtime_archive,
)


class RuntimeArchiveExportTests(unittest.TestCase):
    def make_source(self, root: Path, *, private_evidence: bool = False):
        source = root / "source"
        source.mkdir()
        revision = "a" * 40
        values = {
            "workflow/contract.json": {
                "workflow_id": "export-test",
                "root_input_ref": "root",
                "stages": [{"id": "alpha", "skill_id": "alpha", "required_fields": ["decision"]}],
            },
            "workflow/stages/alpha.json": {
                "stage": "alpha",
                "skill_id": "alpha",
                "input_ref": "root",
                "output_ref": "out:alpha",
                "status": "completed",
                "decision": "synthetic-pass",
                "evidence": [{"location": "fixture:proof", "observation": "synthetic only"}],
                "artifact_provenance": {"producer": {"id": "alpha"}},
                "integrity_bundle": {
                    "statement": {
                        "execution_context": {
                            "run_id": "run-export-001",
                            "workflow_id": "export-test",
                            "stage_id": "alpha",
                            "skill_id": "alpha",
                            "input_ref": "root",
                            "issued_at": "2026-11-28T10:00:00Z",
                            "expires_at": "2026-11-28T10:05:00Z",
                        },
                        "evidence": [{
                            "ref": "proof",
                            "path": "proof.txt",
                            "sha256": "d" * 64,
                        }]
                    }
                },
            },
            "trust/registry.json": {
                "registry_version": "1.0",
                "keys": [{"key_id": "test-key", "public_key_file": "test.pub"}],
            },
            "trust/history.json": [],
            "trust/history-checkpoint.json": {"event_count": 0, "head_sha256": "0" * 64},
            "trust/history-anchor.json": {"anchor_version": "1.0"},
        }
        for relative, value in values.items():
            path = source / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(value), encoding="utf-8")
        byte_files = {
            "workflow/stages/alpha/timestamp.tsr": b"synthetic timestamp response",
            "workflow/stages/alpha/evidence/proof.txt": (
                b"-----BEGIN PRIVATE KEY-----" if private_evidence else b"synthetic evidence"
            ),
            "trust/keys/test.pub": b"-----BEGIN PUBLIC KEY-----\nfixture\n",
            "trust/history-anchor.tsr": b"synthetic anchor timestamp",
        }
        for relative, data in byte_files.items():
            path = source / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        files = {
            relative: relative
            for relative in (*values.keys(), *byte_files.keys())
        }
        metadata = {
            "run_id": "run-export-001",
            "workflow_id": "export-test",
            "stage_ids": ["alpha"],
            "skill_ids": ["alpha"],
            "personal_ai_library_revision": revision,
            "ai_toolbox_revision": "b" * 40,
            "created_at": "2026-11-28T10:00:00Z",
            "run_status": "completed",
            "verification_policy": {"require_trusted_timestamp": True},
        }
        return source, files, metadata

    def test_complete_export_creates_verifier_compatible_package(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, files, metadata = self.make_source(root)
            report = create_cryptographic_runtime_archive(
                source, root / "archive", metadata, files
            )
            self.assertEqual(report["status"], "archive_integrity_verified")
            self.assertEqual(report["verification_scope"], "file_integrity_only")
            self.assertTrue((root / "archive" / "workflow" / "contract.json").is_file())
            self.assertTrue((root / "archive" / "trust" / "history-anchor.tsr").is_file())

    def test_missing_stage_timestamp_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, files, metadata = self.make_source(root)
            files.pop("workflow/stages/alpha/timestamp.tsr")
            with self.assertRaisesRegex(RuntimeArchiveExportError, "export_required_files_missing"):
                create_cryptographic_runtime_archive(
                    source, root / "archive", metadata, files
                )

    def test_private_key_material_is_never_exported(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, files, metadata = self.make_source(root, private_evidence=True)
            with self.assertRaisesRegex(RuntimeArchiveExportError, "private_key_material_not_allowed"):
                create_cryptographic_runtime_archive(
                    source, root / "archive", metadata, files
                )

    def test_unlisted_extra_files_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, files, metadata = self.make_source(root)
            extra = source / "extra.txt"
            extra.write_text("not in archive schema", encoding="utf-8")
            files["extra.txt"] = "extra.txt"
            with self.assertRaisesRegex(RuntimeArchiveExportError, "export_unexpected_files"):
                create_cryptographic_runtime_archive(
                    source, root / "archive", metadata, files
                )

    def test_non_timestamp_policy_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, files, metadata = self.make_source(root)
            metadata["verification_policy"]["require_trusted_timestamp"] = False
            with self.assertRaisesRegex(
                RuntimeArchiveExportError, "cryptographic_archive_requires_trusted_timestamps"
            ):
                create_cryptographic_runtime_archive(
                    source, root / "archive", metadata, files
                )


if __name__ == "__main__":
    unittest.main()
