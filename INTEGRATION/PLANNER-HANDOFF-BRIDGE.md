# Planner-to-handoff bridge

## Purpose

The provider-neutral planner returns a model decision and ordered Skill IDs. The handoff runtime requires a reviewed workflow contract with explicit stages, outputs, dependencies, constraints, and approval gates. The bridge connects those layers without inventing a workflow.

Implementation: `scripts/planner_handoff_bridge.py`.

## Preferred catalog-based entry point

Use `prepare_workflow_from_catalog()` when integrating a host runtime:

1. The host supplies the validated planner result, task, task reference, trusted local catalog path, Skill map, canonical Skills checkout path, and pinned Skills revision.
2. The bridge loads the JSON catalog using `workflow_catalog.load_workflow_catalog()`.
3. The catalog is structurally validated against `CATALOG/skill-tools.json`.
4. Only `reviewed` and `reviewed_fixture` templates are eligible; `draft` and `deprecated` entries are ignored.
5. The selected ordered Skill IDs must match exactly one eligible template.
6. The bridge validates the selection contract and prepares canonical Skill envelopes through the existing handoff runtime.
7. It returns a prepared plan. It does not invoke `execute_with_adapter()`.

The lower-level `prepare_workflow_from_planner()` remains available for callers that already supply a trusted, reviewed contract list.

## Outcomes

- `prepared`: exactly one eligible template matched, selection validation passed, and canonical manifest files were present.
- `no_matching_reviewed_workflow`: no eligible template matched. The host must ask for clarification or arrange a separately reviewed template; the bridge does not invent stages.
- `abstain` / `clarify`: no workflow plan is returned.
- Invalid data, duplicate Skills, revision mismatch, ambiguous matches, invalid catalogs, and missing manifests fail closed.

The matcher currently supports exact ordered Skill sequence equality only. It intentionally does not reorder, omit, append, or substitute Skills.

## Trust and safety boundaries

The host must verify that the catalog and `skills_root` come from trusted checkouts, and that the Skills checkout is at the exact commit SHA carried by the planner result. The bridge checks SHA equality and manifest file presence; it does not independently authenticate Git checkouts or fetch remote content.

The current planner result provides one workflow-level rationale. Stage rationales inherit it and are not independent per-Skill explanations.

A prepared plan is not execution. No Skill, LLM, tool, network request, remote host, production system, or financial action is invoked. Missing approvals remain missing in stage envelopes. A later host must separately authorize and call the existing handoff execution adapter.

## Tests

```bash
python scripts/validate_workflow_catalog.py --pretty
python -m unittest TESTS.test_workflow_catalog -v
python -m unittest TESTS.test_planner_handoff_bridge -v
```

The current catalog contains one synthetic reviewed fixture, not multiple independently reviewed operational templates.
