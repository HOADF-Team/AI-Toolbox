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

Do not place credentials, private keys, tokens, customer data, or other secrets in an envelope, payload, logs, or evidence references. A passing structural check is not proof of correctness, provenance authenticity, or production safety.
