from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from skill_selection_runtime_eval import (  # noqa: E402
    RuntimeExchangeError,
    build_runtime_requests,
    evaluate_runtime_exchange,
    validate_runtime_responses,
)


class RuntimeBenchmarkBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.benchmark: dict[str, Any] = json.loads(
            (ROOT / "TESTS" / "selection-benchmark" / "benchmark.json").read_text(
                encoding="utf-8"
            )
        )
        cls.skill_map: dict[str, Any] = json.loads(
            (ROOT / "CATALOG" / "skill-tools.json").read_text(encoding="utf-8")
        )
        cls.revision = "a" * 40
        cls.requests = build_runtime_requests(
            cls.benchmark, cls.skill_map, cls.revision, "unit-test-run"
        )

    def response_bundle(self) -> dict[str, Any]:
        responses = []
        for request in self.requests["requests"]:
            case = next(
                item for item in self.benchmark["cases"]
                if item["case_id"] == request["case_id"]
            )
            expected = case["expected_decision"]
            decision = (
                "abstain" if expected == "abstain"
                else "clarify" if expected == "abstain_or_clarify"
                else "select"
            )
            responses.append({
                "case_id": request["case_id"],
                "decision": decision,
                "selected_skills": case["required_skills"],
                "rationale": "Synthetic test planner rationale.",
            })
        return {
            "schema_version": "1.0",
            "run": dict(self.requests["run"]),
            "runtime": {"name": "test-runtime", "planner_version": "test-1"},
            "responses": responses,
        }

    def test_requests_cover_cases_without_gold_labels(self) -> None:
        serialized = json.dumps(self.requests)
        self.assertNotIn("required_skills", serialized)
        self.assertNotIn("acceptable_skills", serialized)
        self.assertNotIn("excluded_skills", serialized)
        self.assertEqual(len(self.requests["requests"]), 33)

    def test_invalid_revision_is_rejected(self) -> None:
        with self.assertRaisesRegex(RuntimeExchangeError, "40-character"):
            build_runtime_requests(
                self.benchmark, self.skill_map, "main", "bad-revision"
            )

    def test_complete_response_set_scores(self) -> None:
        report = evaluate_runtime_exchange(
            self.benchmark, self.requests, self.response_bundle(), self.skill_map
        )
        self.assertEqual(report["response_coverage"]["complete"], True)
        self.assertEqual(report["scoring"]["metrics"]["micro_f1"], 1.0)

    def test_missing_response_is_rejected(self) -> None:
        bundle = self.response_bundle()
        bundle["responses"].pop()
        with self.assertRaisesRegex(RuntimeExchangeError, "missing_case_responses"):
            validate_runtime_responses(self.requests, bundle, self.skill_map)

    def test_duplicate_response_is_rejected(self) -> None:
        bundle = self.response_bundle()
        bundle["responses"].append(dict(bundle["responses"][0]))
        with self.assertRaisesRegex(RuntimeExchangeError, "duplicate_case_id"):
            validate_runtime_responses(self.requests, bundle, self.skill_map)

    def test_unknown_skill_is_rejected(self) -> None:
        bundle = self.response_bundle()
        bundle["responses"][0]["selected_skills"] = ["made-up-skill"]
        with self.assertRaisesRegex(RuntimeExchangeError, "unknown_skill"):
            validate_runtime_responses(self.requests, bundle, self.skill_map)

    def test_run_revision_mismatch_is_rejected(self) -> None:
        bundle = self.response_bundle()
        bundle["run"]["skills_revision"] = "b" * 40
        with self.assertRaisesRegex(RuntimeExchangeError, "skills_revision"):
            validate_runtime_responses(self.requests, bundle, self.skill_map)

    def test_runtime_identity_is_required(self) -> None:
        bundle = self.response_bundle()
        bundle["runtime"]["name"] = ""
        with self.assertRaisesRegex(RuntimeExchangeError, "runtime.name"):
            validate_runtime_responses(self.requests, bundle, self.skill_map)


if __name__ == "__main__":
    unittest.main()
