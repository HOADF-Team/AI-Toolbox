#!/usr/bin/env python3
"""Validate that AI-Toolbox maps every real Personal-AI-Library Skill exactly once."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


SKILL_ROW = re.compile(r"^\|\s*`([^ `][^ `]*)`\s*\|")
SKILL_FILE = "SKILL.md"


def discover_skills(skills_root: Path) -> set[str]:
    if not skills_root.is_dir():
        raise ValueError(f"Skills directory does not exist: {skills_root}")
    return {
        skill_file.parent.name
        for skill_file in skills_root.glob(f"*/{SKILL_FILE}")
        if skill_file.is_file()
    }


def mapped_skills(map_path: Path) -> list[str]:
    content = map_path.read_text(encoding="utf-8")
    marker = "## Per-Skill mapping"
    if marker not in content:
        raise ValueError(f"Missing section: {marker}")
    section = content.split(marker, 1)[1]
    next_heading = re.search(r"^## ", section, re.MULTILINE)
    if next_heading:
        section = section[:next_heading.start()]

    result: list[str] = []
    for line in section.splitlines():
        match = SKILL_ROW.match(line)
        if match:
            result.append(match.group(1))
    return result


def validate(skills_root: Path, map_path: Path, tool_mapping_path: Path, catalog_path: Path) -> list[str]:
    errors: list[str] = []
    try:
        actual = discover_skills(skills_root)
    except ValueError as exc:
        return [str(exc)]

    try:
        mapped = mapped_skills(map_path)
    except (OSError, UnicodeError, ValueError) as exc:
        return [f"Cannot read Skill map: {exc}"]

    duplicates = sorted({item for item in mapped if mapped.count(item) > 1})
    if duplicates:
        errors.append("Duplicate Skill map entries: " + ", ".join(duplicates))

    mapped_set = set(mapped)
    missing = sorted(actual - mapped_set)
    unknown = sorted(mapped_set - actual)
    if missing:
        errors.append("Skills missing from AI-Toolbox map: " + ", ".join(missing))
    if unknown:
        errors.append("Map entries without a matching SKILL.md: " + ", ".join(unknown))
    if not actual:
        errors.append(f"No {SKILL_FILE} files found under {skills_root}")

    try:
        tool_mapping = json.loads(tool_mapping_path.read_text(encoding="utf-8"))
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        tool_skills = tool_mapping.get("skills", [])
        tool_skill_ids = [
            item["id"] for item in tool_skills
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        ]
        if len(tool_skill_ids) != len(set(tool_skill_ids)):
            errors.append("Duplicate Skill IDs in machine-readable tool map")
        if set(tool_skill_ids) != actual:
            missing_tool_map = sorted(actual - set(tool_skill_ids))
            extra_tool_map = sorted(set(tool_skill_ids) - actual)
            if missing_tool_map:
                errors.append("Skills missing from machine-readable tool map: " + ", ".join(missing_tool_map))
            if extra_tool_map:
                errors.append("Unknown Skills in machine-readable tool map: " + ", ".join(extra_tool_map))
        catalog_ids = {item.get("id") for item in catalog.get("tools", []) if isinstance(item, dict)}
        for skill in tool_skills:
            if not isinstance(skill, dict):
                errors.append("Invalid entry in machine-readable tool map")
                continue
            for group in skill.get("required_any", []):
                for tool_id in group:
                    if tool_id not in catalog_ids:
                        errors.append(f"{skill.get('id')}: unknown required tool ID {tool_id}")
            for tool_id in skill.get("recommended", []):
                if tool_id not in catalog_ids:
                    errors.append(f"{skill.get('id')}: unknown recommended tool ID {tool_id}")
    except (OSError, UnicodeError, json.JSONDecodeError, AttributeError, TypeError) as exc:
        errors.append(f"Cannot validate machine-readable Skill tool map: {exc}")

    return errors

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skills-root", type=Path, default=Path("Personal-AI-Library/skills"),
                        help="Path to Personal-AI-Library skills directory")
    parser.add_argument("--map", type=Path, default=Path("CATALOG/SKILL-MAP.md"),
                        help="Path to the human-readable Skill-to-tool map")
    parser.add_argument("--tool-mapping", type=Path, default=Path("CATALOG/skill-tools.json"),
                        help="Path to the machine-readable Skill dependency map")
    parser.add_argument("--catalog", type=Path, default=Path("CATALOG/tools.json"),
                        help="Path to the tool catalog")
    args = parser.parse_args()

    errors = validate(args.skills_root, args.map, args.tool_mapping, args.catalog)
    if errors:
        print("Skill map validation failed:")
        for error in errors:
            print(f" - {error}")
        return 1

    count = len(discover_skills(args.skills_root))
    print(f"Skill map validation passed: all {count} Skills are mapped exactly once.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
