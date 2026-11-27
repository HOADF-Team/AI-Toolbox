# age

- **ID:** `age`
- **Category:** security
- **Status:** `tested`
- **Publisher / maintainer:** Filippo Valsorda and contributors
- **License:** BSD-3-Clause

- **Tested version:** 1.3.2
- **CI verification:** GitHub-hosted Ubuntu Linux x86_64; Verified file encryption and decryption round trip using a temporary identity after verifying the official release archive SHA-256.
- **CI record:** `TESTS/SECURITY-TOOL-SMOKE.md`

- **Purpose:** simple file encryption/decryption with explicit recipients or passphrases.
- **Upstream:** https://github.com/FiloSottile/age
- **Documentation:** https://github.com/FiloSottile/age#readme
- **License:** BSD-3-Clause (verify the exact upstream release and bundled components)
- **Platforms:** Windows, Linux, macOS; verify release binary for target platform.
- **Catalog status:** reviewed; installation and runtime are not yet tested in AI-Toolbox.

## Safe use

Encrypt to a recipient public key; keep the corresponding private identity offline or in a dedicated secret store. Example: `age -r <recipient-public-key> -o backup.tar.gz.age backup.tar.gz`. Decrypt only into a directory with restrictive permissions and avoid shell history or logs containing passphrases/private key material.

Keep recovery identities separate from the encrypted files and test recovery before relying on the process.

## Limitations

age is a file encryption tool, not a key-management service, disk/database encryption system, TLS terminator or access-control system. It cannot protect plaintext while an authorized process is using it. Loss or compromise of the identity/passphrase can make data unrecoverable or exposed.
