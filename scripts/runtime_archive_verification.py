"""Offline cryptographic audit of portable runtime-run archives.

Trust roots are supplied by the verifier host, never trusted merely because they
are bundled with the archive. This module is audit-only and cannot authorize handoff.
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from archival_verification import verify_archived_bundle
from handoff_contract import validate_handoff_chain
from handoff_runtime import stage_result_sha256
from artifact_provenance import validate_provenance_envelope
from runtime_run_archive import RuntimeArchiveError, verify_runtime_archive
from trust_registry_history import verify_history_anchor


class RuntimeArchiveVerificationError(ValueError):
    """Raised when an archive lacks authenticated, complete run evidence."""


_STAGE_ID = re.compile(r"[a-z0-9][a-z0-9-]{0,63}\\Z")


def _safe_file(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or "\\\\" in relative:
        raise RuntimeArchiveVerificationError("unsafe_archive_reference")
    rel = Path(relative)
    if rel.is_absolute() or any(part in {"", ".", ".."} for part in rel.parts):
        raise RuntimeArchiveVerificationError("unsafe_archive_reference")
    base = root.resolve(strict=True)
    current = base
    for part in rel.parts:
        current = current / part
        if current.is_symlink():
            raise RuntimeArchiveVerificationError("archive_symlink_not_allowed")
    try:
        resolved = current.resolve(strict=True)
        resolved.relative_to(base)
    except (OSError, ValueError) as exc:
        raise RuntimeArchiveVerificationError("archive_file_missing_or_outside_root") from exc
    if not resolved.is_file():
        raise RuntimeArchiveVerificationError("archive_reference_not_regular_file")
    return resolved


def _read_json(root: Path, relative: str) -> Any:
    path = _safe_file(root, relative)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeArchiveVerificationError(f"invalid_archive_json:{relative}") from exc


def verify_runtime_archive_cryptographically(
    archive_root: Path,
    trust_policy: dict[str, Any],
    now: datetime | None = None,
) -> dict[str, Any]:
    """Verify every stage signature, timestamp, registry history and handoff link.

    Required archive layout:
      workflow/contract.json
      workflow/stages/<stage-id>.json
      workflow/stages/<stage-id>/evidence/...
      trust/registry.json, trust/keys/..., trust/history.json,
      trust/history-checkpoint.json, trust/history-anchor.json,
      trust/registry-snapshots/<snapshot-sha256>.json
      trust/history-anchor.tsr and workflow/stages/<stage-id>/timestamp.tsr

    The history-anchor public key and TSA CA bundle are host-supplied trust roots.
    """
    if not isinstance(trust_policy, dict):
        raise RuntimeArchiveVerificationError("external_trust_policy_required")
    required_policy = {"history_anchor_public_key", "history_anchor_key_id", "timestamp_ca_file"}
    if not required_policy.issubset(trust_policy):
        raise RuntimeArchiveVerificationError("external_trust_anchors_required")
    anchor_key = Path(trust_policy["history_anchor_public_key"])
    tsa_ca = Path(trust_policy["timestamp_ca_file"])
    tsa_chain_value = trust_policy.get("timestamp_untrusted_chain_file")
    tsa_chain = Path(tsa_chain_value) if tsa_chain_value else None
    require_timestamps = trust_policy.get("require_trusted_timestamps", True)
    if not isinstance(require_timestamps, bool):
        raise RuntimeArchiveVerificationError("invalid_timestamp_policy")
    if anchor_key.is_symlink() or not anchor_key.is_file():
        raise RuntimeArchiveVerificationError("external_history_anchor_key_unavailable")
    if tsa_ca.is_symlink() or not tsa_ca.is_file():
        raise RuntimeArchiveVerificationError("external_tsa_trust_bundle_unavailable")
    if tsa_chain is not None and (tsa_chain.is_symlink() or not tsa_chain.is_file()):
        raise RuntimeArchiveVerificationError("external_tsa_chain_unavailable")

    root = Path(archive_root)
    package_report = verify_runtime_archive(root)
    metadata = _read_json(root, "archive.json")
    contract = _read_json(root, "workflow/contract.json")
    stages = contract.get("stages") if isinstance(contract, dict) else None
    if not isinstance(stages, list) or not stages:
        raise RuntimeArchiveVerificationError("archive_workflow_contract_invalid")
    expected_ids = [item.get("id") for item in stages if isinstance(item, dict)]
    if len(expected_ids) != len(stages) or any(
        not isinstance(item, str) or not _STAGE_ID.fullmatch(item) for item in expected_ids
    ):
        raise RuntimeArchiveVerificationError("archive_stage_ids_invalid")
    if metadata.get("stage_ids") != expected_ids:
        raise RuntimeArchiveVerificationError("archive_stage_sequence_metadata_mismatch")
    if metadata.get("workflow_id") != contract.get("workflow_id"):
        raise RuntimeArchiveVerificationError("archive_workflow_id_mismatch")
    if metadata.get("run_status") != "completed":
        raise RuntimeArchiveVerificationError("archive_run_not_completed")

    registry_path = _safe_file(root, "trust/registry.json")
    key_root = _safe_file(root, "trust/keys/.anchor").parent
    history = _read_json(root, "trust/history.json")
    checkpoint = _read_json(root, "trust/history-checkpoint.json")
    anchor = _read_json(root, "trust/history-anchor.json")
    if not isinstance(history, list) or not isinstance(checkpoint, dict):
        raise RuntimeArchiveVerificationError("registry_history_package_invalid")

    anchor_timestamp = None
    if require_timestamps:
        anchor_timestamp = _safe_file(root, "trust/history-anchor.tsr")
    anchor_report = verify_history_anchor(
        history, anchor, anchor_key, str(trust_policy["history_anchor_key_id"]),
        timestamp_response=anchor_timestamp,
        timestamp_ca_file=tsa_ca if require_timestamps else None,
        timestamp_untrusted_chain_file=tsa_chain if require_timestamps else None,
    )
    if anchor_report.get("checkpoint") != checkpoint:
        raise RuntimeArchiveVerificationError("authenticated_history_checkpoint_mismatch")

    snapshots: dict[str, dict[str, Any]] = {}
    for event_record in history:
        event = event_record.get("event", {}) if isinstance(event_record, dict) else {}
        digest = event.get("registry_sha256") if isinstance(event, dict) else None
        if isinstance(digest, str) and digest not in snapshots:
            if not re.fullmatch(r"[0-9a-f]{64}", digest):
                raise RuntimeArchiveVerificationError("invalid_registry_snapshot_reference")
            snapshot = _read_json(root, f"trust/registry-snapshots/{digest}.json")
            snapshots[digest] = snapshot

    stage_results: list[dict[str, Any]] = []
    stage_reports: list[dict[str, Any]] = []
    for stage_spec, stage_id in zip(stages, expected_ids, strict=True):
        result = _read_json(root, f"workflow/stages/{stage_id}.json")
        if not isinstance(result, dict):
            raise RuntimeArchiveVerificationError(f"stage_result_not_object:{stage_id}")
        envelope = result.get("artifact_provenance")
        bundle = result.get("integrity_bundle")
        if not isinstance(envelope, dict) or not isinstance(bundle, dict):
            raise RuntimeArchiveVerificationError(f"stage_signature_material_missing:{stage_id}")
        provenance_report = validate_provenance_envelope(envelope)
        if provenance_report.get("status") != "passed":
            raise RuntimeArchiveVerificationError(f"stage_provenance_invalid:{stage_id}")
        if result.get("stage") != stage_id or result.get("skill_id") != stage_spec.get("skill_id", stage_id):
            raise RuntimeArchiveVerificationError(f"stage_identity_mismatch:{stage_id}")
        context = bundle.get("statement", {}).get("execution_context")
        expected_context = {
            "run_id": metadata["run_id"],
            "workflow_id": metadata["workflow_id"],
            "stage_id": stage_id,
            "skill_id": result["skill_id"],
            "input_ref": result.get("input_ref"),
        }
        if not isinstance(context, dict) or any(context.get(k) != v for k, v in expected_context.items()):
            raise RuntimeArchiveVerificationError(f"signed_execution_context_mismatch:{stage_id}")
        payload = envelope.get("payload", {})
        if (
            envelope.get("producer", {}).get("id") != result["skill_id"]
            or payload.get("stage") != stage_id
            or payload.get("skill_id") != result["skill_id"]
            or payload.get("output_ref") != result.get("output_ref")
            or payload.get("stage_result_sha256") != stage_result_sha256(result)
        ):
            raise RuntimeArchiveVerificationError(f"signed_stage_result_binding_mismatch:{stage_id}")
        timestamp_response = None
        if require_timestamps:
            timestamp_response = _safe_file(root, f"workflow/stages/{stage_id}/timestamp.tsr")
        report = verify_archived_bundle(
            envelope, bundle, registry_path, key_root,
            _safe_file(root, f"workflow/stages/{stage_id}/evidence/.placeholder").parent,
            history_records=history,
            history_checkpoint=checkpoint,
            require_history=True,
            registry_snapshots=snapshots,
            timestamp_response=timestamp_response,
            timestamp_ca_file=tsa_ca if require_timestamps else None,
            timestamp_untrusted_chain_file=tsa_chain if require_timestamps else None,
            require_trusted_timestamp=require_timestamps,
            now=now,
        )
        if report.get("status") != "archived_verified":
            raise RuntimeArchiveVerificationError(f"stage_archival_verification_failed:{stage_id}")
        stage_results.append({
            "stage": stage_id,
            "input_ref": result.get("input_ref"),
            "output_ref": result.get("output_ref"),
            "evidence": result.get("evidence"),
        })
        stage_reports.append({"stage": stage_id, "verification": report})

    chain_report = validate_handoff_chain(contract, stage_results)
    if chain_report.get("status") != "passed":
        raise RuntimeArchiveVerificationError("archived_handoff_chain_invalid")
    return {
        "status": "runtime_archive_cryptographically_verified",
        "run_id": metadata["run_id"],
        "workflow_id": metadata["workflow_id"],
        "archive_integrity": package_report,
        "history_anchor": anchor_report,
        "stages": stage_reports,
        "handoff_validation": chain_report,
        "verification_scope": "offline_audit_only",
        "limitations": [
            "The host-supplied history-anchor public key and TSA trust bundle are the trust roots.",
            "Embedded registry keys are accepted only after historical registry and anchor verification.",
            "Verification is retrospective audit evidence; it never authorizes live runtime handoff or external actions.",
        ],
    }
