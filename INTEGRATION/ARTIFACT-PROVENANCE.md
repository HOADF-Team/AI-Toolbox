# Artifact provenance envelope

The versioned envelope is the common wrapper for artifacts emitted by a future host AI runtime or its Skills. It preserves artifact identity, type, producer/Skill version, immutable source revision, creation time, input references, payload, evidence references, and verification state.

## Contract

The machine-readable field contract is [artifact-provenance.schema.json](../CATALOG/artifact-provenance.schema.json). The deterministic validator is `scripts/artifact_provenance.py`; regression tests are in `TESTS/test_artifact_provenance.py`.

Required fields:
- `envelope_version`: currently `1.0`.
- `artifact_id`, `artifact_type`: stable identifier and namespaced type.
- `producer`: producer kind, ID, version, and full 40-character Git revision.
- `source`: canonical repository and full 40-character source revision.
- `created_at`: ISO 8601 timestamp including timezone.
- `inputs`: typed references to inputs consumed.
- `payload`: artifact data object.
- `evidence`: references to evidence; references are not evidence validation.
- `verification`: status, method, timestamp, and explicit limitations.
- Optional `payload_sha256`: lowercase SHA-256 digest of canonical payload bytes.

Verification states are deliberately distinct:
- `unverified`: no validation claim.
- `structurally_validated`: envelope shape and field constraints passed.
- `independently_verified`: requires evidence references and a named verifier; the host must still establish that the verifier and evidence are trustworthy.

## Validate

```bash
python -m unittest TESTS.test_artifact_provenance -v
```

The validator is offline and deterministic. It does not fetch Git revisions or references, authenticate producer identity, execute Skills/LLMs, inspect payload semantics, verify evidence, calculate payload digests, or guarantee secret redaction. The host runtime must resolve revisions from trusted checkouts, bind references to actual artifacts, compute digests over a documented canonical serialization, and enforce secret-handling policy.


## Cryptographic integrity profile (Ed25519)

The optional verifier in `scripts/artifact_integrity.py` adds three checks:

1. SHA-256 of the complete provenance envelope using the documented canonical JSON encoding (`sort_keys`, compact separators, UTF-8, no NaN/Infinity).
2. SHA-256 of each evidence file, resolved only beneath an explicitly configured local evidence root. Absolute paths, parent traversal, symlinks, missing files, and non-files are rejected. The verifier also requires unique evidence references and exact manifest-entry fields (`ref`, `path`, `sha256`) with lowercase 64-character SHA-256 digests.
3. Ed25519 signature over a statement containing the envelope digest and the evidence reference/path/digest manifest. OpenSSL is invoked with fixed arguments and without a shell.

A bundle has this logical shape:

```json
{
  "bundle_version": "1.0",
  "algorithm": "Ed25519",
  "key_id": "approved-key-identifier",
  "statement": {
    "statement_version": "1.0",
    "envelope_sha256": "<64 lowercase hex characters>",
    "evidence": [
      {
        "ref": "evidence:scan",
        "path": "reports/scan.txt",
        "sha256": "<64 lowercase hex characters>"
      }
    ]
  },
  "signature": "<base64 Ed25519 signature of canonical statement JSON>"
}
```

The `key_id` and public key are trust anchors supplied by the host runtime, not by the artifact. Never trust a public key merely because it is embedded beside the signature. Keep private signing keys outside this repository and outside artifacts/logs. This repository does not generate or store a production signing key.

### Runtime enforcement

Pass an explicit host policy to `execute_with_adapter(..., integrity_policy=...)`:

- `trusted_public_key`: path to the host-managed trusted Ed25519 public key.
- `trusted_key_id`: exact key identifier approved by host policy.
- `evidence_root`: local directory containing the evidence files referenced by the signed bundle.

When this policy is supplied, a missing bundle, bad signature, changed envelope, mismatched evidence reference, or changed evidence file blocks that stage and stops the chain. Without a policy, legacy structural checks continue and the report explicitly does not claim cryptographic verification. The policy is deliberately opt-in until a host has provisioned and reviewed its trust anchor.

### Limits

