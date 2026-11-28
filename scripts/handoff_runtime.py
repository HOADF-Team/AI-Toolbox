"""Runtime-facing adapter protocol for orchestrating externally executed Skills.

This module prepares envelopes and validates adapter responses. It never invokes an
LLM, loads Skill instructions as executable code, installs tools, or performs side effects.
"""
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from artifact_integrity import (
    IntegrityVerificationError,
    canonical_json_bytes,
    sha256_bytes,
    verify_integrity_bundle,
)
from artifact_provenance import validate_provenance_envelope
from trust_registry import TrustRegistryError, resolve_trusted_key
from handoff_contract import validate_handoff_chain


class RuntimeProtocolError(ValueError):
    """Raised when a workflow cannot be safely prepared or continued."""


def _approval_errors(stage_id: str, action_id: str, approval: Any) -> list[str]:
    """Validate a host-supplied, stage/action-scoped approval record."""
    errors: list[str] = []
    if not isinstance(approval, dict):
        return ["approval_record_not_object"]
    if approval.get("stage_id") != stage_id:
        errors.append("approval_stage_mismatch")
    if approval.get("action") != action_id:
        errors.append("approval_action_mismatch")
    approval_id = approval.get("approval_id")
    if not isinstance(approval_id, str) or not approval_id.strip():
        errors.append("approval_id_missing")
    scope = approval.get("scope")
    if not isinstance(scope, dict) or not isinstance(scope.get("target_ref"), str) or not scope["target_ref"].strip() or not isinstance(scope.get("operation"), str) or not scope["operation"].strip():
        errors.append("approval_scope_invalid")
    else:
        try:
            canonical_json_bytes(scope)
        except (IntegrityVerificationError, TypeError, ValueError):
            errors.append("approval_scope_not_canonical_json")
    expires_at = approval.get("expires_at")
    if not isinstance(expires_at, str) or not expires_at.strip():
        errors.append("approval_expiry_missing")
    else:
        try:
            expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            if expiry.tzinfo is None or expiry.utcoffset() is None:
                raise ValueError("timezone required")
            if expiry <= datetime.now(timezone.utc):
                errors.append("approval_expired")
        except ValueError:
            errors.append("approval_expiry_invalid")
    return errors


def stage_result_sha256(result: dict[str, Any]) -> str:
    """Digest the complete stage result, excluding its own envelope and signature fields."""
    if not isinstance(result, dict):
        raise IntegrityVerificationError("stage_result_must_be_object")
    unsigned_fields = {"artifact_provenance", "integrity_bundle", "integrity_verification"}
    content = {key: value for key, value in result.items() if key not in unsigned_fields}
    return sha256_bytes(canonical_json_bytes(content))


