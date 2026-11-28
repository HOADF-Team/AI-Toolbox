# Agent runtime adapter

## Purpose and boundary

This protocol connects catalogued Skills to an AI host runtime. It separates three responsibilities:

1. **Toolbox** discovers Skills, prepares stage envelopes, and validates returned artifacts.
2. **Host agent/runtime** loads and reads the canonical SKILL.md, performs the reasoning and task work, and calls the adapter for each stage.
3. **Adapter implementation** is supplied by the host. It may be a model/tool orchestration layer, but is not implemented by this repository.

The reference implementation in scripts/handoff_runtime.py does not call an LLM, execute Markdown Skills, install tools, make network requests, or perform external actions. Its tests use a deterministic mock adapter. Passing those tests proves protocol mechanics only.

## Lifecycle

1. The host chooses a workflow contract based on the user's task. Skill selection is explicit and recorded in the contract; the runtime does not guess a chain from fuzzy text matching.
2. Load CATALOG/skill-tools.json and confirm each skill_id exists.
3. Resolve the canonical manifest under skills/<skill-id>/SKILL.md in a trusted checkout of HOADF-Team/Personal-AI-Library. Missing manifests stop planning.
4. Optionally run scripts/run_skill_preflight.py in the actual target runtime when tool availability matters. Preserve its report and environment identity. Do not interpret another machine's inventory as the user's local availability.
5. Build ordered stage envelopes. Each envelope identifies the task, stage, Skill, manifest path, prior output reference, required fields, constraints, and approval state.
6. The host agent reads the manifest and performs that stage. The agent returns a structured stage-result object.
7. Validate the response, stop on failed/blocked/invalid output, and pass only the validated output reference to the next stage.
8. Validate the complete chain with scripts/handoff_contract.py and aggregate a final workflow report.

## Envelope and result contracts

The envelope contains workflow/task identity, stage and Skill IDs, canonical manifest path, prior output reference, required outputs, constraints, and requested/granted/missing approvals.

A stage result contains stage and Skill IDs, status (completed/blocked/failed), input_ref, non-empty output_ref, domain fields required by the workflow contract, a non-empty evidence array with location and observation, provenance.execution_mode, provenance.skill_manifest_ref, provenance.agent, and actions_taken. Use an empty actions_taken array when no action was performed.

Every action record must include action and an approval_id matching an approval granted to that exact action. Approval does not make an unsafe action automatically appropriate: host policy must still evaluate scope, reversibility, and user intent. Report recommendations separately from actions actually performed.

## Approval boundary

The host must require explicit, scoped user approval before any installation, configuration change, network operation, remote/VPS access, production change, financial transaction, or externally visible action. An absent approval blocks a stage that declares it as required. Never place secrets, API keys, passwords, private keys, or sensitive customer data in envelopes, artifacts, logs, or reports. Do not infer approval from a catalog entry, tool presence, or prior unrelated permission.

The reference engine verifies only that an action's approval ID matches the caller-supplied approval map. It does not authenticate the user, approval channel, or action execution. The host remains responsible for authorization and enforcement.

## Evidence, failure behavior, and limitations

Evidence locations and observations are agent-reported. The adapter checks basic structure and required provenance fields; it does not authenticate evidence, attest model identity, or verify that an action occurred. Use explicit classifications in final reports: **Observed**, **Inferred**, **Recommended**, and **Not checked**.

Unknown Skill IDs, missing manifests, invalid stage results, missing evidence/provenance, mismatched references, and missing approvals must stop the chain. A failed or blocked stage must not silently pass control to a later stage. Preserve partial outputs and the stop reason; do not relabel an incomplete workflow as completed.

No actual LLM/agent invocation is included. No Skill execution, model quality evaluation, or live action is proven by mock tests. The adapter does not independently verify the Skill repository revision or evidence sources. Secret detection is heuristic. The host runtime must implement secure storage, identity, approval collection, isolation, and side-effect enforcement.

## Reference usage

The host calls build_workflow_plan() with the contract, Skill map, trusted Personal-AI-Library checkout root, task description and task reference. It then supplies execute_with_adapter() with its own adapter callable. That callable is responsible for loading and reading the canonical Skill manifest and returning a structured result. The Toolbox provides no LLM implementation.
