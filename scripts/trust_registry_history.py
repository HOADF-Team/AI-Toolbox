"""Tamper-evident hash-chain records for host-managed signing-key lifecycle events.

The chain detects edits relative to an independently retained checkpoint. It is not
immutable storage and cannot authenticate a checkpoint kept beside the editable log.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from artifact_integrity import canonical_json_bytes, sha256_bytes

GENESIS_HASH = "0" * 64
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ACTIONS = {"key_added", "key_retired", "key_revoked", "key_rotated"}


class RegistryHistoryError(ValueError):
    """Raised when a registry lifecycle history fails validation."""


def _validate_event(event: Any) -> None:
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
        event = record.get("event")
        _validate_event(event)
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
