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
| Source control and repository operations | Git; GitHub CLI (`gh`) | GitHub portfolio, code review, deployment, releases, issue workflows | Candidate; verify separately from GitHub connector capabilities |
| General scripting/runtime | Python; Node.js | Python, audits, API clients, automation, browser tooling | Candidate; versions must be selected per project |
| HTTP/API diagnostics | `curl`; `jq`; OpenAPI tooling | API integrations, webhooks, research, troubleshooting | Candidate; command-line utilities, no credentials in logs |
| Containerized isolation | Docker / Podman | Disposable test environments and VPS deployment | Candidate; not required for every task |
| Browser automation | Playwright | Website testing, browser workflows, screenshots | **In catalog** — `reviewed`; install and runtime not tested |
| Performance / accessibility diagnostics | Lighthouse; axe-core | SEO and web quality checks | Candidate; distinguish lab metrics from field data |

## Per-Skill mapping

| Personal-AI-Library Skill | Required capability | Candidate tools / services to investigate | AI-Toolbox state / notes |
|---|---|---|---|
| `python-development` | Python runtime, isolated environments, linting, tests, debugging | Python, `venv`/uv, pytest, Ruff, mypy | Candidate; prefer standard library where sufficient |
| `code-audit` | Static inspection and syntax/AST checks | Existing Skill AST script; Ruff; Bandit; Semgrep | Candidate tools need separate review; local AST script is already in the Skill repo, not a toolbox software record |
| `web-development` | HTML/CSS/JS workflow, local server, browser testing, build tools | Playwright; Node.js/npm; Vite only when project needs a build step | Playwright in catalog; other candidates not reviewed |
| `devops-vps` | Remote Linux diagnostics, service/container/log inspection | OpenSSH, `ssh`, `journalctl`, systemd tools, Docker/Podman, `curl` | Mostly OS-native tools; avoid installing a second admin stack without need |
| `automation-vps` | API clients, webhook testing, scheduling, state and retries | Python HTTP clients; `curl`; Postman/Insomnia; n8n only for visual workflow needs | Candidate; external API access and credentials require explicit scope |
| `telegram-bots` | Telegram Bot API integration and webhook/polling | aiogram or python-telegram-bot (choose by existing project/version); Telegram Bot API | Candidate; never mix incompatible SDK major versions |
| `max-bots` | MAX platform API integration | Official MAX Bot API/docs and an HTTP client or supported SDK if available | Needs current official API verification; do not assume Telegram compatibility |
| `github-portfolio` | Git operations, repo metadata, Pages and release workflow | Git; GitHub CLI; GitHub Actions; existing GitHub connector | Candidate / built-in overlap; connector may already cover API actions |
| `social-media` | Drafting and platform-specific publishing workflow | Native Telegram, X and GitHub interfaces/APIs | Built-in / service; drafts first, publishing only after approval; no third-party scheduler assumed |
| `content-planning` | Calendar and editorial workflow | Spreadsheet (Google Sheets or LibreOffice Calc); calendar service | Built-in / service; no dedicated app needed for a simple calendar |
| `crypto-research` | Market research, historical data, reproducible analysis | Exchange public APIs; CCXT for supported exchanges; Python/pandas | Candidate; use read-only/public endpoints, verify data provenance and terms |
| `crypto-market-analysis` | Market data, charts, indicators and funding/open-interest inputs | Exchange public market APIs; CCXT; pandas; plotting library | Candidate; data-source coverage and timestamps must be explicit |
| `crypto-futures-risk` | Position sizing, leverage and liquidation/risk calculations | Python standard library / decimal; spreadsheet for independent cross-check | Built-in / lightweight; avoid paid trading terminals unless a concrete gap exists |
| `trading-bot-audit` | Log/DB parsing, execution and PnL reconciliation | Python; SQLite tools; pandas; SQL client appropriate to actual DB | Candidate; read-only audit first, never enable order permissions |
| `product-marketing` | Research, positioning and evidence-backed claims | Browser/search; spreadsheet; document editor | Mostly built-in capabilities; no dedicated software justified yet |
| `marketing-copywriting` | Drafting, editing and factual review | Document editor; spell/style checker if needed | Mostly built-in; optional checker only after language and privacy review |
| `seo-audit` | Crawl, metadata, performance and accessibility checks | Playwright; Lighthouse; Google Search Console; PageSpeed Insights; axe-core | Playwright in catalog; others candidates/services with distinct scopes |
| `business-kwork` | Requirements, estimation, deliverables and handover | Issue/project tracker; spreadsheet; document editor | Needs task-specific decision; avoid prescribing paid project-management software |
| `research-fact-checking` | Source discovery, repository/license review and evidence capture | Browser/search; Git; GitHub API/CLI; license scanners such as ScanCode | Mostly built-in plus candidates; scanners require separate provenance/accuracy review |
| `product-images` | Image inspection, batch conversion, background removal and metadata | GIMP; ImageMagick; ExifTool; rembg (where suitable) | Candidates; image tools have different functions and licensing/models |
| `marketplace-listings` | Image preparation, listing copy and structured product data | Image tools above; spreadsheet; native marketplace interfaces | Mostly built-in / service; no universal marketplace uploader recommended |
| `google-sheets` | Sheets API and Apps Script automation | Google Sheets / Apps Script; clasp for local Apps Script development | External service; OAuth scopes, quotas and account permissions matter |
| `documents-office` | DOCX/XLSX/PPTX/PDF read/write, conversion, OCR and validation | LibreOffice; Pandoc; Poppler; Tesseract; format-specific Python libraries | Candidates; choose per format; macro and formula fidelity must be tested |

## Priority order for adding records

The order below is based on reuse across Skills and the likelihood of providing a concrete capability. It is a research queue, not an approval to install.

1. **Core developer utilities:** Git, Python environment tooling, pytest, Ruff, Node.js — document only those not already available in the execution environment.
2. **Web quality stack:** Lighthouse and axe-core, complementing Playwright.
3. **Document conversion and inspection:** LibreOffice, Pandoc, Poppler and Tesseract; evaluate separately because they solve different tasks.
4. **Image utilities:** ImageMagick and ExifTool first; evaluate GIMP/rembg only for workflows that need them.
5. **API and automation utilities:** HTTP client/testing tool and optional n8n; compare against simple Python scripts before adding.
6. **Data analysis:** pandas and a plotting stack; CCXT only after defining supported exchange/data needs.
7. **Platform-specific SDKs:** Telegram SDK choice and MAX API tooling only when an actual project requires them.

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
