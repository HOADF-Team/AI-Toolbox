# Lighthouse

- **ID:** `lighthouse`
- **Category:** web-testing
- **Status:** `reviewed`
- **Publisher / maintainer:** Google Chrome team / Chromium project contributors
- **Official website:** https://developer.chrome.com/docs/lighthouse/overview/
- **Source repository:** https://github.com/GoogleChrome/lighthouse
- **Documentation:** https://github.com/GoogleChrome/lighthouse#readme
- **License:** Apache License 2.0
- **Platforms:** Windows, macOS, Linux; requires a supported Node.js runtime and Chrome/Chromium for CLI audits
- **Version reviewed:** 13.6.0 (npm package metadata and upstream release)
- **Last reviewed:** 2026-11-26

## What it does

Lighthouse audits web pages and produces reports for performance, accessibility, SEO, and best practices. It collects lab measurements and diagnostic opportunities; results depend on the test environment, page state, network conditions, device emulation, and browser version.

## When an AI agent should use it

Use Lighthouse when a task needs a repeatable technical quality report for a web page, especially performance metrics, accessibility signals, SEO checks, and best-practice diagnostics.

Choose the execution mode deliberately:

- **Chrome DevTools:** useful for a developer inspecting a page manually; Lighthouse is integrated into Chrome DevTools.
- **Node.js CLI:** useful for repeatable local or CI audits and machine-readable reports.
- **PageSpeed Insights:** hosted Google service for publicly reachable pages; do not submit private, authenticated, staging, or sensitive URLs unless the user explicitly approves sending them to the service.

Lighthouse accessibility results are not a complete WCAG conformance assessment. Pair them with axe-core and manual keyboard/screen-reader review where accessibility matters.

## Requirements and costs

- Runtime / dependencies: Node.js 22 LTS or later for the current CLI documentation; Chrome or Chromium for browser-based CLI runs.
- Account required: no for local CLI or DevTools use. Hosted services may have separate terms and quotas.
- API key or token required: not for local CLI; PageSpeed Insights API usage may require an API key depending on usage.
- Paid features or usage costs: Lighthouse is open source; local execution has no per-audit fee. Hosting and CI infrastructure may cost money.
- Network access: local page access is needed; remote pages need network access. Package installation needs registry access.
- Permissions: launches a browser and reads page content; writes report files to the selected output path. Auditing a URL sends requests to that site.

## Installation

Use the official [Lighthouse repository and CLI instructions](https://github.com/GoogleChrome/lighthouse#using-the-node-cli). Prefer a project-local development dependency with a pinned version for repeatable CI, or use a separately managed tool environment. Avoid installing globally when the project already has a suitable pinned version.

Example after reviewing the project and choosing a version:

```bash
npm install --save-dev lighthouse
npx lighthouse https://example.com/ --output html --output-path ./lighthouse-report.html
```

For a private site, run locally with an authorized browser session and do not upload the URL or report to a hosted service without approval.

Remove a project dependency with the project's package manager (for npm, `npm uninstall lighthouse`). Remove global installations using the same package manager and global prefix used to install them.

## Basic usage

```bash
lighthouse https://example.com/ --output html
lighthouse https://example.com/ --output json --output-path ./report.json
lighthouse --help
```

Review the full report, not just the category score. Scores are lab measurements, not a guarantee of real-user experience or compliance.

## Verification

- **Environment inspected:** Debian GNU/Linux 13, Linux x86_64; Node.js 22.16.0, npm 10.9.2, Chromium 144.0.7559.96 were present.
- **Date:** 2026-11-26.
- **Checks performed:** reviewed official project documentation, release information, npm metadata, and Apache-2.0 license; confirmed the CLI was not present in PATH.
- **Installation attempt:** a temporary isolated npm installation was attempted with lifecycle scripts disabled; package retrieval did not complete before the environment command timed out.
- **Runtime test:** not performed. No Lighthouse report was generated.
- **Status rationale:** reviewed, not tested. The existing Node.js and Chromium are prerequisites, not evidence that Lighthouse itself is installed or working.

## Security and limitations

Lighthouse launches a browser and navigates to the target URL. Audit only pages the operator is authorized to access. Browser execution can contact third-party resources loaded by the page. Reports may contain URLs, page text, request metadata, and diagnostic details; treat reports as potentially sensitive.

Scores can vary between runs. Use consistent device/network settings and multiple runs for comparisons. Do not treat a Lighthouse accessibility score as legal certification or a complete manual accessibility audit. Security advisories and all transitive dependencies were not exhaustively audited during this review.

## Sources

- Official project and CLI instructions: https://github.com/GoogleChrome/lighthouse
- Official Lighthouse overview: https://developer.chrome.com/docs/lighthouse/overview/
- Upstream release history: https://github.com/GoogleChrome/lighthouse/releases
- npm package metadata: https://www.npmjs.com/package/lighthouse
- Apache-2.0 license: https://github.com/GoogleChrome/lighthouse/blob/main/LICENSE
