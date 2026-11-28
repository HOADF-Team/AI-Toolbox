# Canonical JSON reference profile

## Purpose

Artifact signatures and digests require every signer and verifier to produce exactly the same bytes from the same JSON data. This repository currently uses a project-specific Python reference profile implemented by `scripts/artifact_integrity.py::canonical_json_bytes`.

This profile is **not RFC 8785/JCS**. Do not label it JCS or assume a generic JSON serializer is compatible.

## Version 1 profile

- Input must be a JSON data tree: object keys are strings; values are objects, arrays, strings, booleans, integers, finite floats, or null. Tuples, sets, byte strings, non-string keys, NaN, and infinities are rejected.
- Object keys are sorted using Python's Unicode code-point ordering.
- UTF-8 output; Unicode characters are emitted directly (`ensure_ascii=False`).
- No insignificant whitespace (`separators=(",", ":")`).
- Python's reference `json.dumps` number formatting is authoritative, including distinctions such as `1` vs `1.0`, `-0.0`, and exponent formatting.
- SHA-256 is calculated over the exact UTF-8 bytes.

## Golden vectors

The machine-readable fixtures are in [canonical-json-vectors.json](../TESTS/fixtures/canonical-json-vectors.json). Each vector contains the source value, exact canonical UTF-8 text, and expected SHA-256 digest.

Run the reference checks:

```bash
python -m unittest TESTS.test_artifact_integrity -v
```

A cross-language implementation must pass every vector byte-for-byte before it is trusted to sign or verify these artifacts. Comparing parsed JSON values is insufficient; compare the canonical byte sequence and digest. Add new vectors whenever serializer behavior or the profile changes.

## Interoperability boundary

These vectors are a first compatibility gate, not a proof that every possible JSON value is interoperable. The number-formatting profile is Python-specific and other runtimes must reproduce it exactly or use a tested compatible serializer. Until an implementation passes the shared vectors and additional edge-case tests, treat its signatures as incompatible with this profile.

A future migration to RFC 8785/JCS would require an explicit profile/version change, migration strategy, and new signatures; never silently change canonicalization for existing signed artifacts.
