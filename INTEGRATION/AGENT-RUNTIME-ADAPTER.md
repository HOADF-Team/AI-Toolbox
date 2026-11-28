# Agent runtime adapter

## Purpose and boundary

This protocol connects catalogued Skills to an AI host runtime. It separates three responsibilities:

1. **Toolbox** discovers Skills, prepares stage envelopes, and validates returned artifacts.
2. **Host agent/runtime** loads and reads the canonical SKILL.md, performs the reasoning and task work, and calls the adapter for each stage.
3. **Adapter implementation** is supplied by the host. It may be a model/tool orchestration layer, but is not implemented by this repository.

The reference implementation in scripts/handoff_runtime.py does not call an LLM, execute Markdown Skills, install tools, make network requests, or perform external actions. Its tests use a deterministic mock adapter. Passing those tests proves protocol mechanics only.

## Lifecycle

1. The host AI planner proposes relevant Skills and emits an explicit selection document. Validate it using [Skill Selection](SKILL-SELECTION.md) before choosing the reviewed workflow contract. Selection validation checks structure and declared rationale, not semantic relevance.
2. Load CATALOG/skill-tools.json and confirm each skill_id exists.
3. Resolve the canonical manifest under skills/<skill-id>/SKILL.md in a trusted checkout of HOADF-Team/Personal-AI-Library. Supply the full 40-character commit SHA of that checkout as skills_revision. The envelope carries an immutable GitHub file reference for each Skill. Missing manifests stop planning.
4. Optionally run scripts/run_skill_preflight.py in the actual target runtime when tool availability matters. Preserve its report and environment identity. Do not interpret another machine's inventory as the user's local availability.
5. Build ordered stage envelopes. Each envelope identifies the task, stage, Skill, manifest path, prior output reference, required fields, constraints, and approval state.
6. The host agent reads the manifest and performs that stage. The agent returns a structured stage-result object.
7. Validate the response, stop on failed/blocked/invalid output, and pass only the validated output reference to the next stage.
8. Validate the complete chain with scripts/handoff_contract.py and aggregate a final workflow report.

## Envelope and result contracts

The envelope contains workflow/task identity, stage and Skill IDs, canonical manifest path, prior output reference, required outputs, constraints, and requested/granted/missing approvals.

A stage result contains stage and Skill IDs, status (completed/blocked/failed), input_ref, non-empty output_ref, domain fields required by the workflow contract, a non-empty evidence array with location and observation, provenance.execution_mode, provenance.skill_manifest_ref, provenance.agent, a required artifact_provenance envelope, and actions_taken. The runtime validates the envelope structure and binds its producer Skill/revision, source revision, input reference, and payload stage/Skill/output reference to the current stage result. The manifest ref must exactly match the pinned commit and path in the stage envelope. Use an empty actions_taken array when no action was performed.

Every action record must include action and an approval_id matching an approval granted to that exact action. Approval does not make an unsafe action automatically appropriate: host policy must still evaluate scope, reversibility, and user intent. Report recommendations separately from actions actually performed.

## Approval boundary

The host must require explicit, scoped user approval before any installation, configuration change, network operation, remote/VPS access, production change, financial transaction, or externally visible action. An absent approval blocks a stage that declares it as required. Never place secrets, API keys, passwords, private keys, or sensitive customer data in envelopes, artifacts, logs, or reports. Do not infer approval from a catalog entry, tool presence, or prior unrelated permission.

The reference engine verifies only that an action's approval ID matches the caller-supplied approval map. It does not authenticate the user, approval channel, or action execution. The host remains responsible for authorization and enforcement.


### Optional cryptographic integrity policy

A host that has provisioned a trusted Ed25519 public key and local evidence store can enable fail-closed artifact verification by passing `integrity_policy` to `execute_with_adapter`. The policy contains `trusted_public_key`, `trusted_key_id`, and `evidence_root`. Each stage result must then include a signed `integrity_bundle`; the runtime verifies the signature, envelope digest, and evidence-file hashes before accepting the stage. A missing or invalid bundle stops the chain. Without a configured policy, only the existing structural and consistency checks run; no cryptographic verification is claimed. See [Artifact provenance](ARTIFACT-PROVENANCE.md) for the signed bundle format and trust limitations.


### Host-managed signing trust registry

