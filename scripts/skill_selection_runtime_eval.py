"""Prepare and score benchmark exchanges with an externally hosted AI planner.

This module defines a transport boundary only. It never imports or invokes a model.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from skill_selection_benchmark import load_json, score_benchmark, validate_benchmark  # noqa: E402

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
DECISIONS = {"select", "abstain", "clarify"}


class RuntimeExchangeError(ValueError):
    """Raised when an external runtime exchange is incomplete or inconsistent."""


def build_runtime_requests(
    benchmark: dict[str, Any],
    skill_map: dict[str, Any],
    skills_revision: str,
    run_id: str,
) -> dict[str, Any]:
    """Build gold-label-free task requests for a separately operated planner."""
    if not SHA_RE.fullmatch(skills_revision):
        raise RuntimeExchangeError("skills_revision must be a lowercase full 40-character commit SHA")
    if not run_id.strip():
        raise RuntimeExchangeError("run_id must be non-empty")
    errors = validate_benchmark(benchmark, skill_map)
    if errors:
        raise RuntimeExchangeError("invalid benchmark: " + "; ".join(errors))

    skill_ids = sorted(item["id"] for item in skill_map["skills"])
    manifest_refs = {
        skill_id: (
            "https://github.com/HOADF-Team/Personal-AI-Library/blob/"
            f"{skills_revision}/skills/{skill_id}/SKILL.md"
        )
        for skill_id in skill_ids
    }
    requests = [
        {
            "case_id": case["case_id"],
            "task": case["task"],
            "available_skill_ids": skill_ids,
            "canonical_manifest_refs": manifest_refs,
            "instructions": (
                "Select only Skills needed to satisfy this task. If the task is "
                "underspecified, return clarify; if no catalog Skill is needed, "
                "return abstain. Do not infer approvals or perform external actions. "
                "Return one JSON object with case_id, decision, selected_skills, "
                "and rationale. Do not include hidden benchmark annotations."
            ),
        }
        for case in benchmark["cases"]
        if not case["needs_human_review"]
    ]
    return {
        "schema_version": "1.0",
        "exchange_type": "skill-selection-benchmark-requests",
        "benchmark_id": benchmark.get("benchmark_id"),
        "run": {
            "run_id": run_id,
            "skills_revision": skills_revision,
            "planner_contract_version": "1.0",
        },
        "candidate_skill_ids": skill_ids,
        "requests": requests,
        "gold_labels_included": False,
        "limitations": [
            "Requests contain synthetic task text and canonical manifest references only.",
            "The host runtime must independently resolve and read trusted Skill manifests.",
            "This file does not invoke an LLM, select Skills, or perform tool actions.",
        ],
    }


def validate_request_bundle(
    benchmark: dict[str, Any],
    request_bundle: dict[str, Any],
    skill_map: dict[str, Any],
) -> None:
    """Ensure the request exchange matches this benchmark without exposing gold labels."""
    if request_bundle.get("exchange_type") != "skill-selection-benchmark-requests":
        raise RuntimeExchangeError("unsupported request bundle")
    if request_bundle.get("benchmark_id") != benchmark.get("benchmark_id"):
        raise RuntimeExchangeError("benchmark_id mismatch")
    run = request_bundle.get("run")
    if not isinstance(run, dict) or not isinstance(run.get("skills_revision"), str):
        raise RuntimeExchangeError("request bundle is missing pinned Skill revision")
    revision = run["skills_revision"]
    if not SHA_RE.fullmatch(revision):
        raise RuntimeExchangeError("request bundle has invalid Skill revision")

    skill_ids = sorted(
        item["id"] for item in skill_map.get("skills", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    )
    if request_bundle.get("candidate_skill_ids") != skill_ids:
        raise RuntimeExchangeError("candidate Skill catalog mismatch")
    expected_refs = {
        skill_id: (
            "https://github.com/HOADF-Team/Personal-AI-Library/blob/"
            f"{revision}/skills/{skill_id}/SKILL.md"
        )
        for skill_id in skill_ids
    }
    expected_cases = {
        case["case_id"]: case["task"]
        for case in benchmark["cases"]
        if not case["needs_human_review"]
    }
    raw_requests = request_bundle.get("requests")
    if not isinstance(raw_requests, list):
        raise RuntimeExchangeError("requests must be an array")
    actual_cases: dict[str, str] = {}
    forbidden_fields = {
        "required_skills", "acceptable_skills", "excluded_skills",
        "expected_decision", "expected_order", "needs_human_review",
    }
    for index, request in enumerate(raw_requests):
        if not isinstance(request, dict):
            raise RuntimeExchangeError(f"request_{index}_must_be_object")
        if forbidden_fields.intersection(request):
            raise RuntimeExchangeError("gold annotations found in request bundle")
        case_id = request.get("case_id")
        task = request.get("task")
        if not isinstance(case_id, str) or case_id in actual_cases:
            raise RuntimeExchangeError(f"invalid_or_duplicate_request_case:{case_id}")
        if not isinstance(task, str):
            raise RuntimeExchangeError(f"invalid_request_task:{case_id}")
        if request.get("available_skill_ids") != skill_ids:
            raise RuntimeExchangeError(f"request_skill_catalog_mismatch:{case_id}")
        if request.get("canonical_manifest_refs") != expected_refs:
            raise RuntimeExchangeError(f"manifest_refs_mismatch:{case_id}")
        actual_cases[case_id] = task
    if actual_cases != expected_cases:
        raise RuntimeExchangeError("request case set or task text does not match benchmark")
    if request_bundle.get("gold_labels_included") is not False:
        raise RuntimeExchangeError("request bundle must explicitly exclude gold labels")


def validate_runtime_responses(
    request_bundle: dict[str, Any],
    response_bundle: dict[str, Any],
    skill_map: dict[str, Any],
) -> dict[str, Any]:
    """Validate response provenance and one-to-one case coverage."""
    if request_bundle.get("exchange_type") != "skill-selection-benchmark-requests":
        raise RuntimeExchangeError("unsupported request bundle")
    expected_run = request_bundle.get("run")
    actual_run = response_bundle.get("run")
    if not isinstance(expected_run, dict) or not isinstance(actual_run, dict):
        raise RuntimeExchangeError("run metadata is required in request and response bundles")
    for field in ("run_id", "skills_revision", "planner_contract_version"):
        if actual_run.get(field) != expected_run.get(field):
            raise RuntimeExchangeError(f"run metadata mismatch: {field}")
    runtime = response_bundle.get("runtime")
    if not isinstance(runtime, dict) or not isinstance(runtime.get("name"), str) or not runtime["name"].strip():
        raise RuntimeExchangeError("runtime.name must identify the external runtime")
    if not isinstance(runtime.get("planner_version"), str) or not runtime["planner_version"].strip():
        raise RuntimeExchangeError("runtime.planner_version is required")

    known_skills = {
        item["id"] for item in skill_map.get("skills", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    request_ids = {
        item["case_id"] for item in request_bundle.get("requests", [])
        if isinstance(item, dict) and isinstance(item.get("case_id"), str)
    }
    raw_responses = response_bundle.get("responses")
    if not isinstance(raw_responses, list):
        raise RuntimeExchangeError("responses must be an array")

    proposals: dict[str, Any] = {}
    for index, response in enumerate(raw_responses):
        if not isinstance(response, dict):
            raise RuntimeExchangeError(f"response_{index}_must_be_object")
        case_id = response.get("case_id")
        if not isinstance(case_id, str) or case_id not in request_ids:
            raise RuntimeExchangeError(f"unknown_case_id:{case_id}")
        if case_id in proposals:
            raise RuntimeExchangeError(f"duplicate_case_id:{case_id}")
        decision = response.get("decision")
        if not isinstance(decision, str) or decision not in DECISIONS:
            raise RuntimeExchangeError(f"invalid_decision:{case_id}")
        selected = response.get("selected_skills")
        if not isinstance(selected, list) or any(not isinstance(item, str) for item in selected):
            raise RuntimeExchangeError(f"selected_skills_must_be_string_array:{case_id}")
        if len(selected) != len(set(selected)):
            raise RuntimeExchangeError(f"duplicate_selected_skill:{case_id}")
        unknown = sorted(set(selected) - known_skills)
        if unknown:
            raise RuntimeExchangeError(f"unknown_skill:{case_id}:{','.join(unknown)}")
        rationale = response.get("rationale", "")
        if not isinstance(rationale, str):
            raise RuntimeExchangeError(f"rationale_must_be_string:{case_id}")
        proposals[case_id] = {
            "decision": decision,
            "selected_skills": selected,
            "rationale": rationale,
        }

    missing = sorted(request_ids - set(proposals))
    if missing:
        raise RuntimeExchangeError("missing_case_responses:" + ",".join(missing))
    extra = sorted(set(proposals) - request_ids)
    if extra:
        raise RuntimeExchangeError("unexpected_case_responses:" + ",".join(extra))
    return proposals


def evaluate_runtime_exchange(
    benchmark: dict[str, Any],
    request_bundle: dict[str, Any],
    response_bundle: dict[str, Any],
    skill_map: dict[str, Any],
) -> dict[str, Any]:
    """Score one complete, provenance-labelled response set from an external planner."""
    validate_request_bundle(benchmark, request_bundle, skill_map)
    proposals = validate_runtime_responses(request_bundle, response_bundle, skill_map)
    scoring = score_benchmark(benchmark, proposals, skill_map)
    if scoring.get("status") != "scored":
        raise RuntimeExchangeError("benchmark scoring failed: " + str(scoring.get("errors")))
    return {
        "schema_version": "1.0",
        "evaluation_type": "external-runtime-skill-selection",
        "benchmark_id": benchmark.get("benchmark_id"),
        "run": response_bundle["run"],
        "runtime": response_bundle["runtime"],
        "response_coverage": {
            "expected": len(request_bundle["requests"]),
            "received": len(proposals),
            "complete": True,
        },
        "scoring": scoring,
        "interpretation": [
            "Metrics describe this supplied runtime response set only.",
            "Rationale presence is measured; rationale truth and reasoning quality require human review.",
            "The runtime identity and version are caller-supplied metadata, not cryptographically attested.",
            "This evaluator does not prove that the runtime actually loaded the referenced manifests.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    prepare = sub.add_parser("prepare", help="Export gold-label-free task requests")
    prepare.add_argument("--benchmark", type=Path, default=ROOT / "TESTS" / "selection-benchmark" / "benchmark.json")
    prepare.add_argument("--skill-map", type=Path, default=ROOT / "CATALOG" / "skill-tools.json")
    prepare.add_argument("--skills-revision", required=True)
    prepare.add_argument("--run-id", required=True)
    prepare.add_argument("--output", type=Path, required=True)

    score = sub.add_parser("score", help="Validate and score external runtime responses")
    score.add_argument("--benchmark", type=Path, default=ROOT / "TESTS" / "selection-benchmark" / "benchmark.json")
    score.add_argument("--skill-map", type=Path, default=ROOT / "CATALOG" / "skill-tools.json")
    score.add_argument("--requests", type=Path, required=True)
    score.add_argument("--responses", type=Path, required=True)
    score.add_argument("--output", type=Path, required=True)

    args = parser.parse_args()
    try:
        benchmark = load_json(args.benchmark)
        skill_map = load_json(args.skill_map)
        if args.command == "prepare":
            result = build_runtime_requests(
                benchmark, skill_map, args.skills_revision, args.run_id
            )
        else:
            result = evaluate_runtime_exchange(
                benchmark,
                load_json(args.requests),
                load_json(args.responses),
                skill_map,
            )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
