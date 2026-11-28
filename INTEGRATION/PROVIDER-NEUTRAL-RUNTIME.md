# Provider-neutral AI runtime interface

## Purpose

This interface lets a host AI environment connect its own model/runtime to the Toolbox without making the Toolbox depend on a particular vendor, model API, local runner, or orchestration framework.

The initial reference contract is implemented in `scripts/provider_neutral_runtime.py`:

- `JsonModelRuntime` is a small Python Protocol that a host implements.
- `build_skill_planner_request()` accepts task text, canonical Skill contents, manifest references, and a pinned Personal-AI-Library revision.
- `run_skill_planner()` passes the request to the injected runtime and validates a strict JSON selection response.
- The same interface can be implemented by ChatGPT-based hosts, local model runners, or hosted providers. Provider-specific authentication and transport remain outside this repository.

## Host responsibilities

Before calling the interface, the host must:

1. Resolve the Personal-AI-Library checkout from a trusted source at the exact pinned 40-character commit SHA.
2. Independently verify the checkout revision and read canonical `skills/<id>/SKILL.md` files.
3. Build the manifest content/reference mapping and pass it to the request builder.
4. Implement `JsonModelRuntime.generate_json()` using the host's supported model interface and enforce its own privacy, policy, and data-handling requirements.
5. Keep credentials outside task text, prompts, manifests, responses, logs, and reports.
6. Treat model output as untrusted and use the returned selection only as a proposal. Run the existing Skill-selection and workflow-contract validators before any execution.
7. Require separate, explicit, scoped approval for installation, network access, remote/VPS access, production changes, financial operations, and externally visible actions.

The Toolbox validates the pinned revision format and the supplied manifest references, but it cannot independently prove that the host actually fetched those manifests from the stated commit. The host must enforce that trust boundary.

## Response contract

The model returns exactly:

```json
{
  "decision": "select",
  "selected_skills": ["code-audit"],
  "rationale": "The task requests a source-code review."
}
```

Allowed decisions: `select`, `abstain`, `clarify`. A `select` decision requires one or more known Skill IDs. The other decisions require an empty Skill list. Duplicate IDs, unknown IDs, missing rationale, extra fields, and malformed responses are rejected.

No hidden chain-of-thought is requested or stored. A concise rationale is enough.

## Minimal integration example

```python
from provider_neutral_runtime import (
    build_skill_planner_request,
    run_skill_planner,
)

class MyHostRuntime:
    runtime_name = "my-ai-host"
    planner_version = "2026.11"

    def generate_json(self, *, system_prompt, user_prompt, response_schema):
        # Call the model using the host's own supported integration.
        # Return the parsed JSON object. Do not perform tools/actions here.
        return my_model_json_call(system_prompt, user_prompt, response_schema)

request = build_skill_planner_request(
    task="Review this repository for security issues",
    skill_manifests=verified_manifest_contents,
    skills_revision=trusted_skills_commit_sha,
    manifest_refs=verified_manifest_refs,
)
selection = run_skill_planner(request, MyHostRuntime())
```

The example's `my_model_json_call`, verified checkout, and manifest mappings are supplied by the host; they are not Toolbox functions.

## What this implementation does not do

- It does not contain a model, provider SDK, API key, or network transport.
- It does not install or start Ollama or another runtime.
- It does not automatically download or fetch Skills.
- It does not execute selected Skills or call tools.
- It does not grant permissions or perform side effects.
- It does not establish semantic selection quality. Unit tests use a deterministic mock runtime only.

This is the provider-neutral interface layer. A concrete provider adapter may be added separately when there is a specific integration target and a safe, testable requirement.
