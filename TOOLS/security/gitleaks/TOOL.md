# Gitleaks

- **ID:** `gitleaks`
- **Category:** security
- **Status:** `tested`
- **Publisher / maintainer:** Truffle Security
- **License:** MIT

- **Tested version:** 8.30.1
- **CI verification:** GitHub-hosted Ubuntu Linux x86_64; Scanned the repository working tree with redacted output after verifying the official release archive SHA-256.
- **CI record:** `TESTS/SECURITY-TOOL-SMOKE.md`

- **Purpose:** detect credentials, API tokens, passwords and other secret-like strings in Git history, repositories, directories and stdin.
- **Upstream:** https://github.com/gitleaks/gitleaks
- **Documentation:** https://github.com/gitleaks/gitleaks#readme
- **License:** MIT
- **Platforms:** Windows, Linux, macOS (verify the selected release binary)
- **Catalog status:** reviewed; installation and runtime are not yet tested in AI-Toolbox.

## Safe use

Run against a local checkout or a controlled copy. Review findings before sharing reports: a finding may contain the secret value. Do not paste raw findings into issues or chat. If a real credential is found in current files or history, treat it as exposed and revoke/rotate it; removing the text from the latest commit does not revoke it or erase history.

Example: `gitleaks git --redact --report-format json --report-path gitleaks-report.json .`

Use `--redact` to reduce accidental secret disclosure in output. Verify CLI flags against the installed version. A clean scan is not proof that no secret exists: custom formats, encoded values and unsupported patterns may be missed.

Upstream maintenance note: the upstream README currently describes Gitleaks as feature-complete with future releases focused on security patches. Recheck maintenance status before adopting it as a long-term mandatory control.

## Limitations

Gitleaks is a detector, not a secrets manager, revocation mechanism, encryption system or runtime access-control layer. It does not guarantee detection of every secret.
