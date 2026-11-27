# pip-audit

- **ID:** `pip-audit`
- **Category:** security
- **Status:** `tested`
- **Publisher / maintainer:** Python Packaging Authority (PyPA)
- **License:** Apache-2.0

- **Tested version:** 2.10.1
- **CI verification:** GitHub-hosted Ubuntu Linux x86_64; Installed the pinned CLI and audited requirements-dev.txt against the current advisory database.
- **CI record:** `TESTS/SECURITY-TOOL-SMOKE.md`

- **Purpose:** audit Python environments and dependency requirement inputs for known published vulnerabilities; can emit CycloneDX SBOM output.
- **Upstream:** https://github.com/pypa/pip-audit
- **Documentation:** https://github.com/pypa/pip-audit#readme
- **License:** Apache-2.0
- **Platforms:** Windows, Linux, macOS; requires Python 3.10+
- **Catalog status:** reviewed; installation and runtime are not yet tested in AI-Toolbox.

## Safe use

Prefer a pinned, isolated environment and a reviewed lock/requirements file. Example: `pip-audit -r requirements.txt`. This operation consults vulnerability data sources and therefore requires network access. Review package resolution behavior and use trusted indexes. Do not add `--fix` automatically; upgrades can change application behavior and require tests.

## Limitations

pip-audit reports known advisories for Python packages; it is not SAST, malware detection, a complete OS/shared-library scanner or proof that dependencies are safe. It cannot guarantee that a package has no unknown vulnerabilities. Treat skipped/unresolved dependencies as gaps, not clean results.
