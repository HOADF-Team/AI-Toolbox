# Provider-neutral runtime interface

Run the provider-neutral adapter contract tests:

```bash
python -m unittest TESTS.test_provider_neutral_runtime -v
```

These tests inject a deterministic mock runtime. They verify request construction, pinned revision format, manifest references, response schema, Skill ID validation, and safe error handling. They do not invoke a model or network service.

See [Provider-neutral AI runtime interface](../INTEGRATION/PROVIDER-NEUTRAL-RUNTIME.md) for the host integration contract.
