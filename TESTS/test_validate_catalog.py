#!/usr/bin/env python3
"""Security regression tests for catalog path validation."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from validate_catalog import validate


def catalog_document(record: str) -> dict:
    return {
        "schema_version": "1.0",
        "catalog_updated": "2026-11-28",
        "tools": [{
            "id": "demo-tool",
            "name": "Demo Tool",
            "category": "test",
            "description": "Test record",
            "status": "reviewed",
            "record": record,
            "official_url": "https://example.com",
            "license": "MIT",
            "platforms": ["linux"],
            "last_reviewed": "2026-11-28",
            "verification": {
                "source_reviewed": True,
                "license_reviewed": True,
                "installation_tested": False,
                "runtime_tested": False,
            },
        }],
    }


class CatalogPathSecurityTests(unittest.TestCase):
    def test_rejects_record_symlink_escaping_repository(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "repo"
            (root / "CATALOG").mkdir(parents=True)
            tools_dir = root / "TOOLS"
            tools_dir.mkdir()
            outside = Path(temp_dir) / "outside.md"
            outside.write_text(
                "- **ID:** `demo-tool`\n- **Status:** `reviewed`\n",
                encoding="utf-8",
            )
            (tools_dir / "linked.md").symlink_to(outside)
            catalog_path = root / "CATALOG" / "tools.json"
            catalog_path.write_text(
                json.dumps(catalog_document("TOOLS/linked.md")),
                encoding="utf-8",
            )

            errors = validate(root, catalog_path)

            self.assertTrue(any("record must stay inside the repository" in error for error in errors))

    def test_rejects_catalog_file_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "repo"
            catalog_dir = root / "CATALOG"
            catalog_dir.mkdir(parents=True)
            outside = Path(temp_dir) / "outside.json"
            outside.write_text(json.dumps(catalog_document("TOOLS/demo.md")), encoding="utf-8")
            catalog_path = catalog_dir / "tools.json"
            catalog_path.symlink_to(outside)

            errors = validate(root, catalog_path)

            self.assertTrue(any("Catalog path must stay inside the repository" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
