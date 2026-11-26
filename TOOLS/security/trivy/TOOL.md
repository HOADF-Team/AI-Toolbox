# Trivy

- **Purpose:** scan container images, filesystems and repositories for known vulnerabilities, secrets, licenses and (when enabled) configuration misconfigurations.
- **Upstream:** https://github.com/aquasecurity/trivy
- **Documentation:** https://trivy.dev/
- **License:** Apache-2.0
- **Platforms:** Windows, Linux, macOS; verify release packaging and runtime requirements.
- **Catalog status:** reviewed; installation and runtime are not yet tested in AI-Toolbox.

## Safe use

Example filesystem scan: `trivy fs --scanners vuln,secret,misconfig .`. Misconfiguration scanning must be explicitly enabled for filesystem/repository scans. Vulnerability and secret scans may use downloaded databases; plan network access, cache and data handling. Scan a local checkout or a built image in an isolated environment.

Review report redaction before publishing. Do not upload proprietary source or private images to third-party services without authorization.

## Limitations

Coverage depends on supported ecosystems, lockfiles, scanner configuration and database freshness. A scan is not a penetration test and does not prove a container or server is secure. Findings need triage; false positives and gaps are possible.
