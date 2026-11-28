"""Verify archived signed artifacts using the host's historical key policy.

This is an audit-only path. It never authorizes an artifact for a live runtime handoff.
"""
from __future__ import annotations

import base64
from datetime import datetime
from pathlib import Path
from typing import Any

from artifact_integrity import IntegrityVerificationError, verify_integrity_bundle
from trust_registry import resolve_trusted_key
from trust_registry_history import (
    RegistryHistoryError,
    registry_snapshot_sha256,
    verify_registry_history,
    verify_rfc3161_timestamp,
)


def verify_archived_bundle(
    envelope: dict[str, Any],
    bundle: dict[str, Any],
    registry_path: Path,
    key_root: Path,
    evidence_root: Path,
    history_records: list[dict[str, Any]] | None = None,
    history_checkpoint: dict[str, Any] | None = None,
    require_history: bool = False,
    registry_snapshots: dict[str, dict[str, Any]] | None = None,
    timestamp_response: Path | None = None,
    timestamp_ca_file: Path | None = None,
    timestamp_untrusted_chain_file: Path | None = None,
    require_trusted_timestamp: bool = False,
    now: datetime | None = None,
    historical_tsa_crl_file: Path | None = None,
    current_tsa_crl_file: Path | None = None,
    require_tsa_revocation: bool = False,
) -> dict[str, Any]:
    """Verify an archived signature using the key's signed-time validity and retirement record."""
    if not isinstance(envelope, dict) or not isinstance(bundle, dict):
        raise IntegrityVerificationError("envelope_and_bundle_must_be_objects")
    statement = bundle.get("statement")
    if not isinstance(statement, dict):
        raise IntegrityVerificationError("integrity_statement_required")
    if not isinstance(require_trusted_timestamp, bool):
        raise RegistryHistoryError("invalid_require_trusted_timestamp_policy")
    if not isinstance(require_tsa_revocation, bool):
        raise RegistryHistoryError("invalid_require_tsa_revocation_policy")
    if (historical_tsa_crl_file is None) != (current_tsa_crl_file is None):
        raise RegistryHistoryError("historical_and_current_tsa_crls_must_be_supplied_together")
    if require_tsa_revocation and historical_tsa_crl_file is None:
        raise RegistryHistoryError("tsa_revocation_crls_required")
    timestamp_paths_supplied = timestamp_response is not None or timestamp_ca_file is not None
    if timestamp_paths_supplied and (timestamp_response is None or timestamp_ca_file is None):
        raise RegistryHistoryError("timestamp_response_and_ca_must_be_supplied_together")
    if require_trusted_timestamp and not timestamp_paths_supplied:
        raise RegistryHistoryError("trusted_timestamp_required")
    timestamp_precheck: dict[str, str] | None = None
    if timestamp_response is not None and timestamp_ca_file is not None:
        signature_text = bundle.get("signature")
        if not isinstance(signature_text, str) or not signature_text:
            raise IntegrityVerificationError("signature_required")
        try:
            signature_bytes = base64.b64decode(signature_text, validate=True)
        except (ValueError, TypeError) as exc:
            raise IntegrityVerificationError("signature_is_not_valid_base64") from exc
        timestamp_precheck = verify_rfc3161_timestamp(
            signature_bytes,
            timestamp_response,
            timestamp_ca_file,
            timestamp_untrusted_chain_file,
            historical_tsa_crl_file,
            current_tsa_crl_file,
            require_tsa_revocation,
            now,
        )
    execution_context = statement.get("execution_context")
    if statement.get("statement_version") == "1.1":
        required = {
            "run_id", "workflow_id", "stage_id", "skill_id",
            "input_ref", "issued_at", "expires_at",
        }
        if not isinstance(execution_context, dict) or set(execution_context) != required:
            raise IntegrityVerificationError("invalid_archived_execution_context")
        signed_at = execution_context.get("issued_at")
    elif statement.get("statement_version") == "1.0":
        signed_at = envelope.get("created_at")
    else:
        raise IntegrityVerificationError("unsupported_archived_statement_version")

    producer = envelope.get("producer")
    if not isinstance(producer, dict):
        raise IntegrityVerificationError("artifact_producer_required")
    artifact_type = envelope.get("artifact_type")
    if not isinstance(artifact_type, str) or not artifact_type:
        raise IntegrityVerificationError("artifact_type_required")

    if timestamp_precheck is not None:
        # TSA-authenticated time, not signer-supplied issued_at/created_at,
        # governs the historical key-validity decision.
        signed_at = timestamp_precheck["gen_time"]

    resolved = resolve_trusted_key(
        registry_path,
        key_root,
        str(bundle.get("key_id", "")),
        str(producer.get("id", "")),
        artifact_type,
        now=now,
        verification_mode="historical",
        signed_at=signed_at if isinstance(signed_at, str) else None,
    )
    report = verify_integrity_bundle(
        envelope,
        bundle,
        Path(resolved["trusted_public_key"]),
        resolved["trusted_key_id"],
        evidence_root,
        timestamp_response=timestamp_response,
        timestamp_ca_file=timestamp_ca_file,
        timestamp_untrusted_chain_file=timestamp_untrusted_chain_file,
        require_trusted_timestamp=require_trusted_timestamp,
        now=now,
        historical_tsa_crl_file=historical_tsa_crl_file,
        current_tsa_crl_file=current_tsa_crl_file,
        require_tsa_revocation=require_tsa_revocation,
    )
    history_report = None
    if not isinstance(require_history, bool):
        raise RegistryHistoryError("invalid_require_history_policy")
    if require_history:
        if history_records is None or history_checkpoint is None or registry_snapshots is None:
            raise RegistryHistoryError("authenticated_registry_history_and_snapshots_required")
        history_report = verify_registry_history(history_records, history_checkpoint)
        key_id = resolved["trusted_key_id"]
        key_events = [
            event for event in history_report["events"]
            if event["key_id"] == key_id
            or (event["action"] == "key_rotated" and event.get("replacement_key_id") == key_id)
        ]
        if any(
            event["action"] == "key_revoked" and event["key_id"] == key_id
            for event in key_events
        ):
            raise RegistryHistoryError("registry_history_key_revoked")
        lifecycle = history_report["key_lifecycle"].get(key_id)
        if lifecycle != resolved["status"]:
            raise RegistryHistoryError("registry_history_lifecycle_mismatch")
        additions = [
            event for event in key_events
            if (event["action"] == "key_added" and event["key_id"] == key_id)
            or (event["action"] == "key_rotated" and event.get("replacement_key_id") == key_id)
        ]
        if len(additions) != 1:
            raise RegistryHistoryError("registry_history_key_addition_missing_or_duplicated")
        retirements = [
            event for event in key_events
            if event["key_id"] == key_id and event["action"] in {"key_retired", "key_rotated"}
        ]
        if resolved["status"] == "retired":
            if len(retirements) != 1 or retirements[0]["effective_at"] != resolved["retired_at"]:
                raise RegistryHistoryError("registry_history_retirement_mismatch")
        elif retirements:
            raise RegistryHistoryError("registry_history_active_key_has_retirement_event")
        required_events = additions + retirements
        for event in required_events:
            digest = event["registry_sha256"]
            snapshot = registry_snapshots.get(digest)
            if not isinstance(snapshot, dict) or registry_snapshot_sha256(snapshot) != digest:
                raise RegistryHistoryError("registry_history_snapshot_digest_mismatch")
            snapshot_keys = snapshot.get("keys")
            if snapshot.get("registry_version") != "1.0" or not isinstance(snapshot_keys, list):
                raise RegistryHistoryError("invalid_historical_registry_snapshot")
            matches = [
                item for item in snapshot_keys
                if isinstance(item, dict) and item.get("key_id") == key_id
            ]
            if len(matches) != 1:
                raise RegistryHistoryError("historical_registry_key_missing_or_duplicated")
            snapshot_entry = matches[0]
            if snapshot_entry.get("public_key_sha256") != resolved["public_key_sha256"]:
                raise RegistryHistoryError("historical_registry_public_key_changed")
            is_addition = event in additions
            if is_addition and snapshot_entry.get("status") != "active":
                raise RegistryHistoryError("historical_key_addition_snapshot_not_active")
            if event in retirements:
                if snapshot_entry.get("status") != "retired":
                    raise RegistryHistoryError("historical_key_retirement_snapshot_not_retired")
                if snapshot_entry.get("retired_at") != event["effective_at"]:
                    raise RegistryHistoryError("historical_key_retirement_snapshot_time_mismatch")
    report["status"] = "archived_verified"
    report["trust_resolution"] = resolved
    report["history_verification"] = history_report
    report["limitations"] = [
        *report["limitations"],
        "Archival verification does not authorize this artifact for a current runtime handoff.",
        "Revoked keys are rejected even when the artifact timestamp predates revocation.",
        "The host must authenticate registry history and distribution independently.",
    ]
    return report
