# Mockoon CLI

- **ID:** `mockoon-cli`
- **Category:** api-mocking
- **Status:** `tested`
- **Publisher / maintainer:** Mockoon (1kB SARL-S)
- **Official website:** https://mockoon.com/cli/
- **Source repository:** https://github.com/mockoon/mockoon
- **Documentation:** https://github.com/mockoon/mockoon/tree/main/packages/cli
- **License:** MIT
- **Platforms:** Windows, Linux, macOS through Node.js; official Docker image and GitHub Action are also available
- **Version reviewed:** 9.10.0
- **Node.js requirement:** >=18; upstream CLI documentation reports testing on Node.js 18, 20, 22, and 24
- **Last reviewed:** 2026-11-26

## What it does

Mockoon CLI runs local mock HTTP APIs for frontend development, integration testing, and CI. It can start a server from a native Mockoon environment file or directly from an OpenAPI 2.0 / 3.0 YAML or JSON document. It can also import an OpenAPI document into a native Mockoon data file, validate native data files, export OpenAPI, and generate a Dockerfile.

The CLI includes an MCP server. Its MCP tools can list local Mockoon files, start mock servers, stop them, and list running mocks. This can let an AI coding agent manage disposable local mock APIs through an MCP-compatible client.

## Relationship to existing API tools

- **Redocly CLI** checks specification quality, bundles descriptions, generates docs, and runs explicitly authored Arazzo workflows.
- **Schemathesis** sends generated property-based requests to a running API and validates its responses.
- **Mockoon CLI** provides the mock API server itself, so developers and agents can test clients before a real backend exists.
- **curl/jq** remain useful for direct HTTP calls and JSON inspection.

Mockoon's OpenAPI import is intentionally partial. It imports API metadata, servers, routes, methods, response status codes, headers, descriptions, and sample response bodies/examples, but not every OpenAPI feature. Generated mock values may not reproduce a media-type example exactly. For full Mockoon templating and response rules, use a native Mockoon data file. Do not treat a successful import as proof of complete OpenAPI fidelity.

Prism is another OpenAPI-native mock server, but the reviewed Prism 5.16.0 CLI package currently declares Node.js >=26.13. Mockoon CLI 9.10.0 supports the Node.js 22 runtime already represented in this toolbox and also provides an MCP management interface, so Mockoon is the more practical candidate for this environment.

## When an AI agent should use it

Use Mockoon when a frontend, integration, or automated test needs a predictable local API without depending on a remote service, credentials, rate limits, or a completed backend.

Typical workflow:

1. Review the OpenAPI description and its operations before starting a mock.
2. Import the specification into a native Mockoon data file when more control is needed:

   ```bash
   mockoon-cli import --input openapi.yaml --output mockoon-data.json --prettify
   mockoon-cli validate --data mockoon-data.json
   ```

3. Start the local mock on loopback:

   ```bash
   mockoon-cli start --data mockoon-data.json --hostname 127.0.0.1 --port 3000 --disable-admin-api
   ```

4. Point the frontend or test client at the local mock and exercise expected responses, error cases, and latency scenarios.
5. Stop the mock when the test session ends.

For an agent that needs to manage mocks through MCP, review the configured data directories and MCP client permissions before starting the server.

## Requirements, installation, and cost

- **Runtime:** Node.js >=18; the current upstream CLI documentation lists Node.js 18, 20, 22, and 24 as tested.
- **Installation:** `npm install --global @mockoon/cli@9.10.0`; use a pinned version for reproducible CI.
- **Removal:** `npm uninstall --global @mockoon/cli`.
- **Account/API key:** not required for local mocks. Legacy Mockoon Cloud environments require a token; Mockoon Pro is a separate commercial product.
- **Cost:** the CLI is MIT-licensed and free/open source; Pro collaboration and remote deployment features are separate paid offerings.
- **Network:** npm installation requires registry access. The mock server itself can run locally without calling the real API.
- **Permissions:** reads OpenAPI or Mockoon data files, opens a local listening port, and may create logs. The MCP server can start and stop mock processes in configured directories.

## Security and limitations

- Bind local development mocks to `127.0.0.1` unless network access is explicitly required. Do not expose mock endpoints to the public internet by default.
- The Admin API is enabled by default. Disable it with `--disable-admin-api` when not needed; otherwise protect it with a strong token and restrict network access. The CLI prints an auto-generated token when none is supplied.
- The MCP server can start and stop mock servers. Restrict its configured data directories to trusted project files and only connect it to authorized MCP clients.
- Do not load untrusted OpenAPI or Mockoon files without reviewing external references and any URLs they may cause the tool to fetch.
- OpenAPI import/export compatibility is partial. The CLI does not preserve every OpenAPI feature, and advanced Mockoon response rules/templates are best stored in native Mockoon data files.
- A successful mock response does not prove that a production API behaves the same way. Mock servers do not replace Schemathesis tests against the real implementation or authorization/security review.

## Verification

- **Review date:** 2026-11-26.
- **Source/license review:** upstream CLI package metadata, README, OpenAPI compatibility documentation, official CLI documentation, and MIT license reviewed.
- **CI environment:** GitHub-hosted Ubuntu runner, Node.js 22.
- **Installation:** pinned `@mockoon/cli@9.10.0` installed successfully through npm; CLI version command completed.
- **Inventory:** `scripts/inventory.py` detected the globally installed `mockoon-cli` executable. The read-only Node package probe intentionally checks project-local modules, not global npm package stores.
- **Import/validation:** OpenAPI 3.0 fixture imported into a native Mockoon data file; `mockoon-cli validate` reported the environment valid.
- **Runtime:** Mockoon started a local HTTP mock bound to `127.0.0.1:8767`; GET `/hello` returned JSON with the schema-required string field.
- **Result:** installation, inventory, import, validation, and loopback HTTP mock checks passed. Run: https://github.com/HOADF-Team/AI-Toolbox/actions/runs/45856059607
- **Additional validation:** catalog validator and Ruff/mypy passed on the same PR revision before the inventory assertion was added; they are rerun on the final PR head.
- **Scope:** confirms the pinned CLI path and tested OpenAPI mock workflow on this CI runner only. MCP command behavior and other OpenAPI features were reviewed but not runtime-tested.
- **Status:** `tested`; see scope and limitations above.

## Sources

- Official CLI guide: https://mockoon.com/cli/
- Upstream CLI README and command reference: https://github.com/mockoon/mockoon/tree/main/packages/cli
- Upstream package metadata and engine requirement: https://github.com/mockoon/mockoon/blob/main/packages/cli/package.json
- OpenAPI compatibility limitations: https://mockoon.com/docs/latest/openapi/openapi-specification-compatibility/
- CLI release 9.10.0: https://mockoon.com/releases/9.10.0/
- Upstream repository and MIT license: https://github.com/mockoon/mockoon
