"""Validation for versioned artifact provenance envelopes.

This validates envelope structure and references only; it does not authenticate
the producer, verify source checkouts, inspect payload semantics, or prove evidence.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_TOKEN = re.compile(r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$")
_PRODUCER_KINDS = {"skill", "runtime", "tool", "human", "system"}
_VERIFICATION_STATES = {"unverified", "structurally_validated", "independently_verified"}


def _is_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def validate_provenance_envelope(envelope: Any) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(envelope, dict):
        return {"status": "failed", "errors": ["envelope_must_be_object"]}
    if envelope.get("envelope_version") != "1.0":
        errors.append("unsupported_envelope_version")

    for field in ("artifact_id", "artifact_type"):
        value = envelope.get(field)
        if not isinstance(value, str) or not _TOKEN.fullmatch(value):
            errors.append(f"invalid_{field}")

    producer = envelope.get("producer")
    if not isinstance(producer, dict):
        errors.append("producer_must_be_object")
    else:
        if producer.get("kind") not in _PRODUCER_KINDS:
            errors.append("invalid_producer_kind")
        for field in ("id", "version"):
            if not isinstance(producer.get(field), str) or not producer[field].strip():
                errors.append(f"producer_{field}_required")
        if not isinstance(producer.get("revision"), str) or not _SHA40.fullmatch(producer["revision"]):
            errors.append("producer_revision_must_be_full_git_sha")

    source = envelope.get("source")
    if not isinstance(source, dict):
        errors.append("source_must_be_object")
    else:
        if not isinstance(source.get("repository"), str) or not source["repository"].strip():
            errors.append("source_repository_required")
        if not isinstance(source.get("revision"), str) or not _SHA40.fullmatch(source["revision"]):
            errors.append("source_revision_must_be_full_git_sha")

    if not _is_timestamp(envelope.get("created_at")):
        errors.append("created_at_must_be_iso8601_timestamp")

    inputs = envelope.get("inputs")
    if not isinstance(inputs, list):
        errors.append("inputs_must_be_array")
    else:
        seen: set[str] = set()
        for index, item in enumerate(inputs):
            if not isinstance(item, dict):
                errors.append(f"inputs_{index}_must_be_object")
                continue
            ref = item.get("ref")
            if not isinstance(ref, str) or not ref.strip():
                errors.append(f"inputs_{index}_ref_required")
            elif ref in seen:
                errors.append(f"inputs_{index}_duplicate_ref")
            else:
                seen.add(ref)
            if not isinstance(item.get("artifact_type"), str) or not _TOKEN.fullmatch(item["artifact_type"]):
                errors.append(f"inputs_{index}_invalid_artifact_type")

    payload = envelope.get("payload")
    if not isinstance(payload, dict):
        errors.append("payload_must_be_object")

    evidence = envelope.get("evidence")
    if not isinstance(evidence, list) or any(not isinstance(item, str) or not item.strip() for item in evidence):
        errors.append("evidence_must_be_array_of_nonempty_refs")

    verification = envelope.get("verification")
    if not isinstance(verification, dict):
        errors.append("verification_must_be_object")
    else:
        state = verification.get("status")
        if state not in _VERIFICATION_STATES:
            errors.append("invalid_verification_status")
        if not isinstance(verification.get("method"), str) or not verification["method"].strip():
            errors.append("verification_method_required")
        if not _is_timestamp(verification.get("checked_at")):
            errors.append("verification_checked_at_must_be_iso8601_timestamp")
        limitations = verification.get("limitations")
        if not isinstance(limitations, list) or any(not isinstance(x, str) or not x.strip() for x in limitations):
            errors.append("verification_limitations_must_be_array_of_strings")
        if state == "independently_verified":
            if not evidence:
                errors.append("independent_verification_requires_evidence_refs")
            if not isinstance(verification.get("verifier"), str) or not verification["verifier"].strip():
                errors.append("independent_verification_requires_verifier")

    digest = envelope.get("payload_sha256")
    if digest is not None and (not isinstance(digest, str) or not _SHA256.fullmatch(digest)):
        errors.append("payload_sha256_must_be_64_lowercase_hex")

    return {
        "envelope_version": "1.0",
        "artifact_id": envelope.get("artifact_id"),
        "status": "passed" if not errors else "failed",
        "errors": errors,
        "limitations": [
            "Structural validation does not authenticate producer identity or prove Git revisions exist.",
            "Input and evidence references are caller-supplied and are not fetched or verified.",
            "Payload semantics, completeness, truthfulness, and secret safety are not established.",
            "A structurally_validated status is not independent verification."
        ]
    }
