# Syft

- **ID:** `syft`
- **Status:** `reviewed`
- **Official site:** https://github.com/anchore/syft
- **Source:** https://github.com/anchore/syft
- **License:** Apache-2.0
- **Platforms:** Windows, Linux, macOS
- **Primary interface:** CLI

## Purpose

Syft generates a Software Bill of Materials (SBOM) from source directories, filesystems and container images. It can emit SPDX and CycloneDX documents for dependency transparency, vulnerability workflows and license review.

## Typical use

```bash
syft dir:. -o cyclonedx-json=sbom.cdx.json
syft dir:. -o spdx-json=sbom.spdx.json
syft image:IMAGE_REFERENCE -o cyclonedx-json=sbom.cdx.json
```

Use a pinned release and verify its published checksum or Sigstore release attestation before execution. Treat generated SBOMs as potentially sensitive: they reveal internal package names and software composition.

## Safety and limitations

- An SBOM is an inventory, not a vulnerability scan, proof of integrity, or security certification.
- Results depend on ecosystem support, source availability and cataloger coverage.
- Review output before publishing; do not upload private source or image contents to third-party services without authorization.
- Pair SBOM generation with vulnerability analysis (for example Trivy) and artifact provenance/signature verification.
- This record is reviewed only. Installation and runtime behavior have not yet been tested by AI-Toolbox CI.
