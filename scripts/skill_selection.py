"""Validate an AI-proposed Skill selection against catalog and workflow contract.

This module checks selection structure and declared ordering. It does not infer task
meaning, rank Skills, load an LLM, or execute Skills.
"""
from __future__ import annotations

from typing import Any


class SkillSelectionError(ValueError):
    """Raised when a proposed Skill selection is structurally unsafe or inconsistent."""


def validate_skill_selection(
    selection: dict[str, Any],
    contract: dict[str, Any],
    skill_map: dict[str, Any],
) -> dict[str, Any]:
    """Validate an explicit planner decision before runtime manifest resolution."""
    errors: list[str] = []
    catalog_ids = {
        item.get("id") for item in skill_map.get("skills", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    expected_workflow = contract.get("workflow_id")
    if selection.get("workflow_id") != expected_workflow:
        errors.append("workflow_id_mismatch")
    if not isinstance(selection.get("task_ref"), str) or not selection["task_ref"].strip():
        errors.append("missing_task_ref")
    if not isinstance(selection.get("selection_rationale"), str) or not selection["selection_rationale"].strip():
        errors.append("missing_selection_rationale")

    proposed = selection.get("selected_skills")
    if not isinstance(proposed, list) or not proposed:
        proposed = []
        errors.append("selected_skills_must_be_non_empty_array")

    stages = contract.get("stages", [])
    expected_ids = [stage.get("id") for stage in stages]
    actual_ids: list[str] = []
    seen_skills: set[str] = set()
    seen_stages: set[str] = set()
    for index, item in enumerate(proposed):
        if not isinstance(item, dict):
            errors.append(f"stage_{index}_must_be_object")
            continue
        stage_id = item.get("stage_id")
        skill_id = item.get("skill_id")
        rationale = item.get("rationale")
        if not isinstance(stage_id, str) or not stage_id:
            errors.append(f"stage_{index}_missing_stage_id")
        else:
            actual_ids.append(stage_id)
            if stage_id in seen_stages:
                errors.append(f"duplicate_stage:{stage_id}")
            seen_stages.add(stage_id)
        if not isinstance(skill_id, str) or not skill_id:
            errors.append(f"stage_{index}_missing_skill_id")
        else:
            if skill_id not in catalog_ids:
                errors.append(f"unknown_skill:{skill_id}")
            if skill_id in seen_skills:
                errors.append(f"duplicate_skill:{skill_id}")
            seen_skills.add(skill_id)
        if not isinstance(rationale, str) or not rationale.strip():
            errors.append(f"stage_{index}_missing_rationale")

        dependencies = item.get("depends_on", [])
        if not isinstance(dependencies, list) or any(not isinstance(dep, str) for dep in dependencies):
            errors.append(f"stage_{index}_invalid_dependencies")
            continue
        prior = set(actual_ids[:-1])
        for dependency in dependencies:
            if dependency not in prior:
                errors.append(f"stage_{index}_dependency_not_prior:{dependency}")

        if index < len(stages):
            contract_skill = stages[index].get("skill_id", stages[index].get("id"))
            if isinstance(skill_id, str) and skill_id != contract_skill:
                errors.append(f"contract_skill_mismatch:{stage_id}")

    if actual_ids != expected_ids:
        errors.append("stage_order_or_membership_mismatch")

    return {
        "schema_version": "1.0",
        "workflow_id": expected_workflow,
        "status": "passed" if not errors else "failed",
        "selected_skill_ids": [item.get("skill_id") for item in proposed if isinstance(item, dict)],
        "checks": {
            "catalog_membership": "passed" if not any(x.startswith("unknown_skill:") for x in errors) else "failed",
            "contract_stage_order": "passed" if actual_ids == expected_ids else "failed",
            "stage_rationales": "passed" if not any("missing_rationale" in x for x in errors) else "failed",
            "dependency_order": "passed" if not any("dependency_not_prior" in x for x in errors) else "failed",
        },
        "errors": errors,
        "limitations": [
            "This validates an explicit planner proposal; it does not decide which Skills are semantically relevant.",
            "Rationales are caller-supplied and are not proof of correct model reasoning.",
            "Canonical Skill manifest existence and immutable revision are checked separately by the runtime planner.",
        ],
    }