A valid signature proves that the signed bytes have not changed since signing and that the signer possessed the corresponding private key. It does **not** prove who the signer is unless the host independently trusts the public key, and it does not prove that evidence is truthful, complete, relevant, or captured from a real system. Evidence files are local inputs supplied by the host; this verifier does not fetch URLs or access remote systems. No live VPS, production system, external service, or paid provider is contacted.

Run the tests with:

```bash
python -m unittest TESTS.test_artifact_integrity TESTS.test_artifact_provenance TESTS.test_handoff_runtime -v
```


## Host trust registry and key lifecycle

The optional host-managed registry resolver is implemented in `scripts/trust_registry.py`. A minimal example is [trust-registry.example.json](../SECURITY/trust-registry.example.json).

Each entry binds:
- a unique `key_id` and the `Ed25519` algorithm;
- a public-key file confined beneath a host-managed key directory;
- SHA-256 of the DER-encoded SubjectPublicKeyInfo public key;
- lifecycle status (`active`, `revoked`, or `retired`);
- timezone-aware `not_before` and `not_after` timestamps;
- explicit allowed producer IDs and artifact types.

The resolver rejects duplicate IDs, unknown IDs, inactive/revoked/retired keys, keys outside their validity window, scope mismatches, changed key bytes, symlinks, and paths outside the key directory. A revoked key is rejected immediately regardless of signature validity. A retired key is also rejected for new verification; if historical verification is required, it should use a separate archival policy and must not silently reuse the active-key path.

### Runtime configuration

For registry-based verification, the host passes this policy to `execute_with_adapter`:

```python
integrity_policy = {
    "trust_registry_path": "/host/policy/trust-registry.json",
    "key_root": "/host/policy/public-keys",
    "evidence_root": "/host/evidence",
}
```

The runtime selects the key by the bundle's `key_id`, then checks the producer ID and artifact type from the provenance envelope against the registry entry before verifying the signature. The older explicit single-key policy remains supported for controlled compatibility, but a registry is the recommended host integration.

### Rotation and revocation procedure

1. Generate a new Ed25519 key pair in the host's approved secret-management environment; never commit the private key.
2. Install the new public key in the host-managed key directory and calculate its DER public-key SHA-256 fingerprint.
3. Add a new registry entry with a unique key ID, narrow producer/artifact scopes, and a bounded validity period.
4. Deploy and verify the updated registry through the host's authenticated configuration channel.
5. Switch authorized signers to the new key and confirm verification with a test artifact.
6. Mark the old key `retired` after planned rotation, or `revoked` immediately after suspected compromise. Deploy the revocation update through the same trusted channel.
7. Preserve historical audit records separately; do not keep compromised keys active merely to validate old signatures.

The registry file itself is security-critical policy. A malicious party able to replace both the registry and its public keys can redefine trust. Therefore the host must authenticate registry distribution, protect write access, audit changes, and use an independently trusted configuration revision. The local resolver does not provide registry signing, remote distribution, private-key custody, HSM integration, automated rotation, or certificate transparency.

Tests use ephemeral local keys only. No production trust anchor is included in this repository.

Do not place credentials, private keys, tokens, customer data, or other secrets in an envelope, payload, logs, or evidence references. A passing structural check is not proof of correctness, provenance authenticity, or production safety.


### Signing helper

The host-side bundle creation helper is documented in [ARTIFACT-SIGNING.md](ARTIFACT-SIGNING.md). It checks that the supplied private key matches the registry-resolved public-key fingerprint before signing. It does not provide key custody or replay protection.


## Historical verification after planned key retirement

The separate audit-only path is implemented in `scripts/archival_verification.py`. It allows a key marked `retired` to verify an archived signature only when the signed timestamp falls within the key's original validity window and strictly before the registry's timezone-aware `retired_at` value.

Example registry entry fields for a retired key:

```json
{
  "key_id": "runtime-signing-2026-01",
  "algorithm": "Ed25519",
  "public_key_file": "runtime-signing-2026-01.pub",
  "public_key_sha256": "<SPKI SHA-256>",
  "status": "retired",
  "not_before": "2026-01-01T00:00:00Z",
  "not_after": "2027-01-01T00:00:00Z",
  "retired_at": "2026-11-01T00:00:00Z",
  "allowed_producers": ["crypto-security"],
  "allowed_artifact_types": ["security.review"]
}
```

