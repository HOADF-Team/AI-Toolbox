# axe-core

- **ID:** `axe-core`
- **Category:** web-testing
- **Status:** `reviewed`
- **Publisher / maintainer:** Deque Systems, Inc. / Deque Labs
- **Official website:** https://www.deque.com/axe/
- **Source repository:** https://github.com/dequelabs/axe-core
- **Documentation:** https://github.com/dequelabs/axe-core#readme
- **License:** Mozilla Public License 2.0 (MPL-2.0); bundled third-party dependencies have separate notices and licenses
- **Platforms:** Browser-based JavaScript; supported browser and DOM environment requirements are documented upstream
- **Version reviewed:** 4.14.1 (npm package metadata)
- **Last reviewed:** 2026-11-26

## What it does

axe-core is an accessibility testing engine for HTML-based user interfaces. It evaluates a rendered page against automated rules covering WCAG 2.0, 2.1, and 2.2 criteria at applicable conformance levels, plus selected accessibility best practices.

It is a JavaScript library, not a standalone desktop application or general-purpose command-line scanner.

## When an AI agent should use it

Use axe-core to add automated accessibility checks to browser tests and UI test suites. It fits naturally alongside Playwright: open the page, wait for the relevant UI state, inject or import axe-core, run the audit, and fail the test when violations exceed the project's accepted threshold.

Run checks after important interactive states appear, not only on the initial page load. For example, open navigation menus, dialogs, validation messages, tabs, and expanded mobile layouts before scanning those states.

axe-core reports issues it can detect automatically, but cannot establish full WCAG conformance. The upstream project estimates that automated checks identify an average of about 57% of WCAG issues; manual testing remains necessary. Review results marked incomplete because they require human judgement.

## Requirements and costs

- Runtime / dependencies: JavaScript in a supported browser/DOM environment; commonly installed as an npm development dependency. Integrates with Playwright and other test frameworks.
- Account required: no for the open-source library.
- API key or token required: no.
- Paid features or usage costs: axe-core is open source; separate Deque commercial products and services are optional and not required to use this library.
- Network access: not required for a local test after the package is available; npm installation requires registry access.
- Permissions: executes JavaScript against the page DOM and inspects rendered UI; it does not require a remote account.

## Installation

Use the official [axe-core repository](https://github.com/dequelabs/axe-core) and npm package. For a Playwright project, install it as a development dependency:

```bash
npm install --save-dev axe-core
```

Then use the package from a test or inject its browser bundle into the page. Follow the integration instructions for the selected Playwright language and version.

Remove it with the same project package manager (for npm, `npm uninstall axe-core`). Do not copy or redistribute modified package files without reviewing MPL-2.0 obligations and third-party notices.

## Basic usage

Example in a browser page after the axe-core script has been loaded:

```javascript
const results = await page.evaluate(async () => await axe.run(document));
if (results.violations.length > 0) {
  throw new Error(`Accessibility violations: ${results.violations.length}`);
}
```

The exact integration differs by Playwright language and fixture design. Report violations with their rule IDs, impact, affected nodes, and remediation guidance; do not reduce the output to a single pass/fail number.

## Verification

- **CI environment:** GitHub-hosted Ubuntu runner, Node.js 22.23.5, npm, Playwright Test 1.65.1, axe-core 4.14.1, Chromium 159.0.8154.6.
- **Date:** 2026-11-26.
- **Installation:** pinned axe-core package installed successfully in an isolated temporary npm project.
- **Runtime:** axe-core was injected into a locally served HTML fixture and executed through Playwright.
- **Result:** 1 passed; zero automated violations for the selected WCAG 2.0 A/AA, WCAG 2.1 A/AA, and WCAG 2.2 AA tags on this fixture.
- **Run:** https://github.com/HOADF-Team/AI-Toolbox/actions/runs/45834945677
- **Scope:** verifies this axe-core + Playwright + Chromium integration on the CI runner only. It does not establish installation in the assistant runtime or on the user's computer. Automated checks do not establish full WCAG conformance; manual evaluation remains necessary.

## Security and limitations

axe-core evaluates the DOM and page state available to the browser. It does not prove that a site is accessible to every person or assistive technology. Manual keyboard navigation, focus management, screen-reader checks, content review, and user testing remain important.

Automated scans can produce incomplete results requiring review. Keep the library reasonably up to date; its rules and results can change between releases. The package includes third-party components under their own licenses; consult the upstream third-party license notices before redistribution. Security advisories and all transitive dependencies were not exhaustively audited during this review.

## Sources

- Official project, integration examples, supported browsers, and limitations: https://github.com/dequelabs/axe-core
- Upstream releases: https://github.com/dequelabs/axe-core/releases
- npm package metadata: https://www.npmjs.com/package/axe-core
- MPL-2.0 license: https://github.com/dequelabs/axe-core/blob/develop/LICENSE
- Third-party license notices: https://github.com/dequelabs/axe-core/blob/develop/LICENSE-3RD-PARTY.txt
