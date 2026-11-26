#!/usr/bin/env python3
"""Validate that AI-Toolbox maps every real Personal-AI-Library Skill exactly once."""
from __future__ import annotations

import argparse
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


def validate(skills_root: Path, map_path: Path) -> list[str]:
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

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skills-root", type=Path, default=Path("Personal-AI-Library/skills"),
                        help="Path to Personal-AI-Library skills directory")
    parser.add_argument("--map", type=Path, default=Path("CATALOG/SKILL-MAP.md"),
                        help="Path to the Skill-to-tool map")
    args = parser.parse_args()

    errors = validate(args.skills_root, args.map)
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
