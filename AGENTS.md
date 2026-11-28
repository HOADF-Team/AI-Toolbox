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

For every candidate, record canonical name and stable ID; official URLs; publisher; license; platforms; dependencies and costs; installation/removal; permissions and security; exact test environment and checks; limitations and verification status. If a fact cannot be verified, write `unknown` or `not checked`.

## Installation and execution safety

- Review unknown installers and binaries before execution; prefer official sources, pinned versions, checksums and isolated environments.
- Do not use root/admin unless necessary and justified.
- Never expose or commit credentials, private keys, cookies or personal data.
- Do not purchase, publish externally or modify production without explicit approval.
- Do not install software on the user's machine unless asked and the target is clear.
- Never execute the intentionally vulnerable inter-Skill fixture or install its requirements. Use only its JSON and source text as inert test data.
- Treat `validate_inter_skill_workflow.py` as a deterministic contract checker, not an LLM/Skill executor or production incident-response tool.
- Never represent a recommendation to revoke a credential or isolate a host as an action actually performed. Never liquidate positions or cancel orders automatically.

## Contribution workflow

1. Update one focused tool record and catalog entry where applicable.
2. Include evidence and a repeatable test procedure.
3. Run repository validation; do not claim tests that were not run.
4. Submit changes through a pull request; do not push directly to the default branch.
5. Distinguish research, review, testing and readiness.

## Status rules

- `discovered`: candidate found, not reviewed.
- `reviewed`: source, license, requirements and risks reviewed.
- `tested`: at least one documented test actually ran.
- `ready`: repeatable instructions are available and tested within the stated scope.
- `blocked`: a specific issue prevents safe or reliable use.
- `deprecated`: no longer recommended; explain why.

Never upgrade status based only on a README or repository listing.

## Personal-AI-Library integration

Use the organization's Skills as task workflows and this repository as the tool inventory. The shared procedure is in [INTEGRATION/SKILLS-WORKFLOW.md](INTEGRATION/SKILLS-WORKFLOW.md); the authoritative detailed workflow is in [Personal-AI-Library](https://github.com/HOADF-Team/Personal-AI-Library/blob/main/INTEGRATION/AI-AGENT-WORKFLOW.md). Select relevant Skills, verify tools in the actual target environment, and record evidence. A catalog status never proves software is installed on a user's device.
