# Portable runtime-run archive format

Status: design specification for issue [#93](https://github.com/HOADF-Team/AI-Toolbox/issues/93).

## 1. Purpose and security boundary

A runtime run may contain multiple ordered Skill stages. Each stage can produce an artifact provenance envelope, an Ed25519 integrity bundle, evidence files, and an RFC 3161 timestamp response. The live runtime currently returns a report containing verification results, while archival verification is available per artifact. This specification defines how to preserve the complete run so a separate auditor can re-check it later.

The archive is an **audit package**, not a runtime authorization token. Successful archival verification MUST NOT authorize a live handoff, external action, installation, deployment, or production operation.

The archive proves only that:
- the included files match the archive manifest;
- each included signature verifies against the independently trusted public key;
- signed envelope, execution context, evidence digests, timestamp message imprint and TSA chain satisfy the supplied verification policy;
- registry history and checkpoint evidence satisfy the historical key-lifecycle policy;
- the ordered stage artifacts satisfy the declared handoff contract.

It does NOT prove that a Skill or LLM actually ran, that agent-reported evidence is truthful, that an action happened in the real world, or that a signer corresponds to a real person or organization. Those require separate host and operational controls.

## 2. Package layout

A version 1 package SHOULD use this layout:

```text
runtime-run-archive/
├── archive.json
├── report/
│   └── runtime-report.json
├── contract/
│   └── workflow-contract.json
├── stages/
│   └── <zero-padded-index>-<stage-id>/
│       ├── artifact.json
│       ├── integrity-bundle.json
│       └── timestamp.tsr
├── evidence/
│   └── <content-sha256>
├── trust/
│   ├── trust-registry.json
│   ├── registry-history.json
│   ├── registry-checkpoint.json
│   ├── registry-snapshots/
│   │   └── <registry-sha256>.json
│   ├── signing-public-keys/
│   │   └── <key-id>.pem
│   ├── tsa-roots.pem
│   └── tsa-untrusted-chain.pem
└── MANIFEST.json
```

Optional files MAY be omitted only when the corresponding policy does not require them. The archive metadata MUST enumerate all included files. No private signing key, TSA private key, credential, token, cookie, unrelated user file, or full host environment dump may be included.

Evidence is stored by content digest to avoid path collisions. The signed artifact's original evidence reference and relative path MUST remain in the artifact bundle; the archive manifest maps that reference to the archived content object.

## 3. Canonical encoding and manifest

All JSON files that participate in hashes MUST use the repository's documented canonical JSON profile and UTF-8 encoding. The format MUST declare the canonicalization profile identifier; it MUST NOT label the Python-specific profile as RFC 8785/JCS.

`MANIFEST.json` is a deterministic list of every regular file except itself. Each entry contains:
- normalized POSIX relative path;
- byte length;
- SHA-256 digest of exact file bytes;
- media type (or `application/octet-stream` when unknown).

Entries MUST be sorted lexicographically by normalized path. Duplicate paths, absolute paths, empty path components, `.`, `..`, backslashes, symlinks, non-regular files, and paths escaping the archive root MUST be rejected. The verifier MUST reject missing files and unlisted extra files. The manifest's own digest MUST be exposed by the verification report; a manifest hash alone is not an independent trust anchor.

A future signed archive-manifest statement MAY be added as a separately versioned feature. Version 1 MUST NOT imply that an unsigned manifest is authenticated merely because its hashes are internally consistent.

## 4. Archive metadata

`archive.json` MUST include:
- archive format and schema version;
- run ID and workflow ID;
- ordered stage IDs and Skill IDs;
- exact Personal-AI-Library repository revision used for the run;
- AI-Toolbox repository revision used for the runtime implementation;
- archive creation time with timezone;
- run status (completed, blocked, or incomplete);
- verification policy flags, including whether per-stage trusted timestamps and registry history were required;
- known limitations and the identity/source of the archive creator as a host-supplied claim.

The archive MUST NOT replace source commit SHAs with mutable branch names.

## 5. Verification algorithm

A verifier MUST perform these steps in order and fail closed:

1. Validate archive root and manifest structure before opening listed files.
2. Reject symlinks and unsafe paths; enumerate the directory and compare the exact file set with the manifest.
3. Recompute file sizes and SHA-256 digests.
4. Validate archive metadata, schema versions, run identity and exact source revisions.
5. Validate stage count, unique stage IDs, declared order, and each next-stage input reference against the preceding output reference.
6. Validate each artifact provenance envelope and its relationship to the corresponding stage and Skill revision.
7. Verify each Ed25519 integrity bundle using the archived public key, while authenticating the key through independently supplied trust anchors and the archived registry history/checkpoint.
8. Recompute evidence hashes from archived evidence bytes and verify that every signed evidence reference resolves exactly once.
9. Verify each RFC 3161 response against the exact raw Ed25519 signature bytes, using the supplied TSA trust root and optional untrusted intermediates. Check generation time against the signed execution-context interval and the historical signing-key validity/retirement policy.
10. Run the existing audit-only archival verifier for each artifact and the handoff contract validator for the complete ordered chain.
11. Emit a machine-readable report listing each check, result, relevant digest, and limitation.

The verifier MUST distinguish an archive-integrity failure from a signature, evidence, timestamp, registry-history, or handoff failure. It MUST NOT silently downgrade a required check to optional.

## 6. Trust inputs

An archive may carry public certificates, public signing keys, registry snapshots, signed registry-history records and checkpoints for portability. Their presence does not make them trusted by themselves.

The verifier MUST receive or otherwise resolve independent trust anchors for:
- the registry-history checkpoint signer;
- the TSA root CA;
- the policy that authorizes the signing-key registry.

The verifier MUST report the source and fingerprint of every trust anchor used. A trust anchor included only inside the archive MUST NOT bootstrap its own trust.

## 7. Test matrix

Use synthetic artifacts, temporary Ed25519 keys, a local ephemeral RFC 3161 TSA, and temporary directories only. Required cases:
- valid complete four-stage archive verifies;
- valid incomplete run is archived and reported as incomplete, never as completed;
- missing stage timestamp fails when timestamps are required;
- altered signature, evidence bytes, timestamp response, registry snapshot or checkpoint fails;
- wrong signing key, revoked key, retired key outside its historical window, and TSA time outside the signed context fail;
- broken stage order or input/output reference fails;
- path traversal, absolute path, symlink, duplicate path, missing file and unexpected file fail;
- archive can be verified after the original evidence and temporary runtime directories are removed.

Tests MUST NOT contact a public TSA, external service, exchange, VPS, production key or real LLM/Skill runtime.

## 8. Implementation sequence

1. Implement safe deterministic package creation and manifest generation.
2. Implement manifest and archive-structure verification.
3. Add offline re-verification of every archived stage using existing artifact and registry-history verifiers.
4. Add full-chain handoff verification and machine-readable audit output.
5. Add CLI and documentation only after the Python API and tests are stable.

Do not change live runtime authorization behavior as part of this archive feature.


## 9. Implemented milestone: archive package v1

The first implementation is available in `scripts/runtime_run_archive.py`:

- `create_runtime_archive(source_root, destination, metadata, files)` creates a directory archive from an explicit allowlist mapping archive-relative paths to source-relative paths. It generates `archive.json` and `MANIFEST.json`; metadata is never inferred from the host.
- `verify_runtime_archive(archive_root)` checks the exact file set, normalized paths, symlink/non-regular-file exclusions, byte sizes and SHA-256 digests without network access.
- `RuntimeArchiveError` exposes stable machine-readable error identifiers in its message.

Example:

```python
from pathlib import Path
from runtime_run_archive import create_runtime_archive, verify_runtime_archive

metadata = {
    "run_id": "run-001",
    "workflow_id": "workflow-001",
    "stage_ids": ["stage-a"],
    "skill_ids": ["example-skill"],
    "personal_ai_library_revision": "<40-character-commit-sha>",
    "ai_toolbox_revision": "<40-character-commit-sha>",
    "created_at": "2026-11-28T12:00:00Z",
    "run_status": "incomplete",
    "verification_policy": {
        "require_trusted_timestamps": True,
        "require_registry_history": True,
    },
}
report = create_runtime_archive(
    source_root=Path("./run-output"),
    destination=Path("./run-archive"),
    metadata=metadata,
    files={
        "report/runtime-report.json": "runtime-report.json",
        "stages/000-stage-a/artifact.json": "stage-a/artifact.json",
        "stages/000-stage-a/integrity-bundle.json": "stage-a/integrity-bundle.json",
        "stages/000-stage-a/timestamp.tsr": "stage-a/timestamp.tsr",
    },
)
assert report["status"] == "archive_integrity_verified"
assert verify_runtime_archive(Path("./run-archive"))["status"] == "archive_integrity_verified"
```

The source map is an allowlist: no directory is recursively copied and no secret/private key is automatically collected. The caller must explicitly select only public trust material and evidence required by policy. The archive destination must not already exist.

**Important v1 boundary:** the implemented verifier currently authenticates only the package's internal file set and SHA-256 consistency. The manifest is not signed and does not authenticate itself. The implementation does not yet invoke `verify_archived_bundle`, validate RFC 3161 responses, authenticate trust-registry history, or validate the complete handoff chain. Do not describe a v1 pass as cryptographic proof of a runtime run. Those checks remain the next implementation milestone.
