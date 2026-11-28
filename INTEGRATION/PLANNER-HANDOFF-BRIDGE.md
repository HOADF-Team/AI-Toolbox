# Planner-to-handoff bridge

## Purpose

The provider-neutral planner returns a model decision and ordered Skill IDs. The handoff runtime requires a reviewed workflow contract with explicit stages, outputs, dependencies, constraints, and approval gates. This bridge connects those two existing layers without inventing a workflow.

Implementation: `scripts/planner_handoff_bridge.py`.

## Flow

1. The host supplies a validated planner result, task and task reference.
2. The bridge checks the decision, selected IDs, and exact pinned Skills revision.
3. It searches only the reviewed workflow contracts supplied by the host.
4. The selected Skill IDs must match exactly one contract's ordered Skill sequence.
5. The bridge builds a selection document and runs the existing Skill-selection validator.
6. It calls the existing handoff planner to resolve canonical manifest paths and prepare stage envelopes.
7. It returns a prepared plan. It does not invoke `execute_with_adapter()`.

## Outcomes

- `prepared`: exactly one reviewed workflow matched, the selection contract passed, and canonical manifest files were present.
- `no_matching_reviewed_workflow`: no contract matched. The host must ask for clarification or arrange a separately reviewed contract; the bridge does not invent stages.
- `abstain` / `clarify`: the planner did not request workflow preparation, so no plan is returned.
- Invalid data, duplicate or unknown Skills, revision mismatch, ambiguous contract matches, and missing manifests fail closed.

The bridge currently supports exact ordered matches only. It intentionally does not reorder, omit, append, or substitute Skills to force a match.

## Trust and safety boundaries

The host must verify that `skills_root` is a trusted Personal-AI-Library checkout at the exact commit SHA carried by the planner result. The bridge checks the SHA format/equality and manifest file presence; it does not independently authenticate the Git checkout or fetch remote content.

The current planner result provides one workflow-level rationale. The bridge carries it into each stage entry and explicitly labels those stage rationales as inherited, not independently generated per-Skill explanations.

A prepared plan is not execution. No Skill, LLM, tool, network request, remote host, production system, or financial action is invoked. Missing approvals remain missing in the stage envelopes. A later host must separately authorize and call the existing handoff execution adapter.

## Test

```bash
python -m unittest TESTS.test_planner_handoff_bridge -v
```

Tests use the repository's synthetic reviewed workflow fixture and temporary manifest files. They validate bridge mechanics only, not model reasoning or real Skill execution.
