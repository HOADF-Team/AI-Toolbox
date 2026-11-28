# Handoff payload schemas

The payload schema registry adds field-level contracts on top of Skill artifact type compatibility.

- `skill-interfaces.json` declares artifact types a Skill may accept and produce.
- `handoff-payload-schemas.json` declares fields, primitive/nested types, requiredness, and selected enumerated safety states.
- `workflows.json` declares ordered stages and artifact connections.
- Handoff JSON artifacts contain the actual payloads to validate.

## Supported schema subset

The validator supports object, array, string, boolean, integer, number and null types; required object properties; array item schemas; and enum constraints. It rejects booleans as integers/numbers. It does not claim full JSON Schema compatibility.

## Run

```bash
python scripts/validate_handoff_payloads.py --pretty
python -m unittest TESTS.test_handoff_payload_schemas -v
```

The included payloads are synthetic fixtures. A passing result means only that those fixture values conform to the declared schema. It does not establish LLM output quality, real-world truth, runtime provenance, or permission to perform side effects.
