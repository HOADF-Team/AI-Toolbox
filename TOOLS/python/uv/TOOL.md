# uv

- **ID:** `uv`
- **Category:** python
- **Status:** `tested`
- **Publisher / maintainer:** Astral Software Inc.
- **Official website:** https://docs.astral.sh/uv/
- **Source repository:** https://github.com/astral-sh/uv
- **Documentation:** https://docs.astral.sh/uv/
- **License:** MIT or Apache License 2.0, at the user's option
- **Platforms:** Tier 1: macOS arm64/x86_64, Linux x86_64, Windows x86_64; additional Tier 2/3 targets are documented upstream
- **Version observed in test environment:** 0.10.0
- **Last reviewed:** 2026-11-26

## What it does

uv is a fast Python package and project manager. It can create and manage virtual environments, resolve and install dependencies, manage Python versions, and run Python tools and scripts.

## When an AI agent should use it

Use uv when a project already uses it or when a reproducible Python environment and lockfile are useful. Do not introduce uv into a project that already has a suitable, functioning workflow without a concrete benefit. It can replace several overlapping Python packaging tools, so avoid adding redundant managers.

## Requirements and costs

- Runtime / dependencies: standalone native executable; no Python installation is required for the standalone binary.
- Account required: no.
- API key or token required: no for public package indexes; private indexes may require credentials.
- Paid features or usage costs: open source; package indexes and infrastructure may have separate costs.
- Network access: required to fetch packages or Python distributions; not required for local commands.
- Permissions: writes project environments, caches, lockfiles, and managed Python installations.

## Installation

Official installation methods include versioned standalone installers and package managers. Review the installer before executing it; prefer a pinned version and avoid unreviewed `curl | sh` execution. Official instructions: https://docs.astral.sh/uv/getting-started/installation/

Example for macOS/Linux after reviewing the script:

```bash
curl -LsSf https://astral.sh/uv/0.10.0/install.sh -o /tmp/uv-install.sh
less /tmp/uv-install.sh
sh /tmp/uv-install.sh
```

On Windows, use the official PowerShell instructions or WinGet. Removal depends on installation method; use the official uninstall instructions and remove only uv-managed files. Do not remove project environments or caches without checking whether they are shared or needed.

## Basic usage

```bash
uv init example
cd example
uv add --dev pytest
uv run pytest
uv lock
uv sync
```

## Verification

- **Environment:** Debian GNU/Linux 13, Linux x86_64, current isolated execution container.
- **Date:** 2026-11-26.
- **Checks performed:** `uv --version` reported 0.10.0; `uv help` completed successfully.
- **Result:** executable startup and CLI help smoke test passed.
- **Installation tested:** no; uv was pre-existing in the environment.
- **Not tested:** downloading packages, creating Python environments, lockfile resolution, self-update, installer, Windows/macOS behavior.

## Security and limitations

Package installation executes build backends and may install native code. Review dependencies and lockfiles, use project isolation, and do not pass credentials in command-line arguments. The official installer can modify PATH/shell configuration unless configured otherwise. Security advisories were not exhaustively audited during this review.

## Sources

- Official documentation: https://docs.astral.sh/uv/
- Installation: https://docs.astral.sh/uv/getting-started/installation/
- Platform support: https://docs.astral.sh/uv/reference/platforms/
- Source repository and dual license: https://github.com/astral-sh/uv
- Apache-2.0: https://github.com/astral-sh/uv/blob/main/LICENSE-APACHE
- MIT: https://github.com/astral-sh/uv/blob/main/LICENSE-MIT
