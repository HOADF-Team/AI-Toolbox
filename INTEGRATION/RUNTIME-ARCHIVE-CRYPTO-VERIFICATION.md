# Cryptographic verification of portable runtime archives

## Purpose

`scripts/runtime_archive_verification.py` adds an offline, audit-only verification layer on top of the portable package verifier in `runtime_run_archive.py`. It reuses the existing Ed25519/RFC 3161 and historical trust-registry verifier in `archival_verification.py`, the signed registry-history anchor verifier, and the declarative handoff-chain validator. It does not create a second signature format or trust registry.

## Trust boundary

The archive is untrusted input. Its embedded public keys, registry, history, snapshots, stage records, and timestamp responses are evidence to be checked; they are not trust anchors by themselves.

The verifier host must supply:
- `history_anchor_public_key`: independently provisioned public key that authenticates the registry-history checkpoint;
- `history_anchor_key_id`: expected key identifier for that anchor;
- `timestamp_ca_file`: independently provisioned TSA trust bundle;
- optionally `timestamp_untrusted_chain_file`: intermediate/TSA certificates, never a trust root.

Trusted RFC 3161 timestamps are required by default for both the registry-history anchor and every stage signature. Setting `require_trusted_timestamps=False` is an explicit weaker audit policy and must not be used where trusted time is required.

## Archive layout

The archive must contain the following paths (plus `archive.json` and `MANIFEST.json`):

```text
workflow/
  contract.json
  stages/
    <stage-id>.json
    <stage-id>/
      timestamp.tsr
      evidence/
        <evidence files referenced by the signed bundle>
trust/
  registry.json
  keys/
    <public keys named by registry.json>
  history.json
  history-checkpoint.json
  history-anchor.json
  history-anchor.tsr
  registry-snapshots/
    <registry snapshot SHA-256>.json
```

The archive metadata's `stage_ids`, `skill_ids`, `workflow_id`, and `run_id` must match the workflow contract and signed stage contexts. Only completed runs are accepted as fully verified. Each stage JSON is the complete stage result emitted by the runtime adapter and includes `artifact_provenance` and `integrity_bundle`.

## API

```python
from pathlib import Path
from runtime_archive_verification import verify_runtime_archive_cryptographically

report = verify_runtime_archive_cryptographically(
    Path("portable-run"),
    {
        "history_anchor_public_key": Path("/host-trust/registry-anchor.pub"),
        "history_anchor_key_id": "registry-anchor-2026",
        "timestamp_ca_file": Path("/host-trust/tsa-roots.pem"),
        # Optional:
        # "timestamp_untrusted_chain_file": Path("/host-trust/tsa-chain.pem",
        # "require_trusted_timestamps": True,
    },
)
```

The verifier performs these checks in order:
1. exact archive file set, file sizes, SHA-256 digests, and safe paths;
2. signed registry-history anchor against the host-supplied anchor public key;
3. RFC 3161 timestamp of the exact registry-anchor signature bytes;
4. every stage's signed run/workflow/stage/Skill/input context and result digest binding;
5. Ed25519 signature, evidence digests, TSA timestamp of the exact stage signature bytes, historical key validity, and registry lifecycle history;
6. four-stage (or contract-declared) order, required fields, evidence, and input/output reference continuity.

Missing anchors, invalid signatures, missing timestamps under strict policy, revoked keys, changed snapshots, tampering, or broken handoff references fail closed.

## Security limitations

- The history anchor key and TSA CA bundle must be provisioned independently by the verifier host. Copying them from the archive would defeat the trust boundary.
- A signed history proves integrity relative to the trusted anchor; it does not prove that lifecycle events were truthful when recorded.
- Evidence hashes authenticate the archived bytes, not the truth of observations contained in those bytes.
- This is retrospective offline audit only. A successful report never authorizes live runtime handoff, Skill execution, production changes, or external actions.
- The verifier does not contact a public TSA, registry service, server, or external runtime.


## Exporting a verifier-compatible archive

Use `scripts/runtime_archive_export.py` when the run result and its evidence files have already been written to a staging directory. Supply an explicit archive-path-to-source-path map; the exporter derives and enforces the required paths from the contract, stage integrity bundles, registry key references, and registry history.

```python
from pathlib import Path
from runtime_archive_export import create_cryptographic_runtime_archive

report = create_cryptographic_runtime_archive(
    source_root=Path("run-staging"),
    destination=Path("portable-run"),
    metadata=run_metadata,
    files=explicit_archive_file_map,
)
```

The exporter rejects missing stage timestamps, missing evidence, unexpected files, path traversal, symlinks, incomplete stages, mismatched signed run contexts, and private-key material. It does not discover files recursively or create signatures/timestamps; those must already exist and be explicitly supplied. The returned report confirms package file integrity only. Run `verify_runtime_archive_cryptographically` separately with host-provisioned trust roots to authenticate the archive.


## End-to-end verification test

`TESTS/test_runtime_archive_end_to_end.py` exercises the complete local pipeline with temporary Ed25519 signer and history-anchor keys plus an ephemeral local RFC 3161 TSA:

1. Execute the four-stage workflow through the adapter protocol.
2. Sign each stage result and evidence manifest; timestamp each exact signature.
3. Build and sign a registry-history checkpoint; timestamp the anchor signature.
4. Export the explicit evidence set into the portable archive layout.
5. Verify the archive using only host-supplied history-anchor and TSA trust roots.
6. Alter a stage signature while updating the package manifest and confirm that cryptographic verification still fails.

The test uses synthetic stage fixtures and local OpenSSL-generated keys/certificates. It does not call a public TSA, use production keys, perform real Skill/LLM actions, or require a server. A passing test demonstrates protocol and cryptographic integration in this controlled fixture; it does not establish that the synthetic evidence is truthful or that an arbitrary machine already trusts the supplied roots.
