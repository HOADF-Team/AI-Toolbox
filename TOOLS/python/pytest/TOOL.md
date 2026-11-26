# pytest

- **ID:** `pytest`
- **Category:** python
- **Status:** `tested`
- **Publisher / maintainer:** pytest-dev contributors
- **Official website:** https://pytest.org/
- **Source repository:** https://github.com/pytest-dev/pytest
- **Documentation:** https://docs.pytest.org/en/stable/
- **License:** MIT
- **Platforms:** Windows, macOS, Linux / POSIX; requires a supported Python version
- **Version observed in test environment:** 9.0.2
- **Last reviewed:** 2026-11-26

## What it does

pytest is a Python test framework with assertion introspection, fixtures, parametrization, plugins, and command-line test discovery.

## When an AI agent should use it

Use pytest to run or author tests for Python projects. Follow the project's existing test framework and configuration. Do not add pytest to a project that uses another test runner unless the task justifies the change.

## Requirements and costs

- Runtime / dependencies: Python; pytest is distributed as a Python package.
- Account required: no.
- API key or token required: no.
- Paid features or usage costs: open source; third-party plugins may have separate terms.
- Network access: package installation and tests that call external services may use the network; ordinary local tests do not need it.
- Permissions: test code runs with the permissions of the invoking user and can modify files or external systems.

## Installation

Install into a project virtual environment, not into the operating system's Python:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install pytest
```

If the project uses uv, prefer `uv add --dev pytest`. Remove it with `python -m pip uninstall pytest` inside the same environment, or `uv remove --dev pytest` when managed by uv.

## Basic usage

```bash
python -m pytest
python -m pytest -q
python -m pytest tests/test_example.py
```

## Verification

- **Environment:** Debian GNU/Linux 13, Linux x86_64, Python 3.13.5, current isolated execution container.
- **Date:** 2026-11-26.
- **Checks performed:** `pytest --version` reported 9.0.2; created a temporary test containing one assertion and ran `python -m pytest -q`.
- **Result:** 1 test passed.
- **Installation tested:** no; pytest was pre-existing in the environment.
- **Not tested:** plugin compatibility, async test plugins, coverage integrations, Windows/macOS environments.

## Security and limitations

Tests are arbitrary Python code and can access files, network, and credentials available to the process. Run untrusted test suites in an isolated environment without production credentials. Plugins execute code and must be reviewed separately. pytest itself does not provide a security sandbox.

## Sources

- Official documentation: https://docs.pytest.org/en/stable/
- Getting started and virtual-environment guidance: https://docs.pytest.org/en/stable/getting-started.html
- License: https://github.com/pytest-dev/pytest/blob/main/LICENSE
- Package metadata: https://pypi.org/project/pytest/
