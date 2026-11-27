#!/usr/bin/env python3
"""Run the non-mutating inventory, catalog match, and Skill preflight as one command."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from check_skill_tools import check_skill  # noqa: E402
from match_inventory import match_catalog  # noqa: E402


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def run_preflight(
    skill_ids: list[str] | None = None,
    mapping_path: Path = ROOT / "CATALOG" / "skill-tools.json",
    catalog_path: Path = ROOT / "CATALOG" / "tools.json",
) -> dict[str, Any]:
    """Collect a fresh local inventory and evaluate selected Skills."""
    mapping = load_json(mapping_path)
    catalog = load_json(catalog_path)
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "inventory.py")],
        cwd=ROOT, capture_output=True, text=True, timeout=60, check=False,
    )
    if completed.returncode:
        raise RuntimeError(
            f"inventory.py exited {completed.returncode}: {completed.stderr.strip()}"
        )
    inventory = json.loads(completed.stdout)
    matches = match_catalog(catalog, inventory)
    skill_map = {
        item["id"]: item for item in mapping.get("skills", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    selected = skill_ids or sorted(skill_map)
    unknown = [skill_id for skill_id in selected if skill_id not in skill_map]
    if unknown:
        raise ValueError("Unknown Skill ID(s): " + ", ".join(unknown))
    results = [check_skill(skill_map[skill_id], matches) for skill_id in selected]
    counts = {
        state: sum(item["readiness"] == state for item in results)
        for state in ("ready", "blocked", "unknown")
    }
    return {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": inventory.get("scope", "unknown"),
        "safety": inventory.get("safety", {}),
        "summary": {"skills_total": len(results), "readiness": counts,
                    "tools_total": matches["catalog_match"]["total"],
                    "tool_availability": matches["catalog_match"]["counts"]},
        "skills": results,
        "inventory": inventory,
        "tool_matches": matches,
        "limitations": [
            "This report covers only the environment where this command was run.",
            "Detected availability is not a functional test or proof of credentials/service access.",
            "Preflight checks declared prerequisites; it does not execute Skill workflows.",
            "No installation, network request by the inventory itself, remote-host scan, or system modification is requested.",
            "Detected PATH binaries are executed with fixed version/help arguments; they are not sandboxed and may have tool-specific side effects.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skill", action="append", dest="skills",
                        help="Skill ID; repeat to check several. Defaults to all mapped Skills.")
    parser.add_argument("--mapping", type=Path,
                        default=ROOT / "CATALOG" / "skill-tools.json")
    parser.add_argument("--catalog", type=Path,
                        default=ROOT / "CATALOG" / "tools.json")
    parser.add_argument("--output", type=Path,
                        help="Optional path for the JSON report; stdout is the default.")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    try:
        report = run_preflight(args.skills, args.mapping, args.catalog)
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    rendered = json.dumps(report, ensure_ascii=False,
                          indent=2 if args.pretty else None) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
