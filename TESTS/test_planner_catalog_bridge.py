from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REVISION = "a" * 40
sys.path.insert(0, str(ROOT / "scripts"))

from planner_handoff_bridge import (  # noqa: E402
    PlannerHandoffBridgeError,
    prepare_workflow_from_catalog,
)


class PlannerCatalogBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.skill_map: dict[str, Any] = json.loads(
            (ROOT / "CATALOG" / "skill-tools.json").read_text(encoding="utf-8")
        )
        cls.catalog_path = ROOT / "CATALOG" / "workflows" / "workflows.json"
        cls.catalog = json.loads(cls.catalog_path.read_text(encoding="utf-8"))

    def make_skills_root(self) -> Path:
        root = Path(tempfile.mkdtemp())
        for stage in self.catalog["workflows"][0]["stages"]:
            skill_id = stage["skill_id"]
            manifest = root / "skills" / skill_id / "SKILL.md"
            manifest.parent.mkdir(parents=True, exist_ok=True)
            manifest.write_text(f"# {skill_id}\nMock canonical manifest", encoding="utf-8")
        return root

    def planner_result(self) -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "decision": "select",
            "selected_skills": [
                stage["skill_id"] for stage in self.catalog["workflows"][0]["stages"]
            ],
            "rationale": "The synthetic scenario needs a coordinated security review.",
            "run": {"skills_revision": REVISION},
            "runtime": {"name": "mock-runtime", "planner_version": "test"},
        }

    def test_catalog_drives_workflow_preparation(self) -> None:
        result = prepare_workflow_from_catalog(
            self.planner_result(), "Review synthetic fixture", "task:catalog-1",
            self.catalog_path, self.skill_map, self.make_skills_root(), REVISION,
        )
        self.assertEqual(result["status"], "prepared")
        self.assertEqual(result["workflow_catalog"]["catalog_id"], "hoadf-reviewed-workflows")
        self.assertEqual(result["workflow_catalog"]["eligible_template_count"], 1)
        self.assertFalse(result["execution_started"])

    def test_draft_template_is_not_selected(self) -> None:
        catalog = json.loads(json.dumps(self.catalog))
        catalog["workflows"][0]["catalog_status"] = "draft"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "workflows.json"
            path.write_text(json.dumps(catalog), encoding="utf-8")
            result = prepare_workflow_from_catalog(
                self.planner_result(), "Review fixture", "task:draft",
                path, self.skill_map, self.make_skills_root(), REVISION,
            )
        self.assertEqual(result["status"], "no_matching_reviewed_workflow")
        self.assertEqual(result["plan"], [])

    def test_invalid_catalog_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "workflows.json"
            path.write_text('{"schema_version":"1.0","catalog_id":"x","workflows":[]}', encoding="utf-8")
            with self.assertRaisesRegex(PlannerHandoffBridgeError, "catalog rejected"):
                prepare_workflow_from_catalog(
                    self.planner_result(), "Review fixture", "task:invalid",
                    path, self.skill_map, self.make_skills_root(), REVISION,
                )


if __name__ == "__main__":
    unittest.main()
