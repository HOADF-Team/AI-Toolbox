# Ruff

- **ID:** `ruff`
- **Category:** python
- **Status:** `reviewed`
- **Publisher / maintainer:** Astral and contributors
- **Official website / documentation:** https://docs.astral.sh/ruff/
- **Source repository:** https://github.com/astral-sh/ruff
- **License:** MIT (current releases; verify bundled notices when redistributing)
- **Platforms:** Windows, Linux, macOS; official wheels are platform-specific
- **Version reviewed:** 0.17.6
- **Last reviewed:** 2026-11-26

## What it does

Ruff is a fast Python linter and formatter. It detects common errors and style issues, and can automatically format code and organize imports.

## When an AI agent should use it

Use Ruff for repeatable lint checks in Python repositories and, when the project opts in, formatting. Follow the project's existing configuration rather than applying broad autofixes without review.

## Requirements and costs

- Runtime: Python package distributed with platform-specific executable wheels.
- Account / API key: not required.
- Cost: open source; no usage fee.
- Network: required to install or update from package indexes; not required for local checks.
- Permissions: reads source files and configuration; autofix/format commands modify files.

## Installation

Prefer a project-local development environment:

```bash
python -m pip install ruff==0.17.6
```

## Basic usage

```bash
ruff --version
ruff check scripts/
ruff format --check scripts/
```

Use `ruff check --fix` or `ruff format` only after reviewing the proposed scope; these commands can change files.

## Verification

- **Review environment:** repository and official package/release metadata; no local executable detected in the current isolated runtime.
- **Date:** 2026-11-26.
- **Checks performed:** reviewed official project documentation, repository, PyPI release information, and license metadata.
- **Result:** source and license reviewed; runtime execution and installation not tested.
- **Status limitation:** this record does not claim Ruff is installed in the assistant runtime or on the user's computer.

## Security and limitations

Ruff analyzes code; it does not prove correctness or security. Review automatic fixes before accepting them. Install only from the official package index or trusted distribution channel and pin versions in CI for reproducibility.

## Sources

- Documentation: https://docs.astral.sh/ruff/
- Repository and license: https://github.com/astral-sh/ruff
- PyPI release: https://pypi.org/project/ruff/
