"""Validate the repository workflow template catalog."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from workflow_catalog import validate_workflow_catalog


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=Path("CATALOG/workflows/workflows.json"))
    parser.add_argument("--skill-map", type=Path, default=Path("CATALOG/skill-tools.json"))
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    try:
        catalog: dict[str, Any] = json.loads(args.catalog.read_text(encoding="utf-8"))
        skill_map: dict[str, Any] = json.loads(args.skill_map.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "failed", "error": type(exc).__name__}))
        return 2
    report = validate_workflow_catalog(catalog, skill_map)
    print(json.dumps(report, indent=2 if args.pretty else None, ensure_ascii=False))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
