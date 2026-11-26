# jq

- **ID:** `jq`
- **Category:** networking
- **Status:** `tested`
- **Publisher / maintainer:** jqlang project
- **Official website:** https://jqlang.org/
- **Source repository:** https://github.com/jqlang/jq
- **Documentation / manual:** https://jqlang.org/manual/
- **License:** MIT for jq code; documentation is CC-BY-3.0; bundled decNumber code is ICU 1.8.1 licensed
- **Platforms:** Linux, macOS, Windows
- **Version reviewed:** 1.8.2 (released 2026-06-20)
- **Runtime version tested:** jq-1.7 in the current isolated assistant runtime
- **Last reviewed:** 2026-11-26

## What it does

jq is a command-line JSON processor. It parses JSON and provides a compact language for selecting fields, filtering arrays, transforming objects, aggregating values, and producing normalized output.

## When an AI agent should use it

Use jq to:
- extract fields from API responses;
- filter and reshape arrays of objects;
- validate expected response properties;
- combine curl output with deterministic JSON processing;
- inspect JSON configuration and tool outputs.

Use a schema validator such as an OpenAPI/JSON Schema tool when structural contract validation is required; jq expressions alone are not a full schema-validation system.

## Requirements and costs

- Runtime: native jq executable; no Python or Node.js required.
- Account / API key: not required.
- Cost: open source; no per-request fee.
- Network: not required; commonly processes data piped from curl or files.
- Dependencies: official project describes jq as having no runtime dependencies; review bundled component notices when redistributing binaries.

## Installation

Debian / Ubuntu:

```bash
sudo apt-get update
sudo apt-get install jq
```

macOS (Homebrew):

```bash
brew install jq
```

Windows (winget):

```powershell
winget install jqlang.jq
```

Verify:

```bash
jq --version
```

## Basic usage

Extract a property:

```bash
curl --fail --silent --show-error https://api.example.com/user | jq -r '.name'
```

Filter an array:

```bash
jq '[.items[] | select(.active == true) | {id, name}]' response.json
```

Validate that a property exists and has the expected value:

```bash
jq -e '.status == "ok" and (.items | type == "array")' response.json
```

## Verification

- **Current isolated runtime:** Debian-based Linux x86_64; jq 1.7 available at `/usr/bin/jq`.
- **Local functional test:** parsed JSON returned by a local HTTP fixture; extracted and joined array values; all assertions passed.
- **CI test:** workflow reinstalls jq from the Ubuntu package repository and validates JSON received from a local HTTP fixture, including jq exit-status behavior for a boolean assertion.
- **Status scope:** these checks verify the tested Linux runtime and package only. They do not establish availability on the user's computer or verify every jq feature.

## Security and limitations

- jq parses input; it does not make untrusted JSON trustworthy. Validate types, ranges, and required fields before using values in privileged operations.
- Avoid interpolating untrusted strings into jq program source. Pass values with `--arg` / `--argjson`.
- Do not use `eval` or shell execution on values extracted from JSON.
- jq is not a full OpenAPI or JSON Schema validator.
- Large JSON inputs and expensive recursive filters can consume significant memory and CPU.

## Sources

- Official project and release information: https://jqlang.org/
- Official download and installation guidance: https://jqlang.org/download/
- Official manual: https://jqlang.org/manual/
- Source repository and license: https://github.com/jqlang/jq
