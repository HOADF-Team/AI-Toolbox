from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from skill_interfaces import validate_skill_interfaces  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate draft Skill interface metadata.")
    parser.add_argument("--interfaces", type=Path, default=ROOT / "CATALOG" / "skill-interfaces.json")
    parser.add_argument("--skill-map", type=Path, default=ROOT / "CATALOG" / "skill-tools.json")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    catalog = json.loads(args.interfaces.read_text(encoding="utf-8"))
    skill_map = json.loads(args.skill_map.read_text(encoding="utf-8"))
    report = validate_skill_interfaces(catalog, skill_map)
    print(json.dumps(report, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
