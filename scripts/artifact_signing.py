"""Create Ed25519 integrity bundles using host-managed signing keys.

The helper never generates, stores, or exports private keys. Key custody and registry
distribution remain responsibilities of the host runtime.
"""
from __future__ import annotations

import base64
import hashlib
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from artifact_integrity import IntegrityVerificationError, canonical_json_bytes, sha256_bytes
from trust_registry import TrustRegistryError, public_key_fingerprint

_KEY_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


def _confined_evidence_file(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative.strip():
        raise IntegrityVerificationError("evidence_path_required")
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts:
        raise IntegrityVerificationError("evidence_path_must_be_relative_and_confined")
    base = root.resolve(strict=True)
    current = base
    for part in rel.parts:
        current = current / part
        if current.is_symlink():
            raise IntegrityVerificationError("evidence_symlink_not_allowed")
    try:
        path = (base / rel).resolve(strict=True)
        path.relative_to(base)
    except (OSError, ValueError) as exc:
        raise IntegrityVerificationError("evidence_file_missing_or_outside_root") from exc
    if not path.is_file():
        raise IntegrityVerificationError("evidence_reference_is_not_a_file")
    return path


def _private_key_matches_registry(
    private_key: Path,
    trusted_public_key: Path,
    expected_fingerprint: str,
) -> None:
    if private_key.is_symlink() or not private_key.is_file():
        raise IntegrityVerificationError("signing_private_key_unavailable_or_unsafe")
    if os.name == "posix" and private_key.stat().st_mode & 0o077:
        raise IntegrityVerificationError("signing_private_key_permissions_too_open")
    try:
        derived = subprocess.run(
            ["openssl", "pkey", "-in", str(private_key), "-pubout", "-outform", "DER"],
            check=True, capture_output=True, timeout=15,
        ).stdout
        trusted_fingerprint = public_key_fingerprint(trusted_public_key)
    except (OSError, subprocess.SubprocessError, TrustRegistryError) as exc:
        raise IntegrityVerificationError("signing_key_validation_unavailable") from exc
    if hashlib.sha256(derived).hexdigest() != expected_fingerprint:
        raise IntegrityVerificationError("signing_private_key_does_not_match_registered_key")
    if trusted_fingerprint != expected_fingerprint:
        raise IntegrityVerificationError("registered_public_key_fingerprint_mismatch")


def create_integrity_bundle(
    envelope: dict[str, Any],
    key_id: str,
    private_key: Path,
    trusted_public_key: Path,
    expected_public_key_sha256: str,
    evidence_root: Path,
    evidence_paths: dict[str, str],
) -> dict[str, Any]:
    """Build a signed bundle; callers must resolve the key through host trust policy first."""
    if not isinstance(envelope, dict):
        raise IntegrityVerificationError("envelope_must_be_object")
    if not isinstance(key_id, str) or not _KEY_ID.fullmatch(key_id):
        raise IntegrityVerificationError("invalid_key_id")
    if not isinstance(expected_public_key_sha256, str) or not re.fullmatch(
        r"[0-9a-f]{64}", expected_public_key_sha256
    ):
        raise IntegrityVerificationError("invalid_expected_public_key_fingerprint")
    refs = envelope.get("evidence")
    if not isinstance(refs, list) or any(not isinstance(ref, str) or not ref for ref in refs):
        raise IntegrityVerificationError("envelope_evidence_refs_must_be_strings")
    if not isinstance(evidence_paths, dict) or set(evidence_paths) != set(refs):
        raise IntegrityVerificationError("evidence_paths_must_match_envelope_refs_exactly")

    _private_key_matches_registry(private_key, trusted_public_key, expected_public_key_sha256)
    root = evidence_root.resolve(strict=True)
    manifest: list[dict[str, str]] = []
    for ref in refs:
        path = _confined_evidence_file(root, evidence_paths[ref])
        manifest.append({
            "ref": ref,
            "path": evidence_paths[ref],
            "sha256": sha256_bytes(path.read_bytes()),
        })

    statement = {
        "statement_version": "1.0",
        "envelope_sha256": sha256_bytes(canonical_json_bytes(envelope)),
        "evidence": manifest,
    }
    with tempfile.TemporaryDirectory(prefix="artifact-signing-") as temp_dir:
        statement_path = Path(temp_dir) / "statement.json"
        signature_path = Path(temp_dir) / "statement.sig"
        statement_path.write_bytes(canonical_json_bytes(statement))
        try:
            subprocess.run(
                [
                    "openssl", "pkeyutl", "-sign", "-inkey", str(private_key),
                    "-rawin", "-in", str(statement_path), "-out", str(signature_path),
                ],
                check=True, capture_output=True, timeout=15,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise IntegrityVerificationError("openssl_signing_unavailable_or_failed") from exc
        signature = base64.b64encode(signature_path.read_bytes()).decode("ascii")

    return {
        "bundle_version": "1.0",
        "algorithm": "Ed25519",
        "key_id": key_id,
        "statement": statement,
        "signature": signature,
    }
