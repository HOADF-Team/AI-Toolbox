"""Host-managed trust registry for artifact signing keys.

The registry is policy data, not a trust anchor by itself: its file and key directory
must be provisioned by the host from an authenticated configuration source.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any


class TrustRegistryError(ValueError):
    """Raised when a trust registry entry cannot authorize a signature."""


_KEY_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _parse_time(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise TrustRegistryError(f"invalid_{field}")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise TrustRegistryError(f"invalid_{field}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise TrustRegistryError(f"{field}_must_include_timezone")
    return parsed


def _confined_file(root: Path, relative: Any) -> Path:
    if not isinstance(relative, str) or not relative.strip():
        raise TrustRegistryError("public_key_path_required")
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts:
        raise TrustRegistryError("public_key_path_must_be_relative_and_confined")
    base = root.resolve(strict=True)
    current = base
    for part in rel.parts:
        current = current / part
        if current.is_symlink():
            raise TrustRegistryError("public_key_symlink_not_allowed")
    try:
        path = (base / rel).resolve(strict=True)
        path.relative_to(base)
    except (OSError, ValueError) as exc:
        raise TrustRegistryError("public_key_file_missing_or_outside_root") from exc
    if not path.is_file():
        raise TrustRegistryError("public_key_path_is_not_a_file")
    return path


def public_key_fingerprint(public_key: Path) -> str:
    """Return SHA-256 fingerprint of DER-encoded SubjectPublicKeyInfo."""
    try:
        result = subprocess.run(
            ["openssl", "pkey", "-pubin", "-in", str(public_key), "-outform", "DER"],
            check=True, capture_output=True, timeout=15,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise TrustRegistryError("public_key_fingerprint_unavailable") from exc
    return hashlib.sha256(result.stdout).hexdigest()


def resolve_trusted_key(
    registry_path: Path,
    key_root: Path,
    key_id: str,
    producer_id: str,
    artifact_type: str,
    now: datetime | None = None,
    verification_mode: str = "current",
    signed_at: str | None = None,
) -> dict[str, Any]:
    """Resolve a key under current-use or explicitly requested archival policy."""
    if not isinstance(key_id, str) or not _KEY_ID.fullmatch(key_id):
        raise TrustRegistryError("invalid_key_id")
    if not isinstance(producer_id, str) or not producer_id:
        raise TrustRegistryError("producer_id_required")
    if not isinstance(artifact_type, str) or not artifact_type:
        raise TrustRegistryError("artifact_type_required")
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TrustRegistryError("trust_registry_unavailable_or_invalid_json") from exc
    if not isinstance(registry, dict) or registry.get("registry_version") != "1.0":
        raise TrustRegistryError("unsupported_trust_registry_version")
    entries = registry.get("keys")
    if not isinstance(entries, list):
        raise TrustRegistryError("trust_registry_keys_must_be_array")
    matches = [entry for entry in entries if isinstance(entry, dict) and entry.get("key_id") == key_id]
    if len(matches) != 1:
        raise TrustRegistryError("key_id_missing_or_duplicated")
    entry = matches[0]
    if entry.get("algorithm") != "Ed25519":
        raise TrustRegistryError("unsupported_trusted_key_algorithm")
    if verification_mode not in {"current", "historical"}:
        raise TrustRegistryError("invalid_verification_mode")
    status = entry.get("status")
    if status == "revoked":
        raise TrustRegistryError("signing_key_revoked")
    if verification_mode == "current" and status != "active":
        raise TrustRegistryError("signing_key_not_active")
    if verification_mode == "historical" and status not in {"active", "retired"}:
        raise TrustRegistryError("signing_key_not_archivable")
    not_before = _parse_time(entry.get("not_before"), "not_before")
    not_after = _parse_time(entry.get("not_after"), "not_after")
    if not_before >= not_after:
        raise TrustRegistryError("invalid_key_validity_window")
    if verification_mode == "current":
        current = now or datetime.now().astimezone()
        if current.tzinfo is None or current.utcoffset() is None:
            raise TrustRegistryError("verification_time_must_include_timezone")
        if current < not_before or current >= not_after:
            raise TrustRegistryError("signing_key_outside_validity_window")
    else:
        signed_time = _parse_time(signed_at, "signed_at")
        if signed_time < not_before or signed_time >= not_after:
            raise TrustRegistryError("historical_signature_outside_key_validity")
        if status == "retired":
            retired_at = _parse_time(entry.get("retired_at"), "retired_at")
            if retired_at <= not_before:
                raise TrustRegistryError("invalid_key_retirement_time")
            if signed_time >= retired_at:
                raise TrustRegistryError("historical_signature_after_key_retirement")

    producers = entry.get("allowed_producers")
    artifact_types = entry.get("allowed_artifact_types")
    if not isinstance(producers, list) or not producers or any(not isinstance(x, str) or not x for x in producers):
        raise TrustRegistryError("invalid_allowed_producers")
    if not isinstance(artifact_types, list) or not artifact_types or any(not isinstance(x, str) or not x for x in artifact_types):
        raise TrustRegistryError("invalid_allowed_artifact_types")
    if producer_id not in producers:
        raise TrustRegistryError("producer_not_authorized_for_key")
    if artifact_type not in artifact_types:
        raise TrustRegistryError("artifact_type_not_authorized_for_key")

    expected_fingerprint = entry.get("public_key_sha256")
    if not isinstance(expected_fingerprint, str) or not _SHA256.fullmatch(expected_fingerprint):
        raise TrustRegistryError("invalid_registered_public_key_fingerprint")
    public_key = _confined_file(key_root, entry.get("public_key_file"))
    actual_fingerprint = public_key_fingerprint(public_key)
    if actual_fingerprint != expected_fingerprint:
        raise TrustRegistryError("trusted_public_key_fingerprint_mismatch")
    return {
        "trusted_public_key": str(public_key),
        "trusted_key_id": key_id,
        "public_key_sha256": actual_fingerprint,
        "status": status,
        "verification_mode": verification_mode,
        "valid_until": not_after.isoformat(),
        "retired_at": entry.get("retired_at"),
        "producer_id": producer_id,
        "artifact_type": artifact_type,
    }
