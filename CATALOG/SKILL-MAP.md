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
| HTTP/API diagnostics | `curl`; `jq`; OpenAPI tooling | API integrations, webhooks, research, troubleshooting | curl and jq in catalog (`tested`); OpenAPI tooling remains a separate research item |
| Containerized isolation | Docker / Podman | Disposable test environments and VPS deployment | Candidate; not required for every task |
| Browser automation | Playwright | Website testing, browser workflows, screenshots | In catalog — `reviewed`; installation and runtime testing remain pending |
| Performance / accessibility diagnostics | Lighthouse; axe-core | SEO and web quality checks | Both in catalog (`tested`); fixture audits passed; distinguish lab metrics from field data |

## Per-Skill mapping

| Personal-AI-Library Skill | Required capability | Candidate tools / services to investigate | AI-Toolbox state / notes |
|---|---|---|---|
| `python-development` | Python runtime, isolated environments, linting, tests, debugging | Python, `venv`/uv, pytest, Ruff, mypy | Python, uv, and pytest in catalog (`tested`); Ruff and mypy in catalog (`tested`); prefer standard library where sufficient |
| `code-audit` | Static inspection and syntax/AST checks | Existing Skill AST script; Ruff; Bandit; Semgrep | Candidate tools need separate review; local AST script is already in the Skill repo, not a toolbox software record |
| `web-development` | HTML/CSS/JS workflow, local server, browser testing, build tools | Playwright; Node.js/npm; Vite only when project needs a build step | Playwright in catalog (`tested`); Node.js in catalog (`tested`); Vite only when project needs a build step |
| `devops-vps` | Remote Linux diagnostics, service/container/log inspection | OpenSSH, `ssh`, `journalctl`, systemd tools, Docker/Podman, `curl` | Mostly OS-native tools; avoid installing a second admin stack without need |
| `automation-vps` | API clients, webhook testing, scheduling, state and retries | Python HTTP clients; `curl`; Postman/Insomnia; n8n only for visual workflow needs | Candidate; external API access and credentials require explicit scope |
| `telegram-bots` | Telegram Bot API integration and webhook/polling | aiogram or python-telegram-bot (choose by existing project/version); Telegram Bot API | Candidate; never mix incompatible SDK major versions |
| `max-bots` | MAX platform API integration | Official MAX Bot API/docs and an HTTP client or supported SDK if available | Needs current official API verification; do not assume Telegram compatibility |
| `github-portfolio` | Git operations, repo metadata, Pages and release workflow | Git; GitHub CLI; GitHub Actions; existing GitHub connector | Git in catalog (`tested`); GitHub CLI remains a candidate; Actions and connector are hosted capabilities |
| `social-media` | Drafting and platform-specific publishing workflow | Native Telegram, X and GitHub interfaces/APIs | Built-in / service; drafts first, publishing only after approval; no third-party scheduler assumed |
| `content-planning` | Calendar and editorial workflow | Spreadsheet (Google Sheets or LibreOffice Calc); calendar service | LibreOffice is in catalog (`tested`); calendar remains service/task-specific; no dedicated app needed for a simple calendar |
| `crypto-research` | Market research, historical data, reproducible analysis | Exchange public APIs; CCXT for supported exchanges; Python/pandas | Candidate; use read-only/public endpoints, verify data provenance and terms |
| `crypto-market-analysis` | Market data, charts, indicators and funding/open-interest inputs | Exchange public market APIs; CCXT; pandas; plotting library | Candidate; data-source coverage and timestamps must be explicit |
| `crypto-futures-risk` | Position sizing, leverage and liquidation/risk calculations | Python standard library / decimal; spreadsheet for independent cross-check | Built-in / lightweight; avoid paid trading terminals unless a concrete gap exists |
| `trading-bot-audit` | Log/DB parsing, execution and PnL reconciliation | Python; SQLite tools; pandas; SQL client appropriate to actual DB | Candidate; read-only audit first, never enable order permissions |
| `product-marketing` | Research, positioning and evidence-backed claims | Browser/search; spreadsheet; document editor | Mostly built-in capabilities; no dedicated software justified yet |
| `marketing-copywriting` | Drafting, editing and factual review | Document editor; spell/style checker if needed | Mostly built-in; optional checker only after language and privacy review |
| `seo-audit` | Crawl, metadata, performance and accessibility checks | Playwright; Lighthouse; Google Search Console; PageSpeed Insights; axe-core | Playwright (`reviewed`), Lighthouse (`reviewed`), and axe-core (`reviewed`) in catalog; Search Console and PageSpeed Insights are external services |
| `business-kwork` | Requirements, estimation, deliverables and handover | Issue/project tracker; spreadsheet; document editor | Needs task-specific decision; avoid prescribing paid project-management software |
| `research-fact-checking` | Source discovery, repository/license review and evidence capture | Browser/search; Git; GitHub API/CLI; license scanners such as ScanCode | Mostly built-in plus candidates; scanners require separate provenance/accuracy review |
| `product-images` | Image inspection, batch conversion, background removal and metadata | GIMP; ImageMagick; ExifTool; rembg (where suitable) | ImageMagick, ExifTool, GIMP, and rembg in catalog (`tested`); GIMP and rembg remain candidates |
| `marketplace-listings` | Image preparation, listing copy and structured product data | Image tools above; spreadsheet; native marketplace interfaces | ImageMagick, ExifTool, GIMP, and rembg (`tested`) in catalog; native marketplace interfaces remain service-specific; no universal uploader recommended |
| `google-sheets` | Sheets API and Apps Script automation | Google Sheets / Apps Script; clasp for local Apps Script development | External service; OAuth scopes, quotas and account permissions matter |
| `documents-office` | DOCX/XLSX/PPTX/PDF read/write, conversion, OCR and validation | LibreOffice; Pandoc; Poppler; Tesseract; format-specific Python libraries | LibreOffice, Pandoc, Poppler, and Tesseract in catalog (`tested`); choose per format; macro and formula fidelity still require task-specific tests |

## Current coverage and remaining work

The catalog now contains **21 tool records — all 21 are `tested`**. There are currently no `reviewed` or `candidate` entries.

The catalog covers source control, Python development and quality checks, JavaScript runtime, browser testing and audits, document conversion/OCR, image processing and metadata, background removal, media processing, and HTTP/JSON API utilities.

`tested` means a documented installation and/or runtime smoke test passed in the specific environment described in that tool's record. It does **not** mean the tool is installed on a user's computer, nor does a smoke test prove every feature or platform works. Check each record for the exact scope and limitations.

Remaining research priorities:

1. **API and automation utilities:** compare HTTP clients/testing tools and optional n8n against existing Python and OS-native capabilities.
2. **Data analysis:** validate pandas and a plotting stack; investigate CCXT only after defining exchange and data requirements.
3. **Platform-specific SDKs:** choose Telegram SDK and MAX API tooling only when an actual project requires them.
4. **VPS/container operations:** assess Docker/Podman and SSH diagnostics only against a concrete deployment or administration workflow.
5. **Security/code audit:** evaluate Bandit, Semgrep, and license scanners when a project requires deeper static or supply-chain analysis.

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
