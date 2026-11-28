# Reusable workflow catalog

## Purpose

`CATALOG/workflows/workflows.json` is the central registry of declarative workflow templates. It lets different host AI runtimes use the same reviewed handoff patterns without embedding workflow definitions in provider-specific code.

Each entry has:
- a stable `workflow_id`;
- `catalog_status` (`reviewed`, `reviewed_fixture`, `draft`, or `deprecated`);
- a `classification` and human-readable description;
- a root input reference;
- an ordered list of Skill stages and required output fields;
- declarative handoff rules;
- workflow-level constraints.

## Selection and preparation

1. A host loads the catalog from its trusted Toolbox checkout.
2. Run `scripts/validate_workflow_catalog.py --pretty`.
3. The host obtains a planner decision and ordered Skill IDs.
4. Only entries marked `reviewed` or `reviewed_fixture` are eligible for exact ordered matching. Draft and deprecated entries are not selectable.
5. The selected sequence must match exactly one template. No stages are silently inserted, removed, reordered, or inferred.
6. The existing planner-to-handoff bridge prepares stage envelopes from that exact contract.
7. The host separately validates the resulting plan and obtains explicit approvals before any execution.

The current registry contains one `reviewed_fixture`: a synthetic four-Skill security scenario. It is included to validate the architecture and is **not** an operational production workflow. There are not yet multiple independently reviewed operational templates.

## Validation

The catalog validator checks:
- catalog and workflow IDs;
- non-empty ordered stages;
- each stage's Skill ID against `CATALOG/skill-tools.json`;
- duplicate stage IDs;
- required output and approval field shapes;
- rule IDs, stage references, paths, and supported rule types;
- constraint structure.

Run:

```bash
python scripts/validate_workflow_catalog.py --pretty
python -m unittest TESTS.test_workflow_catalog -v
```

Validation is structural. It does not prove that the template is semantically correct, that the Skills are suitable for a task, or that its maintainer-declared review status is independently certified.

## Safety and limitations

- The catalog is data, not executable code.
- Rule types are declarative and allowlisted; no shell, Python, or arbitrary expression execution is supported.
- The current matching algorithm requires exact ordered Skill sequence equality.
- A matching template only prepares envelopes; it does not execute Skills or tools.
- External actions, installation, network access, remote/VPS access, production changes, and financial operations still require separate explicit authorization.
- Catalog provenance and reviewer identity are not cryptographically attested by this module.
