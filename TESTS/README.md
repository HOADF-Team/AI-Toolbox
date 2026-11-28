# Testing policy

A tool is not "tested" merely because its repository, documentation, or installer was inspected.

Record the actual environment (OS/version, runtime, tool version), exact checks, expected and observed results, date, and limitations. Prefer isolated test environments. Separate installation checks from functional checks and security review.

Do not test untrusted software on a production machine or with real credentials.

## Inter-Skill workflow fixture

The synthetic cross-Skill security scenario is documented in [`fixtures/inter-skill-demo/`](fixtures/inter-skill-demo/). Its contract test validates the four-Skill route and safety boundaries using synthetic tool-availability data:

```bash
python -m unittest TESTS.test_inter_skill_workflow -v
```

The fixture is intentionally vulnerable and must not be executed, installed, or deployed. The general Trivy repository scan excludes only its deliberately outdated `requirements.txt`; a separate CI step scans that fixture and asserts detection of the known `requests==2.19.1` advisory. The exclusion therefore does not hide the fixture from security testing. These tests do not establish live credential revocation, remote VPS access, or production hardening.
