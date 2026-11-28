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


## Signed external checkpoint anchors

The module also provides `build_history_anchor_statement(...)` and `verify_history_anchor(...)`. An independent audit authority can sign the checkpoint statement with an Ed25519 key and retain the signed anchor outside the editable registry/history store.

The signed statement binds:
- a stable `log_id`;
- `anchor_key_id`, selected by host policy;
- timezone-aware `anchored_at`;
- the exact `event_count` and `head_sha256` checkpoint.

The verifier receives the trusted anchor public-key path and expected key ID from host policy. It verifies the signature first, then validates the complete hash chain against the signed checkpoint. Editing the checkpoint, changing the history, using another anchor key ID, or truncating the chain is rejected.

Example anchor payload creation:

```python
statement = build_history_anchor_statement(
    log_id="security-key-lifecycle",
    checkpoint=build_history_checkpoint(records),
    anchored_at="2026-11-28T12:00:00Z",
    anchor_key_id="external-audit-anchor-2026",
)
```

The independent authority signs the canonical JSON bytes of this statement using its protected Ed25519 private key. Store the resulting signature alongside the statement, but retain both the signed anchor and trusted public key through a separately authenticated channel. The library does not hold the private key or publish the anchor.

**Time limitation:** `anchored_at` is the signing authority's assertion. This mechanism authenticates who signed the checkpoint, not an independent time source. Strong proof of time requires an RFC 3161 timestamp token or another independently trusted timestamp service, verified against separately provisioned trust roots. Do not treat the host's local clock or a self-reported timestamp as trusted time.


## RFC 3161 trusted timestamp verification

`verify_rfc3161_timestamp(data, timestamp_response, trusted_ca_file, untrusted_chain_file=None)` verifies an RFC 3161 timestamp response with OpenSSL's timestamp verifier. The verifier checks the message imprint against the exact supplied bytes, validates the TSA certificate chain against the host-supplied CA trust bundle, and extracts the TSA-authenticated `genTime`.

For lifecycle history anchors, pass the exact canonical statement bytes (the same bytes signed by the external anchor authority) to the timestamp authority. Then verify both the Ed25519 anchor signature and the timestamp response:

```python
report = verify_history_anchor(
    records,
    anchor,
    trusted_public_key=Path("anchor-public.pem"),
    trusted_anchor_key_id="external-audit-anchor-2026",
    timestamp_response=Path("anchor.tsr"),
    timestamp_ca_file=Path("tsa-trust-roots.pem"),
    timestamp_untrusted_chain_file=Path("tsa-intermediates.pem"),
)
```

The timestamp response and CA bundle must be supplied together. The optional untrusted chain file may provide intermediates, but it is not trusted as a root. The host must provision the trust bundle independently, retain the response outside the editable history store, and define its TSA trust and certificate-rotation policy. OpenSSL validates the timestamp token's signature, message imprint, TSA certificate purpose, and chain against the supplied trust store.

The report distinguishes the auditor's `anchored_at` assertion from the verified TSA `timestamp.gen_time`. Without a valid RFC 3161 response, the result is only `signed_checkpoint_verified`; it is not a trusted-time result.

This helper does not request timestamps from a TSA, select a provider, manage trust roots, or guarantee that a TSA is honest or available. A valid timestamp proves that the exact statement bytes were presented to the trusted TSA no later than its asserted generation time; it does not prove that the underlying lifecycle event was true or authorized. The local tests mock the OpenSSL command boundary and validate fail-closed behavior; they are not an end-to-end test against a live TSA. A real TSA interoperability test remains a deployment gate.
