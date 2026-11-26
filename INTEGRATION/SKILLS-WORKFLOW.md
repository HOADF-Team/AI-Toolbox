# Skills integration

This repository is the tool inventory and verification layer for the organization's Skills.

- Skills describe workflows and decision rules: [HOADF-Team/Personal-AI-Library](https://github.com/HOADF-Team/Personal-AI-Library).
- Tool records describe concrete software, provenance, licenses, installation requirements, verification evidence and limitations.
- The [Skill → Tool map](../CATALOG/SKILL-MAP.md) connects the 23 actual Skills to relevant tool capabilities.
- The authoritative operating procedure is maintained in [Personal-AI-Library: AI agent workflow](https://github.com/HOADF-Team/Personal-AI-Library/blob/main/INTEGRATION/AI-AGENT-WORKFLOW.md).

## Required behavior

For each task, select only relevant Skills, inspect their instructions, then consult the matching Toolbox records. Verify the tool in the actual execution environment; a catalog status does not prove local installation or availability. Reuse suitable installed tools, review source/license/security before adding dependencies, request approval for paid or externally visible actions, and record test evidence honestly.

Do not store credentials, customer data, proprietary product source code or private project assets in this public repository. Keep this repository focused on reusable tool metadata and approved generic test procedures.
