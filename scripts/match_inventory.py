#!/usr/bin/env python3
"""Match a runtime inventory report to AI-Toolbox catalog records."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

# Each catalog ID maps to one or more alternative probes. A probe is a
# (inventory section, key) pair; alternatives are OR-ed, not AND-ed.
PROBES: dict[str, list[tuple[str, str]]] = {
    "git": [("commands", "git")],
    "python": [("commands", "python"), ("commands", "python3")],
    "uv": [("commands", "uv")],
    "pytest": [("commands", "pytest"), ("python_modules", "pytest")],
    "nodejs": [("commands", "node")],
    "playwright": [("python_modules", "playwright"), ("node_packages", "playwright")],
    "lighthouse": [("commands", "lighthouse"), ("node_packages", "lighthouse")],
    "axe-core": [("node_packages", "axe-core")],
    "libreoffice": [("commands", "libreoffice")],
    "pandoc": [("commands", "pandoc")],
    "poppler-utils": [("commands", "pdftotext"), ("commands", "pdfinfo"),
                      ("commands", "pdftoppm"), ("commands", "pdftocairo")],
    "tesseract": [("commands", "tesseract")],
    "imagemagick": [("commands", "magick")],
    "exiftool": [("commands", "exiftool")],
    "ruff": [("commands", "ruff"), ("python_modules", "ruff")],
    "mypy": [("commands", "mypy"), ("python_modules", "mypy")],
    "ffmpeg": [("commands", "ffmpeg")],
    "gimp": [("commands", "gimp")],
    "rembg": [("commands", "rembg"), ("python_modules", "rembg")],
    "curl": [("commands", "curl")],
    "jq": [("commands", "jq")],
    "redocly-cli": [("commands", "redocly"), ("node_packages", "@redocly/cli")],
    "schemathesis": [("commands", "schemathesis"), ("python_modules", "schemathesis")],
    "pandas": [("python_modules", "pandas")],
    "matplotlib": [("python_modules", "matplotlib")],
    "bandit": [("commands", "bandit"), ("python_modules", "bandit")],
    "gitleaks": [("commands", "gitleaks")],
    "pip-audit": [("commands", "pip-audit"), ("python_modules", "pip_audit")],
    "trivy": [("commands", "trivy")],
    "age": [("commands", "age")],
    "restic": [("commands", "restic")],
    "ccxt": [("commands", "ccxt"), ("python_modules", "ccxt")],
    "ta-py": [("python_modules", "ta")],
    "backtesting-py": [("python_modules", "backtesting")],
    "hummingbot": [("commands", "hummingbot"), ("python_modules", "hummingbot")],
    "freqtrade": [("commands", "freqtrade"), ("python_modules", "freqtrade")],
    "mockoon-cli": [("commands", "mockoon-cli")],
    "podman": [("commands", "podman")],
}

def probe_available(report: dict[str, Any], section: str, key: str) -> bool | None:
    group = report.get(section)
    if not isinstance(group, dict) or key not in group:
        return None
    item = group[key]
    if not isinstance(item, dict):
        return None
    if section == "commands":
        value = item.get("installed")
    else:
        value = item.get("available")
    return value if isinstance(value, bool) else None


def match_catalog(catalog: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for tool in catalog.get("tools", []):
        if not isinstance(tool, dict) or not isinstance(tool.get("id"), str):
            continue
        tool_id = tool["id"]
        probes = PROBES.get(tool_id)
        if probes is None:
            results.append({
                "id": tool_id,
                "name": tool.get("name", tool_id),
                "catalog_record": tool.get("record"),
                "availability": "not_probed",
                "evidence": [],
                "note": "No runtime probe is configured for this catalog ID.",
            })
            continue
        evidence = []
        values: list[bool] = []
        for section, key in probes:
            available = probe_available(report, section, key)
            if available is not None:
                values.append(available)
                evidence.append({"source": section, "key": key, "available": available})
        if not values:
            status = "not_probed"
        elif any(values):
            status = "available"
        else:
            status = "missing"
        results.append({
            "id": tool_id,
            "name": tool.get("name", tool_id),
            "catalog_record": tool.get("record"),
            "availability": status,
            "evidence": evidence,
        })
    counts = {key: sum(item["availability"] == key for item in results)
              for key in ("available", "missing", "not_probed")}
    return {
        "schema_version": "1.0",
        "inventory_scope": report.get("scope", "unknown"),
        "generated_at": report.get("generated_at"),
        "catalog_match": {"total": len(results), "counts": counts},
        "tools": results,
        "limitations": [
            "Availability means a configured executable/module/package probe was detected.",
            "It does not prove functional correctness, compatibility, credentials, or service access.",
            "A catalog record without a configured probe is reported as not_probed, never as missing.",
            "The inventory describes only the environment in which it was generated.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, required=True,
                        help="JSON report produced by scripts/inventory.py")
    parser.add_argument("--catalog", type=Path, default=Path("CATALOG/tools.json"))
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    try:
        report = json.loads(args.inventory.read_text(encoding="utf-8"))
        catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    if not isinstance(report, dict) or not isinstance(catalog, dict):
        parser.error("Inventory and catalog roots must be JSON objects.")
    result = match_catalog(catalog, report)
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
