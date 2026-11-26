#!/usr/bin/env python3
"""Check the availability of tools mapped to one or more Personal-AI-Library Skills."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def check_skill(skill: dict[str, Any], match_report: dict[str, Any]) -> dict[str, Any]:
    tools = {
        item["id"]: item
        for item in match_report.get("tools", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    groups = skill.get("required_any", [])
    group_results = []
    for group in groups:
        candidates = []
        for tool_id in group:
            item = tools.get(tool_id)
            candidates.append({
                "id": tool_id,
                "availability": item.get("availability", "not_probed") if item else "not_probed",
            })
        statuses = [item["availability"] for item in candidates]
        if "available" in statuses:
            status = "satisfied"
        elif statuses and all(value == "missing" for value in statuses):
            status = "blocked"
        else:
            status = "unknown"
        group_results.append({"status": status, "any_of": candidates})

    if any(item["status"] == "blocked" for item in group_results):
        readiness = "blocked"
    elif any(item["status"] == "unknown" for item in group_results):
        readiness = "unknown"
    else:
        readiness = "ready"

    recommended = []
    for tool_id in skill.get("recommended", []):
        item = tools.get(tool_id)
        recommended.append({
            "id": tool_id,
            "availability": item.get("availability", "not_probed") if item else "not_probed",
        })

    return {
        "skill": skill["id"],
        "readiness": readiness,
        "required_groups": group_results,
        "recommended_tools": recommended,
        "note": (
            "Readiness checks only declared prerequisites. Review the Skill and tool records, "
            "version/platform compatibility, and task-specific functionality before execution."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skill", action="append", dest="skills",
                        help="Skill ID; repeat to check multiple Skills. Defaults to all.")
    parser.add_argument("--mapping", type=Path, default=Path("CATALOG/skill-tools.json"))
    parser.add_argument("--matches", type=Path, required=True,
                        help="JSON output from scripts/match_inventory.py")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    try:
        mapping = load_json(args.mapping)
        matches = load_json(args.matches)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        parser.error(str(exc))

    skills = mapping.get("skills", [])
    by_id = {item["id"]: item for item in skills if isinstance(item, dict) and "id" in item}
    requested = args.skills or list(by_id)
    unknown = [skill_id for skill_id in requested if skill_id not in by_id]
    if unknown:
        parser.error("Unknown Skill ID(s): " + ", ".join(unknown))

    results = [check_skill(by_id[skill_id], matches) for skill_id in requested]
    counts = {state: sum(item["readiness"] == state for item in results)
              for state in ("ready", "blocked", "unknown")}
    output = {
        "schema_version": "1.0",
        "inventory_scope": matches.get("inventory_scope", "unknown"),
        "summary": {"total": len(results), "counts": counts},
        "skills": results,
        "limitations": [
            "This is a dependency preflight, not proof that a Skill's workflow can be completed.",
            "Only tools listed in required_any can block readiness; recommended tools are advisory.",
            "The inventory scope is the environment where inventory.py was executed, not the user's device unless run there.",
        ],
    }
    print(json.dumps(output, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
