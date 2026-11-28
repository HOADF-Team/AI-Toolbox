"""Tamper-evident hash-chain records for host-managed signing-key lifecycle events.

The chain detects edits relative to an independently retained checkpoint. It is not
immutable storage and cannot authenticate a checkpoint kept beside the editable log.
"""
from __future__ import annotations

import base64
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from artifact_integrity import canonical_json_bytes, sha256_bytes

GENESIS_HASH = "0" * 64
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ACTIONS = {"key_added", "key_retired", "key_revoked", "key_rotated"}


class RegistryHistoryError(ValueError):
    """Raised when a registry lifecycle history fails validation."""


def _validate_event(event: Any) -> dict[str, Any]:
    if not isinstance(event, dict):
        raise RegistryHistoryError("history_event_must_be_object")
    required = {"event_id", "action", "key_id", "effective_at", "registry_sha256"}
    allowed = required | {"reason", "replacement_key_id"}
    if not required.issubset(event) or not set(event).issubset(allowed):
        raise RegistryHistoryError("invalid_history_event_fields")
    for field in ("event_id", "key_id"):
        if not isinstance(event.get(field), str) or not event[field].strip():
            raise RegistryHistoryError(f"invalid_{field}")
    if event.get("action") not in _ACTIONS:
        raise RegistryHistoryError("invalid_history_action")
    timestamp = event.get("effective_at")
    if not isinstance(timestamp, str) or not timestamp:
        raise RegistryHistoryError("invalid_effective_at")
    try:
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RegistryHistoryError("invalid_effective_at") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise RegistryHistoryError("effective_at_must_include_timezone")
    if not isinstance(event.get("registry_sha256"), str) or not _SHA256.fullmatch(
        event["registry_sha256"]
    ):
        raise RegistryHistoryError("invalid_registry_snapshot_sha256")
    if event["action"] in {"key_revoked", "key_rotated"}:
        reason = event.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            raise RegistryHistoryError("history_event_reason_required")
    if event["action"] == "key_rotated":
        replacement = event.get("replacement_key_id")
        if not isinstance(replacement, str) or not replacement.strip():
            raise RegistryHistoryError("replacement_key_id_required")
        if replacement == event["key_id"]:
            raise RegistryHistoryError("replacement_key_id_must_differ")
    return event


def registry_snapshot_sha256(registry: dict[str, Any]) -> str:
    """Digest a registry snapshot using the shared canonical JSON encoding."""
    if not isinstance(registry, dict):
        raise RegistryHistoryError("registry_snapshot_must_be_object")
    return sha256_bytes(canonical_json_bytes(registry))


def build_history_record(
    event: dict[str, Any],
    sequence: int,
    previous_event_sha256: str | None = None,
) -> dict[str, Any]:
    """Build one deterministic record; storage/append-only enforcement is host-owned."""
    _validate_event(event)
    if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 1:
        raise RegistryHistoryError("invalid_history_sequence")
    previous = previous_event_sha256 or GENESIS_HASH
    if not isinstance(previous, str) or not _SHA256.fullmatch(previous):
        raise RegistryHistoryError("invalid_previous_event_sha256")
    if sequence == 1 and previous != GENESIS_HASH:
        raise RegistryHistoryError("first_event_must_use_genesis_hash")
    body = {
        "sequence": sequence,
        "previous_event_sha256": previous,
        "event": event,
    }
    return {**body, "event_sha256": sha256_bytes(canonical_json_bytes(body))}


