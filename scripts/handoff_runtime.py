"""Runtime-facing adapter protocol for orchestrating externally executed Skills.

This module prepares envelopes and validates adapter responses. It never invokes an
LLM, loads Skill instructions as executable code, installs tools, or performs side effects.
"""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from handoff_contract import validate_handoff_chain


class RuntimeProtocolError(ValueError):
    """Raised when a workflow cannot be safely prepared or continued."""


def build_workflow_plan(
    contract: dict[str, Any],
    skill_map: dict[str, Any],
    skills_root: Path,
    task: str,
    task_ref: str,
    approvals: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """Resolve explicit contract stages to canonical Skill manifests and envelopes."""
    if not task.strip() or not task_ref.strip():
        raise RuntimeProtocolError("task and task_ref must be non-empty")
    catalog_ids = {
        item.get("id") for item in skill_map.get("skills", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    if not isinstance(contract.get("stages"), list) or not contract["stages"]:
        raise RuntimeProtocolError("contract must declare at least one ordered stage")

    granted = approvals or {}
    plan: list[dict[str, Any]] = []
    previous_ref = contract.get("root_input_ref", task_ref)
    seen: set[str] = set()
    for index, stage in enumerate(contract["stages"]):
        stage_id = stage.get("id")
        skill_id = stage.get("skill_id", stage_id)
        if not isinstance(stage_id, str) or not stage_id or stage_id in seen:
            raise RuntimeProtocolError(f"invalid or duplicate stage id: {stage_id!r}")
        seen.add(stage_id)
        if skill_id not in catalog_ids:
            raise RuntimeProtocolError(f"unknown Skill ID in catalog map: {skill_id!r}")
        manifest_rel = Path("skills") / skill_id / "SKILL.md"
        manifest = skills_root / manifest_rel
        if not manifest.is_file():
            raise RuntimeProtocolError(f"canonical Skill manifest unavailable: {manifest_rel.as_posix()}")
        requested = stage.get("required_approvals", [])
        if not isinstance(requested, list) or any(not isinstance(item, str) for item in requested):
            raise RuntimeProtocolError(f"invalid required_approvals for stage {stage_id}")
        envelope = {
            "schema_version": "1.0",
            "workflow_id": contract.get("workflow_id", "unnamed"),
            "task": {"ref": task_ref, "description": task},
            "stage": {"id": stage_id, "index": index, "skill_id": skill_id},
            "skill": {
                "manifest_path": manifest_rel.as_posix(),
                "manifest_available": True,
                "execution_instruction": "The host agent must read this canonical Markdown Skill and execute it; this adapter does not.",
            },
            "input_ref": previous_ref,
            "required_outputs": list(stage.get("required_fields", [])),
            "constraints": list(contract.get("constraints", [])),
            "permissions": {
                "requested_approvals": requested,
                "granted_approvals": {
                    action: granted[action] for action in requested if action in granted
                },
                "missing_approvals": [action for action in requested if action not in granted],
            },
            "prior_stage_output_ref": None if index == 0 else previous_ref,
        }
        plan.append({"stage_spec": stage, "envelope": envelope})
        previous_ref = f"stage-output:{stage_id}"
    return plan


def _validate_stage_result(
    result: dict[str, Any], envelope: dict[str, Any], approvals: dict[str, str]
) -> list[str]:
    errors: list[str] = []
    stage = envelope["stage"]
    if result.get("stage") != stage["id"]:
        errors.append("stage_id_mismatch")
    if result.get("skill_id") != stage["skill_id"]:
        errors.append("skill_id_mismatch")
    if result.get("input_ref") != envelope["input_ref"]:
        errors.append("input_ref_mismatch")
    if not isinstance(result.get("output_ref"), str) or not result["output_ref"].strip():
        errors.append("missing_output_ref")
    if result.get("status") not in {"completed", "blocked", "failed"}:
        errors.append("invalid_status")
    if not isinstance(result.get("evidence"), list) or not result["evidence"]:
        errors.append("missing_evidence")
    provenance = result.get("provenance")
    if not isinstance(provenance, dict) or not all(
        isinstance(provenance.get(key), str) and provenance[key].strip()
        for key in ("execution_mode", "skill_manifest_ref", "agent")
    ):
        errors.append("invalid_provenance")
    actions = result.get("actions_taken", [])
    if not isinstance(actions, list):
        errors.append("invalid_actions_taken")
    else:
        for action in actions:
            if not isinstance(action, dict):
                errors.append("invalid_action_record")
                continue
            action_id = action.get("action")
            approval_id = action.get("approval_id")
            if not isinstance(action_id, str) or not action_id:
                errors.append("invalid_action_id")
            elif not isinstance(approval_id, str) or approvals.get(action_id) != approval_id:
                errors.append(f"action_without_matching_approval:{action_id}")
    return errors


def execute_with_adapter(
    contract: dict[str, Any],
    plan: list[dict[str, Any]],
    adapter: Callable[[dict[str, Any]], dict[str, Any]],
    approvals: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Run an injected adapter sequentially; stop on invalid, blocked, or failed output."""
    granted = approvals or {}
    artifacts: list[dict[str, Any]] = []
    stage_reports: list[dict[str, Any]] = []
    stopped_reason: str | None = None

    for item in plan:
        envelope = item["envelope"]
        missing = envelope["permissions"]["missing_approvals"]
        if missing:
            stopped_reason = f"approval_required:{envelope['stage']['id']}:{','.join(missing)}"
            break
        try:
            result = adapter(envelope)
        except Exception as exc:
            stopped_reason = f"adapter_error:{envelope['stage']['id']}:{type(exc).__name__}"
            break
        if not isinstance(result, dict):
            stopped_reason = f"invalid_adapter_response:{envelope['stage']['id']}"
            break
        errors = _validate_stage_result(result, envelope, granted)
        if errors:
            stopped_reason = f"invalid_stage_result:{envelope['stage']['id']}"
            stage_reports.append({"stage": envelope["stage"]["id"], "status": "invalid", "errors": errors})
            break
        stage_reports.append({
            "stage": result["stage"], "skill_id": result["skill_id"],
            "status": result["status"], "output_ref": result["output_ref"],
        })
        artifacts.append(result)
        if result["status"] != "completed":
            stopped_reason = f"stage_{result['status']}:{result['stage']}"
            break

    chain_report = None
    if len(artifacts) == len(contract.get("stages", [])) and stopped_reason is None:
        chain_report = validate_handoff_chain(contract, artifacts)
        if chain_report["status"] != "passed":
            stopped_reason = "handoff_contract_validation_failed"

    complete = len(artifacts) == len(contract.get("stages", [])) and stopped_reason is None
    return {
        "schema_version": "1.0",
        "workflow_id": contract.get("workflow_id", "unnamed"),
        "status": "completed" if complete else ("blocked" if stopped_reason and "approval_required" in stopped_reason else "incomplete"),
        "stages": stage_reports,
        "artifacts": artifacts,
        "handoff_validation": chain_report,
        "stopped_reason": stopped_reason,
        "evidence_classification": {
            "adapter_output": "agent-reported; not independently authenticated",
            "runtime_validation": "deterministic structural and contract checks",
            "real_world_actions": "only those explicitly recorded with matching approval IDs; not independently verified",
        },
        "limitations": [
            "The adapter is an integration boundary, not an LLM or Skill execution engine.",
            "The host runtime must load the canonical Skill manifest and supply the adapter implementation.",
            "A mock adapter tests protocol mechanics only, not model reasoning or real actions.",
            "Evidence and agent identity are caller-supplied and are not cryptographically authenticated.",
        ],
    }
