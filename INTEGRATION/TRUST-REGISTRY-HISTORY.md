# Trust registry lifecycle history

`scripts/trust_registry_history.py` provides deterministic, tamper-evident records for key lifecycle events. It is designed to accompany the host-managed registry in `scripts/trust_registry.py`.

## Event format

Each event records:
- unique `event_id`;
- `action`: `key_added`, `key_retired`, `key_revoked`, or `key_rotated`;
- `key_id`;
- timezone-aware `effective_at`;
- `registry_sha256`: canonical SHA-256 digest of the registry snapshot associated with the event;
- optional `reason` and `replacement_key_id` where applicable.

The helper builds a sequential hash chain. Each record contains its sequence number, previous event digest, event object, and digest of the canonical record body. It checks lifecycle order: a key must be added before retirement or revocation; a retired key may later be revoked; revoked is terminal. A `key_rotated` event is an atomic transition: the named old key becomes `retired`, and the previously unknown `replacement_key_id` becomes `active`. The registry snapshot for that event must contain both entries in those resulting states. The replacement cannot be registered a second time.

## Host-side flow

1. Read the current registry snapshot and compute its canonical digest with `registry_snapshot_sha256(registry)`.
2. Construct a lifecycle event and append a record using `build_history_record(event, sequence, previous_event_sha256)`.
3. Store the history in append-only or versioned storage controlled by the host.
4. After validating the chain, create a checkpoint with `build_history_checkpoint(records)`.
5. Store the checkpoint independently from the editable history log, such as in a separately access-controlled audit store or an authenticated release record.
6. When reading the history, call `verify_registry_history(records, checkpoint)` before relying on its contents.

Example:

```python
from trust_registry_history import (
    build_history_checkpoint,
    build_history_record,
    registry_snapshot_sha256,
    verify_registry_history,
)

event = {
    "event_id": "audit-event-2026-001",
    "action": "key_retired",
    "key_id": "runtime-signing-2026-01",
    "effective_at": "2026-11-01T00:00:00Z",
    "registry_sha256": registry_snapshot_sha256(registry_snapshot),
}
record = build_history_record(event, sequence=next_sequence, previous_event_sha256=previous_hash)
records.append(record)
checkpoint = build_history_checkpoint(records)
report = verify_registry_history(records, checkpoint)
```

The example shows the data contract only; this repository does not provision storage, permissions, immutable retention, or an external checkpoint service. For rotation, create one `key_rotated` event whose `registry_sha256` points to a snapshot containing the old key as `retired` (with matching `retired_at`) and the replacement key as `active`.

## Security boundary

A hash chain detects record edits, reordering, and truncation **relative to a separately retained checkpoint**. If an attacker can replace both the history and its checkpoint, the attacker can rewrite the complete history. Therefore the checkpoint must be stored and authenticated independently. The helper does not sign checkpoints, enforce append-only filesystem semantics, authenticate the registry file, or provide WORM storage.

The `registry_sha256` binds each event to a canonical registry snapshot digest, but the host must retain and authenticate the corresponding snapshot if it needs to reconstruct the exact historical registry state. A hash chain is not proof that the recorded event was authorized or that the underlying key was safely handled.

Revoked keys remain rejected by archival verification even if a historical event appears before the revocation event. The history is an audit aid, not a way to override current revocation policy.

Run:

```bash
python -m unittest TESTS.test_trust_registry_history -v
```


## Enforcing history during archival verification

The audit-only `verify_archived_bundle(..., require_history=True)` option requires both the complete event records and a separately authenticated checkpoint. It checks that the chain's lifecycle state agrees with the current host registry, that a retired key has exactly one retirement or rotation event matching `retired_at`, and that no revocation event exists for the key. A missing, truncated, altered, or contradictory history blocks archival verification.

This is still not an authorization path for live workflow stages. The host must authenticate the checkpoint and retain the relevant registry snapshots; a valid hash chain alone does not establish that the lifecycle action was authorized.


Strict archival verification also requires the retained registry snapshots referenced by the key-add and key-retirement/rotation events. Pass them as a mapping from each canonical `registry_sha256` to the corresponding parsed registry snapshot using `registry_snapshots=...`. The verifier recalculates each snapshot digest, checks that the key's public-key fingerprint is unchanged, and confirms the snapshot status and `retired_at` agree with the lifecycle event. Missing or altered snapshots block strict archival verification.
