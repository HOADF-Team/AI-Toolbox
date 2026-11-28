from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from handoff_payload_schemas import validate_payload_schemas, validate_stage_payloads  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate JSON handoff payloads against field-level schemas.")
    parser.add_argument("--workflow", type=Path, default=ROOT / "CATALOG" / "workflows" / "workflows.json")
    parser.add_argument("--interfaces", type=Path, default=ROOT / "CATALOG" / "skill-interfaces.json")
    parser.add_argument("--schemas", type=Path, default=ROOT / "CATALOG" / "handoff-payload-schemas.json")
    parser.add_argument("--artifacts-dir", type=Path, default=ROOT / "TESTS" / "fixtures" / "inter-skill-demo" / "handoffs")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    workflows = json.loads(args.workflow.read_text(encoding="utf-8"))
    interfaces = json.loads(args.interfaces.read_text(encoding="utf-8"))
    schemas = json.loads(args.schemas.read_text(encoding="utf-8"))
    workflow = next((item for item in workflows.get("workflows", [])
                     if item.get("catalog_status") in {"reviewed", "reviewed_fixture"}), None)
    if workflow is None:
        print(json.dumps({"status": "failed", "errors": ["no_eligible_workflow"]}))
        return 1
    registry = validate_payload_schemas(schemas)
    if registry["status"] != "passed":
        print(json.dumps(registry, ensure_ascii=False, indent=2 if args.pretty else None))
        return 1
    artifacts = [json.loads((args.artifacts_dir / f"{stage['id']}.json").read_text(encoding="utf-8"))
                 for stage in workflow["stages"]]
    report = validate_stage_payloads(workflow, interfaces, schemas, artifacts)
    print(json.dumps(report, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
