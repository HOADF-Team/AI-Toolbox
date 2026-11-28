"""Validation and deterministic lookup for reusable reviewed workflow contracts."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class WorkflowCatalogError(ValueError):
    """Raised when a workflow catalog is malformed or unsafe to use."""


def validate_workflow_catalog(
    catalog: dict[str, Any],
    skill_map: dict[str, Any],
) -> dict[str, Any]:
    """Validate catalog structure, workflow IDs, stage IDs, Skills, and rule targets."""
    errors: list[str] = []
    if not isinstance(catalog, dict) or catalog.get("schema_version") != "1.0":
        return {"schema_version": "1.0", "status": "failed", "errors": ["unsupported_catalog_schema"]}
    catalog_id = catalog.get("catalog_id")
    if not isinstance(catalog_id, str) or not catalog_id.strip():
        errors.append("missing_catalog_id")
    workflows = catalog.get("workflows")
    if not isinstance(workflows, list) or not workflows:
        errors.append("workflows_must_be_non_empty_array")
        workflows = []

    known_skills = {
        item.get("id") for item in skill_map.get("skills", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    workflow_ids: set[str] = set()
    for wi, workflow in enumerate(workflows):
        if not isinstance(workflow, dict):
            errors.append(f"workflow_{wi}_must_be_object")
            continue
        workflow_id = workflow.get("workflow_id")
        if not isinstance(workflow_id, str) or not workflow_id.strip():
            errors.append(f"workflow_{wi}_missing_workflow_id")
        elif workflow_id in workflow_ids:
            errors.append(f"duplicate_workflow_id:{workflow_id}")
        else:
            workflow_ids.add(workflow_id)

        status = workflow.get("catalog_status")
        if status not in {"reviewed", "reviewed_fixture", "draft", "deprecated"}:
            errors.append(f"workflow_{wi}_invalid_catalog_status")
        if not isinstance(workflow.get("description"), str) or not workflow["description"].strip():
            errors.append(f"workflow_{wi}_missing_description")
        if not isinstance(workflow.get("root_input_ref"), str) or not workflow["root_input_ref"].strip():
            errors.append(f"workflow_{wi}_missing_root_input_ref")

        stages = workflow.get("stages")
        if not isinstance(stages, list) or not stages:
            errors.append(f"workflow_{wi}_stages_must_be_non_empty_array")
            stages = []
        stage_ids: set[str] = set()
        for si, stage in enumerate(stages):
            if not isinstance(stage, dict):
                errors.append(f"workflow_{wi}_stage_{si}_must_be_object")
                continue
            stage_id = stage.get("id")
            skill_id = stage.get("skill_id", stage_id)
            if not isinstance(stage_id, str) or not stage_id.strip():
                errors.append(f"workflow_{wi}_stage_{si}_missing_id")
            elif stage_id in stage_ids:
                errors.append(f"workflow_{wi}_duplicate_stage_id:{stage_id}")
            else:
                stage_ids.add(stage_id)
            if not isinstance(skill_id, str) or skill_id not in known_skills:
                errors.append(f"workflow_{wi}_stage_{si}_unknown_skill:{skill_id}")
            fields = stage.get("required_fields", [])
            if not isinstance(fields, list) or any(not isinstance(field, str) or not field.strip() for field in fields):
                errors.append(f"workflow_{wi}_stage_{si}_invalid_required_fields")
            approvals = stage.get("required_approvals", [])
            if not isinstance(approvals, list) or any(not isinstance(item, str) or not item.strip() for item in approvals):
                errors.append(f"workflow_{wi}_stage_{si}_invalid_required_approvals")

        rules = workflow.get("rules", [])
        if not isinstance(rules, list):
            errors.append(f"workflow_{wi}_rules_must_be_array")
            rules = []
        rule_ids: set[str] = set()
        for ri, rule in enumerate(rules):
            if not isinstance(rule, dict):
                errors.append(f"workflow_{wi}_rule_{ri}_must_be_object")
                continue
            rule_id = rule.get("id")
            if not isinstance(rule_id, str) or not rule_id.strip() or rule_id in rule_ids:
                errors.append(f"workflow_{wi}_rule_{ri}_invalid_or_duplicate_id")
            else:
                rule_ids.add(rule_id)
            if rule.get("stage") not in stage_ids:
                errors.append(f"workflow_{wi}_rule_{ri}_unknown_stage")
            if not isinstance(rule.get("path"), str) or not rule["path"].strip():
                errors.append(f"workflow_{wi}_rule_{ri}_missing_path")
            if rule.get("type") not in {"equals", "is_empty", "ordered_values"}:
                errors.append(f"workflow_{wi}_rule_{ri}_unsupported_type")

        constraints = workflow.get("constraints", [])
        if not isinstance(constraints, list) or any(not isinstance(item, str) or not item.strip() for item in constraints):
            errors.append(f"workflow_{wi}_invalid_constraints")

    return {
        "schema_version": "1.0",
        "catalog_id": catalog_id,
        "status": "passed" if not errors else "failed",
        "workflow_count": len(workflows),
        "workflow_ids": sorted(workflow_ids),
        "errors": errors,
        "limitations": [
            "Catalog validation checks structure and references, not whether a workflow is semantically correct or operationally safe.",
            "A reviewed_fixture entry is a synthetic test scenario, not an approved production procedure.",
            "Catalog status and workflow content are repository-maintained claims, not independent certification.",
        ],
    }


def load_workflow_catalog(path: Path, skill_map: dict[str, Any]) -> dict[str, Any]:
    """Load a JSON catalog from a trusted local checkout and validate it."""
    try:
        catalog = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkflowCatalogError(f"cannot load workflow catalog: {type(exc).__name__}") from exc
    report = validate_workflow_catalog(catalog, skill_map)
    if report["status"] != "passed":
        raise WorkflowCatalogError("workflow catalog validation failed: " + ",".join(report["errors"]))
    return catalog


def find_exact_workflow(
    catalog: dict[str, Any],
    selected_skill_ids: list[str],
) -> dict[str, Any] | None:
    """Find exactly one non-draft workflow whose ordered Skill sequence matches."""
    matches: list[dict[str, Any]] = []
    for workflow in catalog.get("workflows", []):
        if workflow.get("catalog_status") not in {"reviewed", "reviewed_fixture"}:
            continue
        stages = workflow.get("stages", [])
        sequence = [stage.get("skill_id", stage.get("id")) for stage in stages]
        if sequence == selected_skill_ids:
            matches.append(workflow)
    if len(matches) > 1:
        raise WorkflowCatalogError("selection matches multiple reviewed workflow templates")
    return matches[0] if matches else None
