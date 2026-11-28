from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from skill_selection_benchmark import score_benchmark, validate_benchmark  # noqa: E402


class SelectionBenchmarkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.benchmark = json.loads(
            (ROOT / "TESTS" / "selection-benchmark" / "benchmark.json").read_text(
                encoding="utf-8"
            )
        )
        cls.catalog = json.loads(
            (ROOT / "CATALOG" / "skill-tools.json").read_text(encoding="utf-8")
        )

    def test_schema_and_coverage(self) -> None:
        self.assertEqual(validate_benchmark(self.benchmark, self.catalog), [])

    def test_all_catalog_skills_covered(self) -> None:
        covered = {
            skill
            for case in self.benchmark["cases"]
            for skill in case["required_skills"]
        }
        catalog_ids = {item["id"] for item in self.catalog["skills"]}
        self.assertEqual(covered, catalog_ids)

    def test_perfect_proposals(self) -> None:
        proposals = {}
        for case in self.benchmark["cases"]:
            if case["needs_human_review"]:
                continue
            expected = case["expected_decision"]
            decision = (
                "abstain"
                if expected == "abstain"
                else "clarify"
                if expected == "abstain_or_clarify"
                else "select"
            )
            proposals[case["case_id"]] = {
                "selected_skills": case["required_skills"],
                "decision": decision,
                "rationale": "reason",
            }
        report = score_benchmark(self.benchmark, proposals, self.catalog)
        self.assertEqual(report["metrics"]["micro_f1"], 1.0)
        self.assertEqual(report["metrics"]["macro_f1"], 1.0)
        self.assertEqual(report["metrics"]["exact_match_rate"], 1.0)

    def test_wrong_decision_is_not_an_exact_match(self) -> None:
        report = score_benchmark(
            self.benchmark,
            {
                "single-01": {
                    "decision": "clarify",
                    "selected_skills": ["automation-vps"],
                    "rationale": "The skill is selected but the decision label is wrong.",
                }
            },
            self.catalog,
        )
        self.assertEqual(report["metrics"]["micro_f1"], 1.0)
        self.assertLess(report["metrics"]["decision_accuracy"], 1.0)
        self.assertLess(report["metrics"]["exact_match_rate"], 1.0)

    def test_unnecessary_skill_is_false_positive(self) -> None:
        proposals = {
            "single-01": {
                "selected_skills": ["automation-vps", "server-security"]
            }
        }
        report = score_benchmark(self.benchmark, proposals, self.catalog)
        result = next(
            row for row in report["case_results"] if row["case_id"] == "single-01"
        )
        self.assertEqual(result["unnecessary_skills"], ["server-security"])

    def test_missing_required_skill_is_false_negative(self) -> None:
        report = score_benchmark(
            self.benchmark, {"single-01": {"selected_skills": []}}, self.catalog
        )
        result = next(
            row for row in report["case_results"] if row["case_id"] == "single-01"
        )
        self.assertEqual(result["missing_required"], ["automation-vps"])

    def test_ambiguous_clarification(self) -> None:
        report = score_benchmark(
            self.benchmark,
            {"ambiguous-01": {"decision": "clarify", "selected_skills": []}},
            self.catalog,
        )
        self.assertEqual(report["status"], "scored")

    def test_human_review_case_is_excluded(self) -> None:
        report = score_benchmark(self.benchmark, {}, self.catalog)
        self.assertEqual(report["cases_human_review"], 1)

    def test_duplicate_case_is_rejected(self) -> None:
        benchmark = json.loads(json.dumps(self.benchmark))
        benchmark["cases"].append(benchmark["cases"][0])
        errors = validate_benchmark(benchmark, self.catalog)
        self.assertTrue(any("duplicate_case_id" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