The audit helper uses the signed execution-context `issued_at` timestamp for statement version 1.1, or the envelope's signed `created_at` field for legacy statement version 1.0. It then verifies the Ed25519 signature, envelope digest, and local evidence digests.

**Revoked keys are never accepted**, including for historical verification. This deliberately sacrifices some archival availability after suspected compromise rather than treating signatures from a compromised key as trustworthy. Planned retirement and compromise revocation are different lifecycle events.

Historical verification returns `archived_verified` and is not an authorization path for a live runtime handoff. Do not feed an archived verification result into a current workflow as if it were a newly verified stage result. The host must preserve authenticated registry history and public-key material; editing a local registry file is not itself a tamper-evident audit trail.

Tests:

```bash
python -m unittest TESTS.test_trust_registry TESTS.test_archival_verification -v
```


## Tamper-evident lifecycle history

The optional hash-chain helper in [TRUST-REGISTRY-HISTORY.md](TRUST-REGISTRY-HISTORY.md) records key addition, retirement, revocation, and atomic rotation events against canonical registry snapshot digests. A rotation event retires the old key and activates its replacement in one transition; the referenced registry snapshot must contain both resulting entries. It detects edits and truncation relative to an independently authenticated checkpoint. It does not create immutable storage or authenticate a checkpoint stored beside the log. The host must retain the checkpoint through a separate trusted channel.

This history does not override revocation: revoked keys remain rejected by archival verification even when an earlier signature timestamp predates the revocation event.


For strict archival verification, pass the independently authenticated lifecycle records and checkpoint to `verify_archived_bundle(..., require_history=True)`. The verifier then requires history to agree with the registry's key status and retirement timestamp and rejects any key with a revocation event. See [Trust registry history](TRUST-REGISTRY-HISTORY.md).


Strict archival verification also takes the retained registry snapshots referenced by the key-add and retirement events. Each snapshot is rehashed and checked against the event digest, key fingerprint, lifecycle status, and retirement timestamp. A hash chain without the referenced snapshots is not sufficient for strict archive acceptance.


## Consolidated regression suite

Run the full focused regression set for signing, verification, key policy, archival history, and runtime handoffs:

```bash
python -m unittest \
  TESTS.test_artifact_signing \
  TESTS.test_artifact_integrity \
  TESTS.test_trust_registry \
  TESTS.test_trust_registry_history \
  TESTS.test_archival_verification \
  TESTS.test_handoff_runtime -v
```

This suite validates deterministic protocol mechanics with ephemeral local keys and synthetic artifacts. It does not execute an LLM or the four Skills and does not prove that a real host has configured or enforced the documented policies.


### Binding the stage-result object

For runtime handoffs, `artifact_provenance.payload.stage_result_sha256` must contain the SHA-256 digest returned by `stage_result_sha256(result)` from `scripts/handoff_runtime.py`. The digest covers the entire stage-result JSON except the provenance envelope, signature bundle, and runtime-generated verification report. The runtime recomputes it before accepting the handoff. This prevents a stage result's evidence, actions, or domain-specific claims from being changed independently of the provenance envelope. With Ed25519 verification enabled, the envelope digest also cryptographically binds this stage-result digest. The digest establishes integrity of the supplied bytes, not truthfulness of the agent's original observations.


Historical key resolution also compares the signed timestamp with the verifier's current timezone-aware clock and rejects future-dated signatures. A valid key window alone is insufficient: an active key must not be allowed to make a not-yet-created artifact appear historically verified.


The serializer now rejects non-string object keys and Python-only container/value types rather than silently coercing them. The canonical profile is the exact Python reference encoding described above; it is not claimed to be RFC 8785/JCS. A non-Python host must implement byte-for-byte compatible serialization (including number formatting and Unicode handling) or call a compatible reference implementation before signing/verifying. Cross-language golden test vectors remain a useful future interoperability gate.
