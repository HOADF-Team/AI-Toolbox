# Artifact signing helper

The helper in `scripts/artifact_signing.py` creates Ed25519 bundles compatible with `scripts/artifact_integrity.py`. It signs the canonical provenance-envelope digest and a manifest of evidence references, confined relative paths, and SHA-256 file digests.

## Host-side use

Resolve the intended active key through the authenticated host trust registry first. Then pass the resolved public key and registered fingerprint alongside the host-held private-key path:

```python
from pathlib import Path
from artifact_signing import create_integrity_bundle
from trust_registry import resolve_trusted_key

resolved = resolve_trusted_key(
    Path("/host/policy/trust-registry.json"),
    Path("/host/policy/public-keys"),
    "runtime-signing-2026-01",
    "crypto-security",
    "security.review",
)
bundle = create_integrity_bundle(
    envelope=artifact_provenance,
    key_id=resolved["trusted_key_id"],
    private_key=Path("/host/secret-store/runtime-signing.pem"),
    trusted_public_key=Path(resolved["trusted_public_key"]),
    expected_public_key_sha256=resolved["public_key_sha256"],
    evidence_root=Path("/host/evidence"),
    evidence_paths={"evidence:scan": "reports/scan.txt"},
)
```

The returned object is the `integrity_bundle` expected by the runtime verifier. The host attaches it to the stage result; the helper does not upload or transmit it.

## Safety and limitations

- The helper never creates, copies, logs, or stores private keys. Private-key custody, access control, backups, HSM integration, and authenticated registry distribution remain host responsibilities.
- On POSIX, the private-key file must not grant group or other permissions. Symlinked private-key files are rejected.
- Before signing, the helper derives the public key from the private key and compares its SHA-256 SPKI fingerprint with the registry-resolved trusted public key.
- Evidence paths must be relative, remain beneath the configured evidence root, and contain no symlink component. The mapping must exactly cover the envelope's evidence references.
- OpenSSL is invoked with fixed argument arrays and no shell. No network or paid service is used.
- A successful signature proves integrity and possession of the matching private key, not real-world signer identity or evidence truthfulness. The host must enforce producer and artifact scopes through the trust registry before invoking this helper.
- This helper does not prevent replay of a previously signed artifact in a different workflow run. Run/stage binding and historical-key verification are separate follow-up controls; do not treat this signing profile as replay protection.

Tests use ephemeral local keys only. No production key or credential belongs in this repository.

Run:

```bash
python -m unittest TESTS.test_artifact_signing TESTS.test_artifact_integrity -v
```


## Replay-resistant execution binding

For a workflow stage, pass the five expected identifiers to `create_integrity_bundle(..., execution_context=...)`:

```python
execution_context = {
    "run_id": host_generated_unique_run_id,
    "workflow_id": stage_envelope["workflow_id"],
    "stage_id": stage_envelope["stage"]["id"],
    "skill_id": stage_envelope["stage"]["skill_id"],
    "input_ref": stage_envelope["input_ref"],
}
bundle = create_integrity_bundle(
    ...,
    execution_context=execution_context,
    ttl_seconds=300,
)
```

This produces statement version `1.1`, with signed `issued_at` and `expires_at` timestamps. The host must generate a new, non-reused run ID for every workflow execution. A bundle signed for another run, workflow, stage, Skill, or input reference will fail when the runtime checks the expected context. Expired and future-dated bundles are rejected. The maximum permitted signature lifetime is one day; the verifier policy may impose a shorter maximum.

Enable enforcement in the runtime policy:

```python
integrity_policy = {
    "trust_registry_path": "/host/policy/trust-registry.json",
    "key_root": "/host/policy/public-keys",
    "evidence_root": "/host/evidence",
    "require_execution_context": True,
    "run_id": host_generated_unique_run_id,
    "max_signature_age_seconds": 300,
}
```

If `require_execution_context` is omitted or false, compatibility verification accepts the earlier statement format and does not claim replay protection. The host must persist run IDs and ensure they are never reused. This mechanism binds signatures to a host-declared run context; it is not a globally distributed nonce database and cannot stop a compromised host from deliberately reusing its own run ID.
