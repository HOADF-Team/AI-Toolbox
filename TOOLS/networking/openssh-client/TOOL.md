# OpenSSH client

- **ID:** `openssh-client`
- **Category:** remote-access
- **Status:** `reviewed`
- **Publisher / maintainer:** OpenSSH project
- **Official website:** https://www.openssh.com/
- **Source repository:** https://github.com/openssh/openssh-portable
- **License:** BSD-style; verify the license notices for the exact distribution build
- **Platforms:** Linux, macOS, Windows (availability and packaging depend on the OS/distribution)
- **Last reviewed:** 2026-11-27

## What it does

The OpenSSH client provides encrypted remote login and command execution using the SSH protocol. It is commonly used to administer Linux VPS hosts and to transfer files with related tools such as `scp` and `sftp`.

## When an AI agent should use it

Use the client only when the task requires an SSH connection to a host and the user has authorized that access. Before connecting:

1. Confirm the target hostname/address, account, purpose, and permitted scope.
2. Use the user's approved identity mechanism; never request that a private key, passphrase, password, or token be pasted into chat.
3. Verify the host key using a trusted source or an established `known_hosts` entry. Do not bypass host-key checking with `StrictHostKeyChecking=no` or blindly accept an unexpected key change.
4. Start with read-only commands and inspect/redact output before sharing it.
5. Obtain explicit approval before changing files, services, firewall rules, users, credentials, or production state.

A detected `ssh` executable proves only that the local client binary is present. It does not prove network reachability, valid credentials, host identity, authorization, or access to any VPS.

## Basic usage

Check the local client version:

```bash
ssh -V
```

Connect only to a user-approved host with a verified host key:

```bash
ssh -o BatchMode=yes USER@HOST
```

Do not put passwords or private-key contents in command arguments. Do not disable host-key verification to make a connection succeed.

## Security and limitations

- SSH encrypts the connection but does not make an untrusted host trustworthy.
- Protect private keys with restrictive filesystem permissions and an appropriate agent or hardware-backed key store.
- Do not copy private keys into repositories, chat, logs, container images, or temporary reports.
- Avoid forwarding the local SSH agent to untrusted hosts and avoid mounting the agent socket into untrusted containers.
- Restrict account permissions and use per-host/user authorization. Prefer dedicated, least-privilege accounts for automation.
- A successful version probe does not test authentication, connectivity, host-key validation, or remote command authorization.
- SSH is a transport and remote-access client, not a VPS security scanner or host-hardening tool.

## Verification status

- **Source/license review:** official OpenSSH project site, portable source repository, and license notices reviewed.
- **Installation tested:** no.
- **Runtime tested:** no.
- **Local probe configured:** `ssh -V`; this only reports the local client version.
- **Status limitation:** this record does not claim the client is installed in the assistant runtime, on the user's computer, or that any remote host is reachable.
