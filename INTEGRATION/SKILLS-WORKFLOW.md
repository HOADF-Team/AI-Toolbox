# Skills integration

This repository is the tool inventory and verification layer for the organization's Skills.

- Skills describe workflows and decision rules: [HOADF-Team/Personal-AI-Library](https://github.com/HOADF-Team/Personal-AI-Library) (**25 Skills on main**).
- Tool records describe concrete software, provenance, licenses, installation requirements, verification evidence and limitations.
- The [Skill → Tool map](../CATALOG/SKILL-MAP.md) connects Skills to relevant tool capabilities.
- The machine-readable [Skill dependency map](../CATALOG/skill-tools.json) and [preflight checker](../scripts/check_skill_tools.py) compare declared prerequisites with current-runtime inventory evidence.
- Run the complete non-mutating preflight with one command: `python scripts/run_skill_preflight.py --skill crypto-security --pretty`.
- For multi-Skill tasks, use the reusable [declarative handoff protocol](HANDOFF-PROTOCOL.md) and `scripts/validate_handoff_chain.py`.

## Required behavior

For each task, select only relevant Skills and inspect their instructions. Run the one-command preflight in the actual execution target, then review the report's inventory evidence, catalog matches, and required prerequisite groups. Treat recommended tools as advisory. Inspect matching Toolbox records, verify version/platform compatibility, and perform task-specific checks before relying on a tool. A catalog status or CI result does not prove availability on the user's device. Reuse suitable installations; review source/license/security before adding dependencies; obtain approval for paid or externally visible actions; and record evidence honestly.

The preflight does not install software, intentionally change configuration, make network requests itself, scan remote hosts, or execute Skill workflows. It does execute detected PATH binaries with fixed version/help arguments; those binaries are not sandboxed and may have tool-specific side effects or network behavior. Run it only in a trusted environment with a trusted `PATH`. Python modules are checked with `find_spec`; Node packages are resolved without loading package code. It reports only the process environment in which it runs. A detected executable/module is not proof of functional correctness, credentials, or external service access.

## Multi-Skill handoffs

Use a declarative contract to define ordered stages, required fields, evidence requirements, artifact references, and domain-specific rules. Each stage emits a JSON artifact; the next stage consumes the preceding output reference. The generic validator checks the chain and writes an auditable report. The synthetic reference contract is in `TESTS/fixtures/inter-skill-demo/`.

This validates contract structure only. It does not execute Skills or an LLM, prove reasoning quality, carry out incident response, execute fixture code, install fixture dependencies, connect over SSH, access a VPS, or change production. Credential revocation and host isolation in the reference scenario are recommendations only; positions and orders are not automatically liquidated or cancelled.

Do not store credentials, customer data, proprietary product source code or private project assets in this public repository. Keep this repository focused on reusable tool metadata and approved generic test procedures.
