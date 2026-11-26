# Skills integration

This repository is the tool inventory and verification layer for the organization's Skills.

- Skills describe workflows and decision rules: [HOADF-Team/Personal-AI-Library](https://github.com/HOADF-Team/Personal-AI-Library).
- Tool records describe concrete software, provenance, licenses, installation requirements, verification evidence and limitations.
- The [Skill → Tool map](../CATALOG/SKILL-MAP.md) connects the 24 Skills on the integration branch (including crypto-security; PR #9 pending) to relevant tool capabilities.
- The machine-readable [Skill dependency map](../CATALOG/skill-tools.json) and [preflight checker](../scripts/check_skill_tools.py) compare declared prerequisites with current-runtime inventory evidence.
- The authoritative operating procedure is maintained in [Personal-AI-Library: AI agent workflow](https://github.com/HOADF-Team/Personal-AI-Library/blob/main/INTEGRATION/AI-AGENT-WORKFLOW.md).

## Required behavior

For each task, select only relevant Skills and inspect their instructions. Run read-only inventory in the actual execution target, match the report to catalog IDs, then use the Skill preflight to identify declared prerequisites as ready, blocked, or unknown. Treat recommended tools as advisory. Inspect matching Toolbox records, verify version/platform compatibility, and perform task-specific checks before relying on a tool. A catalog status or CI result does not prove availability on the user's device. Reuse suitable installations; review source/license/security before adding dependencies; obtain approval for paid or externally visible actions; and record evidence honestly.

Do not store credentials, customer data, proprietary product source code or private project assets in this public repository. Keep this repository focused on reusable tool metadata and approved generic test procedures.
