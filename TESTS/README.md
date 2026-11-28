# Testing policy

A tool is not "tested" merely because its repository, documentation, or installer was inspected.

Record the actual environment (OS/version, runtime, tool version), exact checks, expected and observed results, date, and limitations. Prefer isolated test environments. Separate installation checks from functional checks and security review.

Do not test untrusted software on a production machine or with real credentials.

## Inter-Skill workflow fixture

The synthetic cross-Skill security scenario in [fixtures/inter-skill-demo/](fixtures/inter-skill-demo/) contains four structured handoff artifacts and a declarative workflow contract. The reusable engine validates stage order, artifact linkage, required fields, evidence, contract rules, and heuristic secret redaction.

Run the generic contract tests:

```bash
python -m unittest TESTS.test_handoff_contract -v
python scripts/validate_handoff_chain.py \
  --contract TESTS/fixtures/inter-skill-demo/workflow-contract.json \
  --artifacts-dir TESTS/fixtures/inter-skill-demo/handoffs \
  --context TESTS/fixtures/inter-skill-demo/scenario.json \
  --output handoff-report.json
```

Run the additional scenario-specific security regression tests:

```bash
python -m unittest TESTS.test_inter_skill_workflow -v
```

The fixture is intentionally vulnerable and must not be executed, installed, or deployed. These tests validate JSON contract/orchestration integrity only. They do not execute Skills or an LLM, prove real agent reasoning, perform credential revocation or host isolation, establish remote VPS access, or harden production.
