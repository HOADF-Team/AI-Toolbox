#!/usr/bin/env python3
"""Offline Bandit smoke test using safe and intentionally unsafe source fixtures."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
FIXTURES = ROOT / "fixtures" / "bandit"


def scan(target: Path) -> dict:
    executable = shutil.which("bandit")
    if executable is None:
        raise SystemExit("Bandit executable not found; install the pinned package first")

    completed = subprocess.run(
        [executable, "-r", str(target), "-f", "json", "--exit-zero"],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise SystemExit(
            f"Bandit failed to scan {target} (exit {completed.returncode}): "
            f"{completed.stderr}"
        )
    try:
        report = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise SystemExit(f"Bandit did not return valid JSON for {target}: {error}") from error
    if report.get("errors"):
        raise SystemExit(f"Bandit reported scan errors for {target}: {report['errors']}")
    return report


def main() -> int:
    print(subprocess.run(
        ["bandit", "--version"], check=True, capture_output=True, text=True
    ).stdout.strip())

    unsafe_report = scan(FIXTURES / "insecure.py")
    unsafe_ids = {item["test_id"] for item in unsafe_report["results"]}
    expected_ids = {"B301", "B602"}
    missing = expected_ids - unsafe_ids
    assert not missing, f"Expected Bandit findings were not reported: {sorted(missing)}"

    safe_report = scan(FIXTURES / "safe.py")
    safe_ids = {item["test_id"] for item in safe_report["results"]}
    assert not safe_ids, f"Unexpected findings in safe fixture: {sorted(safe_ids)}"

    print("unsafe fixture detects B301 and B602: PASS")
    print("safe fixture has zero findings: PASS")
    print("All fixtures were scanned as source; none were executed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
