# Skill → Tool dependency map

**Source:** `HOADF-Team/Personal-AI-Library` — 23 `SKILL.md` files in `main`.
**Inventory date:** 2026-11-26.
**Purpose:** map workflow instructions to concrete software capabilities. This is a discovery and planning document, not a claim that every candidate is installed, reviewed, or tested.

## Status legend

- **In catalog** — an AI-Toolbox record exists; its own verification status still applies.
- **Candidate** — a plausible upstream tool or tool family to research; not yet reviewed or endorsed.
- **Built-in / service** — capability may already exist in the runtime or is provided by an external service; do not add a redundant download.
- **Needs task-specific decision** — select only after examining the actual project, operating system, budget, data sensitivity, and required workflow.

## Cross-cutting foundation

| Capability | Candidate tools / services | Why it is shared | Current decision |
|---|---|---|---|
| Source control and repository operations | Git; GitHub CLI (`gh`) | GitHub portfolio, code review, deployment, releases, issue workflows | Git in catalog (`tested`); GitHub CLI remains a candidate; verify separately from GitHub connector capabilities |
| General scripting/runtime | Python; Node.js | Python, audits, API clients, automation, browser tooling | Python and Node.js in catalog (`tested`); versions must still be selected per project |
| HTTP/API diagnostics | `curl`; `jq`; Redocly CLI | API integrations, webhooks, OpenAPI linting and request-workflow checks | curl and jq in catalog (`tested`); Redocly CLI in catalog (`tested`); OpenAPI lint and Arazzo workflow checks passed |
| Containerized isolation | Docker / Podman | Disposable test environments and VPS deployment | Candidate; not required for every task |
| Browser automation | Playwright | Website testing, browser workflows, screenshots | In catalog (`tested`); browser automation smoke test passed |
| Performance / accessibility diagnostics | Lighthouse; axe-core | SEO and web quality checks | Both in catalog (`tested`); fixture audits passed; distinguish lab metrics from field data |

## Per-Skill mapping

| Personal-AI-Library Skill | Required capability | Candidate tools / services to investigate | AI-Toolbox state / notes |
|---|---|---|---|
| `python-development` | Python runtime, isolated environments, linting, tests, debugging | Python, `venv`/uv, pytest, Ruff, mypy | Python, uv, and pytest in catalog (`tested`); Ruff and mypy in catalog (`tested`); prefer standard library where sufficient |
| `code-audit` | Static inspection, syntax/AST checks, and Python security patterns | Existing Skill AST script; Ruff; Bandit; Semgrep only for broader multi-language/data-flow needs | Bandit in catalog (`tested`); B301/B602 findings detected and safe fixture clean; local AST script remains in Personal-AI-Library |
| `web-development` | HTML/CSS/JS workflow, local server, browser testing, build tools | Playwright; Node.js/npm; Vite only when project needs a build step | Playwright in catalog (`tested`); Node.js in catalog (`tested`); Vite only when project needs a build step |
| `devops-vps` | Remote Linux diagnostics, service/container/log inspection | OpenSSH, `ssh`, `journalctl`, systemd tools, Docker/Podman, `curl` | Mostly OS-native tools; avoid installing a second admin stack without need |
| `automation-vps` | API clients, webhook testing, scheduling, state and retries | Python HTTP clients; `curl`; `jq`; Redocly CLI for OpenAPI/Arazzo workflows; n8n only for visual workflow needs | curl and jq in catalog (`tested`); Redocly CLI (`tested`); external API access and credentials require explicit scope |
| `telegram-bots` | Telegram Bot API integration and webhook/polling | aiogram or python-telegram-bot (choose by existing project/version); Telegram Bot API | Candidate; never mix incompatible SDK major versions |
| `max-bots` | MAX platform API integration | Official MAX Bot API/docs and an HTTP client or supported SDK if available | Needs current official API verification; do not assume Telegram compatibility |
| `github-portfolio` | Git operations, repo metadata, Pages and release workflow | Git; GitHub CLI; GitHub Actions; existing GitHub connector | Git in catalog (`tested`); GitHub CLI remains a candidate; Actions and connector are hosted capabilities |
| `social-media` | Drafting and platform-specific publishing workflow | Native Telegram, X and GitHub interfaces/APIs | Built-in / service; drafts first, publishing only after approval; no third-party scheduler assumed |
| `content-planning` | Calendar and editorial workflow | Spreadsheet (Google Sheets or LibreOffice Calc); calendar service | LibreOffice is in catalog (`tested`); calendar remains service/task-specific; no dedicated app needed for a simple calendar |
| `crypto-research` | Market research, historical data, reproducible analysis | CCXT unified public APIs for BingX (primary), Binance, Bybit and OKX; Python/pandas; Matplotlib | CCXT in catalog (`tested`): BingX spot/swap and OKX spot passed; Binance and Bybit listed but public CI requests were region-blocked; pandas/Matplotlib `tested` |
| `crypto-market-analysis` | Market data, charts, indicators and funding/open-interest inputs | CCXT for BingX (primary), Binance, Bybit and OKX; pandas; Matplotlib | CCXT `tested` for BingX spot/swap and OKX spot; Binance/Bybit runtime connectivity remains unverified due to CI runner geo-blocks; document spot/swap support separately, with explicit units and timestamps |
| `crypto-futures-risk` | Position sizing, leverage and liquidation/risk calculations | Python standard library / decimal; spreadsheet for independent cross-check | Built-in / lightweight; avoid paid trading terminals unless a concrete gap exists |
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

The catalog now contains **26 tool records — all 26 are `tested`**. CCXT installation passed; BingX spot/swap and OKX spot public data passed. Binance and Bybit were blocked by GitHub runner region restrictions and remain unverified at the endpoint level. Bandit passed pinned installation and safe/unsafe fixture scans in isolated CI. Redocly CLI passed pinned installation, OpenAPI lint, and Arazzo API workflow checks in isolated CI.

The catalog covers source control, Python development and quality checks, JavaScript runtime, browser testing and audits, document conversion/OCR, image processing and metadata, background removal, media processing, HTTP/JSON API utilities, OpenAPI workflow testing, Python data analysis/visualization, and Python security scanning, and multi-exchange cryptocurrency market-data access.

`tested` means a documented installation and/or runtime smoke test passed in the specific environment described in that tool's record. It does **not** mean the tool is installed on a user's computer, nor does a smoke test prove every feature or platform works. Check each record for the exact scope and limitations.

Remaining research priorities:

1. **API and automation utilities:** compare HTTP clients/testing tools and optional n8n against existing Python and OS-native capabilities.
2. **Crypto exchange integration:** CCXT is tested with BingX (primary) spot/swap and OKX spot; Binance and Bybit adapters are listed upstream but public API checks were geo-blocked from the GitHub runner.
3. **Platform-specific SDKs:** choose Telegram SDK and MAX API tooling only when an actual project requires them.
4. **VPS/container operations:** assess Docker/Podman and SSH diagnostics only against a concrete deployment or administration workflow.
5. **Security/code audit:** Bandit is tested as a Python security-pattern scanner; consider Semgrep or license scanners only when a project needs broader multi-language or supply-chain analysis.

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
- [Skills catalog](https://github.com/HOADF-Team/Personal-AI-Library/blob/main/CATALOG.md)
- [AI-Toolbox verification and contribution rules](../AGENTS.md)
- [AI-Toolbox tool catalog](tools.json)
