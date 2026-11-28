# Skill interface contracts

## Purpose

`CATALOG/skill-interfaces.json` describes draft input/output artifact types and possible side-effect classes for Skills. It is separate from the tool map and workflow catalog:

- `skill-tools.json`: tool prerequisites and recommendations;
- `skill-interfaces.json`: what data a Skill may accept and produce;
- `workflows.json`: ordered stages and their connections.

## Status and evidence

The initial four interfaces are `draft` hypotheses derived from canonical `SKILL.md` files at Personal-AI-Library revision `b2c98066d7ea620d22ba814f44617ab5f70b4b3c`. They are not schemas promised by the Skills, and no live runtime has verified that a model emits these artifacts. Promote an interface to `reviewed` only after a separate review of its field-level contract and representative positive/negative fixtures.

Artifact type identifiers use normalized dotted names. A stage may consume only:
1. an artifact type declared in its Skill's `accepts`;
2. an external input explicitly listed by the workflow; and
3. an artifact type supplied by an earlier stage.

No forward references, implicit coercion, or automatic insertion of missing stages is allowed.

## Side effects and authorization

`possible_side_effects` is risk metadata only. It does not authorize an action. `permission_gates` names actions that require separate explicit user authorization in the host runtime. A stage selection or successful compatibility check never grants those permissions.

## Validation

```bash
python scripts/validate_skill_interfaces.py --pretty
python scripts/validate_workflow_compatibility.py --pretty
python -m unittest TESTS.test_skill_interfaces -v
```

The compatibility function is currently a library API, not an execution adapter. It checks artifact type labels only; field-level JSON Schema validation, provenance verification, and runtime conformance tests are future work.
