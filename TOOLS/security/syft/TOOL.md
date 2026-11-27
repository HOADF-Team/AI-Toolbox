# Syft

- **ID:** `syft`
- **Category:** security
- **Status:** `tested`
- **Publisher / maintainer:** Anchore
- **License:** Apache-2.0
- **Tested version:** 1.57.1
- **CI verification:** GitHub-hosted Ubuntu Linux x86_64; verified the official checksum manifest and release archive SHA-256, installed the pinned CLI, and generated a non-empty CycloneDX SBOM from the AI-Toolbox checkout.
- **CI record:** `../../.github/workflows/security-tools.yml`

- **Purpose:** generate a Software Bill of Materials (SBOM) from source directories, filesystems and container images in SPDX or CycloneDX formats.
- **Upstream:** https://github.com/anchore/syft
- **Documentation:** https://github.com/anchore/syft
- **Platforms:** Windows, Linux, macOS (verify the selected release binary)

## Typical use

```bash
syft dir:. -o cyclonedx-json=sbom.cdx.json
syft dir:. -o spdx-json=sbom.spdx.json
syft image:IMAGE_REFERENCE -o cyclonedx-json=sbom.cdx.json
```

Treat generated SBOMs as potentially sensitive: they reveal internal package names and software composition. Review output before publishing; do not upload private source or image contents to third-party services without authorization.

## Safety and limitations

- An SBOM is an inventory, not a vulnerability scan, proof of integrity, or security certification.
- Results depend on ecosystem support, source availability and cataloger coverage.
- Pair SBOM generation with vulnerability analysis (for example Trivy) and artifact provenance/signature verification.
- This test proves only the pinned CLI installation and representative SBOM generation in GitHub-hosted Ubuntu Linux x86_64 CI. It does not establish installation on a user's PC or production host.
