# Testing policy

A tool is not "tested" merely because its repository, documentation, or installer was inspected.

Record the actual environment (OS/version, runtime, tool version), exact checks, expected and observed results, date, and limitations. Prefer isolated test environments. Separate installation checks from functional checks and security review.

Do not test untrusted software on a production machine or with real credentials.

## Inter-Skill workflow fixture

The synthetic cross-Skill security scenario in [fixtures/inter-skill-demo/](fixtures/inter-skill-demo/) contains four structured handoff artifacts. The deterministic validator checks stage order, artifact linkage, evidence fields, incident recommendation order, secret redaction, and non-interference constraints.

Run the contract suite:

```bash
python -m unittest TESTS.test_inter_skill_workflow -v
python scripts/validate_inter_skill_workflow.py \
  --scenario TESTS/fixtures/inter-skill-demo/scenario.json \
  --handoff-dir TESTS/fixtures/inter-skill-demo/handoffs \
  --output inter-skill-report.json
```

The fixture is intentionally vulnerable and must not be executed, installed, or deployed. The general Trivy repository scan excludes only its deliberately outdated `requirements.txt`; a separate CI step scans that fixture and asserts detection of the known `requests==2.19.1` advisory.

These tests validate JSON orchestration contracts only. They do not execute Skills or an LLM, prove real agent reasoning, perform credential revocation or host isolation, establish remote VPS access, or harden production.
