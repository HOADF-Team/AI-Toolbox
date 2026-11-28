"""Reusable, declarative validator for ordered JSON handoff workflows.

This module validates artifacts only. It never imports, invokes, or executes Skills.
"""
from __future__ import annotations

import re
from typing import Any

SECRET_KEY = re.compile(
    r"(?:^|_)(?:api_?key|access_?token|secret|password|private_?key|credential_?value)$",
    re.IGNORECASE,
)
SECRET_VALUE = re.compile(
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----|(?:gh[pousr]_|sk_live_|AKIA)[A-Za-z0-9_\\-]{12,}"
)
REDACTED = {"[redacted]", "redacted", "***", "****", "<redacted>"}


def _get_path(value: Any, path: str) -> Any:
    """Resolve a dotted path; list expansion is supported with a terminal [*]."""
    current = value
    for part in path.split("."):
        if part.endswith("[*]"):
            key = part[:-3]
            current = current.get(key, []) if isinstance(current, dict) else []
            if not isinstance(current, list):
                return []
        else:
            if isinstance(current, list):
                current = [item.get(part) if isinstance(item, dict) else None for item in current]
            elif isinstance(current, dict):
                current = current.get(part)
            else:
                return None
    return current


def _secret_paths(value: Any, path: str = "$") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            current = f"{path}.{key}"
            if SECRET_KEY.fullmatch(str(key)):
                if not isinstance(child, str) or child.strip().lower() not in REDACTED:
                    found.append(current)
            found.extend(_secret_paths(child, current))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_secret_paths(child, f"{path}[{index}]"))
    elif isinstance(value, str) and SECRET_VALUE.search(value):
        found.append(path)
    return found


def validate_handoff_chain(
    contract: dict[str, Any], artifacts: list[dict[str, Any]],
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate an artifact chain against a declarative workflow contract."""
    checks: list[dict[str, Any]] = []
    errors: list[str] = []

    def check(check_id: str, passed: bool, detail: str) -> None:
        checks.append({"id": check_id, "passed": bool(passed), "detail": detail})
        if not passed:
            errors.append(check_id)

    stages = contract.get("stages", [])
    expected_ids = [stage.get("id") for stage in stages]
    actual_ids = [artifact.get("stage") for artifact in artifacts]
    check("stage_sequence", actual_ids == expected_ids,
          f"expected={expected_ids}; actual={actual_ids}")

    previous_ref = contract.get("root_input_ref", "root")
    indexed: dict[str, dict[str, Any]] = {}
    for index, stage_spec in enumerate(stages):
        stage_id = stage_spec.get("id", f"stage-{index}")
        artifact = artifacts[index] if index < len(artifacts) else {}
        check(f"{stage_id}.input_ref",
              artifact.get("input_ref") == previous_ref,
              f"expected input_ref={previous_ref!r}; actual={artifact.get('input_ref')!r}")
        output_ref = artifact.get("output_ref")
        valid_output = isinstance(output_ref, str) and bool(output_ref.strip())
        check(f"{stage_id}.output_ref", valid_output,
              "output_ref must be a non-empty artifact identifier")
        if valid_output:
            previous_ref = output_ref
        indexed[stage_id] = artifact

        for field in stage_spec.get("required_fields", []):
            value = _get_path(artifact, field)
            check(f"{stage_id}.required.{field}", value is not None and value != "",
                  f"required field {field!r} must be present")
        evidence_field = stage_spec.get("evidence_field", "evidence")
        if stage_spec.get("require_evidence", True):
            evidence = _get_path(artifact, evidence_field)
            valid_evidence = (
                isinstance(evidence, list) and bool(evidence)
                and all(isinstance(item, dict) and item.get("location") and item.get("observation")
                        for item in evidence)
            )
            check(f"{stage_id}.evidence", valid_evidence,
                  f"{evidence_field} must contain location and observation for each item")

    all_data = {"context": context or {}, "artifacts": artifacts}
    secret_paths = _secret_paths(all_data)
    check("secret_redaction", not secret_paths,
          "secret-like values must be absent or explicitly redacted"
          + (f"; paths={secret_paths}" if secret_paths else ""))

    for rule in contract.get("rules", []):
        rule_id = rule["id"]
        stage_id = rule.get("stage")
        source = indexed.get(stage_id, {}) if stage_id else all_data
        path = rule["path"]
        value = _get_path(source, path)
        kind = rule["type"]
        passed = False
        detail = f"{stage_id or 'workflow'}.{path}={value!r}"
        if kind == "equals":
            passed = value == rule.get("value")
        elif kind == "is_empty":
            passed = value in (None, [], {}, "")
        elif kind == "ordered_values":
            sequence = value if isinstance(value, list) else []
            if rule.get("item_field"):
                sequence = [item.get(rule["item_field"]) for item in sequence
                            if isinstance(item, dict)]
            required = rule.get("values", [])
            positions = [sequence.index(item) if item in sequence else -1 for item in required]
            passed = bool(required) and all(pos >= 0 for pos in positions) and positions == sorted(positions)
        elif kind == "forbid_values":
            sequence = value if isinstance(value, list) else []
            if rule.get("item_field"):
                sequence = [item.get(rule["item_field"]) for item in sequence
                            if isinstance(item, dict)]
            passed = not any(item in sequence for item in rule.get("values", []))
        else:
            detail += "; unsupported rule type"
        check(rule_id, passed, detail)

    return {
        "schema_version": "1.0",
        "workflow_id": contract.get("workflow_id", "unnamed"),
        "status": "passed" if not errors else "failed",
        "checks": checks,
        "handoff_chain": [
            {"stage": item.get("stage"), "input_ref": item.get("input_ref"),
             "output_ref": item.get("output_ref")} for item in artifacts
        ],
        "limitations": [
            "Validates declarative JSON contracts and artifact references only; it does not execute Skills or an LLM.",
            "A passing report does not establish reasoning quality, factual correctness, or successful real-world actions.",
            "Secret detection is heuristic and is not a substitute for a dedicated secret scanner.",
        ],
        "evidence_provenance": {
            "contract": "caller-supplied declarative workflow contract",
            "artifacts": "caller-supplied JSON handoff artifacts",
            "execution": "deterministic local validation; no network or subprocess calls",
        },
        "errors": errors,
    }
