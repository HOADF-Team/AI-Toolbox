# restic

- **ID:** `restic`
- **Category:** security
- **Status:** `tested`
- **Publisher / maintainer:** restic maintainers
- **License:** BSD-2-Clause

- **Tested version:** 0.20.0
- **CI verification:** GitHub-hosted Ubuntu Linux x86_64; Verified encrypted local repository initialization, backup, integrity check and restore round trip after verifying the official release binary SHA-256.
- **CI record:** `TESTS/SECURITY-TOOL-SMOKE.md`

- **Purpose:** backup program for versioned snapshots in encrypted repositories across local and remote storage backends.
- **Upstream:** https://github.com/restic/restic
- **Documentation:** https://restic.readthedocs.io/
- **License:** BSD-2-Clause
- **Platforms:** Windows, Linux, macOS; backend availability varies.
- **Catalog status:** reviewed; installation and runtime are not yet tested in AI-Toolbox.

## Safe use

Initialize a repository with a strong unique password and store recovery material separately from both the source host and backup destination. Example read-only check: `restic check`. A backup command writes data; repository maintenance and forget/prune operations can delete data and require explicit approval.

Use separate repository credentials and retention controls. Schedule restore drills into an isolated target and verify application-level consistency, not only backup command success.

## Limitations

Encryption does not prevent deletion by an attacker who has write access to the repository. Protect credentials, isolate storage, use immutability/versioning where available, and monitor backup success. A backup is not considered verified until restoration has been tested.
