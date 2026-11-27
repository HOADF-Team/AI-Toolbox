# Cosign

- **ID:** `cosign`
- **Category:** security
- **Status:** `reviewed`
- **Publisher / maintainer:** Sigstore project
- **License:** Apache-2.0
- **Reviewed version:** 3.1.5
- **Upstream:** https://github.com/sigstore/cosign
- **Documentation:** https://docs.sigstore.dev/cosign/overview/
- **Platforms:** Linux, macOS, Windows (verify the selected release and installer for the target platform)
- **Catalog status:** reviewed; pinned installation and functional runtime test are pending CI.

## Purpose

Cosign signs and verifies software artifacts and OCI container images. It supports local key pairs, keyless signing through Sigstore identity and transparency services, KMS-backed keys, and signing/verification bundles.

## Safe-use guidance

- Verify the signer identity and OIDC issuer explicitly for keyless signatures. A valid signature from an unexpected identity is not sufficient.
- Prefer signing immutable artifact digests rather than mutable image tags.
- Protect private keys and KMS access. Never commit private keys, put them in logs, or send them to an untrusted service.
- Keep signing and verification policies explicit: expected identity, issuer, artifact digest, trusted root and bundle format.
- Treat SBOM signing as one part of provenance; a signature does not prove that the source code is safe or that the build was reproducible.
- Do not grant `id-token: write` unless a workflow intentionally performs keyless signing and its identity policy has been reviewed.
- Do not publish private SBOMs, signatures or metadata without checking whether they disclose internal dependency information.

## CI verification plan

The AI-Toolbox workflow pins Cosign 3.1.5 and uses the official `sigstore/cosign-installer` action, which verifies release integrity during installation. The smoke test creates an ephemeral local key pair, signs a synthetic file using a signing configuration with external Fulcio/OIDC/Rekor/TSA services disabled, verifies the signature, then modifies the file and expects verification to fail.

This deliberately does not use GitHub OIDC, production credentials, real keys, public transparency-log publication or an OCI registry. The test remains pending until the workflow passes.

## Limitations

Cosign is a signing and verification tool, not a secrets manager, HSM, KMS, vulnerability scanner, malware detector or proof of secure build. Keyless signing depends on identity-provider and Sigstore service availability. Key-based signing shifts responsibility for private-key protection, rotation, backup and revocation to the operator.
