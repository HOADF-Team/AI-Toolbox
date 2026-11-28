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
2. SHA-256 of each evidence file, resolved only beneath an explicitly configured local evidence root. Absolute paths, parent traversal, symlinks, missing files, and non-files are rejected.
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
