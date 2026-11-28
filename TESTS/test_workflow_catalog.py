from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from workflow_catalog import (  # noqa: E402
    WorkflowCatalogError,
    find_exact_workflow,
    load_workflow_catalog,
    validate_workflow_catalog,
)


class WorkflowCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = json.loads(
            (ROOT / "CATALOG" / "workflows" / "workflows.json").read_text(encoding="utf-8")
        )
        cls.skill_map = json.loads(
            (ROOT / "CATALOG" / "skill-tools.json").read_text(encoding="utf-8")
        )

    def test_repository_catalog_passes(self) -> None:
        report = validate_workflow_catalog(self.catalog, self.skill_map)
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["workflow_count"], 1)

    def test_loads_catalog_from_trusted_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "workflows.json"
            path.write_text(json.dumps(self.catalog), encoding="utf-8")
            loaded = load_workflow_catalog(path, self.skill_map)
        self.assertEqual(loaded["catalog_id"], "hoadf-reviewed-workflows")

    def test_exact_ordered_match_returns_workflow(self) -> None:
        workflow = self.catalog["workflows"][0]
        selected = [stage["skill_id"] for stage in workflow["stages"]]
        self.assertEqual(find_exact_workflow(self.catalog, selected)["workflow_id"],
                         workflow["workflow_id"])

    def test_reordered_selection_does_not_match(self) -> None:
        self.assertIsNone(find_exact_workflow(
            self.catalog, ["code-audit", "crypto-security", "python-development", "devops-vps"]
        ))

    def test_draft_workflow_is_not_selectable(self) -> None:
        catalog = copy.deepcopy(self.catalog)
        catalog["workflows"][0]["catalog_status"] = "draft"
        self.assertIsNone(find_exact_workflow(
            catalog, [stage["skill_id"] for stage in catalog["workflows"][0]["stages"]]
        ))

    def test_duplicate_workflow_id_fails_validation(self) -> None:
        catalog = copy.deepcopy(self.catalog)
        catalog["workflows"].append(copy.deepcopy(catalog["workflows"][0]))
        report = validate_workflow_catalog(catalog, self.skill_map)
        self.assertEqual(report["status"], "failed")
        self.assertTrue(any("duplicate_workflow_id" in item for item in report["errors"]))

    def test_unknown_skill_reference_fails_validation(self) -> None:
        catalog = copy.deepcopy(self.catalog)
        catalog["workflows"][0]["stages"][0]["skill_id"] = "unknown-skill"
        report = validate_workflow_catalog(catalog, self.skill_map)
        self.assertTrue(any("unknown_skill" in item for item in report["errors"]))

    def test_rule_must_reference_existing_stage(self) -> None:
        catalog = copy.deepcopy(self.catalog)
        catalog["workflows"][0]["rules"][0]["stage"] = "missing-stage"
        report = validate_workflow_catalog(catalog, self.skill_map)
        self.assertTrue(any("unknown_stage" in item for item in report["errors"]))

    def test_unsupported_rule_type_fails_validation(self) -> None:
        catalog = copy.deepcopy(self.catalog)
        catalog["workflows"][0]["rules"][0]["type"] = "execute_shell"
        report = validate_workflow_catalog(catalog, self.skill_map)
        self.assertTrue(any("unsupported_type" in item for item in report["errors"]))

    def test_multiple_matching_templates_fail_closed(self) -> None:
        catalog = copy.deepcopy(self.catalog)
        catalog["workflows"].append(copy.deepcopy(catalog["workflows"][0]))
        with self.assertRaisesRegex(WorkflowCatalogError, "multiple"):
            find_exact_workflow(
                catalog,
                [stage["skill_id"] for stage in catalog["workflows"][0]["stages"]],
            )


if __name__ == "__main__":
    unittest.main()
