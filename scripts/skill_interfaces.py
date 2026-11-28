"""Draft Skill interface registry and deterministic workflow compatibility checks.

This module validates metadata only. It never executes Skills, models, or tools.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

_TOKEN = re.compile(r"^[a-z][a-z0-9_]*(?:[.-][a-z0-9_]+)*$")
_SIDE_EFFECTS = {"local_write", "network", "remote", "production", "financial"}
_STATUSES = {"draft", "reviewed", "deprecated"}


class SkillInterfaceError(ValueError):
    """Raised when Skill interface metadata is invalid."""


def validate_skill_interfaces(catalog: dict[str, Any], skill_map: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(catalog, dict) or catalog.get("schema_version") != "1.0":
        return {"schema_version": "1.0", "status": "failed", "errors": ["unsupported_interface_schema"]}
    if not isinstance(catalog.get("catalog_id"), str) or not catalog["catalog_id"].strip():
        errors.append("missing_catalog_id")
    known = {item.get("id") for item in skill_map.get("skills", []) if isinstance(item, dict)}
    interfaces = catalog.get("interfaces")
    if not isinstance(interfaces, list) or not interfaces:
        errors.append("interfaces_must_be_non_empty_array")
        interfaces = []
    seen: set[str] = set()
    for index, item in enumerate(interfaces):
        prefix = f"interface_{index}"
        if not isinstance(item, dict):
            errors.append(f"{prefix}_must_be_object")
            continue
        skill_id = item.get("skill_id")
        if not isinstance(skill_id, str) or skill_id not in known:
            errors.append(f"{prefix}_unknown_skill")
        elif skill_id in seen:
            errors.append(f"duplicate_skill_interface:{skill_id}")
        else:
            seen.add(skill_id)
        if item.get("status") not in _STATUSES:
            errors.append(f"{prefix}_invalid_status")
        for field in ("accepts", "produces", "permission_gates"):
            values = item.get(field)
            if not isinstance(values, list) or any(not isinstance(v, str) or not _TOKEN.fullmatch(v) for v in values):
                errors.append(f"{prefix}_invalid_{field}")
            elif len(values) != len(set(values)):
                errors.append(f"{prefix}_duplicate_{field}")
        effects = item.get("possible_side_effects")
        if not isinstance(effects, list) or any(effect not in _SIDE_EFFECTS for effect in effects):
            errors.append(f"{prefix}_invalid_possible_side_effects")
        if not isinstance(item.get("status"), str) or item.get("status") == "reviewed":
            # A reviewed interface must carry explicit review metadata; this first schema has none.
            if item.get("status") == "reviewed":
                errors.append(f"{prefix}_review_metadata_required")
    return {
        "schema_version": "1.0", "catalog_id": catalog.get("catalog_id"),
        "status": "passed" if not errors else "failed",
        "interface_count": len(interfaces), "skill_ids": sorted(seen), "errors": errors,
        "limitations": [
            "Draft interfaces are hypotheses derived from Skill instructions, not certified API schemas.",
            "Possible side effects are risk labels, not grants of permission.",
            "Validation checks metadata structure, not semantic suitability or runtime behavior."
        ]
    }


def validate_workflow_compatibility(
    workflow: dict[str, Any], interfaces: dict[str, Any]
) -> dict[str, Any]:
    registry = {item["skill_id"]: item for item in interfaces.get("interfaces", []) if isinstance(item, dict) and isinstance(item.get("skill_id"), str)}
    errors: list[str] = []
    checks: list[dict[str, Any]] = []

    def check(name: str, passed: bool, detail: str) -> None:
        checks.append({"id": name, "passed": bool(passed), "detail": detail})
        if not passed:
            errors.append(name)

    external = workflow.get("external_inputs", [])
    if not isinstance(external, list) or any(not isinstance(x, str) for x in external):
        external = []
        check("external_inputs_shape", False, "external_inputs must be an array of artifact type IDs")
    else:
        check("external_inputs_shape", True, f"{len(external)} external artifact type(s)")
    available = set(external)
    stages = workflow.get("stages", [])
    for index, stage in enumerate(stages if isinstance(stages, list) else []):
        sid = stage.get("skill_id", stage.get("id")) if isinstance(stage, dict) else None
        iface = registry.get(sid)
        if iface is None:
            check(f"stage_{index}.interface_exists", False, f"no interface for Skill {sid!r}")
            continue
        check(f"{sid}.interface_exists", True, f"interface status={iface.get('status')}")
        consumes, produces = stage.get("consumes"), stage.get("produces")
        valid_bindings = (
            isinstance(consumes, list) and isinstance(produces, list)
            and all(isinstance(value, str) and _TOKEN.fullmatch(value) for value in consumes)
            and all(isinstance(value, str) and _TOKEN.fullmatch(value) for value in produces)
        )
        if not valid_bindings:
            check(f"{sid}.bindings_shape", False, "stage consumes and produces must be arrays of valid artifact type IDs")
            continue
        check(f"{sid}.bindings_unique", len(consumes) == len(set(consumes)) and len(produces) == len(set(produces)),
              "consumes and produces must not contain duplicates")
        accepted = set(iface.get("accepts", []))
        declared_outputs = set(iface.get("produces", []))
        check(f"{sid}.consumes_supported", set(consumes).issubset(accepted),
              f"consumes={consumes}; accepts={sorted(accepted)}")
        check(f"{sid}.produces_supported", set(produces).issubset(declared_outputs),
              f"produces={produces}; interface outputs={sorted(declared_outputs)}")
        missing = [artifact for artifact in consumes if artifact not in available]
        check(f"{sid}.inputs_available", not missing,
              f"unavailable inputs={missing}" if missing else "all consumed artifact types are available")
        available.update(produces)
        effects = set(iface.get("possible_side_effects", []))
        check(f"{sid}.side_effects_not_permissions", True,
              f"possible side effects={sorted(effects)}; separate user authorization remains mandatory")
    return {
        "schema_version": "1.0", "workflow_id": workflow.get("workflow_id", "unnamed"),
        "status": "passed" if not errors else "failed", "checks": checks, "errors": errors,
        "limitations": [
            "Compatibility is based on declared artifact type labels; payload JSON schemas are not yet enforced.",
            "Only earlier-stage outputs and explicitly declared external inputs satisfy a stage input.",
            "This check prepares no execution and grants no permissions.",
            "A passing check does not prove that the Skill actually emits the declared artifact."
        ]
    }


def load_skill_interfaces(path: Path, skill_map: dict[str, Any]) -> dict[str, Any]:
    try:
        catalog = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SkillInterfaceError(f"cannot load Skill interface catalog: {type(exc).__name__}") from exc
    report = validate_skill_interfaces(catalog, skill_map)
    if report["status"] != "passed":
        raise SkillInterfaceError("Skill interface validation failed: " + ",".join(report["errors"]))
    return catalog
