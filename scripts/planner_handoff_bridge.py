"""Bridge validated model Skill selections into reviewed handoff workflows.

This module prepares a workflow plan only. It never executes a Skill or adapter.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from handoff_runtime import RuntimeProtocolError, build_workflow_plan
from skill_selection import validate_skill_selection


class PlannerHandoffBridgeError(ValueError):
    """Raised when a planner result cannot safely be mapped to a reviewed workflow."""


def prepare_workflow_from_planner(
    planner_result: dict[str, Any],
    task: str,
    task_ref: str,
    reviewed_contracts: list[dict[str, Any]],
    skill_map: dict[str, Any],
    skills_root: Path,
    skills_revision: str,
    approvals: dict[str, dict[str, dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Validate a planner choice and prepare matching canonical Skill envelopes.

    A planner's ordered Skill IDs must match exactly one reviewed contract. This
    deliberately avoids inventing stage order, dependencies, or operational rules.
    """
    if not isinstance(planner_result, dict):
        raise PlannerHandoffBridgeError("planner_result must be an object")
    if planner_result.get("schema_version") != "1.0":
        raise PlannerHandoffBridgeError("unsupported planner result schema")
    decision = planner_result.get("decision")
    selected = planner_result.get("selected_skills")
    rationale = planner_result.get("rationale")
    run = planner_result.get("run")
    if decision not in {"select", "abstain", "clarify"}:
        raise PlannerHandoffBridgeError("invalid planner decision")
    if not isinstance(selected, list) or any(not isinstance(item, str) for item in selected):
        raise PlannerHandoffBridgeError("selected_skills must be an array of Skill IDs")
    if len(selected) != len(set(selected)):
        raise PlannerHandoffBridgeError("planner selected duplicate Skill IDs")
    if not isinstance(rationale, str) or not rationale.strip():
        raise PlannerHandoffBridgeError("planner rationale is required")
    if not isinstance(run, dict) or run.get("skills_revision") != skills_revision:
        raise PlannerHandoffBridgeError("planner result revision does not match requested Skills checkout")

    if decision != "select":
        if selected:
            raise PlannerHandoffBridgeError("abstain/clarify decisions cannot contain selected Skills")
        return {
            "schema_version": "1.0",
            "status": decision,
            "workflow_id": None,
            "selection_validation": None,
            "plan": [],
            "reason": rationale.strip(),
            "limitations": ["No workflow was prepared because the planner did not select Skills."],
        }
    if not selected:
        raise PlannerHandoffBridgeError("select decision requires at least one Skill")
    if not isinstance(task, str) or not task.strip() or not isinstance(task_ref, str) or not task_ref.strip():
        raise PlannerHandoffBridgeError("task and task_ref must be non-empty")

    matches: list[dict[str, Any]] = []
    for contract in reviewed_contracts:
        stages = contract.get("stages") if isinstance(contract, dict) else None
        if not isinstance(stages, list) or not stages:
            continue
        contract_skills = [
            stage.get("skill_id", stage.get("id")) if isinstance(stage, dict) else None
            for stage in stages
        ]
        if contract_skills == selected:
            matches.append(contract)

    if not matches:
        return {
            "schema_version": "1.0",
            "status": "no_matching_reviewed_workflow",
            "workflow_id": None,
            "selection_validation": None,
            "plan": [],
            "reason": "The selected ordered Skill sequence does not match an available reviewed workflow contract.",
            "limitations": [
                "No workflow was invented or reordered automatically.",
                "A new sequence requires a separately reviewed workflow contract before execution.",
            ],
        }
    if len(matches) != 1:
        raise PlannerHandoffBridgeError("planner selection matches multiple reviewed workflow contracts")

    contract = matches[0]
    workflow_id = contract.get("workflow_id")
    if not isinstance(workflow_id, str) or not workflow_id:
        raise PlannerHandoffBridgeError("matched workflow contract has no workflow_id")

    selection = {
        "schema_version": "1.0",
        "workflow_id": workflow_id,
        "task_ref": task_ref,
        "selection_rationale": rationale.strip(),
        "selected_skills": [
            {
                "stage_id": stage["id"],
                "skill_id": stage.get("skill_id", stage["id"]),
                "rationale": f"Included under the planner's workflow-level rationale: {rationale.strip()}",
                "depends_on": [previous["id"] for previous in contract["stages"][:index]],
            }
            for index, stage in enumerate(contract["stages"])
        ],
    }
    selection_report = validate_skill_selection(selection, contract, skill_map)
    if selection_report["status"] != "passed":
        raise PlannerHandoffBridgeError(
            "planner selection failed workflow validation: " + ",".join(selection_report["errors"])
        )

    try:
        plan = build_workflow_plan(
            contract=contract,
            skill_map=skill_map,
            skills_root=skills_root,
            task=task.strip(),
            task_ref=task_ref.strip(),
            skills_revision=skills_revision,
            approvals=approvals,
        )
    except RuntimeProtocolError as exc:
        raise PlannerHandoffBridgeError(f"workflow preparation failed: {exc}") from exc

    return {
        "schema_version": "1.0",
        "status": "prepared",
        "workflow_id": workflow_id,
        "selected_skill_ids": selected,
        "selection_validation": selection_report,
        "plan": plan,
        "execution_started": False,
        "limitations": [
            "The workflow was matched to a reviewed contract; no new stage order or operational rules were inferred.",
            "The stage-level rationales inherit the planner's workflow-level rationale; they are not independent per-Skill explanations.",
            "The host must verify that skills_root is a trusted checkout at the exact pinned commit before calling this bridge.",
            "Manifest file presence is checked, but this function does not independently authenticate the checkout revision.",
            "No Skill, model, tool, network request, remote host, production system, or financial action was executed.",
            "Preparation does not grant approvals; missing approvals remain visible in each stage envelope.",
        ],
    }



def prepare_workflow_from_catalog(
    planner_result: dict[str, Any],
    task: str,
    task_ref: str,
    catalog_path: Path,
    skill_map: dict[str, Any],
    skills_root: Path,
    skills_revision: str,
    approvals: dict[str, dict[str, dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Load a validated workflow catalog and prepare only an eligible exact match."""
    from workflow_catalog import WorkflowCatalogError, load_workflow_catalog

    try:
        catalog = load_workflow_catalog(catalog_path, skill_map)
    except WorkflowCatalogError as exc:
        raise PlannerHandoffBridgeError(f"workflow catalog rejected: {exc}") from exc

    eligible = [
        workflow for workflow in catalog["workflows"]
        if workflow.get("catalog_status") in {"reviewed", "reviewed_fixture"}
    ]
    result = prepare_workflow_from_planner(
        planner_result=planner_result,
        task=task,
        task_ref=task_ref,
        reviewed_contracts=eligible,
        skill_map=skill_map,
        skills_root=skills_root,
        skills_revision=skills_revision,
        approvals=approvals,
    )
    result["workflow_catalog"] = {
        "catalog_id": catalog["catalog_id"],
        "catalog_status": "validated",
        "eligible_template_count": len(eligible),
    }
    return result