def _validate_timestamp_key_window(
    timestamp_report: dict[str, Any], trust_resolution: dict[str, Any]
) -> None:
    """Require TSA genTime to fall inside the registry key's authorized validity window."""
    generation_time = timestamp_report.get("gen_time")
    if not isinstance(generation_time, str) or not generation_time:
        raise IntegrityVerificationError("trusted_timestamp_generation_time_missing")
    try:
        timestamp = datetime.fromisoformat(generation_time.replace("Z", "+00:00"))
        valid_from = datetime.fromisoformat(
            str(trust_resolution["valid_from"]).replace("Z", "+00:00")
        )
        valid_until = datetime.fromisoformat(
            str(trust_resolution["valid_until"]).replace("Z", "+00:00")
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise IntegrityVerificationError("trusted_key_validity_window_unavailable") from exc
    if any(value.tzinfo is None or value.utcoffset() is None for value in (timestamp, valid_from, valid_until)):
        raise IntegrityVerificationError("trusted_timestamp_or_key_window_timezone_missing")
    if timestamp < valid_from or timestamp >= valid_until:
        raise IntegrityVerificationError("trusted_timestamp_outside_signing_key_validity")


def _resolve_skill_manifest(skills_root: Path, relative_path: Path) -> Path:
    """Resolve a canonical Skill manifest without following links outside the checkout."""
    try:
        base = skills_root.resolve(strict=True)
    except OSError as exc:
        raise RuntimeProtocolError("trusted Skills checkout root unavailable") from exc
    if not base.is_dir():
        raise RuntimeProtocolError("trusted Skills checkout root is not a directory")
    current = base
    for part in relative_path.parts:
        current = current / part
        if current.is_symlink():
            raise RuntimeProtocolError("canonical Skill manifest path contains a symlink")
    try:
        manifest = current.resolve(strict=True)
        manifest.relative_to(base)
    except (OSError, ValueError) as exc:
        raise RuntimeProtocolError("canonical Skill manifest unavailable or escapes checkout") from exc
    if not manifest.is_file():
        raise RuntimeProtocolError("canonical Skill manifest is not a regular file")
    return manifest



def build_workflow_plan(
    contract: dict[str, Any],
    skill_map: dict[str, Any],
    skills_root: Path,
    task: str,
    task_ref: str,
    skills_revision: str,
    approvals: dict[str, dict[str, dict[str, Any]]] | None = None,
) -> list[dict[str, Any]]:
    """Resolve explicit contract stages to canonical Skill manifests and envelopes."""
    if not task.strip() or not task_ref.strip():
        raise RuntimeProtocolError("task and task_ref must be non-empty")
    if len(skills_revision) != 40 or any(ch not in "0123456789abcdef" for ch in skills_revision.lower()):
        raise RuntimeProtocolError("skills_revision must be a full 40-character Git commit SHA")
    skills_revision = skills_revision.lower()
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
        if not isinstance(skill_id, str) or not skill_id or any(ch not in "abcdefghijklmnopqrstuvwxyz0123456789-" for ch in skill_id):
            raise RuntimeProtocolError(f"invalid Skill ID: {skill_id!r}")
        if skill_id not in catalog_ids:
            raise RuntimeProtocolError(f"unknown Skill ID in catalog map: {skill_id!r}")
        manifest_rel = Path("skills") / skill_id / "SKILL.md"
        _resolve_skill_manifest(skills_root, manifest_rel)
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
                "manifest_revision": skills_revision,
                "manifest_ref": f"https://github.com/HOADF-Team/Personal-AI-Library/blob/{skills_revision}/{manifest_rel.as_posix()}",
                "manifest_available": True,
                "execution_instruction": "The host agent must read this canonical Markdown Skill and execute it; this adapter does not.",
            },
            "input_ref": previous_ref,
            "required_outputs": list(stage.get("required_fields", [])),
            "constraints": list(contract.get("constraints", [])),
            "permissions": {
                "requested_approvals": requested,
                "granted_approvals": {
                    action: granted.get(stage_id, {}).get(action)
                    for action in requested
                    if isinstance(granted.get(stage_id, {}), dict)
                    and action in granted.get(stage_id, {})
                },
                "missing_approvals": [
                    action for action in requested
                    if not isinstance(granted.get(stage_id, {}), dict)
                    or action not in granted.get(stage_id, {})
                    or _approval_errors(stage_id, action, granted[stage_id][action])
                ],
            },
            "prior_stage_output_ref": None if index == 0 else previous_ref,
        }
        plan.append({"stage_spec": stage, "envelope": envelope})
        previous_ref = f"stage-output:{stage_id}"
    return plan


