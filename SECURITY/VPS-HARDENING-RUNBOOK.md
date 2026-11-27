# Trading VPS security deployment checklist

**Purpose:** controlled preparation and verification of a production crypto-trading VPS.  
**Mode:** read-only assessment first. No production change is authorized by this document.  
**Status:** procedure drafted; no real VPS has been inspected or hardened.

## 0. Safety gates before touching production

Do not begin configuration changes until all are true:

- The server owner has explicitly authorized the exact host and scope.
- A separate provider console/rescue path is available and tested; SSH must not be the only recovery channel.
- A recent backup exists, its encryption key is stored separately, and a restore test has succeeded.
- Current firewall rules, SSH settings, users, services, listening ports, mounts and deployment method have been captured without secrets.
- The public management IP/VPN range is known and confirmed by the operator.
- A maintenance window, rollback procedure and responsible operator are agreed.
- No exchange API secret, SSH private key, password, seed phrase or full environment file is sent to ChatGPT or committed to Git.

If any gate is missing, stop at assessment and report the blocker.

## 1. Read-only baseline inventory

Run from an authorized administrative session. Commands below inspect state; review their output locally and redact hostnames, public IPs, usernames and paths before sharing.

```bash
date -u
uname -a
cat /etc/os-release
id
who
last -a | head -30
sudo ss -tulpn
sudo systemctl --failed
sudo systemctl list-units --type=service --state=running
sudo ufw status verbose
sudo nft list ruleset
sudo sshd -T
sudo getent passwd
sudo find /etc/ssh -maxdepth 2 -type f -printf '%m %u:%g %p\n'
```

Do not publish raw `sshd -T`, user, firewall or service output if it exposes sensitive network topology. Never print private keys, secret environment variables, tokens or full credential files.

Record:
- OS release, kernel and update status;
- listening sockets and their owning services;
- inbound firewall policy and provider firewall/security-group rules;
- SSH authentication policy and authorized access paths;
- privileged users, sudo grants, service users and scheduled tasks;
- running bot/API/database/container services;
- mounted volumes, disk encryption state and backup destinations;
- CI/CD credentials and deployment access boundaries.

## 2. Exchange and API credential controls

For every exchange and environment, record only metadata (never secret values):

- key owner, purpose, environment, creation date, last rotation and expiry policy;
- exact permissions and whether trading is enabled;
- withdrawal and transfer permissions disabled;
- IP allowlist enabled for the VPS egress IP where supported;
- separate credentials for production, staging, monitoring and read-only reporting;
- revocation and replacement procedure tested without disclosing credentials.

**Acceptance:** a trading key cannot withdraw or transfer funds; a compromised bot process cannot read unrelated exchange credentials or backup credentials.

## 3. SSH and operator access

Target policy, to be staged and validated against the actual OS/OpenSSH version:

- unique named operator accounts; no shared daily-use root login;
- public-key authentication; disable password authentication only after a second session and provider console recovery have been verified;
- disable direct root SSH login where operationally safe;
- restrict SSH source addresses to VPN/known management IPs where possible;
- protect private keys on operator devices and rotate any exposed key;
- restrict sudo to named operators and required commands;
- monitor new accounts, sudo grants, authorized_keys changes and failed logins.

Do not edit sshd configuration or restart SSH until syntax validation, a second working session and rollback access are confirmed.

## 4. Firewall and network segmentation

Create a port/service matrix before changing rules:

| Service | Intended exposure | Required control |
|---|---|---|
| SSH | VPN or approved operator IPs only | Source allowlist, key auth, monitoring |
| Trading bot outbound API | Outbound only to required endpoints where feasible | Egress policy and TLS verification |
| Admin panel | VPN/private network only | Strong authentication, MFA if supported |
| Database/cache | Loopback or private service network | No public listener; service credentials |
| Metrics/logging | Private network or authenticated collector | No public unauthenticated endpoint |

- Deny unsolicited inbound traffic by default.
- Keep provider firewall and host firewall policies consistent.
- Do not expose database, Redis, container daemon/socket or debug ports to the public internet.
- Stage changes in a separate rule set; test new access before removing old access.
- Never run a remote `ufw enable`, flush nftables, or replace firewall rules without an out-of-band recovery path.

## 5. Runtime isolation and least privilege

