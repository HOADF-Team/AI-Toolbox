# Skill → Tool dependency map

**Source:** `HOADF-Team/Personal-AI-Library` — 25 `SKILL.md` files on `main` (PR #9 merged).
**Inventory date:** 2026-11-27.
**Purpose:** map workflow instructions to concrete software capabilities. This is a discovery and planning document, not a claim that every candidate is installed, reviewed, or tested.

## Status legend

- **In catalog** — an AI-Toolbox record exists; its own verification status still applies.
- **Candidate** — a plausible upstream tool or tool family to research; not yet reviewed or endorsed.
- **Built-in / service** — capability may already exist in the runtime or is provided by an external service; do not add a redundant download.
- **Needs task-specific decision** — select only after examining the actual project, operating system, budget, data sensitivity, and required workflow.

## Cross-cutting foundation

| Capability | Candidate tools / services | Why it is shared | Current decision |
|---|---|---|---|
| Security and data protection | Bandit; pip-audit; Gitleaks; Trivy; Syft; Cosign; age; restic; OS-native SSH/firewall/TLS controls | Protect code, credentials, runtime, stored data and recovery copies | Bandit, Gitleaks, pip-audit, Trivy, Syft, Cosign, age and restic `tested` in isolated Linux CI; GitHub OIDC CycloneDX SBOM and SLSA provenance attestations passed signer-identity verification on `main`; Cosign CLI scope remains local detached-signature verification and tamper detection; SSH/firewall/TLS and production controls still require target-host inspection |
| Source control and repository operations | Git; GitHub CLI (`gh`) | GitHub portfolio, code review, deployment, releases, issue workflows | Git in catalog (`tested`); GitHub CLI remains a candidate; verify separately from GitHub connector capabilities |
| General scripting/runtime | Python; Node.js | Python, audits, API clients, automation, browser tooling | Python and Node.js in catalog (`tested`); versions must still be selected per project |
| HTTP/API diagnostics | `curl`; `jq`; Redocly CLI; Schemathesis; Mockoon CLI | API integrations, webhooks, OpenAPI linting, explicit Arazzo workflows, property-based API testing, and local mock APIs | curl, jq, Redocly CLI, Schemathesis, and Mockoon CLI (`tested`); Mockoon local OpenAPI import/validation and loopback HTTP checks passed |
| Containerized isolation | Podman; Docker only if a compatibility gap appears | Disposable test environments and VPS deployment | Podman `tested` for rootless container smoke checks; Docker remains a candidate; not required for every task |
| Browser automation | Playwright | Website testing, browser workflows, screenshots | In catalog (`tested`); browser automation smoke test passed |
| Performance / accessibility diagnostics | Lighthouse; axe-core | SEO and web quality checks | Both in catalog (`tested`); fixture audits passed; distinguish lab metrics from field data |

## Per-Skill mapping

| Personal-AI-Library Skill | Required capability | Candidate tools / services to investigate | AI-Toolbox state / notes |
|---|---|---|---|
| `python-development` | Python runtime, isolated environments, linting, tests, debugging | Python, `venv`/uv, pytest, Ruff, mypy | Python, uv, and pytest in catalog (`tested`); Ruff and mypy in catalog (`tested`); prefer standard library where sufficient |
| `code-audit` | Static inspection, syntax/AST checks, and Python security patterns | Existing Skill AST script; Ruff; Bandit; Semgrep only for broader multi-language/data-flow needs | Bandit in catalog (`tested`); B301/B602 findings detected and safe fixture clean; local AST script remains in Personal-AI-Library |
| `web-development` | HTML/CSS/JS workflow, local server, browser testing, build tools | Playwright; Node.js/npm; Vite only when project needs a build step | Playwright in catalog (`tested`); Node.js in catalog (`tested`); Vite only when project needs a build step |
| `devops-vps` | Remote Linux diagnostics, service/container/log inspection | OpenSSH, `ssh`, `journalctl`, systemd tools, Docker/Podman, `curl` | Mostly OS-native tools; avoid installing a second admin stack without need |
| `server-security` | Linux server/VPS security audit, SSH/network/firewall, encryption, backups, monitoring and incident response | OS-native SSH/firewall/systemd tools; Trivy; Gitleaks; age; restic; Podman; Syft; Cosign; curl/jq | OS-native controls remain target-specific; Trivy/Gitleaks and encryption/backup tools are tested in isolated CI; GitHub OIDC SBOM/provenance attestations are verified for AI-Toolbox, not for a user's server |
| `automation-vps` | API clients, webhook testing, scheduling, state and retries | Python HTTP clients; `curl`; `jq`; Redocly CLI for OpenAPI lint/Arazzo workflows; Schemathesis for generated contract/edge-case tests; Mockoon CLI for local mock APIs and optional MCP control; n8n only for visual workflow needs | curl, jq, Redocly CLI, and Schemathesis (`tested`); Mockoon CLI (`tested`); pinned install, import/validation, inventory detection, and local mock HTTP checks passed; external API access and credentials require explicit scope |
| `telegram-bots` | Telegram Bot API integration and webhook/polling | aiogram or python-telegram-bot (choose by existing project/version); Telegram Bot API | Candidate; never mix incompatible SDK major versions |
| `max-bots` | MAX platform API integration | Official MAX Bot API/docs and an HTTP client or supported SDK if available | Needs current official API verification; do not assume Telegram compatibility |
| `github-portfolio` | Git operations, repo metadata, Pages and release workflow | Git; GitHub CLI; GitHub Actions; existing GitHub connector | Git in catalog (`tested`); GitHub CLI remains a candidate; Actions and connector are hosted capabilities |
| `social-media` | Drafting and platform-specific publishing workflow | Native Telegram, X and GitHub interfaces/APIs | Built-in / service; drafts first, publishing only after approval; no third-party scheduler assumed |
| `content-planning` | Calendar and editorial workflow | Spreadsheet (Google Sheets or LibreOffice Calc); calendar service | LibreOffice is in catalog (`tested`); calendar remains service/task-specific; no dedicated app needed for a simple calendar |
| `crypto-research` | Market research, historical data, reproducible analysis and strategy simulation | CCXT for BingX (primary), Binance, Bybit and OKX; pandas; Matplotlib; ta.py; backtesting.py | CCXT `tested` within documented scope; Binance/Bybit remain supported adapter targets but were geo-blocked in CI; ta.py and backtesting.py `tested` for selected indicators and synthetic OHLCV backtest; backtesting.py is AGPL-3.0-or-later |
| `crypto-market-analysis` | Market data, charts, indicators and funding/open-interest inputs | CCXT for BingX (primary), Binance, Bybit and OKX; pandas; Matplotlib; ta.py for technical indicators | CCXT `tested` for BingX spot/swap and OKX spot; Binance/Bybit adapters remain in scope but endpoint connectivity is unverified due to CI runner geo-blocks; ta.py `tested` for selected SMA/RSI calls; document spot/swap support separately, with explicit units and timestamps |
| `crypto-futures-risk` | Position sizing, leverage and liquidation/risk calculations | Python standard library / decimal; spreadsheet for independent cross-check | Built-in / lightweight; avoid paid trading terminals unless a concrete gap exists |
| **Future capability (not a Personal-AI-Library Skill)** | Strategy execution, paper trading, order lifecycle, operator controls and persistence | Hummingbot; Freqtrade; CCXT plus a dedicated execution/risk layer | Hummingbot and Freqtrade reviewed, not installed/tested; compatibility matrix at `TOOLS/crypto-engines/ENGINE-COMPATIBILITY.md`; neither currently lists BingX USDT-M perpetual support |
| `crypto-security` | Threat modeling, secrets and credential lifecycle, encryption, secure development, dependency/container scanning, CI/CD, host/network controls, monitoring, backup/recovery and incident response | Bandit; pip-audit; Gitleaks; Trivy; Syft; Cosign; age; restic; Podman; OS-native SSH/firewall/TLS controls | Bandit, pip-audit, Gitleaks, Trivy, age and restic `tested` in pinned GitHub Actions Linux CI (see each record for scope); Syft `tested` with pinned release verification, non-empty CycloneDX SBOM generation, and verified GitHub OIDC SBOM/SLSA attestations on `main`; Cosign 3.1.5 `tested` for pinned installation, ephemeral-key local signature verification and tamper detection in Linux CI; Podman is rootless-runtime tested separately; host controls, secret-manager integration and production deployments remain unverified |
| `trading-bot-audit` | Log/DB parsing, execution and PnL reconciliation | Python; SQLite (Python standard library); pandas; Matplotlib; CCXT for venue-specific reconciliation where required | pandas/Matplotlib and CCXT `tested` within documented scope; BingX spot/swap and OKX spot passed public checks; read-only audit first, no order permissions |
| `product-marketing` | Research, positioning and evidence-backed claims | Browser/search; spreadsheet; document editor | Mostly built-in capabilities; no dedicated software justified yet |
| `marketing-copywriting` | Drafting, editing and factual review | Document editor; spell/style checker if needed | Mostly built-in; optional checker only after language and privacy review |
| `seo-audit` | Crawl, metadata, performance and accessibility checks | Playwright; Lighthouse; Google Search Console; PageSpeed Insights; axe-core | Playwright, Lighthouse, and axe-core (`tested`) in catalog; Search Console and PageSpeed Insights are external services |
| `business-kwork` | Requirements, estimation, deliverables and handover | Issue/project tracker; spreadsheet; document editor | Needs task-specific decision; avoid prescribing paid project-management software |
| `research-fact-checking` | Source discovery, repository/license review and evidence capture | Browser/search; Git; GitHub API/CLI; license scanners such as ScanCode | Mostly built-in plus candidates; scanners require separate provenance/accuracy review |
| `product-images` | Image inspection, batch conversion, background removal and metadata | GIMP; ImageMagick; ExifTool; rembg (where suitable) | ImageMagick, ExifTool, GIMP, and rembg in catalog (`tested`) |
| `marketplace-listings` | Image preparation, listing copy and structured product data | Image tools above; spreadsheet; native marketplace interfaces | ImageMagick, ExifTool, GIMP, and rembg (`tested`) in catalog; native marketplace interfaces remain service-specific; no universal uploader recommended |
| `google-sheets` | Sheets API and Apps Script automation | Google Sheets / Apps Script; clasp for local Apps Script development | External service; OAuth scopes, quotas and account permissions matter |
| `documents-office` | DOCX/XLSX/PPTX/PDF read/write, conversion, OCR and validation | LibreOffice; Pandoc; Poppler; Tesseract; format-specific Python libraries | LibreOffice, Pandoc, Poppler, and Tesseract in catalog (`tested`); choose per format; macro and formula fidelity still require task-specific tests |

## Current coverage and remaining work

The catalog now contains **40 tool records**: 38 `tested` and 2 `reviewed`.  Security is a first-class Toolbox capability under `TOOLS/security/`, with its own smoke-test workflow and a coverage index at `TOOLS/security/README.md`. Hummingbot and Freqtrade are reviewed engine candidates only; neither has been installed or runtime-tested in AI-Toolbox. The new ta.py and backtesting.py records passed pinned installation and focused offline runtime checks in GitHub Actions; see each record for exact scope and limitations. CCXT installation passed; BingX spot/swap and OKX spot public data passed. Binance and Bybit were blocked by GitHub runner region restrictions and remain unverified at the endpoint level. Bandit passed pinned installation and safe/unsafe fixture scans in isolated CI. Redocly CLI passed pinned installation, OpenAPI lint, and Arazzo API workflow checks in isolated CI. Schemathesis passed pinned installation and a bounded property-based test against a loopback API fixture; 30 generated cases passed. Mockoon CLI passed pinned installation, inventory detection, OpenAPI import/validation, and a loopback HTTP mock test; its MCP server interface is documented but not runtime-tested. Podman passed a rootless container smoke test and is marked `tested`; see `TOOLS/container-runtime/podman/TOOL.md` for the exact environment and scope.

The catalog covers source control, Python development and quality checks, JavaScript runtime, browser testing and audits, document conversion/OCR, image processing and metadata, background removal, media processing, HTTP/JSON API utilities, OpenAPI workflow testing, Python data analysis/visualization, and Python/security scanning, file encryption and encrypted backup tooling, and multi-exchange cryptocurrency market-data access, technical indicators, and historical strategy simulation.

`tested` means a documented installation and/or runtime smoke test passed in the specific environment described in that tool's record. It does **not** mean the tool is installed on a user's computer, nor does a smoke test prove every feature or platform works. Check each record for the exact scope and limitations.

Remaining research priorities:

1. **Container execution and isolation:** Podman is now `tested` as a rootless OCI runtime for disposable environments; evaluate Docker only if a concrete compatibility gap appears.
2. **Crypto exchange integration:** CCXT is tested with BingX (primary) spot/swap and OKX spot; Binance and Bybit adapters are listed upstream but public API checks were geo-blocked from the GitHub runner.
3. **Platform-specific SDKs:** choose Telegram SDK and MAX API tooling only when an actual project requires them.
4. **VPS/container operations:** assess Docker/Podman and SSH diagnostics only against a concrete deployment or administration workflow.
5. **Security engineering:** Bandit, pip-audit, Gitleaks, Trivy, age and restic have passed scoped Linux CI tests. Syft 1.57.1 passed pinned installation, official checksum verification and non-empty CycloneDX SBOM generation in GitHub-hosted Ubuntu Linux x86_64 CI; a trusted `main` workflow then generated and verified GitHub OIDC CycloneDX SBOM and SLSA provenance attestations with exact signer-workflow identity. Cosign 3.1.5 passed pinned installation, ephemeral-key local detached-signature verification and tamper-detection tests in GitHub-hosted Ubuntu Linux x86_64 CI. Coverage includes Python SAST, dependency vulnerability checks, secret scanning, filesystem/container/misconfiguration scanning, file encryption and encrypted backup/restore. Remaining work includes evaluating a general-purpose multi-language SAST tool, OCI registry signing, independent clean-consumer provenance verification, secret-manager integrations, host auditing and security event monitoring. These are research candidates, not yet verified capabilities. CI tests do not mean tools are installed on a user's computer or production host; scanners do not replace secure design, key management, hardening or incident response.

This is a research queue, not an instruction to install every candidate. Reuse tools already available in the target environment and avoid redundant dependencies.

## Do not add as standalone tools yet

- Generic “AI assistant” wrappers that duplicate the model/runtime.
- Multiple overlapping API clients without a concrete workflow gap.
- Paid SaaS products without an explicit budget and a clear advantage over free/native alternatives.
- A separate tool for every Skill when the capability is already supplied by the operating system, a connected service, or the existing execution environment.
- Any candidate whose official source, license, security posture, maintenance state, or installation effects remain unclear.

## Next review procedure

For each candidate promoted from this map:

1. Search the catalog and existing records for duplicates.
2. Verify official source, maintainer, license, supported platforms, release activity and security advisories.
3. Record dependencies, permissions, network access, data handling, account/API-key needs and actual cost.
4. Decide whether it is downloadable software, a library, a hosted service, or an OS-native utility.
5. Test in an isolated environment where practical; record exact version, environment, commands and observed results.
6. Add a `TOOLS/<category>/<id>/TOOL.md` record and catalog entry only after review. Set status honestly; do not mark `tested` or `ready` without execution evidence.

## Source links

- [Personal-AI-Library](https://github.com/HOADF-Team/Personal-AI-Library)
- [Unified Skills + Toolbox operating workflow](../INTEGRATION/SKILLS-WORKFLOW.md)
- [Skills catalog](https://github.com/HOADF-Team/Personal-AI-Library/blob/main/CATALOG.md)
- [AI-Toolbox verification and contribution rules](../AGENTS.md)
- [AI-Toolbox tool catalog](tools.json)