def _validate_stage_result(
    result: dict[str, Any], envelope: dict[str, Any], approvals: dict[str, dict[str, Any]],
    integrity_policy: dict[str, Any] | None = None,
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
    elif provenance.get("skill_manifest_ref") != envelope["skill"]["manifest_ref"]:
        errors.append("skill_manifest_ref_mismatch")
    artifact_provenance = result.get("artifact_provenance")
    if not isinstance(artifact_provenance, dict):
        errors.append("missing_artifact_provenance_envelope")
    else:
        provenance_report = validate_provenance_envelope(artifact_provenance)
        if provenance_report["status"] != "passed":
            errors.extend(f"artifact_provenance:{error}" for error in provenance_report["errors"])
        else:
            expected_revision = envelope["skill"]["manifest_revision"]
            if artifact_provenance["producer"]["id"] != stage["skill_id"]:
                errors.append("artifact_provenance_producer_mismatch")
            if artifact_provenance["producer"]["revision"] != expected_revision:
                errors.append("artifact_provenance_revision_mismatch")
            if artifact_provenance["source"]["revision"] != expected_revision:
                errors.append("artifact_provenance_source_revision_mismatch")
            payload = artifact_provenance["payload"]
            if payload.get("stage") != stage["id"] or payload.get("skill_id") != stage["skill_id"]:
                errors.append("artifact_provenance_payload_identity_mismatch")
            if payload.get("output_ref") != result.get("output_ref"):
                errors.append("artifact_provenance_output_ref_mismatch")
            try:
                expected_stage_digest = stage_result_sha256(result)
            except IntegrityVerificationError:
                errors.append("stage_result_not_canonical_json")
            else:
                if payload.get("stage_result_sha256") != expected_stage_digest:
                    errors.append("artifact_provenance_stage_result_digest_mismatch")
            inputs = artifact_provenance.get("inputs", [])
            if not inputs or inputs[0].get("ref") != envelope["input_ref"]:
                errors.append("artifact_provenance_input_ref_mismatch")
    if integrity_policy is not None and isinstance(artifact_provenance, dict):
        bundle = result.get("integrity_bundle")
        if not isinstance(bundle, dict):
            errors.append("missing_integrity_bundle")
        else:
            try:
                if "trust_registry_path" in integrity_policy:
                    producer = artifact_provenance["producer"]["id"]
                    artifact_type = artifact_provenance["artifact_type"]
                    resolved = resolve_trusted_key(
                        Path(integrity_policy["trust_registry_path"]),
                        Path(integrity_policy["key_root"]),
                        str(bundle.get("key_id", "")),
                        producer,
                        artifact_type,
                    )
                    trusted_public_key = Path(resolved["trusted_public_key"])
                    trusted_key_id = resolved["trusted_key_id"]
                else:
                    trusted_public_key = Path(integrity_policy["trusted_public_key"])
                    trusted_key_id = str(integrity_policy["trusted_key_id"])
                    resolved = {"status": "active", "key_id": trusted_key_id}
                expected_execution_context = None
                require_execution_context = integrity_policy.get("require_execution_context", False)
                if not isinstance(require_execution_context, bool):
                    raise IntegrityVerificationError("invalid_require_execution_context_policy")
                if require_execution_context:
                    run_id = integrity_policy.get("run_id")
                    if not isinstance(run_id, str) or not run_id.strip():
                        raise IntegrityVerificationError("runtime_run_id_required")
                    expected_execution_context = {
                        "run_id": run_id,
                        "workflow_id": str(envelope["workflow_id"]),
                        "stage_id": str(stage["id"]),
                        "skill_id": str(stage["skill_id"]),
                        "input_ref": str(envelope["input_ref"]),
                    }
                require_trusted_timestamp = integrity_policy.get("require_trusted_timestamp", False)
                if not isinstance(require_trusted_timestamp, bool):
                    raise IntegrityVerificationError("invalid_require_trusted_timestamp_policy")
                timestamp_responses = integrity_policy.get("timestamp_responses", {})
                if not isinstance(timestamp_responses, dict) or any(
                    not isinstance(key, str) or not key
                    or not isinstance(value, str) or not value
                    for key, value in timestamp_responses.items()
                ):
                    raise IntegrityVerificationError("invalid_timestamp_response_map")
                timestamp_response_path = timestamp_responses.get(str(stage["id"]))
                if require_trusted_timestamp and timestamp_response_path is None:
                    raise IntegrityVerificationError("stage_trusted_timestamp_required")
                timestamp_ca_path = integrity_policy.get("timestamp_ca_file")
                timestamp_chain_path = integrity_policy.get("timestamp_untrusted_chain_file")
                if timestamp_response_path is not None and not isinstance(timestamp_ca_path, str):
                    raise IntegrityVerificationError("timestamp_ca_file_required")
                report = verify_integrity_bundle(
                    artifact_provenance, bundle,
                    trusted_public_key, trusted_key_id,
                    Path(integrity_policy["evidence_root"]),
                    expected_execution_context=expected_execution_context,
                    max_age_seconds=integrity_policy.get("max_signature_age_seconds", 900),
                    timestamp_response=Path(timestamp_response_path) if timestamp_response_path else None,
                    timestamp_ca_file=Path(timestamp_ca_path) if timestamp_response_path else None,
                    timestamp_untrusted_chain_file=(
                        Path(timestamp_chain_path)
                        if timestamp_response_path and isinstance(timestamp_chain_path, str)
                        else None
                    ),
                    require_trusted_timestamp=require_trusted_timestamp,
                )
                if report.get("trusted_timestamp") is not None and "valid_from" in resolved:
                    _validate_timestamp_key_window(report["trusted_timestamp"], resolved)
                report["trust_resolution"] = resolved
                result["integrity_verification"] = report
            except (IntegrityVerificationError, TrustRegistryError, KeyError, TypeError, OSError):
                errors.append("artifact_integrity_verification_failed")
    actions = result.get("actions_taken", [])
    if not isinstance(actions, list):
        errors.append("invalid_actions_taken")
    else:
        for action in actions:
            if not isinstance(action, dict):
                errors.append("invalid_action_record")
                continue
            action_id = action.get("action")
            if not isinstance(action_id, str) or not action_id:
                errors.append("invalid_action_id")
                continue
            approval = approvals.get(action_id)
            approval_errors = _approval_errors(stage["id"], action_id, approval)
            if approval_errors:
                errors.extend(f"action_approval:{action_id}:{error}" for error in approval_errors)
                continue
            if not isinstance(approval, dict):
                errors.append(f"action_approval:{action_id}:approval_record_not_object")
                continue
            if action.get("stage_id") != stage["id"]:
                errors.append(f"action_stage_mismatch:{action_id}")
            if action.get("approval_id") != approval.get("approval_id"):
                errors.append(f"action_without_matching_approval:{action_id}")
            if action.get("scope") != approval.get("scope"):
                errors.append(f"action_scope_mismatch:{action_id}")
    return errors


def execute_with_adapter(
    contract: dict[str, Any],
    plan: list[dict[str, Any]],
    adapter: Callable[[dict[str, Any]], dict[str, Any]],
    approvals: dict[str, dict[str, dict[str, Any]]] | None = None,
    integrity_policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run an injected adapter; optional host trust policy enforces signatures and evidence hashes."""
    raw_contract_stages = contract.get("stages")
    contract_stages: list[Any] = (
        raw_contract_stages if isinstance(raw_contract_stages, list) else []
    )
    expected_stage_count = len(contract_stages) if contract_stages else -1
    granted = approvals if approvals is not None else {}
    artifacts: list[dict[str, Any]] = []
    stage_reports: list[dict[str, Any]] = []
    stopped_reason: str | None = None

    if not contract_stages:
        stopped_reason = "invalid_contract_stages"
    elif not isinstance(plan, list) or len(plan) != len(contract_stages):
        stopped_reason = "invalid_plan_stage_count"
    elif not isinstance(granted, dict) or any(
        not isinstance(stage_id, str) or not stage_id
        or not isinstance(stage_records, dict)
        or any(not isinstance(action, str) or not action for action in stage_records)
        for stage_id, stage_records in granted.items()
    ):
        stopped_reason = "invalid_approval_map"

    for index, item in enumerate(plan if stopped_reason is None else []):
        expected_stage = contract_stages[index]
        if not isinstance(expected_stage, dict) or not isinstance(item, dict):
            stopped_reason = "invalid_plan_stage"
            break
        stage_id = expected_stage.get("id")
        skill_id = expected_stage.get("skill_id", stage_id)
        if not isinstance(stage_id, str) or not stage_id or not isinstance(skill_id, str) or not skill_id:
            stopped_reason = "invalid_contract_stage_identity"
            break
        supplied_envelope = item.get("envelope")
        if not isinstance(supplied_envelope, dict):
            stopped_reason = f"invalid_plan_envelope:{stage_id}"
            break
        supplied_stage = supplied_envelope.get("stage")
        if not isinstance(supplied_stage, dict) or (
            supplied_stage.get("id") != stage_id or supplied_stage.get("skill_id") != skill_id
        ):
            stopped_reason = f"plan_contract_stage_mismatch:{stage_id}"
            break
        requested = expected_stage.get("required_approvals", [])
        if not isinstance(requested, list) or any(
            not isinstance(action, str) or not action for action in requested
        ) or len(set(requested)) != len(requested):
            stopped_reason = f"invalid_required_approvals:{stage_id}"
            break
        supplied_approvals: dict[str, Any] = granted.get(stage_id, {})
        if not isinstance(supplied_approvals, dict):
            stopped_reason = f"invalid_approval_records:{stage_id}"
            break
        stage_approvals = {
            action: supplied_approvals[action]
            for action in requested
            if action in supplied_approvals
        }
        invalid_approvals = {
            action: _approval_errors(stage_id, action, stage_approvals[action])
            for action in stage_approvals
        }
        missing = [
            action for action in requested
            if action not in stage_approvals or invalid_approvals.get(action)
        ]
        envelope = dict(supplied_envelope)
        envelope["stage"] = dict(supplied_stage)
        envelope["permissions"] = {
            "requested_approvals": list(requested),
            "granted_approvals": stage_approvals,
            "missing_approvals": missing,
        }
        if artifacts:
            envelope["input_ref"] = artifacts[-1]["output_ref"]
            envelope["prior_stage_output_ref"] = artifacts[-1]["output_ref"]
        if missing:
            stopped_reason = f"approval_required:{stage_id}:{','.join(missing)}"
            break
        try:
            result = adapter(envelope)
        except Exception as exc:
            stopped_reason = f"adapter_error:{envelope['stage']['id']}:{type(exc).__name__}"
            break
        if not isinstance(result, dict):
            stopped_reason = f"invalid_adapter_response:{envelope['stage']['id']}"
            break
        errors = _validate_stage_result(result, envelope, stage_approvals, integrity_policy)
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
    if len(artifacts) == expected_stage_count and stopped_reason is None:
        chain_report = validate_handoff_chain(contract, artifacts)
        if chain_report["status"] != "passed":
            stopped_reason = "handoff_contract_validation_failed"

    complete = len(artifacts) == expected_stage_count and stopped_reason is None
    return {
        "schema_version": "1.0",
        "workflow_id": contract.get("workflow_id", "unnamed"),
        "status": "completed" if complete else ("blocked" if stopped_reason and ("approval_required" in stopped_reason or "stage_blocked" in stopped_reason) else "incomplete"),
        "stages": stage_reports,
        "artifacts": artifacts,
        "handoff_validation": chain_report,
        "stopped_reason": stopped_reason,
        "evidence_classification": {
            "adapter_output": "agent-reported; not independently authenticated",
            "runtime_validation": "deterministic structural and contract checks",
            "real_world_actions": "only those explicitly recorded with matching stage/action/scope approvals; not independently verified",
        },
        "limitations": [
            "The adapter is an integration boundary, not an LLM or Skill execution engine.",
            "The host runtime must load the canonical Skill manifest and supply the adapter implementation.",
            "A mock adapter tests protocol mechanics only, not model reasoning or real actions.",
            "Without an integrity_policy, artifact signatures and evidence hashes are not verified.",
            "With an integrity_policy, Ed25519 signatures are checked against its trusted public key and local evidence root; this does not prove evidence truthfulness.",
        ],
    }
