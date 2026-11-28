"""Cryptographic integrity checks for artifact provenance bundles.

Uses OpenSSL Ed25519 through fixed-argument subprocess calls; no shell is used.
Trust is anchored only by the public key and key ID supplied by host policy.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class IntegrityVerificationError(ValueError):
    """Raised when an artifact integrity bundle cannot be trusted."""


def _validate_json_tree(value: Any) -> None:
    """Reject Python values that JSON would silently coerce or reinterpret."""
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                raise IntegrityVerificationError("canonical_json_object_keys_must_be_strings")
            _validate_json_tree(child)
    elif isinstance(value, list):
        for child in value:
            _validate_json_tree(child)
    elif value is None or isinstance(value, (str, bool, int, float)):
        return
    else:
        raise IntegrityVerificationError("value_is_not_json_data")


def canonical_json_bytes(value: Any) -> bytes:
    """Return deterministic JSON bytes without Python-specific key coercion."""
    _validate_json_tree(value)
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise IntegrityVerificationError("value_is_not_canonical_json") from exc


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _safe_evidence_file(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative.strip():
        raise IntegrityVerificationError("evidence_path_required")
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts:
        raise IntegrityVerificationError("evidence_path_must_be_relative_and_confined")
    base = root.resolve(strict=True)
    candidate = base / rel
    current = base
    for part in rel.parts:
        current = current / part
        if current.is_symlink():
            raise IntegrityVerificationError("evidence_symlink_not_allowed")
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(base)
    except (OSError, ValueError) as exc:
        raise IntegrityVerificationError("evidence_file_missing_or_outside_root") from exc
    if not resolved.is_file():
        raise IntegrityVerificationError("evidence_reference_is_not_a_file")
    return resolved


def _parse_aware_time(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise IntegrityVerificationError(f"invalid_{field}")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise IntegrityVerificationError(f"invalid_{field}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise IntegrityVerificationError(f"{field}_must_include_timezone")
    return parsed


def _validate_execution_context(
    statement: dict[str, Any],
    expected: dict[str, str],
    max_age_seconds: int,
    now: datetime | None,
) -> dict[str, Any]:
    context = statement.get("execution_context")
    if not isinstance(expected, dict) or set(expected) != {
        "run_id", "workflow_id", "stage_id", "skill_id", "input_ref"
    }:
        raise IntegrityVerificationError("invalid_expected_execution_context_fields")
    if not isinstance(context, dict):
        raise IntegrityVerificationError("signed_execution_context_required")
    required = {"run_id", "workflow_id", "stage_id", "skill_id", "input_ref", "issued_at", "expires_at"}
    if set(context) != required:
        raise IntegrityVerificationError("invalid_signed_execution_context_fields")
    for key, value in expected.items():
        if not isinstance(value, str) or not value or context.get(key) != value:
            raise IntegrityVerificationError(f"signed_execution_context_mismatch:{key}")
    issued = _parse_aware_time(context.get("issued_at"), "issued_at")
    expires = _parse_aware_time(context.get("expires_at"), "expires_at")
    if expires <= issued:
        raise IntegrityVerificationError("invalid_execution_context_expiry")
    if not isinstance(max_age_seconds, int) or isinstance(max_age_seconds, bool) or not 1 <= max_age_seconds <= 86400:
        raise IntegrityVerificationError("invalid_max_signature_age_seconds")
    if (expires - issued).total_seconds() > max_age_seconds:
        raise IntegrityVerificationError("execution_context_ttl_exceeds_policy")
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None or current.utcoffset() is None:
        raise IntegrityVerificationError("verification_time_must_include_timezone")
    if issued > current:
        raise IntegrityVerificationError("signature_issued_in_future")
    if current >= expires:
        raise IntegrityVerificationError("signed_execution_context_expired")
    if (current - issued).total_seconds() > max_age_seconds:
        raise IntegrityVerificationError("signed_execution_context_too_old")
    return context


def verify_integrity_bundle(
    envelope: dict[str, Any],
    bundle: dict[str, Any],
    trusted_public_key: Path,
    trusted_key_id: str,
    evidence_root: Path,
    expected_execution_context: dict[str, str] | None = None,
    max_age_seconds: int = 900,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Verify payload/evidence hashes and an Ed25519 signature from a trusted key."""
    if not isinstance(envelope, dict) or not isinstance(bundle, dict):
        raise IntegrityVerificationError("envelope_and_bundle_must_be_objects")
    if not trusted_key_id or bundle.get("key_id") != trusted_key_id:
        raise IntegrityVerificationError("untrusted_signing_key_id")
    if bundle.get("algorithm") != "Ed25519":
        raise IntegrityVerificationError("unsupported_signature_algorithm")
    statement = bundle.get("statement")
    if not isinstance(statement, dict) or statement.get("statement_version") not in {"1.0", "1.1"}:
        raise IntegrityVerificationError("invalid_integrity_statement")
    if expected_execution_context is not None:
        if statement.get("statement_version") != "1.1":
            raise IntegrityVerificationError("signed_execution_context_required")
        execution_context = _validate_execution_context(
            statement, expected_execution_context, max_age_seconds, now
        )
    else:
        execution_context = None

    envelope_digest = sha256_bytes(canonical_json_bytes(envelope))
    if statement.get("envelope_sha256") != envelope_digest:
        raise IntegrityVerificationError("artifact_envelope_digest_mismatch")

    payload_digest = envelope.get("payload_sha256")
    if payload_digest is not None:
        actual_payload_digest = sha256_bytes(canonical_json_bytes(envelope.get("payload")))
        if payload_digest != actual_payload_digest:
            raise IntegrityVerificationError("payload_digest_mismatch")

    evidence = statement.get("evidence")
    refs = envelope.get("evidence")
    if not isinstance(evidence, list) or not isinstance(refs, list):
        raise IntegrityVerificationError("evidence_manifest_must_be_arrays")
    if any(not isinstance(ref, str) or not ref.strip() for ref in refs):
        raise IntegrityVerificationError("envelope_evidence_refs_must_be_nonempty_strings")
    if len(set(refs)) != len(refs):
        raise IntegrityVerificationError("duplicate_envelope_evidence_reference")
    manifest_refs: list[str] = []
    for item in evidence:
        if not isinstance(item, dict):
            raise IntegrityVerificationError("evidence_manifest_entry_must_be_object")
        if set(item) != {"ref", "path", "sha256"}:
            raise IntegrityVerificationError("invalid_evidence_manifest_entry_fields")
        ref = item.get("ref")
        relative_path = item.get("path")
        digest = item.get("sha256")
        if not isinstance(ref, str) or not ref.strip():
            raise IntegrityVerificationError("evidence_manifest_reference_required")
        if not isinstance(relative_path, str) or not relative_path.strip():
            raise IntegrityVerificationError("evidence_path_required")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise IntegrityVerificationError("invalid_evidence_sha256")
        manifest_refs.append(ref)
    if len(set(manifest_refs)) != len(manifest_refs):
        raise IntegrityVerificationError("duplicate_evidence_manifest_reference")
    if set(manifest_refs) != set(refs) or len(manifest_refs) != len(refs):
        raise IntegrityVerificationError("evidence_reference_set_mismatch")

    root = evidence_root.resolve(strict=True)
    verified_evidence: list[str] = []
    for item in evidence:
        relative_path = item["path"]
        path = _safe_evidence_file(root, relative_path)
        actual = sha256_bytes(path.read_bytes())
        if item["sha256"] != actual:
            raise IntegrityVerificationError("evidence_digest_mismatch")
        verified_evidence.append(item["ref"])

    signature_text = bundle.get("signature")
    if not isinstance(signature_text, str) or not signature_text:
        raise IntegrityVerificationError("signature_required")
    try:
        signature = base64.b64decode(signature_text, validate=True)
    except ValueError as exc:
        raise IntegrityVerificationError("signature_is_not_valid_base64") from exc
    if not trusted_public_key.is_file():
        raise IntegrityVerificationError("trusted_public_key_unavailable")

    with tempfile.TemporaryDirectory(prefix="artifact-integrity-") as temp_dir:
        statement_path = Path(temp_dir) / "statement.json"
        signature_path = Path(temp_dir) / "statement.sig"
        statement_path.write_bytes(canonical_json_bytes(statement))
        signature_path.write_bytes(signature)
        try:
            completed = subprocess.run(
                [
                    "openssl", "pkeyutl", "-verify", "-pubin", "-inkey",
                    str(trusted_public_key), "-rawin", "-in", str(statement_path),
                    "-sigfile", str(signature_path),
                ],
                check=False, capture_output=True, text=True, timeout=15,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise IntegrityVerificationError("openssl_verification_unavailable") from exc
        if completed.returncode != 0:
            raise IntegrityVerificationError("signature_verification_failed")

    return {
        "status": "verified",
        "algorithm": "Ed25519",
        "key_id": trusted_key_id,
        "envelope_sha256": envelope_digest,
        "verified_evidence": verified_evidence,
        "execution_context": execution_context,
        "replay_protection": "run_stage_bound_and_time_limited" if execution_context else "not_enabled",
        "limitations": [
            "The public key is trusted only because the host supplied it through policy.",
            "A valid signature proves integrity and key possession, not that evidence is truthful.",
            "The verifier does not establish real-world producer identity or the correctness of payload claims.",
        ],
    }
