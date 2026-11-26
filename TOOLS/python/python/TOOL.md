# Python

- **ID:** `python`
- **Category:** python
- **Status:** `tested`
- **Publisher / maintainer:** Python Software Foundation and Python core developers
- **Official website:** https://www.python.org/
- **Source repository:** https://github.com/python/cpython
- **Documentation:** https://docs.python.org/3/
- **License:** Python Software Foundation License Version 2 (PSF-2.0)
- **Platforms:** Windows, macOS, Linux; availability and packaging vary by distribution
- **Version observed in test environment:** 3.13.5
- **Last reviewed:** 2026-11-26

## What it does

Python is an interpreted programming language and runtime used for scripts, automation, backend services, data processing, testing, and tooling.

## When an AI agent should use it

Use Python for general scripting, automation, API clients, data processing, and project-specific applications. First inspect the target project's Python version and environment. Prefer the existing interpreter and a project-local virtual environment over a global package installation.

## Requirements and costs

- Runtime / dependencies: Python interpreter; third-party packages are optional and have their own requirements and licenses.
- Account required: no.
- API key or token required: only when a particular application or external API requires one.
- Paid features or usage costs: Python is open source; infrastructure and external services may cost money.
- Network access: not required for local scripts; package installation and networked applications may require it.
- Permissions: scripts inherit the permissions of the user running them.

## Installation

Use the official [Python downloads](https://www.python.org/downloads/) for Windows and macOS, or the target Linux distribution's supported package manager. Avoid replacing a system-managed Python on Linux.

Create an isolated environment for a project:

```bash
python3 -m venv .venv
# Linux/macOS
. .venv/bin/activate
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
python -m pip install package-name
```

Remove a project environment by deleting its `.venv` directory after confirming it contains no needed data. Remove a system installation only through the original installer or package manager.

## Basic usage

```bash
python --version
python script.py
python -m pytest
```

Use `python -m pip` so package installation targets the interpreter being invoked.

## Verification

- **Environment:** Debian GNU/Linux 13, Linux x86_64, current isolated execution container.
- **Date:** 2026-11-26.
- **Checks performed:** `python --version` reported 3.13.5; executed `python -c 'assert 2 + 2 == 4'`; ran the repository's Python environment inventory script.
- **Result:** interpreter startup and script execution passed.
- **Installation tested:** no; Python was pre-existing in the environment.
- **Not tested:** building Python from source, Windows/macOS installers, package installation in a fresh environment, ABI compatibility of third-party extensions.

## Security and limitations

Python scripts execute with the caller's permissions. Review third-party packages, setup hooks, build backends, and scripts before execution. Use virtual environments; do not install packages into a system-managed interpreter. Python distributions may bundle third-party components with their own licenses.

## Sources

- Official website and downloads: https://www.python.org/
- Official documentation: https://docs.python.org/3/
- License terms: https://docs.python.org/3/license.html
- Source repository: https://github.com/python/cpython
