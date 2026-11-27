# Security tool smoke tests

The `Security tools smoke tests` workflow exercises the security tools recorded in the catalog. It runs only on a disposable GitHub-hosted Ubuntu runner and uses synthetic files and ephemeral credentials.

## Coverage

| Tool | CI verification | What it does not prove |
|---|---|---|
| pip-audit 2.10.1 | Installs the pinned CLI and audits `requirements-dev.txt` against current advisory data | No coverage of OS packages, production lockfiles, unknown vulnerabilities or malicious packages |
| Gitleaks 8.30.1 | Verifies the official release archive checksum, runs a redacted scan of the repository working tree | No guarantee that every secret format is detected; this workflow does not scan deleted Git history |
| Syft 1.57.1 | Verifies the official checksum manifest and release archive SHA-256, installs the pinned CLI, and generates a non-empty CycloneDX SBOM from this checkout | SBOM completeness depends on cataloger coverage; it is not a vulnerability scan or proof of integrity |\n| Cosign 3.1.5 | Installs through the official cosign-installer action with a pinned Cosign release; signs and verifies a test blob with a temporary key pair and confirms tamper detection | Does not test keyless OIDC signing, production key custody, KMS, OCI registry publishing or build provenance |\n| Trivy 0.76.2 | Verifies the official release archive checksum and scans repository files for vulnerabilities, secrets and misconfigurations | Coverage depends on supported ecosystems and fresh databases; not a penetration test or VPS audit |
| age 1.3.2 | Downloads the official Linux release binary, verifies its pinned SHA-256 digest, and verifies encrypt/decrypt round trip with a temporary identity | Does not test production key custody, disk/DB encryption or recovery procedures |
| restic 0.20.0 | Downloads the official Linux release binary, verifies its pinned SHA-256 digest, and verifies local encrypted repository init, backup, check and restore | Does not test remote storage, immutability, offsite isolation, retention policy or disaster recovery |

## Supply-chain and safety controls

- The workflow has read-only repository permissions.
- Gitleaks and Trivy archives are downloaded from their official release URLs and checked against the checksum files published with those releases.
- age 1.3.2 and restic 0.20.0 are downloaded from their official release pages and checked against SHA-256 digests published in GitHub release metadata.
- Python dependency audit is pinned to pip-audit 2.10.1.
- The age identity, restic password and Cosign signing key pair are generated temporarily at runtime. No real credentials, exchange keys, user files, production keys or production backups are used.
- The workflow does not install software on a user machine or VPS and does not deploy any configuration.

## Interpreting results

A green run confirms only that the pinned tools installed and the described CI checks passed on that runner at that time. A red run may indicate a detected repository issue, a known vulnerable dependency, an upstream download/checksum problem or a CI environment failure; inspect the failed step before drawing conclusions.

The CI scanner gates intentionally fail on detected findings. Do not suppress findings broadly to make the workflow green. Triage each finding, fix confirmed issues, and document narrowly justified false-positive exceptions.

This workflow is not a substitute for a separate read-only audit and approved hardening of the actual trading VPS.
