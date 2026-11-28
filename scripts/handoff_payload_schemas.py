"""Field-level validation for declared JSON handoff artifact payloads.

Only a deliberately small JSON-schema subset is supported. No Skills or models run.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_TYPES = {"object", "array", "string", "boolean", "integer", "number", "null"}


def _matches_type(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "null":
        return value is None
    return False


def _validate_value(value: Any, spec: dict[str, Any], path: str) -> list[str]:
    errors: list[str] = []
    expected = spec.get("type")
    if expected not in _TYPES:
        return [f"{path}:unsupported_type"]
    if not _matches_type(value, expected):
        return [f"{path}:expected_{expected}"]
    if "enum" in spec and value not in spec["enum"]:
        errors.append(f"{path}:value_not_in_enum")
    if expected == "array" and "items" in spec:
        item_spec = spec["items"]
        if not isinstance(item_spec, dict):
            errors.append(f"{path}:invalid_items_schema")
        else:
            for index, item in enumerate(value):
                errors.extend(_validate_value(item, item_spec, f"{path}[{index}]"))
    if expected == "object":
        properties = spec.get("properties", {})
        required = spec.get("required", [])
        if not isinstance(properties, dict) or not isinstance(required, list):
            errors.append(f"{path}:invalid_object_schema")
        else:
            for name in required:
                if name not in value:
                    errors.append(f"{path}.{name}:missing_required")
            for name, child_spec in properties.items():
                if name in value:
                    if not isinstance(child_spec, dict):
                        errors.append(f"{path}.{name}:invalid_property_schema")
                    else:
                        errors.extend(_validate_value(value[name], child_spec, f"{path}.{name}"))
    return errors


def validate_payload_schemas(catalog: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(catalog, dict) or catalog.get("schema_version") != "1.0":
        return {"status": "failed", "errors": ["unsupported_payload_schema_version"]}
    entries = catalog.get("artifacts")
    if not isinstance(entries, list) or not entries:
        return {"status": "failed", "errors": ["artifacts_must_be_non_empty_array"]}
    seen: set[tuple[str, str]] = set()
    for index, entry in enumerate(entries):
        prefix = f"artifact_schema_{index}"
        if not isinstance(entry, dict):
            errors.append(f"{prefix}:must_be_object")
            continue
        artifact_type, field = entry.get("artifact_type"), entry.get("field")
        if not isinstance(artifact_type, str) or not artifact_type.strip():
            errors.append(f"{prefix}:invalid_artifact_type")
        if not isinstance(field, str) or not field.strip():
            errors.append(f"{prefix}:invalid_field")
        if isinstance(artifact_type, str) and isinstance(field, str):
            key = (artifact_type, field)
            if key in seen:
                errors.append(f"{prefix}:duplicate_field_schema")
            seen.add(key)
        probe = {key: value for key, value in entry.items() if key not in {"artifact_type", "field", "required"}}
        errors.extend(_validate_value(None, probe, prefix) if probe.get("type") == "null" else
                      ([] if probe.get("type") in _TYPES else [f"{prefix}:unsupported_type"]))
    return {"schema_version": "1.0", "catalog_id": catalog.get("catalog_id"),
            "status": "passed" if not errors else "failed", "artifact_schema_count": len(entries),
            "errors": errors,
            "limitations": ["Supports only a small documented JSON Schema subset.",
                            "Schema validity does not establish semantic correctness or runtime conformance."]}


def validate_stage_payloads(
    workflow: dict[str, Any], interfaces: dict[str, Any], schemas: dict[str, Any],
    artifacts: list[dict[str, Any]],
) -> dict[str, Any]:
    interface_map = {entry.get("skill_id"): entry for entry in interfaces.get("interfaces", []) if isinstance(entry, dict)}
    errors: list[str] = []
    checks: list[dict[str, Any]] = []
    by_stage = {item.get("stage"): item for item in artifacts if isinstance(item, dict)}
    if len(by_stage) != len(artifacts):
        errors.append("duplicate_or_invalid_stage_artifact")

    for stage in workflow.get("stages", []):
        if not isinstance(stage, dict):
            errors.append("invalid_workflow_stage")
            continue
        stage_id = stage.get("id")
        iface = interface_map.get(stage.get("skill_id"))
        artifact = by_stage.get(stage_id)
        if iface is None or artifact is None:
            errors.append(f"{stage_id}:missing_interface_or_payload")
            continue
        declared = stage.get("produces")
        if not isinstance(declared, list):
            errors.append(f"{stage_id}:missing_declared_outputs")
            continue
        allowed = set(iface.get("produces", []))
        for artifact_type in declared:
            schema_fields = [entry for entry in schemas.get("artifacts", [])
                             if isinstance(entry, dict) and entry.get("artifact_type") == artifact_type]
            supported = artifact_type in allowed and bool(schema_fields)
            checks.append({"id": f"{stage_id}.{artifact_type}.schema_exists", "passed": supported})
            if not supported:
                errors.append(f"{stage_id}:{artifact_type}:missing_or_unsupported_schema")
                continue
            for field_schema in schema_fields:
                field = field_schema["field"]
                required = field_schema.get("required", True)
                if field not in artifact:
                    if required:
                        errors.append(f"{stage_id}.{artifact_type}.{field}:missing_required")
                        checks.append({"id": f"{stage_id}.{field}.present", "passed": False})
                    continue
                spec = {key: value for key, value in field_schema.items()
                        if key not in {"artifact_type", "field", "required"}}
                field_errors = _validate_value(artifact[field], spec, f"{stage_id}.{field}")
                checks.append({"id": f"{stage_id}.{field}.valid", "passed": not field_errors,
                               "errors": field_errors})
                errors.extend(field_errors)
    return {"schema_version": "1.0", "workflow_id": workflow.get("workflow_id", "unnamed"),
            "status": "passed" if not errors else "failed", "checks": checks, "errors": errors,
            "limitations": ["Validates declared fields and primitive/nested types only.",
                            "Does not execute Skills, validate reasoning, or grant permissions.",
                            "Payload provenance and semantic accuracy require separate verification."]}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
