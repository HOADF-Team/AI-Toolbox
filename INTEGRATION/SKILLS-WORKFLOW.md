# Skills integration

This repository is the tool inventory and verification layer for the organization's Skills.

- Skills describe workflows and decision rules: [HOADF-Team/Personal-AI-Library](https://github.com/HOADF-Team/Personal-AI-Library) (**25 Skills on main**).
- Tool records describe concrete software, provenance, licenses, installation requirements, verification evidence and limitations.
- The [Skill → Tool map](../CATALOG/SKILL-MAP.md) connects Skills to relevant tool capabilities.
- The machine-readable [Skill dependency map](../CATALOG/skill-tools.json) and [preflight checker](../scripts/check_skill_tools.py) compare declared prerequisites with current-runtime inventory evidence.
- Run the complete non-mutating preflight with one command: `python scripts/run_skill_preflight.py --skill crypto-security --pretty`.
- The deterministic inter-Skill handoff contract is validated with `python scripts/validate_inter_skill_workflow.py --scenario TESTS/fixtures/inter-skill-demo/scenario.json --handoff-dir TESTS/fixtures/inter-skill-demo/handoffs`.
- The authoritative detailed operating procedure is maintained in [Personal-AI-Library: AI agent workflow](https://github.com/HOADF-Team/Personal-AI-Library/blob/main/INTEGRATION/AI-AGENT-WORKFLOW.md).

## Required behavior

For each task, select only relevant Skills and inspect their instructions. Run the one-command preflight in the actual execution target, then review the report's inventory evidence, catalog matches, and required prerequisite groups. Treat recommended tools as advisory. Inspect matching Toolbox records, verify version/platform compatibility, and perform task-specific checks before relying on a tool. A catalog status or CI result does not prove availability on the user's device. Reuse suitable installations; review source/license/security before adding dependencies; obtain approval for paid or externally visible actions; and record evidence honestly.

The preflight does not install software, intentionally change configuration, make network requests itself, scan remote hosts, or execute Skill workflows. It does execute detected PATH binaries with fixed version/help arguments; those binaries are not sandboxed and may have tool-specific side effects or network behavior. Run it only in a trusted environment with a trusted `PATH`. Python modules are checked with `find_spec`; Node packages are resolved without loading package code. It reports only the process environment in which it runs. A detected executable/module is not proof of functional correctness, credentials, or external service access.

## Deterministic handoff contract

The inter-Skill fixture models the sequence `crypto-security → code-audit → python-development → devops-vps` through explicit JSON input/output references. The validator checks order, linked artifacts, evidence locations, secret redaction, recommendation ordering, and prohibited automatic actions. Each stage's output is synthetic fixture data, not a live Skill result.

This is a contract test, not an LLM orchestrator or a claim that Skills were executed. It does not validate reasoning quality, carry out incident response, execute code, install fixture dependencies, connect over SSH, access a VPS, or change production. In particular, credential revocation and host isolation are recommendations only; positions and orders are not automatically liquidated or cancelled.

Do not store credentials, customer data, proprietary product source code or private project assets in this public repository. Keep this repository focused on reusable tool metadata and approved generic test procedures.
