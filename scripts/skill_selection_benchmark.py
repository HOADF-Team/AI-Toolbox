"""Offline semantic Skill-selection benchmark scorer; never invokes an LLM."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BENCHMARK = ROOT / "TESTS" / "selection-benchmark" / "benchmark.json"


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def validate_benchmark(data: dict[str, Any], catalog: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    ids = {
        item.get("id")
        for item in catalog.get("skills", [])
        if isinstance(item, dict)
    }
    cases = data.get("cases")
    if not isinstance(cases, list) or not cases:
        return ["cases_must_be_non_empty_array"]

    seen: set[str] = set()
    covered: set[str] = set()
    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            errors.append(f"case_{index}_must_be_object")
            continue
        case_id = case.get("case_id")
        if not isinstance(case_id, str) or not case_id:
            errors.append(f"case_{index}_missing_case_id")
        elif case_id in seen:
            errors.append(f"duplicate_case_id:{case_id}")
        else:
            seen.add(case_id)
        if not isinstance(case.get("task"), str) or not case["task"].strip():
            errors.append(f"{case_id}_missing_task")

        for field in (
            "required_skills",
            "acceptable_skills",
            "excluded_skills",
            "expected_order",
        ):
            values = case.get(field)
            if not isinstance(values, list) or any(
                not isinstance(item, str) for item in values
            ):
                errors.append(f"{case_id}_{field}_must_be_string_array")
                continue
            for skill_id in values:
                if skill_id not in ids:
                    errors.append(f"{case_id}_unknown_skill:{skill_id}")

        required = case.get("required_skills")
        if isinstance(required, list):
            covered.update(required)
        if case.get("expected_decision") not in {
            "select",
            "abstain",
            "abstain_or_clarify",
            "human_review",
        }:
            errors.append(f"{case_id}_invalid_expected_decision")
        if not isinstance(case.get("needs_human_review"), bool):
            errors.append(f"{case_id}_needs_human_review_must_be_boolean")

    missing = ids - covered
    if missing:
        errors.append("uncovered_skills:" + ",".join(sorted(missing)))
    return errors


def score_benchmark(
    benchmark: dict[str, Any],
    proposals: dict[str, Any],
    catalog: dict[str, Any],
) -> dict[str, Any]:
    errors = validate_benchmark(benchmark, catalog)
    if errors:
        return {"status": "invalid_benchmark", "errors": errors}

    rows = []
    true_positives = false_positives = false_negatives = 0
    exact_matches = eligible = order_checked = order_passed = 0
    abstain_expected = abstain_correct = rationale_present = 0
    per_skill: dict[str, dict[str, int]] = {}

    for case in benchmark["cases"]:
        case_id = case["case_id"]
        proposal = proposals.get(case_id, {})
        if not isinstance(proposal, dict):
            proposal = {}
        raw_selected = proposal.get("selected_skills", [])
        selected = (
            list(dict.fromkeys(item for item in raw_selected if isinstance(item, str)))
            if isinstance(raw_selected, list)
            else []
        )
        decision = proposal.get("decision", "select" if selected else "abstain")
        required = set(case["required_skills"])
        allowed = required | set(case["acceptable_skills"])
        chosen = set(selected)
        missing = required - chosen
        unnecessary = chosen - allowed

        if not case["needs_human_review"]:
            true_positives += len(required & chosen)
            false_positives += len(unnecessary)
            false_negatives += len(missing)
            eligible += 1

            decision_ok = (
                case["expected_decision"] not in {"abstain", "abstain_or_clarify"}
                or decision
                in (
                    {"abstain"}
                    if case["expected_decision"] == "abstain"
                    else {"abstain", "clarify"}
                )
            )
            exact_matches += int(chosen == required and decision_ok)

            if case["expected_decision"] in {"abstain", "abstain_or_clarify"}:
                abstain_expected += 1
                accepted = (
                    {"abstain"}
                    if case["expected_decision"] == "abstain"
                    else {"abstain", "clarify"}
                )
                abstain_correct += int(decision in accepted)

            expected_order = case.get("expected_order", [])
            if expected_order and not case.get("order_is_advisory", False):
                order_checked += 1
                position = -1
                correct_order = True
                for skill_id in expected_order:
                    try:
                        position = selected.index(skill_id, position + 1)
                    except ValueError:
                        correct_order = False
                        break
                order_passed += int(correct_order)

            rationale_present += int(
                isinstance(proposal.get("rationale"), str)
                and bool(proposal["rationale"].strip())
            )
            for skill_id in required:
                metrics = per_skill.setdefault(skill_id, {"tp": 0, "fn": 0})
                metrics["tp"] += int(skill_id in chosen)
                metrics["fn"] += int(skill_id not in chosen)

        rows.append(
            {
                "case_id": case_id,
                "kind": case["kind"],
                "excluded_from_aggregate": case["needs_human_review"],
                "decision": decision,
                "selected_skills": selected,
                "missing_required": sorted(missing),
                "unnecessary_skills": sorted(unnecessary),
                "exact_match": chosen == required,
                "rationale_present": bool(proposal.get("rationale")),
            }
        )

    denominator = true_positives + false_positives
    precision = (
        true_positives / denominator
        if denominator
        else (1.0 if true_positives + false_negatives == 0 else 0.0)
    )
    recall = (
        true_positives / (true_positives + false_negatives)
        if true_positives + false_negatives
        else 1.0
    )
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall
        else 0.0
    )
    per_skill_recall = {
        skill_id: round(values["tp"] / (values["tp"] + values["fn"]), 4)
        if values["tp"] + values["fn"]
        else 1.0
        for skill_id, values in sorted(per_skill.items())
    }

    return {
        "status": "scored",
        "benchmark_id": benchmark.get("benchmark_id"),
        "cases_total": len(benchmark["cases"]),
        "cases_scored": eligible,
        "cases_human_review": sum(
            bool(case["needs_human_review"]) for case in benchmark["cases"]
        ),
        "metrics": {
            "micro_precision": round(precision, 4),
            "micro_recall": round(recall, 4),
            "micro_f1": round(f1, 4),
            "exact_match_rate": round(exact_matches / eligible, 4) if eligible else 0.0,
            "ordered_chain_accuracy": (
                round(order_passed / order_checked, 4) if order_checked else None
            ),
            "abstention_accuracy": (
                round(abstain_correct / abstain_expected, 4)
                if abstain_expected
                else None
            ),
            "rationale_presence_rate": (
                round(rationale_present / eligible, 4) if eligible else 0.0
            ),
            "true_positives": true_positives,
            "false_positives": false_positives,
            "false_negatives": false_negatives,
        },
        "per_skill_recall": per_skill_recall,
        "case_results": rows,
        "limitations": [
            "Scores proposal JSON only; does not call an LLM or execute Skills.",
            "Rationale metric checks presence, not correctness.",
            "Annotations are manually curated and synthetic; ambiguous cases may need expert revision.",
            "Acceptable Skills are permitted alternatives and do not count as required recall.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
    parser.add_argument("--proposals", type=Path, required=True)
    parser.add_argument(
        "--skill-map", type=Path, default=ROOT / "CATALOG" / "skill-tools.json"
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    report = score_benchmark(
        load_json(args.benchmark),
        load_json(args.proposals),
        load_json(args.skill_map),
    )
    rendered = json.dumps(
        report, ensure_ascii=False, indent=2 if args.pretty else None
    ) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0 if report["status"] == "scored" else 2


if __name__ == "__main__":
    raise SystemExit(main())
