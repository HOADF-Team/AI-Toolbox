from __future__ import annotations

import copy
import unittest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from trust_registry_history import (  # noqa: E402
    GENESIS_HASH,
    RegistryHistoryError,
    build_history_checkpoint,
    build_history_record,
    registry_snapshot_sha256,
    verify_registry_history,
)


class TrustRegistryHistoryTests(unittest.TestCase):
    def event(self, event_id, action, key_id="signing-key-2026", **extra):
        return {
            "event_id": event_id,
            "action": action,
            "key_id": key_id,
            "effective_at": "2026-06-01T12:00:00Z",
            "registry_sha256": "a" * 64,
            **extra,
        }

    def chain(self):
        first = build_history_record(self.event("evt-1", "key_added"), 1)
        second = build_history_record(
            self.event("evt-2", "key_retired"), 2, first["event_sha256"]
        )
        records = [first, second]
        return records, build_history_checkpoint(records)

    def test_valid_add_and_retirement_chain_passes_checkpoint(self) -> None:
        records, checkpoint = self.chain()
        report = verify_registry_history(records, checkpoint)
        self.assertEqual(report["status"], "verified")
        self.assertEqual(report["event_count"], 2)
        self.assertEqual(report["key_lifecycle"]["signing-key-2026"], "retired")

    def test_modified_event_is_detected(self) -> None:
        records, checkpoint = self.chain()
        changed = copy.deepcopy(records)
        changed[1]["event"]["effective_at"] = "2026-06-02T12:00:00Z"
        with self.assertRaisesRegex(RegistryHistoryError, "history_event_hash_mismatch"):
            verify_registry_history(changed, checkpoint)

    def test_reordered_events_are_rejected(self) -> None:
        records, checkpoint = self.chain()
        with self.assertRaisesRegex(RegistryHistoryError, "history_sequence_mismatch"):
            verify_registry_history(list(reversed(records)), checkpoint)

    def test_truncated_history_is_detected_by_external_checkpoint(self) -> None:
        records, checkpoint = self.chain()
        with self.assertRaisesRegex(
            RegistryHistoryError, "history_event_count_checkpoint_mismatch"
        ):
            verify_registry_history(records[:1], checkpoint)

    def test_changed_checkpoint_head_is_rejected(self) -> None:
        records, checkpoint = self.chain()
        bad = {**checkpoint, "head_sha256": "0" * 64}
        with self.assertRaisesRegex(
            RegistryHistoryError, "history_head_checkpoint_mismatch"
        ):
            verify_registry_history(records, bad)

    def test_wrong_previous_hash_is_rejected(self) -> None:
        first = build_history_record(self.event("evt-1", "key_added"), 1)
        second = build_history_record(
            self.event("evt-2", "key_retired"), 2, "f" * 64
        )
        records = [first, second]
        with self.assertRaisesRegex(
            RegistryHistoryError, "history_previous_hash_mismatch"
        ):
            verify_registry_history(records, build_history_checkpoint(records))

    def test_retirement_requires_prior_key_registration(self) -> None:
        record = build_history_record(self.event("evt-1", "key_retired"), 1)
        records = [record]
        with self.assertRaisesRegex(
            RegistryHistoryError, "key_retired_without_active_key"
        ):
            verify_registry_history(records, build_history_checkpoint(records))

    def test_revocation_after_retirement_is_terminal(self) -> None:
        first = build_history_record(self.event("evt-1", "key_added"), 1)
        second = build_history_record(
            self.event("evt-2", "key_retired"), 2, first["event_sha256"]
        )
        third = build_history_record(
            self.event("evt-3", "key_revoked", reason="suspected compromise"),
            3,
            second["event_sha256"],
        )
        report = verify_registry_history(
            [first, second, third],
            build_history_checkpoint([first, second, third]),
        )
        self.assertEqual(report["key_lifecycle"]["signing-key-2026"], "revoked")

    def test_duplicate_event_id_is_rejected(self) -> None:
        first = build_history_record(self.event("same-id", "key_added"), 1)
        second = build_history_record(
            self.event("same-id", "key_retired"), 2, first["event_sha256"]
        )
        records = [first, second]
        with self.assertRaisesRegex(RegistryHistoryError, "duplicate_history_event_id"):
            verify_registry_history(records, build_history_checkpoint(records))

    def test_rotation_event_requires_replacement_and_reason(self) -> None:
        event = self.event("evt-rotation", "key_rotated", replacement_key_id="next-key", reason="planned rotation")
        record = build_history_record(event, 1)
        with self.assertRaisesRegex(
            RegistryHistoryError, "key_rotated_without_active_key"
        ):
            verify_registry_history([record], build_history_checkpoint([record]))

    def test_first_record_requires_genesis_hash(self) -> None:
        with self.assertRaisesRegex(
            RegistryHistoryError, "first_event_must_use_genesis_hash"
        ):
            build_history_record(self.event("evt-1", "key_added"), 1, "1" * 64)

    def test_empty_history_uses_genesis_checkpoint(self) -> None:
        checkpoint = build_history_checkpoint([])
        self.assertEqual(checkpoint["head_sha256"], GENESIS_HASH)
        report = verify_registry_history([], checkpoint)
        self.assertEqual(report["status"], "verified")


    def test_registry_snapshot_digest_is_canonical(self) -> None:
        first = {"registry_version": "1.0", "keys": []}
        second = {"keys": [], "registry_version": "1.0"}
        self.assertEqual(registry_snapshot_sha256(first), registry_snapshot_sha256(second))


    def test_rotation_atomically_retires_old_key_and_activates_replacement(self) -> None:
        first = build_history_record(
            self.event("old-key-added", "key_added", key_id="old-key"), 1
        )
        rotation = build_history_record(
            self.event(
                "old-key-rotated",
                "key_rotated",
                key_id="old-key",
                replacement_key_id="new-key",
                reason="planned key rotation",
            ),
            2,
            first["event_sha256"],
        )
        records = [first, rotation]
        report = verify_registry_history(records, build_history_checkpoint(records))
        self.assertEqual(report["key_lifecycle"]["old-key"], "retired")
        self.assertEqual(report["key_lifecycle"]["new-key"], "active")

    def test_replacement_key_cannot_be_activated_twice(self) -> None:
        first = build_history_record(
            self.event("old-key-added", "key_added", key_id="old-key"), 1
        )
        rotation = build_history_record(
            self.event(
                "old-key-rotated",
                "key_rotated",
                key_id="old-key",
                replacement_key_id="new-key",
                reason="planned key rotation",
            ),
            2,
            first["event_sha256"],
        )
        duplicate = build_history_record(
            self.event("new-key-added-again", "key_added", key_id="new-key"),
            3,
            rotation["event_sha256"],
        )
        records = [first, rotation, duplicate]
        with self.assertRaisesRegex(
            RegistryHistoryError, "key_added_after_existing_lifecycle"
        ):
            verify_registry_history(records, build_history_checkpoint(records))


if __name__ == "__main__":
    unittest.main()