def build_history_checkpoint(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Return a checkpoint digest for storage outside the editable history log."""
    if not isinstance(records, list):
        raise RegistryHistoryError("history_records_must_be_array")
    if records:
        last = records[-1]
        if not isinstance(last, dict) or not isinstance(last.get("event_sha256"), str):
            raise RegistryHistoryError("invalid_history_head_record")
        head = last["event_sha256"]
    else:
        head = GENESIS_HASH
    return {"event_count": len(records), "head_sha256": head}



def build_history_anchor_statement(
    log_id: str,
    checkpoint: dict[str, Any],
    anchored_at: str,
    anchor_key_id: str,
) -> dict[str, Any]:
    """Build the exact statement an independent anchor signer must sign."""
    if not isinstance(log_id, str) or not log_id.strip():
        raise RegistryHistoryError("history_anchor_log_id_required")
    if not isinstance(anchor_key_id, str) or not anchor_key_id.strip():
        raise RegistryHistoryError("history_anchor_key_id_required")
    if not isinstance(checkpoint, dict) or set(checkpoint) != {"event_count", "head_sha256"}:
        raise RegistryHistoryError("invalid_history_anchor_checkpoint")
    count = checkpoint.get("event_count")
    head = checkpoint.get("head_sha256")
    if not isinstance(count, int) or isinstance(count, bool) or count < 0:
        raise RegistryHistoryError("invalid_history_anchor_event_count")
    if not isinstance(head, str) or not _SHA256.fullmatch(head):
        raise RegistryHistoryError("invalid_history_anchor_head_sha256")
    if not isinstance(anchored_at, str) or not anchored_at.strip():
        raise RegistryHistoryError("history_anchor_timestamp_required")
    try:
        parsed = datetime.fromisoformat(anchored_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RegistryHistoryError("invalid_history_anchor_timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise RegistryHistoryError("history_anchor_timestamp_must_include_timezone")
    return {
        "anchor_version": "1.0",
        "log_id": log_id,
        "anchor_key_id": anchor_key_id,
        "anchored_at": anchored_at,
        "checkpoint": {"event_count": count, "head_sha256": head},
    }


def verify_rfc3161_timestamp(
    data: bytes,
    timestamp_response: Path,
    trusted_ca_file: Path,
    untrusted_chain_file: Path | None = None,
) -> dict[str, str]:
    """Verify an RFC 3161 token and validate its TSA chain at authenticated genTime.

    genTime is parsed before certificate validation only to select OpenSSL's
    historical verification instant. The timestamp token signature and imprint
    are then verified by OpenSSL at that instant, binding genTime to the TSA key.
    Trust roots are supplied by the verifier host; untrusted certificates can
    complete a chain but can never become trust anchors.
    """
    if not isinstance(data, bytes) or not data:
        raise RegistryHistoryError("timestamped_data_must_be_nonempty_bytes")
    for path, error_code in (
        (timestamp_response, "timestamp_response_unavailable"),
        (trusted_ca_file, "timestamp_trust_bundle_unavailable"),
    ):
        if not isinstance(path, Path) or path.is_symlink() or not path.is_file():
            raise RegistryHistoryError(error_code)
    if untrusted_chain_file is not None and (
        not isinstance(untrusted_chain_file, Path)
        or untrusted_chain_file.is_symlink()
        or not untrusted_chain_file.is_file()
    ):
        raise RegistryHistoryError("timestamp_untrusted_chain_unavailable")

    with tempfile.TemporaryDirectory(prefix="rfc3161-verify-") as temp_dir:
        data_path = Path(temp_dir) / "timestamped-data.bin"
        data_path.write_bytes(data)
        try:
            details = subprocess.run(
                ["openssl", "ts", "-reply", "-in", str(timestamp_response), "-text"],
                check=False, capture_output=True, text=True, timeout=20,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RegistryHistoryError("rfc3161_response_parser_unavailable") from exc
        if details.returncode != 0:
            raise RegistryHistoryError("rfc3161_response_parse_failed")

        generation_time: datetime | None = None
        for line in details.stdout.splitlines():
            stripped = line.strip()
            if stripped.lower().startswith("time stamp:"):
                value = stripped.split(":", 1)[1].strip()
                try:
                    from email.utils import parsedate_to_datetime
                    generation_time = parsedate_to_datetime(value)
                except (TypeError, ValueError, OverflowError) as exc:
                    raise RegistryHistoryError("rfc3161_generation_time_invalid") from exc
                break
        if generation_time is None or generation_time.tzinfo is None:
            raise RegistryHistoryError("rfc3161_generation_time_missing")
        generation_time = generation_time.astimezone(timezone.utc)
        # OpenSSL -attime takes Unix seconds. This preliminary value is not
        # trusted until the subsequent signature/imprint verification succeeds.
        attime = str(int(generation_time.timestamp()))
        command = [
            "openssl", "ts", "-verify", "-in", str(timestamp_response),
            "-data", str(data_path), "-CAfile", str(trusted_ca_file),
            "-attime", attime,
        ]
        if untrusted_chain_file is not None:
            command.extend(["-untrusted", str(untrusted_chain_file)])
        try:
            verified = subprocess.run(
                command, check=False, capture_output=True, text=True, timeout=20,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RegistryHistoryError("rfc3161_verifier_unavailable") from exc
        if verified.returncode != 0:
            raise RegistryHistoryError("rfc3161_signature_or_trust_verification_failed")

    return {
        "status": "verified",
        "gen_time": generation_time.isoformat(),
        "verification": "openssl_ts_verify_with_host_supplied_ca_at_authenticated_gen_time",
    }

def verify_history_anchor(
    records: list[dict[str, Any]],
    anchor: dict[str, Any],
    trusted_public_key: Path,
    trusted_anchor_key_id: str,
    timestamp_response: Path | None = None,
    timestamp_ca_file: Path | None = None,
    timestamp_untrusted_chain_file: Path | None = None,
) -> dict[str, Any]:
    """Verify a signed history checkpoint and, optionally, its RFC 3161 timestamp."""
    if not isinstance(anchor, dict) or set(anchor) != {
        "anchor_version", "log_id", "anchor_key_id", "anchored_at", "checkpoint", "signature"
    }:
        raise RegistryHistoryError("invalid_history_anchor_fields")
    if anchor.get("anchor_version") != "1.0":
        raise RegistryHistoryError("unsupported_history_anchor_version")
    if not isinstance(trusted_anchor_key_id, str) or not trusted_anchor_key_id:
        raise RegistryHistoryError("trusted_history_anchor_key_id_required")
    if anchor.get("anchor_key_id") != trusted_anchor_key_id:
        raise RegistryHistoryError("untrusted_history_anchor_key_id")
    log_id = anchor.get("log_id")
    checkpoint = anchor.get("checkpoint")
    anchored_at = anchor.get("anchored_at")
    anchor_key_id = anchor.get("anchor_key_id")
    if not isinstance(log_id, str) or not isinstance(checkpoint, dict) or not isinstance(anchored_at, str) or not isinstance(anchor_key_id, str):
        raise RegistryHistoryError("invalid_history_anchor_statement_fields")
    statement = build_history_anchor_statement(
        log_id, checkpoint, anchored_at, anchor_key_id
    )
    signature_text = anchor.get("signature")
    if not isinstance(signature_text, str) or not signature_text:
        raise RegistryHistoryError("history_anchor_signature_required")
    try:
        signature = base64.b64decode(signature_text, validate=True)
    except ValueError as exc:
        raise RegistryHistoryError("history_anchor_signature_invalid_base64") from exc
    if not isinstance(trusted_public_key, Path) or trusted_public_key.is_symlink() or not trusted_public_key.is_file():
        raise RegistryHistoryError("trusted_history_anchor_public_key_unavailable")
    with tempfile.TemporaryDirectory(prefix="history-anchor-") as temp_dir:
        statement_path = Path(temp_dir) / "anchor.json"
        signature_path = Path(temp_dir) / "anchor.sig"
        statement_bytes = canonical_json_bytes(statement)
        statement_path.write_bytes(statement_bytes)
        signature_path.write_bytes(signature)
        try:
            completed = subprocess.run(
                ["openssl", "pkeyutl", "-verify", "-pubin", "-inkey",
                 str(trusted_public_key), "-rawin", "-in", str(statement_path),
                 "-sigfile", str(signature_path)],
                check=False, capture_output=True, text=True, timeout=15,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RegistryHistoryError("history_anchor_verifier_unavailable") from exc
        if completed.returncode != 0:
            raise RegistryHistoryError("history_anchor_signature_verification_failed")

    if (timestamp_response is None) != (timestamp_ca_file is None):
        raise RegistryHistoryError("timestamp_response_and_ca_must_be_supplied_together")
    timestamp_report: dict[str, str] | None = None
    if timestamp_response is not None and timestamp_ca_file is not None:
        # Timestamp the Ed25519 signature itself, not only its public statement.
        # This proves that this exact signature value existed by the TSA genTime.
        timestamp_report = verify_rfc3161_timestamp(
            signature, timestamp_response, timestamp_ca_file,
            timestamp_untrusted_chain_file,
        )
    history_report = verify_registry_history(records, statement["checkpoint"])
    return {
        "status": "signed_checkpoint_verified",
        "log_id": statement["log_id"],
        "anchor_key_id": trusted_anchor_key_id,
        "anchored_at": statement["anchored_at"],
        "timestamp": timestamp_report,
        "checkpoint": statement["checkpoint"],
        "history": history_report,
        "limitations": [
            "The anchor signature authenticates the checkpoint statement and proves key possession.",
            "Only a verified RFC 3161 response supplies an independently trusted generation time.",
            "The host must retain the timestamp response and trust bundle independently.",
            "A valid signature and timestamp do not prove that the underlying lifecycle events are truthful.",
        ],
    }


def verify_registry_history(
    records: list[dict[str, Any]],
    checkpoint: dict[str, Any],
) -> dict[str, Any]:
    """Verify event ordering, lifecycle transitions, hash links, and external checkpoint."""
    if not isinstance(records, list) or not isinstance(checkpoint, dict):
        raise RegistryHistoryError("history_and_checkpoint_must_be_objects")
    if set(checkpoint) != {"event_count", "head_sha256"}:
        raise RegistryHistoryError("invalid_history_checkpoint_fields")
    expected_count = checkpoint.get("event_count")
    expected_head = checkpoint.get("head_sha256")
    if not isinstance(expected_count, int) or isinstance(expected_count, bool) or expected_count < 0:
        raise RegistryHistoryError("invalid_checkpoint_event_count")
    if not isinstance(expected_head, str) or not _SHA256.fullmatch(expected_head):
        raise RegistryHistoryError("invalid_checkpoint_head_sha256")
    if len(records) != expected_count:
        raise RegistryHistoryError("history_event_count_checkpoint_mismatch")

    previous = GENESIS_HASH
    event_ids: set[str] = set()
    lifecycle: dict[str, str] = {}
    events: list[dict[str, Any]] = []
    for index, record in enumerate(records, start=1):
        if not isinstance(record, dict) or set(record) != {
            "sequence", "previous_event_sha256", "event", "event_sha256"
        }:
            raise RegistryHistoryError("invalid_history_record_fields")
        if record.get("sequence") != index:
            raise RegistryHistoryError("history_sequence_mismatch")
        if record.get("previous_event_sha256") != previous:
            raise RegistryHistoryError("history_previous_hash_mismatch")
        event = _validate_event(record.get("event"))
        event_id = event["event_id"]
        if event_id in event_ids:
            raise RegistryHistoryError("duplicate_history_event_id")
        event_ids.add(event_id)
        key_id = event["key_id"]
        action = event["action"]
        state = lifecycle.get(key_id)
        if action == "key_added":
            if state is not None:
                raise RegistryHistoryError("key_added_after_existing_lifecycle")
            lifecycle[key_id] = "active"
        elif action == "key_retired":
            if state != "active":
                raise RegistryHistoryError("key_retired_without_active_key")
            lifecycle[key_id] = "retired"
        elif action == "key_revoked":
            if state not in {"active", "retired"}:
                raise RegistryHistoryError("key_revoked_without_registered_key")
            lifecycle[key_id] = "revoked"
        elif action == "key_rotated":
            if state != "active":
                raise RegistryHistoryError("key_rotated_without_active_key")
            replacement = event["replacement_key_id"]
            if lifecycle.get(replacement) is not None:
                raise RegistryHistoryError("replacement_key_already_registered")
            lifecycle[key_id] = "retired"
            lifecycle[replacement] = "active"
        body = {
            "sequence": index,
            "previous_event_sha256": previous,
            "event": event,
        }
        actual_hash = sha256_bytes(canonical_json_bytes(body))
        if record.get("event_sha256") != actual_hash:
            raise RegistryHistoryError("history_event_hash_mismatch")
        previous = actual_hash
        events.append(event)

    if previous != expected_head:
        raise RegistryHistoryError("history_head_checkpoint_mismatch")
    return {
        "status": "verified",
        "event_count": len(records),
        "head_sha256": previous,
        "events": events,
        "key_lifecycle": lifecycle,
        "limitations": [
            "The history is tamper-evident only relative to an independently authenticated checkpoint.",
            "The helper does not enforce append-only storage or authenticate the registry snapshot.",
            "The host must retain checkpoints and history through a separate trusted channel.",
        ],
    }
