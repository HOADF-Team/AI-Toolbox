# Schemathesis

- **ID:** `schemathesis`
- **Category:** api-tooling
- **Status:** `reviewed`
- **Publisher / maintainer:** Schemathesis project; upstream repository maintained by the Schemathesis team
- **Official website:** https://schemathesis.readthedocs.io/
- **Source repository:** https://github.com/schemathesis/schemathesis
- **Documentation:** https://schemathesis.readthedocs.io/
- **License:** MIT
- **Platforms:** Windows, Linux, macOS; Python package and CLI
- **Version reviewed:** 4.33.1
- **Python requirement:** 3.11 or later
- **Last reviewed:** 2026-11-26

## What it does

Schemathesis generates property-based tests from API descriptions and exercises a running API with examples, boundary values, and generated inputs. It checks for server errors, undocumented responses, and response-schema violations. It can chain related operations into stateful workflows and produces reproducible `curl` commands for failures.

Supported interfaces include a command-line runner, a Python API, and pytest integration. Current upstream documentation lists OpenAPI 2.0, 3.0, 3.1, and 3.2, GraphQL, and unary gRPC.

## Relationship to existing tools

- **Redocly CLI** remains the primary tool in this catalog for OpenAPI linting, bundling, documentation, and explicitly authored Arazzo workflows.
- **Schemathesis** complements it by generating many request variations from the schema and exploring edge cases without requiring a hand-written test for each input.
- **curl/jq** remain useful for manual HTTP calls and JSON inspection.

Do not add Vacuum as a second OpenAPI linter by default: its main linting role overlaps with the already tested Redocly CLI. Reconsider it only if a project needs a specific Vacuum ruleset or capability that Redocly does not provide.

## When an AI agent should use it

Use Schemathesis when a project has an OpenAPI/GraphQL schema and a disposable local or staging API that can safely receive generated requests. It is particularly useful after basic contract linting, when manually written happy-path tests do not cover boundary and malformed inputs.

Typical workflow:

1. Review the OpenAPI schema and identify all operations and side effects.
2. Start a local fixture or authorized staging instance.
3. Run a bounded test session, for example:

   ```bash
   uvx --from schemathesis==4.33.1 schemathesis run openapi.yaml --url http://127.0.0.1:8000 --max-examples 50
   ```

4. Inspect every finding, reproduce it with the emitted `curl` command or saved test case, and distinguish application defects from inaccurate API descriptions.
5. Use a longer fuzzing session only after the target, data reset strategy, rate limits, and allowed operations are understood.

## Requirements, installation, and cost

- **Runtime:** Python 3.11 or later.
- **Dependencies:** installs its Python dependency set, including Hypothesis and HTTP tooling; use an isolated virtual environment or `uvx`.
- **Installation:** `uv tool install schemathesis==4.33.1`, `uvx --from schemathesis==4.33.1 schemathesis ...`, or a pinned project dependency.
- **Removal:** `uv tool uninstall schemathesis` for a uv tool installation, or remove it from the project's dependency manifest and environment.
- **Account/API key:** none for local unauthenticated APIs; target-specific authentication may be required.
- **Cost:** MIT-licensed open-source package; no license fee for the CLI.
- **Network:** package installation needs package-index access. Runtime testing sends HTTP requests to the configured target.
- **Permissions:** reads schema/configuration and sends generated requests. API operations may create, update, or delete data depending on the schema and implementation.

## Safety and limitations

- Never point generated tests at production by default. Schemathesis can send state-changing requests and many generated inputs; use a disposable local fixture or explicitly authorized staging target.
- Bound runs with `--max-examples` or time limits; respect rate limits and isolate test data.
- Review the schema before testing. A schema may describe destructive operations, and generated requests are not inherently safe.
- Authentication credentials must be supplied through protected environment/CI secrets; never commit tokens or place them in public command logs.
- A passing run only covers the selected schema, checks, phases, test budget, and target state. It does not prove security, authorization correctness, or exhaustive correctness.
- GraphQL and gRPC features have protocol-specific requirements; the base install does not imply every optional protocol dependency is installed.
- Schemathesis is not a replacement for OpenAPI linting, manual authorization review, load testing, or monitoring.

## Verification

- **Review date:** 2026-11-26.
- **Source/license review:** upstream repository, project documentation, package metadata, and MIT license reviewed.
- **Installation test:** pending isolated GitHub Actions run.
- **Runtime test:** pending local HTTP fixture test in GitHub Actions.
- **Status:** `reviewed`; do not treat as installed or runtime-tested until the workflow passes.

## Sources

- Official introduction and supported protocols: https://schemathesis.readthedocs.io/en/stable/
- Official quick start and local API usage: https://schemathesis.readthedocs.io/en/stable/quick-start/
- Official CLI tutorial and bounded fuzzing options: https://schemathesis.readthedocs.io/en/stable/tutorials/cli/
- Upstream repository and MIT license: https://github.com/schemathesis/schemathesis
- Upstream package metadata: https://github.com/schemathesis/schemathesis/blob/master/pyproject.toml
