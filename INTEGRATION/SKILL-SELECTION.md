# Skill selection contract

## Purpose

The host AI planner decides which Skills are relevant to a task. It emits an explicit selection document; AI-Toolbox validates its structure against the workflow contract and `CATALOG/skill-tools.json` before the runtime resolves manifests and prepares envelopes.

This separation is deliberate:
- **Planner:** interprets the task and proposes Skills, order, dependencies, and a concise rationale.
- **Selection validator:** checks catalog membership, stage membership/order, rationale presence, and dependency ordering.
- **Runtime adapter:** resolves canonical Skill manifests at a pinned Personal-AI-Library commit, builds envelopes, and validates stage outputs.
- **Host agent:** reads and executes the Skill instructions. The Toolbox does not invoke an LLM.

The validator does not determine semantic relevance or prove that the planner's rationale is correct.

## Selection document

Each selection contains `workflow_id`, `task_ref`, a workflow-level `selection_rationale`, and `selected_skills`. Each selected entry contains:
- `stage_id`: exact stage identifier from the chosen workflow contract;
- `skill_id`: exact Skill ID from the catalog map;
- `rationale`: why the Skill is needed for this task;
- `depends_on`: stage IDs that must have completed first.

Entries must match the workflow contract's exact ordered stage list. Dependencies must point only to earlier stages. A planner must not silently add, omit, reorder, or substitute stages. To use a different Skill sequence, the host must select or author a separately reviewed workflow contract.

## Validate a proposal

```bash
python scripts/validate_skill_selection.py \
  --selection TESTS/fixtures/inter-skill-demo/skill-selection.json \
  --contract TESTS/fixtures/inter-skill-demo/workflow-contract.json \
  --pretty
```

A passing result means the proposal is structurally consistent with the supplied catalog and contract. It does not mean the selected Skills are semantically optimal, that their manifests are available, or that the Skills were executed.

## Safety

Selection never grants permission to install software, change configuration, access networks or remote hosts, alter production, transact financially, or perform externally visible actions. Those remain explicit host-runtime approval gates. Tool availability and functional test evidence are evaluated separately by preflight and the relevant tool checks.