- Run the bot as a dedicated non-root account.
- Use rootless containers when compatible; never mount container-engine sockets into the bot.
- Give each service only its required read/write paths and network access.
- Separate bot, admin panel, database, monitoring and backup identities.
- Use read-only filesystems and drop Linux capabilities where the workload permits.
- Apply systemd hardening (for example, NoNewPrivileges, PrivateTmp, ProtectSystem, ProtectHome, capability bounding and restrictive writable paths) after compatibility testing.
- Pin application and dependency versions; deploy immutable build artifacts and retain a known-good rollback version.

## 6. Secrets, encryption and data stores

- Store exchange credentials in a dedicated secret manager/KMS where practical; environment variables are a constrained fallback, not a full vault.
- Never put secrets in source, container layers, CI logs, shell history, process arguments or diagnostics.
- Encrypt traffic with TLS and certificate/hostname verification; do not disable verification.
- Verify encryption-at-rest for database volumes, attached disks and backups; identify who controls the encryption keys.
- Keep backup encryption identities separate from the production VPS and backup storage account.
- Restrict database accounts and network access; enable authentication and transport encryption.
- Rotate credentials after suspected exposure and revoke the old credential before deploying a replacement.

## 7. Monitoring and incident readiness

Alert on:
- unexpected SSH source IPs, new users, sudo grants and authorized_keys changes;
- new listening ports, processes, containers, scheduled jobs and systemd units;
- changes to firewall, SSH, bot configuration and deployment artifacts;
- API authentication failures, unexpected exchange key use, unusual order volume and risk-limit breaches;
- backup failures, repository deletion attempts and missing restore points.

Maintain a documented emergency stop that can stop **new orders** independently of the trading process. Do not automatically liquidate existing positions unless a separate, approved risk policy explicitly requires it.

## 8. Encrypted backups and restore drill

- Define RPO/RTO and backup retention.
- Back up database-consistent snapshots, required configuration and deployment metadata; exclude ephemeral caches.
- Encrypt before data leaves the host; use separate credentials and preferably immutable/versioned remote storage.
- Prevent the bot's runtime identity from deleting all backup generations.
- Run scheduled repository checks and restore drills into an isolated host/path.
- Verify application-level database consistency, configuration completeness and service startup from the restored copy.

**Acceptance:** at least one documented restore test with measured RPO/RTO; a copy remains recoverable if the VPS and its local credentials are compromised.

## 9. Application and supply-chain checks

Before each production release:
- Gitleaks scan current source and Git history; investigate all findings and revoke exposed credentials.
- pip-audit or the matching ecosystem scanner on locked production dependencies.
- Trivy scan of source/configuration and the exact built container image.
- Bandit/SAST and code review for authentication, authorization, injection, webhook validation, unsafe deserialization and secret handling.
- Review CI token permissions, third-party Actions, artifact provenance and branch protection.
- Retain scan versions, scope, results, exceptions and remediation evidence.

A clean scanner run is not proof of security. Findings need human triage and the production artifact must be the artifact that was scanned.

## 10. Change and rollback record

For each approved change, record:
- change ID, host, operator, timestamp and explicit approval;
- pre-change state and backup reference (not credentials);
- exact configuration diff and validation command;
- access and service health checks;
- rollback command/plan and result;
- post-change evidence and residual risks.

Never bundle SSH, firewall, package upgrades, secret rotation and bot deployment into one unreviewable change.

## 11. Final acceptance checklist

- [ ] No exchange withdrawal/transfer permissions on bot credentials.
- [ ] Exchange keys are separated, IP-restricted where supported, and revocable.
- [ ] SSH management path is restricted and recovery access tested.
- [ ] Public inbound ports match the approved service matrix.
- [ ] Bot and data services run with least privilege and network isolation.
- [ ] TLS verification is enabled; at-rest encryption and key custody are evidenced.
- [ ] Secrets are absent from repository, image layers and logs.
- [ ] Monitoring and an independently operable new-order kill switch are tested.
- [ ] Encrypted off-host backups exist and restore has been verified.
- [ ] Dependency, secret, configuration and application scans are reviewed.
- [ ] Rollback and incident-response procedures are rehearsed.

**Current result:** this is a deployment checklist only. Until a real VPS is inspected with authorized access, every host-level control remains **unverified**.
