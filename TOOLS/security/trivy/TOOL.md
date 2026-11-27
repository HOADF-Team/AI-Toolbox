# Trivy

- **ID:** `trivy`
- **Category:** security
- **Status:** `tested`
- **Publisher / maintainer:** Aqua Security
- **License:** Apache-2.0

- **Tested version:** 0.76.2
- **CI verification:** GitHub-hosted Ubuntu Linux x86_64; Scanned repository dependencies, secrets and misconfigurations after verifying the official release archive SHA-256.
- **CI record:** `TESTS/SECURITY-TOOL-SMOKE.md`

- **Purpose:** scan container images, filesystems and repositories for known vulnerabilities, secrets, licenses and (when enabled) configuration misconfigurations.
- **Upstream:** https://github.com/aquasecurity/trivy
- **Documentation:** https://trivy.dev/
- **License:** Apache-2.0
- **Platforms:** Windows, Linux, macOS; verify release packaging and runtime requirements.

## Safe use

Example filesystem scan: `trivy fs --scanners vuln,secret,misconfig .`. Misconfiguration scanning must be explicitly enabled for filesystem/repository scans. Vulnerability and secret scans may use downloaded databases; plan network access, cache and data handling. Scan a local checkout or a built image in an isolated environment. By default, Trivy may exit with code 0 even when findings are present; for a CI gate, configure `--exit-code 1` (and the intended severity/scanner scope) and still review the report.

Review report redaction before publishing. Do not upload proprietary source or private images to third-party services without authorization.

## Limitations

Coverage depends on supported ecosystems, lockfiles, scanner configuration and database freshness. A scan is not a penetration test and does not prove a container or server is secure. Findings need triage; false positives and gaps are possible. A successful process exit without a configured failure threshold must not be interpreted as a findings-free result.
