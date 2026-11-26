# Git

- **ID:** `git`
- **Category:** version-control
- **Status:** `tested`
- **Publisher / maintainer:** Git project contributors
- **Official website:** https://git-scm.com/
- **Source repository:** https://github.com/git/git
- **Documentation:** https://git-scm.com/docs
- **License:** GNU GPL version 2 (project COPYING file)
- **Platforms:** Windows, macOS, Linux
- **Version observed in test environment:** 2.47.3
- **Last reviewed:** 2026-11-26

## What it does

Distributed version control: records source changes, supports branches and merges, and synchronizes repositories with remote hosts.

## When an AI agent should use it

Use Git for local repository operations, diffs, branches, commits, tags, and remote synchronization. A GitHub connector or hosted Git service can provide API operations without requiring the Git CLI; do not install Git just to duplicate an already available connector action.

## Requirements and costs

- Runtime / dependencies: standalone native executable; some optional transports and credential helpers have additional dependencies.
- Account required: no for local repositories; remote hosting may require an account.
- API key or token required: only for authenticated remote operations, depending on the host and credential helper.
- Paid features or usage costs: Git itself is free; hosting providers may charge separately.
- Network access: only for remote operations.
- Permissions: reads and writes within the selected working tree; commits change local repository history.

## Installation

Use the official [Git installation page](https://git-scm.com/install/) to select the operating system and a supported installation method. Prefer the OS package manager or official Git for Windows/macOS distribution. Verify the installed version with `git --version`.

Removal is platform/package-manager specific; use the same package manager or official uninstaller used for installation. Do not delete a system-managed binary manually.

## Basic usage

```bash
git status
git diff
git switch -c feature/my-change
git add path/to/file
git commit -m "Describe the change"
```

Review the diff and target branch before committing or pushing. Never commit credentials.

## Verification

- **Environment:** Debian GNU/Linux 13, Linux x86_64, current isolated execution container.
- **Date:** 2026-11-26.
- **Checks performed:** `git --version` reported 2.47.3; initialized a disposable repository; created an empty commit with a temporary test identity; `git rev-parse --is-inside-work-tree` returned `true`.
- **Result:** local repository initialization and commit smoke test passed.
- **Installation tested:** no; Git was pre-existing in the environment.
- **Not tested:** remote authentication, push/pull, credential helpers, GUI clients, Windows/macOS installers.

## Security and limitations

Git does not validate the trustworthiness of repository contents or hooks. Treat cloned repositories, hooks, submodules, filters, and build scripts as untrusted until reviewed. Remote operations can transmit repository data to the configured host. Security advisories were not exhaustively audited during this review.

## Sources

- Official project and documentation: https://git-scm.com/
- Installation: https://git-scm.com/install/
- Source repository and license: https://github.com/git/git/blob/master/COPYING
