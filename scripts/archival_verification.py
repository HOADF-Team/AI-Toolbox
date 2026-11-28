"""Verify archived signed artifacts using the host's historical key policy.

This is an audit-only path. It never authorizes an artifact for a live runtime handoff.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from artifact_integrity import IntegrityVerificationError, verify_integrity_bundle
from trust_registry import resolve_trusted_key


def verify_archived_bundle(
    envelope: dict[str, Any],
    bundle: dict[str, Any],
    registry_path: Path,
    key_root: Path,
    evidence_root: Path,
) -> dict[str, Any]:
    """Verify an archived signature using the key's signed-time validity and retirement record."""
    if not isinstance(envelope, dict) or not isinstance(bundle, dict):
        raise IntegrityVerificationError("envelope_and_bundle_must_be_objects")
    statement = bundle.get("statement")
    if not isinstance(statement, dict):
        raise IntegrityVerificationError("integrity_statement_required")
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

    resolved = resolve_trusted_key(
        registry_path,
        key_root,
        str(bundle.get("key_id", "")),
        str(producer.get("id", "")),
        artifact_type,
        verification_mode="historical",
        signed_at=signed_at if isinstance(signed_at, str) else None,
    )
    report = verify_integrity_bundle(
        envelope,
        bundle,
        Path(resolved["trusted_public_key"]),
        resolved["trusted_key_id"],
        evidence_root,
    )
    report["status"] = "archived_verified"
    report["trust_resolution"] = resolved
    report["limitations"] = [
        *report["limitations"],
        "Archival verification does not authorize this artifact for a current runtime handoff.",
        "Revoked keys are rejected even when the artifact timestamp predates revocation.",
        "The host must authenticate registry history and distribution independently.",
    ]
    return report
