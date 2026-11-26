#!/usr/bin/env python3
"""Read-only inventory of selected developer tools in the current runtime."""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone

COMMANDS = {
    "git": ["--version"],
    "gh": ["--version"],
    "python3": ["--version"],
    "uv": ["--version"],
    "pytest": ["--version"],
    "ruff": ["--version"],
    "node": ["--version"],
    "npm": ["--version"],
    "lighthouse": ["--version"],
    "pandoc": ["--version"],
    "libreoffice": ["--version"],
    "pdftotext": ["-v"],
    "pdfinfo": ["-v"],
    "tesseract": ["--version"],
}
MODULES = ["pytest", "ruff", "playwright", "pandas", "PIL", "docx", "openpyxl"]


def probe_version(path: str, args: list[str]) -> str | None:
    try:
        result = subprocess.run(
            [path, *args], capture_output=True, text=True, timeout=4, check=False
        )
        output = (result.stdout or result.stderr).strip().splitlines()
        return output[0][:240] if output else None
    except (OSError, subprocess.SubprocessError):
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = parser.parse_args()

    commands = {}
    for name, version_args in COMMANDS.items():
        path = shutil.which(name)
        commands[name] = {
            "installed": path is not None,
            "path": path,
            "version": probe_version(path, version_args) if path else None,
        }

    modules = {}
    for name in MODULES:
        try:
            spec = importlib.util.find_spec(name)
            modules[name] = {"available": spec is not None}
        except (ImportError, ValueError, ModuleNotFoundError):
            modules[name] = {"available": False}

    report = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "current_process_environment_only",
        "environment": {
            "os": platform.system(),
            "os_release": platform.release(),
            "architecture": platform.machine(),
            "python_executable": sys.executable,
            "python_version": platform.python_version(),
            "virtual_env": os.environ.get("VIRTUAL_ENV"),
        },
        "commands": commands,
        "python_modules": modules,
        "safety": {
            "read_only": True,
            "network_access": False,
            "installation_attempted": False,
            "note": (
                "Absence from this report does not prove absence on another "
                "host or user device."
            ),
        },
    }
    print(json.dumps(report, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
