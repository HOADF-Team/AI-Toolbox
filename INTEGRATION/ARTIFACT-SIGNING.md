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
