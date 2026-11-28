# Declarative handoff protocol

## Purpose

The handoff protocol defines workflows as data and validates JSON artifacts emitted for each stage. Adding a workflow should normally require a contract file and stage artifacts, not a new domain-specific validator.

This is an orchestration and audit protocol, not an engine that executes Skills or an LLM. For the host-runtime boundary, see [Agent Runtime Adapter](AGENT-RUNTIME-ADAPTER.md).

## Contract format

A contract contains workflow_id, root_input_ref, ordered stages with id and required_fields, optional evidence_field / require_evidence, and declarative rules.

Supported rule types:

| Rule | Purpose |
|---|---|
| equals | Require an exact scalar/object value |
| is_empty | Require an empty/null value |
| ordered_values | Require listed values in the specified order |
| forbid_values | Reject any listed values |

Rule paths use dotted object keys. For list-valued event fields, use item_field to validate a property from each object.

Every artifact has stage, input_ref, output_ref, and (by default) a non-empty evidence array. Each evidence item must contain location and observation. The next artifact's input_ref must equal the preceding artifact's output_ref.

The validator checks secret-like field names and a small set of common secret formats heuristically. This is a safety guard, not a complete secret scanner; do not put credentials in artifacts at all.

## Run

```bash
python scripts/validate_handoff_chain.py \
  --contract TESTS/fixtures/inter-skill-demo/workflow-contract.json \
  --artifacts-dir TESTS/fixtures/inter-skill-demo/handoffs \
  --context TESTS/fixtures/inter-skill-demo/scenario.json \
  --output handoff-report.json
```

Artifact files are named <stage-id>.json. The report includes stage links, checks, errors, limitations, and evidence provenance. Exit code is zero only when all checks pass.

## Safety and limitations

- The validator uses local JSON parsing and deterministic Python checks; it makes no network calls and launches no subprocesses.
- It does not import, prompt, or execute Skills or an LLM.
- A passing contract means the supplied artifacts satisfy the declared structure and rules; it does not prove that their claims are true or that an agent reasoned correctly.
- Evidence provenance is caller-supplied. The validator does not independently authenticate evidence locations.
- Remote access, production changes, and external actions must be represented explicitly and never inferred from a local tool inventory.
- Domain-specific safety rules belong in the workflow contract. Review contracts as code; an incomplete contract can accept incomplete work.

The reference contract in TESTS/fixtures/inter-skill-demo/ demonstrates a four-Skill security review. It is synthetic and does not execute the vulnerable fixture or perform incident response.
