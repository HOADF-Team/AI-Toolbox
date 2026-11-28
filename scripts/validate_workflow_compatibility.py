from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from skill_interfaces import validate_skill_interfaces, validate_workflow_compatibility  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Check workflow artifact compatibility against Skill interfaces.")
    parser.add_argument("--interfaces", type=Path, default=ROOT / "CATALOG" / "skill-interfaces.json")
    parser.add_argument("--workflows", type=Path, default=ROOT / "CATALOG" / "workflows" / "workflows.json")
    parser.add_argument("--skill-map", type=Path, default=ROOT / "CATALOG" / "skill-tools.json")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    interfaces = json.loads(args.interfaces.read_text(encoding="utf-8"))
    workflows = json.loads(args.workflows.read_text(encoding="utf-8"))
    skill_map = json.loads(args.skill_map.read_text(encoding="utf-8"))
    registry_report = validate_skill_interfaces(interfaces, skill_map)
    reports = []
    if registry_report["status"] == "passed":
        for workflow in workflows.get("workflows", []):
            if workflow.get("catalog_status") in {"reviewed", "reviewed_fixture"}:
                reports.append(validate_workflow_compatibility(workflow, interfaces))
    errors = [] if registry_report["status"] == "passed" else registry_report["errors"]
    for report in reports:
        if report["status"] != "passed":
            errors.extend(f"{report['workflow_id']}:{error}" for error in report["errors"])
    result = {"schema_version": "1.0", "status": "passed" if not errors else "failed",
              "interface_registry": registry_report, "workflows": reports, "errors": errors,
              "limitations": ["Draft interfaces are hypotheses, not runtime-verified contracts.",
                              "Compatibility validates artifact type labels only; it does not execute Skills or grant permissions."]}
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