For production host integration, prefer a registry-backed `integrity_policy` with `trust_registry_path`, `key_root`, and `evidence_root`. The runtime resolves the bundle key ID against the registry, checks the public-key fingerprint, active status, validity window, producer scope, and artifact-type scope, then verifies the Ed25519 signature. Revoked or retired keys are rejected. The registry and public-key directory must be protected and authenticated by the host; this repository does not provide key custody or secure policy distribution. See [Artifact provenance](ARTIFACT-PROVENANCE.md) and [the example registry](../SECURITY/trust-registry.example.json).

## Evidence, failure behavior, and limitations

The artifact provenance envelope is required for every stage result. Structural validation checks its schema and binds key identifiers to the stage result; it does not authenticate producer identity, resolve the source revision, or prove evidence. Evidence locations and observations are agent-reported. The adapter checks basic structure and required provenance fields; it does not authenticate evidence, attest model identity, or verify that an action occurred. Use explicit classifications in final reports: **Observed**, **Inferred**, **Recommended**, and **Not checked**.

Unknown Skill IDs, missing manifests, invalid stage results, missing evidence/provenance, mismatched references, and missing approvals must stop the chain. A failed or blocked stage must not silently pass control to a later stage. Preserve partial outputs and the stop reason; do not relabel an incomplete workflow as completed.

No actual LLM/agent invocation is included. No Skill execution, model quality evaluation, or live action is proven by mock tests. The adapter does not independently verify the Skill repository revision or evidence sources. Secret detection is heuristic. The host runtime must implement secure storage, identity, approval collection, isolation, and side-effect enforcement.

## Reference usage

The host calls build_workflow_plan() with the contract, Skill map, trusted Personal-AI-Library checkout root, task description, task reference, and full 40-character skills_revision commit SHA. It then supplies execute_with_adapter() with its own adapter callable. That callable is responsible for loading and reading the canonical Skill manifest and returning a structured result. The Toolbox provides no LLM implementation.

## Measuring planner selection quality

For an external planner evaluation exchange, use [External AI runtime benchmark integration](EXTERNAL-RUNTIME-BENCHMARK.md). The benchmark bridge exports gold-label-free requests and scores complete response bundles from a separately operated host. It does not invoke or authenticate an LLM.


### Creating signed bundles

Use [Artifact signing](ARTIFACT-SIGNING.md) to create the Ed25519 integrity bundle after resolving the active key through the host-managed trust registry. The helper does not store or manage private keys and does not prevent cross-run replay.


### Replay-resistant signature policy

For signed stage results, the host should generate a unique run ID once per workflow execution and configure `require_execution_context=True`, that `run_id`, and a bounded `max_signature_age_seconds` in the integrity policy. The signing helper then binds each signature to the workflow ID, stage ID, Skill ID, and exact input reference, with signed issue/expiry times. A signature from a different run or stage, or one outside its validity window, blocks the stage. If this policy is not enabled, the legacy signature format remains compatible but replay protection is not claimed. The host is responsible for unique run-ID generation and non-reuse.


### Archival verification is not runtime authorization

Use `scripts/archival_verification.py` only when auditing stored artifacts signed by a planned-retired key. It checks the signed timestamp against the original key validity and `retired_at` record. Revoked keys are always rejected. An `archived_verified` result is historical evidence only and must never be treated as a newly completed live Skill stage. See [Artifact provenance](ARTIFACT-PROVENANCE.md).


### Bind the complete stage result to its provenance envelope

The host adapter must compute `stage_result_sha256(result)` from the complete stage-result object before adding `artifact_provenance` or `integrity_bundle`. Store the digest in `artifact_provenance.payload.stage_result_sha256`. The digest covers all stage-result fields, including status, evidence claims, actions taken, output references, and domain-specific results; it excludes only `artifact_provenance`, `integrity_bundle`, and the runtime-generated `integrity_verification` field to avoid a circular digest. The runtime recomputes the digest and rejects any mismatch. When cryptographic integrity policy is enabled, the provenance envelope containing this digest is then signed, binding the complete result to the signature.

This detects post-signing changes to the stage-result object. It does not prove that the original agent-reported claims are true.


### Approval enforcement at execution time

The reference runtime re-derives each stage's required approvals from the workflow contract passed to `execute_with_adapter`; it does not trust a plan's cached `missing_approvals` or `granted_approvals` fields. The adapter is not called until every approval required by that exact stage is present in the execution-time approval map. Action records are checked against approvals scoped to the current stage, so an approval for the same action in a different stage cannot authorize it here. The host still must authenticate the approval channel and ensure the approval is specific to the exact operation, target, and time window.
