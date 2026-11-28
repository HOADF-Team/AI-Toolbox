from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from runtime_run_archive import (  # noqa: E402
    RuntimeArchiveError,
    create_runtime_archive,
    verify_runtime_archive,
)


class RuntimeRunArchiveTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.source.mkdir()
        (self.source / "report.json").write_text('{"status":"synthetic"}\n', encoding="utf-8")
        (self.source / "stage.json").write_text('{"stage":"stage-a"}\n', encoding="utf-8")
        self.destination = self.root / "archive"
        self.metadata = {
            "run_id": "run-fixture-001",
            "workflow_id": "workflow-fixture",
            "stage_ids": ["stage-a"],
            "skill_ids": ["fixture-skill"],
            "personal_ai_library_revision": "a" * 40,
            "ai_toolbox_revision": "b" * 40,
            "created_at": "2026-11-28T12:00:00Z",
            "run_status": "completed",
            "verification_policy": {
                "require_trusted_timestamps": True,
                "require_registry_history": True,
            },
        }
        self.files = {
            "report/runtime-report.json": "report.json",
            "stages/000-stage-a/artifact.json": "stage.json",
        }

    def tearDown(self) -> None:
        self.temp.cleanup()

    def create(self) -> dict:
        return create_runtime_archive(
            self.source, self.destination, self.metadata, self.files
        )

    def test_create_and_verify_archive(self) -> None:
        report = self.create()
        self.assertEqual(report["status"], "archive_integrity_verified")
        self.assertEqual(report["file_count"], 3)
        self.assertEqual(report["run_id"], "run-fixture-001")
        self.assertEqual(report["verification_scope"], "file_integrity_only")

    def test_manifest_is_deterministically_sorted(self) -> None:
        self.create()
        manifest = json.loads((self.destination / "MANIFEST.json").read_text(encoding="utf-8"))
        paths = [entry["path"] for entry in manifest["entries"]]
        self.assertEqual(paths, sorted(paths))
        self.assertEqual(paths, [
            "archive.json",
            "report/runtime-report.json",
            "stages/000-stage-a/artifact.json",
        ])

    def test_tampered_file_is_rejected(self) -> None:
        self.create()
        target = self.destination / "report/runtime-report.json"
        target.write_text("tampered", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeArchiveError, "size_mismatch|digest_mismatch"):
            verify_runtime_archive(self.destination)

    def test_unlisted_file_is_rejected(self) -> None:
        self.create()
        (self.destination / "unexpected.txt").write_text("extra", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeArchiveError, "file_set_mismatch"):
            verify_runtime_archive(self.destination)

    def test_missing_file_is_rejected(self) -> None:
        self.create()
        (self.destination / "stages/000-stage-a/artifact.json").unlink()
        with self.assertRaisesRegex(RuntimeArchiveError, "file_set_mismatch"):
            verify_runtime_archive(self.destination)

    def test_symlink_in_source_is_rejected(self) -> None:
        outside = self.root / "outside.txt"
        outside.write_text("outside", encoding="utf-8")
        link = self.source / "linked.txt"
        try:
            link.symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks are unavailable on this platform")
        files = dict(self.files)
        files["evidence/linked.txt"] = "linked.txt"
        with self.assertRaisesRegex(RuntimeArchiveError, "source_symlink"):
            create_runtime_archive(self.source, self.destination, self.metadata, files)

    def test_unsafe_archive_path_is_rejected(self) -> None:
        files = dict(self.files)
        files["../escape.txt"] = "report.json"
        with self.assertRaisesRegex(RuntimeArchiveError, "unsafe_archive_path"):
            create_runtime_archive(self.source, self.destination, self.metadata, files)

    def test_duplicate_stage_id_is_rejected(self) -> None:
        metadata = dict(self.metadata)
        metadata["stage_ids"] = ["stage-a", "stage-a"]
        metadata["skill_ids"] = ["fixture-skill", "fixture-skill"]
        with self.assertRaisesRegex(RuntimeArchiveError, "duplicate_archive_stage_id"):
            create_runtime_archive(self.source, self.destination, metadata, self.files)

    def test_existing_destination_is_not_overwritten(self) -> None:
        self.destination.mkdir()
        with self.assertRaisesRegex(RuntimeArchiveError, "destination_already_exists"):
            self.create()

    def test_manifest_path_traversal_is_rejected(self) -> None:
        self.create()
        manifest_path = self.destination / "MANIFEST.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["entries"][0]["path"] = "../escape"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaisesRegex(RuntimeArchiveError, "unsafe_archive_path"):
            verify_runtime_archive(self.destination)


if __name__ == "__main__":
    unittest.main()
