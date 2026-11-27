# Agent instructions for AI-Toolbox

## Mission

Maintain a practical collection of real tools that AI agents can discover, install, verify, and use. The collection complements Personal-AI-Library: Skills describe workflows; this repository describes concrete tools and their verified usage.

## Before searching or adding

1. Search `CATALOG/tools.json` and existing `TOOLS/` records for an equivalent tool.
2. Read the existing tool record and check whether its status and compatibility fit the current task.
3. Identify the actual execution target and run the non-mutating [environment discovery procedure](TESTS/ENVIRONMENT-DISCOVERY.md) when possible. It executes fixed version/help probes for detected PATH binaries, so use only a trusted PATH.
4. Distinguish a catalog record, an executable/module in the current runtime, software on the user's device, and a connector/hosted service. These are not interchangeable.
5. Reuse a suitable existing installation; do not reinstall solely because a catalog record exists.
6. Prefer official upstream sources and documentation.
7. Do not add a tool merely because it is popular. Explain the concrete capability or gap it addresses.

## Research and review requirements

For every candidate, record:

- canonical name and stable ID;
- official project and download/documentation URLs;
- publisher/maintainer and source repository where applicable;
- license and redistribution constraints (do not guess);
- supported operating systems and architectures, if known;
- runtime, dependencies, external services, accounts, API keys, and costs;
- installation and removal approach;
- permissions, network access, telemetry, and relevant security considerations;
- test environment, date, exact checks performed, and observed result;
- known limitations and a clear verification status.

If a fact cannot be verified, write `unknown` or `not checked`; do not infer it.

## Installation and execution safety

- Do not run an unknown installer, shell script, binary, container, or remote command before reviewing its source, origin, and expected effects.
- Prefer official package managers, signed releases, checksums, pinned versions, and isolated environments when available.
- Test in a disposable VM, container, sandbox, or separate test account where practical.
- Do not run with administrator/root privileges unless strictly required and explicitly justified.
- Never disable security controls to make a tool work.
- Never expose or commit tokens, passwords, private keys, cookies, credentials, or personal data.
- Do not make purchases, create paid subscriptions, publish externally, or modify production systems without explicit user approval.
- Do not install software on the user's machine unless the user has asked for installation and the target environment is clear.

## Contribution workflow

1. Create or update one focused tool record under `TOOLS/<category>/<tool-id>/TOOL.md`.
2. Update `CATALOG/tools.json` consistently.
3. Include evidence and a repeatable test procedure.
4. Run repository validation if available; do not claim tests that were not run.
5. Submit changes through a pull request. Do not push directly to the default branch unless the repository owner has explicitly established that workflow.
6. A reviewer must be able to distinguish research, review, testing, and readiness.

## Status rules

- `discovered`: candidate found, not yet reviewed.
- `reviewed`: source, license, requirements, and risks reviewed.
- `tested`: at least one documented test actually ran; environment and results recorded.
- `ready`: repeatable installation/use/check instructions are available and tested within the stated scope.
- `blocked`: a specific issue prevents safe or reliable use.
- `deprecated`: no longer recommended; explain why and, where possible, name a replacement.

Never upgrade a status based only on reading a README or seeing that a GitHub repository exists.

## Quality

- Keep records concise, practical, and understandable to non-programmers.
- Prefer one record per distinct tool, not one record per vague technology category.
- Do not duplicate Skills. Link to relevant Skills where useful.
- Keep upstream code upstream unless redistribution is permitted and genuinely needed.
- Record dates in ISO format (`YYYY-MM-DD`).


## Personal-AI-Library integration

Use the organization's Skills as task workflows and this repository as the tool inventory. The shared operating procedure is documented in [INTEGRATION/SKILLS-WORKFLOW.md](INTEGRATION/SKILLS-WORKFLOW.md), with the authoritative detailed workflow in [Personal-AI-Library](https://github.com/HOADF-Team/Personal-AI-Library/blob/main/INTEGRATION/AI-AGENT-WORKFLOW.md). Select only relevant Skills, verify tools in the actual target environment, and record evidence. A catalog status never proves that software is installed on a user's device.
