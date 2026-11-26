# Redocly CLI

- **ID:** `redocly-cli`
- **Category:** api-tooling
- **Status:** `reviewed`
- **Publisher / maintainer:** Redocly, Inc.
- **Official website:** https://redocly.com/docs/cli/
- **Source repository:** https://github.com/Redocly/redocly-cli
- **Documentation:** https://redocly.com/docs/cli/
- **License:** MIT
- **Platforms:** Linux, macOS, Windows; Node.js CLI. Standalone binaries are also published for supported platforms.
- **Version reviewed:** 2.83.0
- **Last reviewed:** 2026-11-26

## What it does

Redocly CLI is an OpenAPI toolchain for authoring, validating, bundling, and documenting API descriptions. Its `lint` command checks OpenAPI descriptions against structural and configurable rules. The `bundle` command resolves references into a distributable description, and `build-docs` generates static API documentation.

The CLI also includes `respect`, which executes API workflows written in the Arazzo format. When an Arazzo workflow references an OpenAPI description, Respect can derive request parameters and example values from that description and validate response status codes, content types, and response bodies against the documented schemas.

## When an AI agent should use it

Use Redocly CLI when a project already has, or needs, an OpenAPI description and requires repeatable specification checks, bundling, documentation, or scenario-based API tests.

Typical workflow:

1. Run `redocly lint` against the OpenAPI entry file.
2. Fix specification and style findings; configure project-specific rules in `redocly.yaml`.
3. Use `redocly bundle` when a single-file artifact is required.
4. Describe request sequences in an Arazzo workflow and run `redocly respect` against an authorized test/staging API.
5. Keep API tests in CI and inspect the generated report when a workflow fails.

Redocly CLI is not a general-purpose interactive API client and does not automatically generate exhaustive test cases from every schema. Respect executes explicitly described Arazzo workflows; for property-based/fuzz testing, evaluate a dedicated tool such as Schemathesis separately rather than assuming this CLI provides it.

## Requirements and costs

- **Runtime:** Node.js 22.12.0 or later for Redocly CLI 2.x; npm 10.9.2 or later for the documented npm installation path.
- **Platforms:** Linux, macOS, and Windows for supported Node.js versions; standalone binaries are also available for supported architectures.
- **Account:** no account required for local open-source lint, bundle, documentation, or Respect workflows. Redocly hosted platform features are separate.
- **API key:** not required for local CLI operations; the target API may require its own credentials.
- **Cost:** open-source CLI is MIT-licensed; hosted Redocly products and infrastructure may have separate pricing.
- **Network:** package installation requires npm registry access. Respect sends requests to the API servers declared in the descriptions; local fixture tests can run entirely on loopback.
- **Permissions:** reads specification/configuration files and may write generated bundles, documentation, or reports. Respect can invoke any HTTP operation described by its workflow, including state-changing operations.

## Installation

Prefer a project-local, pinned development dependency:

```bash
npm install --save-dev @redocly/cli@2.83.0
```

Or run a pinned version without adding it to the project manifest:

```bash
npx --yes @redocly/cli@2.83.0 --version
npx --yes @redocly/cli@2.83.0 lint openapi.yaml
```

Verify the installed version:

```bash
npx redocly --version
```

Remove a project-local dependency with:

```bash
npm uninstall --save-dev @redocly/cli
```

For reproducible automation, pin the CLI version and commit the project's lockfile rather than relying on `@latest`.

## Basic usage

Lint an OpenAPI description:

```bash
npx redocly lint openapi.yaml
```

Bundle a multi-file description:

```bash
npx redocly bundle openapi.yaml --output dist/openapi.yaml
```

Build static API reference documentation:

```bash
npx redocly build-docs openapi.yaml
```

Execute an Arazzo workflow:

```bash
npx redocly respect tests/api-workflows.arazzo.yaml
```

Respect can validate response status codes, content types, and response schemas against the linked OpenAPI description. Use test credentials and a non-production server for workflows that may modify data.

## Verification

- **Review date:** 2026-11-26.
- **Sources reviewed:** official Redocly CLI documentation, installation requirements, command reference, Respect command reference, upstream repository, and MIT license.
- **Installation test:** pending isolated CI run.
- **Runtime test:** pending isolated CI run.
- **Planned test scope:** install pinned CLI 2.83.0 on a GitHub-hosted Ubuntu runner; lint a local OpenAPI 3.1 fixture; run an Arazzo workflow against a loopback-only HTTP fixture and verify the response against the OpenAPI schema.
- **Limitations:** the planned smoke test will not establish compatibility with every OpenAPI/Arazzo feature, every operating system, hosted Redocly services, or the user's computer.

## Security and limitations

- Treat OpenAPI and Arazzo files from untrusted repositories as data requiring review. Arazzo workflows can send real HTTP requests, including requests that change remote state.
- Run workflows only against systems you own or are explicitly authorized to test. Prefer disposable local fixtures or staging APIs.
- Never commit API tokens, passwords, cookies, or private keys. Use CI secret storage and narrowly scoped test credentials when authentication is unavoidable.
- Respect masks sensitive values in its output by default. Do not use `--no-secrets-masking` when secrets may be present.
- Avoid executing workflows against production systems unless the exact operations and effects have been reviewed and approved.
- Lint rules are configurable; a successful lint result means the selected rules passed, not that an API is secure or correctly implemented.
- Respect supports Arazzo 1.0.1 and only a subset of Arazzo 1.1.0 features as documented by Redocly. AsyncAPI source descriptions are not supported by Respect.
- This tool does not replace authorization testing, manual API review, load testing, or dedicated property-based API fuzzing.

## Sources

- Official CLI overview and feature set: https://redocly.com/docs/cli/
- Official installation and runtime requirements: https://redocly.com/docs/cli/installation
- Official lint command: https://redocly.com/docs/cli/commands/lint
- Official Respect command and response checks: https://redocly.com/docs/cli/commands/respect
- Official command list: https://redocly.com/docs/cli/commands
- Upstream source and MIT license: https://github.com/Redocly/redocly-cli
- npm package metadata: https://www.npmjs.com/package/@redocly/cli
