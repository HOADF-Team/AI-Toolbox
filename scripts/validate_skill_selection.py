#!/usr/bin/env python3
"""Validate a planner-proposed Skill sequence against a workflow and catalog."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from skill_selection import validate_skill_selection  # noqa: E402


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--skill-map", type=Path, default=ROOT / "CATALOG" / "skill-tools.json")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    selection = load_object(args.selection)
    contract = load_object(args.contract)
    skill_map = load_object(args.skill_map)
    report = validate_skill_selection(selection, contract, skill_map)
    rendered = json.dumps(report, ensure_ascii=False, indent=2 if args.pretty else None) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
