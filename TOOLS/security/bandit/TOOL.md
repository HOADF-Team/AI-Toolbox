# Bandit

- **ID:** `bandit`
- **Category:** security
- **Status:** `reviewed`
- **Publisher / maintainer:** PyCQA (Python Code Quality Authority)
- **Official website:** https://bandit.readthedocs.io/en/latest/
- **Source repository:** https://github.com/PyCQA/bandit
- **Documentation:** https://bandit.readthedocs.io/en/latest/
- **License:** Apache-2.0
- **Platforms:** Linux and macOS are listed by the project classifiers; Windows is not independently verified in this record.
- **Latest version reviewed:** 1.9.4 (released 2026-02-25)
- **Last reviewed:** 2026-11-26

## What it does

Bandit is a Python security linter. It parses Python source files into abstract syntax trees and runs security-focused plugins against those nodes. It can report patterns such as unsafe deserialization, shell invocation, weak cryptographic primitives, hard-coded credentials, unsafe temporary-file handling, and other risky constructs.

Bandit complements the Personal-AI-Library `code-audit` AST script: that script checks syntax, imports, and code structure, while Bandit applies security-specific rules. The current AI-Toolbox Ruff configuration selects basic E/F rules and does not select Ruff's S security rule family.

## When an AI agent should use it

Use Bandit during a read-only Python security review or as a CI check when a project contains Python source code.

Recommended workflow:

1. Inspect the repository structure and identify first-party Python source directories.
2. Exclude virtual environments, generated code, vendored dependencies, and test fixtures that intentionally contain unsafe examples.
3. Run Bandit recursively and retain a JSON report.
4. Review each finding in context; distinguish an unsafe pattern from an exploitable vulnerability.
5. Confirm input provenance, reachability, runtime configuration, and mitigations before assigning severity.
6. Fix confirmed issues and rerun the affected scan.

Example:

```bash
bandit -r src/ -f json -o bandit-report.json
```

Show only high-severity findings:

```bash
bandit -r src/ -lll
```

Bandit is a pattern-based static analyzer, not a full interprocedural/data-flow SAST engine. It does not scan JavaScript/TypeScript, audit third-party dependency vulnerabilities, or establish that a project is secure.

## Requirements and costs

- **Python:** 3.10 or later; upstream package classifiers include Python 3.10–3.14.
- **Dependencies:** installed by pip from package metadata; no external service is required for local scans.
- **Account / API key:** none.
- **Cost:** free and open source under Apache-2.0.
- **Network:** package-index access is needed for installation; scanning local source files does not require network access.
- **Permissions:** reads source files and writes a report only when an output path is specified. It does not import or execute the target project as part of its normal AST scan.
- **Optional extras:** `bandit[toml]` for TOML configuration support; `bandit[sarif]` for SARIF reporting; `bandit[baseline]` for the baseline CLI.

## Installation

Install in a dedicated project environment:

```bash
python -m pip install bandit==1.9.4
```

With uv:

```bash
uv add --dev bandit==1.9.4
```

Verify:

```bash
bandit --version
```

Remove from the active environment:

```bash
python -m pip uninstall bandit
```

Pin the version in a lockfile for reproducible CI. Do not install into a system Python environment managed by the operating system.

## Configuration and reporting

Bandit can use a `.bandit` INI file or an explicitly selected YAML/TOML configuration. TOML configuration requires the `toml` extra:

```bash
python -m pip install "bandit[toml]==1.9.4"
bandit -c pyproject.toml -r src/
```

It supports text, JSON, CSV, XML, HTML, YAML, and other report formats depending on installed extras. JSON reports can be used for automation and baselines.

A `# nosec` comment suppresses a finding on that line. Use narrow, documented suppressions such as `# nosec B602 -- fixed command and reviewed input`; do not blanket-suppress findings or use `# nosec` as a substitute for remediation.

## Verification

- **Source and license review:** official PyCQA repository, security policy, documentation, and Apache-2.0 license reviewed on 2026-11-26.
- **Version reviewed:** 1.9.4, latest release found on PyPI on the review date.
- **Installation test:** pending isolated CI installation.
- **Runtime test:** pending isolated CI test against safe and intentionally unsafe source fixtures.
- **Planned checks:** install Bandit 1.9.4 on a GitHub-hosted Linux runner; confirm it reports expected rule IDs B301 (unsafe pickle deserialization) and B602 (subprocess with `shell=True`) in a fixture; confirm a safe fixture has no findings.
- **Safety:** fixtures are scanned as source text; no insecure function is executed.
- **Limitations:** the planned smoke test will not verify every plugin, every platform, custom configuration, or every real-project finding.

## Security and limitations

- Bandit findings are indicators requiring human review, not proof of exploitability. False positives and false negatives are possible.
- Its AST-based checks do not perform comprehensive taint tracking or interprocedural data-flow analysis. A clean report does not prove that user input is handled safely.
- Bandit does not audit third-party package vulnerabilities, dependency licenses, containers, infrastructure, JavaScript/TypeScript, or runtime behavior.
- Never run the intentionally insecure test fixtures. They exist only for static scanning.
- Review exclusions, test selections, baselines, and `# nosec` suppressions; an overly broad configuration can hide real findings.
- Do not put secrets or private source code into third-party online scanners. Local Bandit scanning does not upload code.

## Sources

- Official project overview and security scanning model: https://bandit.readthedocs.io/en/latest/
- Official installation and getting-started guide: https://bandit.readthedocs.io/en/latest/start.html
- CLI options, recursive scans, JSON and severity filters: https://bandit.readthedocs.io/en/latest/man/bandit.html
- JSON report format: https://bandit.readthedocs.io/en/latest/formatters/json.html
- Configuration, baselines, and suppressions: https://bandit.readthedocs.io/en/latest/config.html
- Upstream repository and security policy: https://github.com/PyCQA/bandit
- Upstream Apache-2.0 license: https://github.com/PyCQA/bandit/blob/main/LICENSE
- PyPI package metadata and release provenance: https://pypi.org/project/bandit/
