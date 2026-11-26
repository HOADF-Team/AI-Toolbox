# mypy

- **ID:** `mypy`
- **Category:** python
- **Status:** `reviewed`
- **Publisher / maintainer:** Python/mypy maintainers and contributors
- **Official website / documentation:** https://www.mypy-lang.org/
- **Source repository:** https://github.com/python/mypy
- **License:** MIT (some bundled portions use separate licenses; see upstream notices)
- **Platforms:** Windows, Linux, macOS; Python package
- **Version reviewed:** 2.4.1
- **Python requirement:** Python 3.10+
- **Last reviewed:** 2026-11-26

## What it does

mypy is a static type checker for Python. It analyzes type annotations and inferred types to find type inconsistencies without executing the application code.

## When an AI agent should use it

Use mypy in Python projects that benefit from explicit type contracts, especially automation, APIs, and larger codebases. Start with the project's configured scope and strictness; do not assume that a clean type check proves runtime correctness.

## Requirements and costs

- Runtime: Python 3.10 or newer for the reviewed release.
- Dependencies: installed by the Python package manager.
- Account / API key: not required.
- Cost: open source; no usage fee.
- Network: required to install or update; not required for local type checking.
- Permissions: reads source files and configuration; does not normally modify project files.

## Installation

Prefer a project-local development environment:

```bash
python -m pip install mypy==2.4.1
```

## Basic usage

```bash
mypy --version
mypy scripts/
```

Configure target Python version, checked files, and strictness in `pyproject.toml`. Use `--strict` only when the project is prepared to satisfy its full set of checks.

## Verification

- **Review environment:** official mypy documentation, repository, PyPI release metadata, and license file.
- **Date:** 2026-11-26.
- **Checks performed:** reviewed official project information, Python compatibility, current release, and license notices.
- **Result:** source and license reviewed; runtime execution and installation not tested.
- **Status limitation:** this record does not claim mypy is installed in the assistant runtime or on the user's computer.

## Security and limitations

mypy is a static analyzer, not a sandbox or runtime test. It cannot validate all dynamic behavior, external data, or untyped dependencies. Review third-party packages before installing them. Upstream notes that some bundled portions have licenses distinct from MIT.

## Sources

- Official website: https://www.mypy-lang.org/
- Documentation: https://mypy.readthedocs.io/
- Repository and license: https://github.com/python/mypy
- PyPI release: https://pypi.org/project/mypy/
