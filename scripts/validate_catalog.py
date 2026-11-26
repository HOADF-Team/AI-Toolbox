#!/usr/bin/env python3
"""Validate the AI-Toolbox machine-readable catalog and its tool records."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ALLOWED_STATUSES = {
    "discovered", "reviewed", "tested", "ready", "blocked", "deprecated"
}
REQUIRED_FIELDS = {
    "id", "name", "category", "description", "status", "record",
    "official_url", "license", "platforms", "last_reviewed", "verification",
}
VERIFICATION_FIELDS = {
    "source_reviewed", "license_reviewed", "installation_tested", "runtime_tested"
}


def validate(root: Path, catalog_path: Path) -> list[str]:
    errors: list[str] = []
    try:
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"Cannot read valid JSON from {catalog_path}: {exc}"]

    if not isinstance(catalog, dict):
        return ["Catalog root must be a JSON object."]
    if not isinstance(catalog.get("schema_version"), str):
        errors.append("schema_version must be a string.")
    if not isinstance(catalog.get("catalog_updated"), str):
        errors.append("catalog_updated must be a string.")
    tools = catalog.get("tools")
    if not isinstance(tools, list):
        return errors + ["tools must be a JSON array."]

    seen_ids: set[str] = set()
    seen_records: set[str] = set()
    for index, tool in enumerate(tools):
        prefix = f"tools[{index}]"
        if not isinstance(tool, dict):
            errors.append(f"{prefix} must be an object.")
            continue

        missing = sorted(REQUIRED_FIELDS - tool.keys())
        if missing:
            errors.append(f"{prefix} is missing required fields: {', '.join(missing)}")

        tool_id = tool.get("id")
        if not isinstance(tool_id, str) or not tool_id.strip():
            errors.append(f"{prefix}.id must be a non-empty string.")
        elif tool_id in seen_ids:
            errors.append(f"Duplicate tool id: {tool_id}")
        else:
            seen_ids.add(tool_id)

        for field in ("name", "category", "description", "record",
                      "official_url", "license", "last_reviewed"):
            value = tool.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{prefix}.{field} must be a non-empty string.")

        status = tool.get("status")
        if status not in ALLOWED_STATUSES:
            errors.append(
                f"{prefix}.status must be one of: {', '.join(sorted(ALLOWED_STATUSES))}."
            )

        platforms = tool.get("platforms")
        if (not isinstance(platforms, list) or not platforms
                or any(not isinstance(item, str) or not item.strip()
                       for item in platforms)):
            errors.append(f"{prefix}.platforms must be a non-empty array of strings.")

        verification = tool.get("verification")
        if not isinstance(verification, dict):
            errors.append(f"{prefix}.verification must be an object.")
        else:
            missing_verification = sorted(VERIFICATION_FIELDS - verification.keys())
            if missing_verification:
                errors.append(
                    f"{prefix}.verification is missing: {', '.join(missing_verification)}"
                )
            for key in VERIFICATION_FIELDS & verification.keys():
                if not isinstance(verification[key], bool):
                    errors.append(f"{prefix}.verification.{key} must be boolean.")

        record = tool.get("record")
        if isinstance(record, str) and record.strip():
            if record in seen_records:
                errors.append(f"Duplicate record path: {record}")
            seen_records.add(record)
            relative = Path(record)
            if relative.is_absolute() or ".." in relative.parts:
                errors.append(f"{prefix}.record must be a safe repository-relative path.")
            else:
                record_path = root / relative
                if not record_path.is_file():
                    errors.append(f"{prefix}.record does not exist: {record}")
                else:
                    try:
                        content = record_path.read_text(encoding="utf-8")
                    except (OSError, UnicodeError) as exc:
                        errors.append(f"Cannot read {record}: {exc}")
                    else:
                        if isinstance(tool_id, str) and tool_id.strip():
                            expected_id = re.compile(
                                rf"^- \*\*ID:\*\* `{re.escape(tool_id)}`\s*$",
                                re.MULTILINE,
                            )
                            if not expected_id.search(content):
                                errors.append(
                                    f"{record}: ID does not match catalog id {tool_id!r}."
                                )
                        if isinstance(status, str) and status in ALLOWED_STATUSES:
                            # Accept both English and Russian labels used by existing records.
                            expected_status = re.compile(
                                rf"^- \*\*(?:Status|Статус):\*\* `{re.escape(status)}`\s*$",
                                re.MULTILINE,
                            )
                            if not expected_status.search(content):
                                errors.append(
                                    f"{record}: Status does not match catalog status {status!r}."
                                )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(),
                        help="Repository root (default: current directory)")
    parser.add_argument("--catalog", type=Path, default=Path("CATALOG/tools.json"),
                        help="Catalog path relative to --root")
    args = parser.parse_args()
    root = args.root.resolve()
    catalog_path = args.catalog if args.catalog.is_absolute() else root / args.catalog
    errors = validate(root, catalog_path)

    if errors:
        print("Catalog validation failed:")
        for error in errors:
            print(f" - {error}")
        return 1

    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    print(f"Catalog validation passed: {len(catalog['tools'])} tool records checked.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
