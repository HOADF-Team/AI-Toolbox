"""Cryptographic integrity checks for artifact provenance bundles.

Uses OpenSSL Ed25519 through fixed-argument subprocess calls; no shell is used.
Trust is anchored only by the public key and key ID supplied by host policy.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any


class IntegrityVerificationError(ValueError):
    """Raised when an artifact integrity bundle cannot be trusted."""


def canonical_json_bytes(value: Any) -> bytes:
    """Return the project's documented deterministic JSON encoding."""
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


def verify_integrity_bundle(
    envelope: dict[str, Any],
    bundle: dict[str, Any],
    trusted_public_key: Path,
    trusted_key_id: str,
    evidence_root: Path,
) -> dict[str, Any]:
    """Verify payload/evidence hashes and an Ed25519 signature from a trusted key."""
    if not isinstance(envelope, dict) or not isinstance(bundle, dict):
        raise IntegrityVerificationError("envelope_and_bundle_must_be_objects")
    if not trusted_key_id or bundle.get("key_id") != trusted_key_id:
        raise IntegrityVerificationError("untrusted_signing_key_id")
    if bundle.get("algorithm") != "Ed25519":
        raise IntegrityVerificationError("unsupported_signature_algorithm")
    statement = bundle.get("statement")
    if not isinstance(statement, dict) or statement.get("statement_version") != "1.0":
        raise IntegrityVerificationError("invalid_integrity_statement")

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
    if any(not isinstance(ref, str) for ref in refs):
        raise IntegrityVerificationError("envelope_evidence_refs_must_be_strings")
    if sorted(item.get("ref", "") for item in evidence if isinstance(item, dict)) != sorted(refs):
        raise IntegrityVerificationError("evidence_reference_set_mismatch")

    root = evidence_root.resolve(strict=True)
    verified_evidence: list[str] = []
    for item in evidence:
        if not isinstance(item, dict):
            raise IntegrityVerificationError("evidence_manifest_entry_must_be_object")
        path = _safe_evidence_file(root, item.get("path"))
        actual = sha256_bytes(path.read_bytes())
        if item.get("sha256") != actual:
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
        "limitations": [
            "The public key is trusted only because the host supplied it through policy.",
            "A valid signature proves integrity and key possession, not that evidence is truthful.",
            "The verifier does not establish real-world producer identity or the correctness of payload claims.",
        ],
    }
