# Node.js

- **ID:** `nodejs`
- **Category:** javascript
- **Status:** `tested`
- **Publisher / maintainer:** OpenJS Foundation and Node.js contributors
- **Official website:** https://nodejs.org/
- **Source repository:** https://github.com/nodejs/node
- **Documentation:** https://nodejs.org/docs/
- **License:** MIT (Node.js license file; bundled third-party components may use other licenses)
- **Platforms:** Windows, macOS, Linux; official binary availability varies by architecture
- **Version observed in test environment:** Node.js 22.16.0; npm 10.9.2
- **Last reviewed:** 2026-11-26

## What it does

Node.js is a JavaScript runtime for command-line tools, development servers, build systems, backend services, and automation. npm is the standard package manager distributed with Node.js installers.

## When an AI agent should use it

Use Node.js when a project requires JavaScript tooling, a Node backend, npm packages, or browser automation such as Playwright. Check the project's declared Node engine range and lockfile before selecting or changing versions. Do not install Node.js merely because a project contains browser-side JavaScript.

## Requirements and costs

- Runtime / dependencies: platform-specific Node.js binary; npm is included in standard distributions.
- Account required: no for public packages; private registries may require an account.
- API key or token required: only for private registries or external services.
- Paid features or usage costs: Node.js and npm CLI are open source; registry, hosting, and third-party services may charge separately.
- Network access: not needed to run local JavaScript; required to install packages or access remote services.
- Permissions: scripts and package lifecycle hooks run with the permissions of the invoking user.

## Installation

Use the official [Node.js download page](https://nodejs.org/en/download/) and choose an appropriate supported release line for the project. Prefer an LTS release for general production use unless project compatibility requires another line. Verify with `node --version` and `npm --version`.

Removal is installation-method specific. Use the original installer or package manager; if a version manager was used, remove the selected version through that manager. Do not manually delete a system-managed installation.

## Basic usage

```bash
node --version
npm --version
node script.js
npm ci
npm test
```

Run package lifecycle scripts only after reviewing the package manifest and lockfile.

## Verification

- **Environment:** Debian GNU/Linux 13, Linux x86_64, current isolated execution container.
- **Date:** 2026-11-26.
- **Checks performed:** `node --version` reported v22.16.0; `npm --version` reported 10.9.2; executed a minimal Node.js assertion script successfully.
- **Result:** runtime startup and JavaScript execution smoke test passed.
- **Installation tested:** no; Node.js and npm were pre-existing in the environment.
- **Not tested:** package installation, native addon compilation, npm publishing, Windows/macOS installers, production server deployment.

## Security and limitations

Node.js programs and npm lifecycle scripts execute code with the caller's permissions. Review dependencies, lockfiles, install scripts, and registry configuration. Avoid installing untrusted packages globally. Node.js distributions include third-party components with their own licenses; the MIT license for Node.js does not replace those notices. Security advisories were not exhaustively audited during this review.

## Sources

- Official downloads: https://nodejs.org/en/download/
- Official documentation: https://nodejs.org/docs/
- Source repository and license: https://github.com/nodejs/node
- License file: https://github.com/nodejs/node/blob/main/LICENSE
