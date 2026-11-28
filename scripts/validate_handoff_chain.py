#!/usr/bin/env python3
"""Validate a generic JSON handoff chain from a declarative contract."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from handoff_contract import validate_handoff_chain


def read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--artifacts-dir", type=Path, required=True)
    parser.add_argument("--context", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    contract = read_object(args.contract)
    artifacts = [
        read_object(args.artifacts_dir / f"{stage['id']}.json")
        for stage in contract["stages"]
    ]
    context = read_object(args.context) if args.context else {}
    report = validate_handoff_chain(contract, artifacts, context)
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(rendered + "\\n", encoding="utf-8")
    print(rendered)
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
