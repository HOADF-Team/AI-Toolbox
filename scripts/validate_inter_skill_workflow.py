#!/usr/bin/env python3
"""Validate deterministic Skill handoffs; never executes Skills or scenario code."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

SECRET_KEY = re.compile(r"(?:^|_)(?:api_?key|access_?token|secret|password|private_?key|credential_?value)(?:$|_)", re.I)
SECRET_VALUE = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----|(?:gh[pousr]_|sk_live_|AKIA)[A-Za-z0-9_\-]{12,}")
REDACTED = {"[redacted]", "redacted", "***", "****", "<redacted>"}


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def walk_secrets(value: Any, path: str = "$") -> list[str]:
    issues: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            current = f"{path}.{key}"
            if SECRET_KEY.search(str(key)):
                if not isinstance(child, str) or child.strip().lower() not in REDACTED:
                    issues.append(current)
            issues.extend(walk_secrets(child, current))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            issues.extend(walk_secrets(child, f"{path}[{index}]"))
    elif isinstance(value, str) and SECRET_VALUE.search(value):
        issues.append(path)
    return issues


def validate(scenario: dict[str, Any], handoffs: list[dict[str, Any]]) -> dict[str, Any]:
    expected = scenario.get("expected_skill_order", [])
    errors: list[str] = []
    checks: list[dict[str, Any]] = []

    def check(name: str, ok: bool, detail: str) -> None:
        checks.append({"id": name, "passed": bool(ok), "detail": detail})
        if not ok:
            errors.append(name)

    actual = [item.get("stage") for item in handoffs]
    check("required_stages_and_order", actual == expected,
          f"expected={expected}; actual={actual}")

    previous = "scenario"
    for index, item in enumerate(handoffs):
        stage = item.get("stage", f"handoff-{index}")
        check(f"{stage}.input_link", item.get("input_ref") == previous,
              f"input_ref={item.get('input_ref')!r}; expected={previous!r}")
        output_ref = item.get("output_ref")
        check(f"{stage}.output_ref", isinstance(output_ref, str) and bool(output_ref),
              "output_ref must be a non-empty artifact identifier")
        evidence = item.get("evidence")
        check(f"{stage}.evidence", isinstance(evidence, list) and bool(evidence)
              and all(isinstance(x, dict) and x.get("location") and x.get("observation")
                      for x in evidence),
              "each stage needs evidence locations and observations")
        previous = output_ref if isinstance(output_ref, str) else ""

    by_stage = {item.get("stage"): item for item in handoffs}
    crypto = by_stage.get("crypto-security", {})
    events = crypto.get("incident_events", [])
    event_names = [event.get("event") for event in events if isinstance(event, dict)]
    revoke = event_names.index("credential_revocation_recommended") if "credential_revocation_recommended" in event_names else -1
    isolate = event_names.index("host_isolation_recommended") if "host_isolation_recommended" in event_names else -1
    check("incident_recommendation_order", revoke >= 0 and isolate >= 0 and revoke < isolate,
          f"event sequence={event_names}; recommendations are not actual actions")
    check("no_automatic_liquidation", all(
        event not in {"position_liquidation", "automatic_order_cancellation"}
        for event in event_names
    ) and crypto.get("automatic_actions", []) == [],
          "no automatic trading/position action may be proposed or executed")

    code = by_stage.get("code-audit", {})
    check("static_analysis_only", code.get("execution") == "not_executed",
          "fixture/application code must not be executed")
    dev = by_stage.get("python-development", {})
    check("patch_is_proposal", dev.get("patch_status") == "proposed_not_applied"
          and dev.get("fixture_dependencies_installed") is False,
          "patch remains a proposal; fixture dependencies are not installed")
    ops = by_stage.get("devops-vps", {})
    check("remote_and_production_scope", ops.get("remote_access") == "not_checked"
          and ops.get("production_changes") == "not_performed"
          and ops.get("ssh_attempted") is False,
          "no SSH, remote access, or production mutation is claimed")

    secret_paths = walk_secrets({"scenario": scenario, "handoffs": handoffs})
    check("secret_redaction", not secret_paths,
          "secret-like fields/values must be absent or explicitly redacted"
          + (f"; violations={secret_paths}" if secret_paths else ""))

    return {
        "schema_version": "1.0",
        "scenario_id": scenario.get("scenario_id", "unknown"),
        "status": "passed" if not errors else "failed",
        "checks": checks,
        "handoff_chain": [
            {"stage": item.get("stage"), "input_ref": item.get("input_ref"),
             "output_ref": item.get("output_ref")} for item in handoffs
        ],
        "findings": [finding.get("id") for finding in scenario.get("findings", [])
                     if isinstance(finding, dict)],
        "limitations": [
            "Validates deterministic JSON contracts and handoff links only; no LLM or Skill is executed.",
            "Does not establish correctness or completeness of an agent's real-world analysis.",
            "No fixture code or fixture dependencies are executed or installed.",
            "Credential revocation and host isolation are recommendations in a simulation, not performed actions.",
            "Remote access is not checked; production systems are not accessed or changed.",
            "Secret detection is heuristic and is not a substitute for a dedicated secret scanner.",
        ],
        "evidence_provenance": {
            "scenario": "repository synthetic fixture",
            "handoffs": "repository synthetic contract fixtures",
            "execution": "deterministic local JSON validation",
        },
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", type=Path, required=True)
    parser.add_argument("--handoff-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    scenario = load_json(args.scenario)
    handoffs = [load_json(args.handoff_dir / f"{stage}.json")
                for stage in scenario["expected_skill_order"]]
    report = validate(scenario, handoffs)
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
