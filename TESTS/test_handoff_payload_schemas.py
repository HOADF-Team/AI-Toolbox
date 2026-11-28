from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "TESTS" / "fixtures" / "inter-skill-demo"
sys.path.insert(0, str(ROOT / "scripts"))
from handoff_payload_schemas import validate_payload_schemas, validate_stage_payloads  # noqa: E402


class HandoffPayloadSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.workflow = json.loads((ROOT / "CATALOG" / "workflows" / "workflows.json").read_text(encoding="utf-8"))["workflows"][0]
        cls.interfaces = json.loads((ROOT / "CATALOG" / "skill-interfaces.json").read_text(encoding="utf-8"))
        cls.schemas = json.loads((ROOT / "CATALOG" / "handoff-payload-schemas.json").read_text(encoding="utf-8"))
        cls.artifacts = [json.loads((FIXTURE / "handoffs" / f"{stage['id']}.json").read_text(encoding="utf-8")) for stage in cls.workflow["stages"]]

    def report(self, artifacts=None):
        return validate_stage_payloads(self.workflow, self.interfaces, self.schemas,
                                       copy.deepcopy(self.artifacts if artifacts is None else artifacts))

    def test_schema_catalog_valid(self):
        self.assertEqual(validate_payload_schemas(self.schemas)["status"], "passed")

    def test_required_flag_must_be_boolean(self):
        bad = copy.deepcopy(self.schemas)
        bad["artifacts"][0]["required"] = "yes"
        self.assertIn("artifact_schema_0:required_must_be_boolean",
                      validate_payload_schemas(bad)["errors"])

    def test_nested_schema_required_field_must_be_declared(self):
        bad = copy.deepcopy(self.schemas)
        bad["artifacts"][2]["items"]["required"].append("missing_property")
        self.assertTrue(any("required_property_not_declared" in error
                            for error in validate_payload_schemas(bad)["errors"]))

    def test_schema_rejects_unsupported_keywords(self):
        bad = copy.deepcopy(self.schemas)
        bad["artifacts"][0]["pattern"] = ".*"
        self.assertTrue(any("unsupported_schema_keywords" in error
                            for error in validate_payload_schemas(bad)["errors"]))

    def test_schema_rejects_enum_type_mismatch(self):
        bad = copy.deepcopy(self.schemas)
        bad["artifacts"][0]["enum"] = [False]
        self.assertIn("artifact_schema_0:enum_value_type_mismatch",
                      validate_payload_schemas(bad)["errors"])

    def test_reference_fixture_payloads_pass(self):
        report = self.report()
        self.assertEqual(report["status"], "passed", report["errors"])

    def test_missing_required_field_fails(self):
        bad = copy.deepcopy(self.artifacts)
        del bad[0]["risk"]
        self.assertIn("crypto-security.security.risk_assessment.risk:missing_required", self.report(bad)["errors"])

    def test_wrong_primitive_type_fails(self):
        bad = copy.deepcopy(self.artifacts)
        bad[2]["fixture_dependencies_installed"] = "false"
        self.assertTrue(any("expected_boolean" in error for error in self.report(bad)["errors"]))

    def test_boolean_is_not_accepted_as_integer(self):
        bad_schema = {"type": "integer"}
        from handoff_payload_schemas import _validate_value
        self.assertIn("value:expected_integer", _validate_value(True, bad_schema, "value"))

    def test_nested_array_item_type_fails(self):
        bad = copy.deepcopy(self.artifacts)
        bad[0]["incident_events"][0]["mode"] = 42
        self.assertTrue(any("expected_string" in error for error in self.report(bad)["errors"]))

    def test_enum_violation_fails(self):
        bad = copy.deepcopy(self.artifacts)
        bad[3]["production_changes"] = "performed"
        self.assertTrue(any("value_not_in_enum" in error for error in self.report(bad)["errors"]))

    def test_duplicate_stage_artifact_fails(self):
        bad = copy.deepcopy(self.artifacts)
        bad.append(copy.deepcopy(bad[0]))
        self.assertIn("duplicate_or_invalid_stage_artifact", self.report(bad)["errors"])


if __name__ == "__main__":
    unittest.main()
