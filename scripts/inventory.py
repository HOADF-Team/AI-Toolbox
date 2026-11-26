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
    "curl": ["--version"],
    "jq": ["--version"],
    "redocly": ["--version"],
    "bandit": ["--version"],
    "gh": ["--version"],
    "python": ["--version"],
    "python3": ["--version"],
    "uv": ["--version"],
    "pytest": ["--version"],
    "ruff": ["--version"],
    "mypy": ["--version"],
    "node": ["--version"],
    "npm": ["--version"],
    "npx": ["--version"],
    "lighthouse": ["--version"],
    "pandoc": ["--version"],
    "libreoffice": ["--version"],
    "pdftotext": ["-v"],
    "pdfinfo": ["-v"],
    "pdftoppm": ["-v"],
    "pdftocairo": ["-v"],
    "tesseract": ["--version"],
    "magick": ["-version"],
    "exiftool": ["-ver"],
    "gimp": ["--version"],
    "rembg": ["--help"],
    "ffmpeg": ["-version"],
    "ffprobe": ["-version"],
    "chromium": ["--version"],
}

PYTHON_MODULES = [
    "pytest", "ruff", "mypy", "playwright", "pandas", "PIL", "docx",
    "openpyxl", "reportlab", "cv2", "rembg", "imageio", "matplotlib", "bandit",
]
NODE_PACKAGES = ["playwright", "lighthouse", "axe-core", "@redocly/cli"]


def probe(args: list[str], timeout: int = 4) -> str | None:
    try:
        result = subprocess.run(
            args, capture_output=True, text=True, timeout=timeout, check=False
        )
        output = (result.stdout or result.stderr).strip().splitlines()
        return output[0][:240] if output else None
    except (OSError, subprocess.SubprocessError):
        return None


def probe_node_package(name: str) -> dict[str, str | bool | None]:
    node = shutil.which("node")
    if not node:
        return {"available": False, "resolved_path": None}
    source = (
        "try { process.stdout.write(require.resolve(process.argv[1])); } "
        "catch (_) { process.exitCode = 1; }"
    )
    try:
        result = subprocess.run(
            [node, "-e", source, name],
            capture_output=True,
            text=True,
            timeout=4,
            check=False,
        )
        resolved = result.stdout.strip() if result.returncode == 0 else None
        return {"available": resolved is not None, "resolved_path": resolved}
    except (OSError, subprocess.SubprocessError):
        return {"available": False, "resolved_path": None}


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
            "version_or_help": probe([path, *version_args]) if path else None,
        }

    python_modules = {}
    for name in PYTHON_MODULES:
        try:
            spec = importlib.util.find_spec(name)
            python_modules[name] = {"available": spec is not None}
        except (ImportError, ValueError, ModuleNotFoundError):
            python_modules[name] = {"available": False}

    node_packages = {
        name: probe_node_package(name) for name in NODE_PACKAGES
    }

    report = {
        "schema_version": "1.1",
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
        "python_modules": python_modules,
        "node_packages": node_packages,
        "safety": {
            "read_only": True,
            "network_access": False,
            "installation_attempted": False,
            "note": (
                "Checks PATH, Python import discovery, and Node.js module "
                "resolution from the current working directory. It does not "
                "scan other hosts, user devices, or global package stores."
            ),
        },
    }
    print(json.dumps(report, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
