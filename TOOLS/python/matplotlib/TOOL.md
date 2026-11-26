# Matplotlib

- **ID:** `matplotlib`
- **Category:** python
- **Status:** `tested`
- **Publisher / maintainer:** Matplotlib Development Team and community contributors
- **Official website:** https://matplotlib.org/
- **Source repository:** https://github.com/matplotlib/matplotlib
- **Documentation:** https://matplotlib.org/stable/
- **License:** Python Software Foundation License (Matplotlib versions 1.3.0 and later)
- **Platforms:** Windows, macOS, and Linux on supported Python versions and architectures
- **Latest version reviewed:** 3.11.2 (released 2026-09-11)
- **Runtime version tested:** 3.10.8
- **Last reviewed:** 2026-11-26

## What it does

Matplotlib is a Python library for static, animated, and interactive visualizations. Its `pyplot` interface and object-oriented figure/axes API support line charts, bars, scatter plots, histograms, heatmaps, and many specialized plot types.

It can export figures to PNG, PDF, SVG, and other formats. Non-interactive backends such as Agg, PDF, and SVG work in headless environments. Interactive desktop windows require a compatible GUI backend and its system dependencies.

## When an AI agent should use it

Use Matplotlib when a task needs reproducible charts from Python data, including:

- time-series and financial charts;
- comparisons, distributions, and statistical summaries;
- charts embedded in reports, PDFs, or presentations;
- batch rendering on a server or in CI;
- customized axes, labels, annotations, and multi-panel figures.

Matplotlib is a plotting library, not a data-cleaning framework. Pair it with pandas or NumPy when appropriate. Use the Agg backend for automated/headless rendering; do not assume a desktop display server or GUI toolkit is available.

## Requirements and costs

- **Python:** current Matplotlib 3.11.x supports Python 3.11 and later.
- **Core dependency:** NumPy; other Python dependencies are installed from package metadata and wheels.
- **Optional dependencies:** GUI toolkits such as Tk or Qt are needed for corresponding interactive backends; LaTeX and other integrations have additional requirements.
- **Account / API key:** none.
- **Cost:** open source; no per-chart fee.
- **Network:** not required for local plotting after installation. Package installation requires package-index access.
- **Permissions:** reads data supplied by the calling program and writes image/document files to requested paths. Rendering untrusted files or fonts should be handled in an isolated environment.

## Installation

Install in the project's isolated Python environment:

```bash
python -m pip install matplotlib
```

With uv:

```bash
uv add matplotlib
```

Verify:

```bash
python -c "import matplotlib; print(matplotlib.__version__)"
```

For a headless environment, select Agg before importing pyplot:

```python
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
```

Remove from the active environment with:

```bash
python -m pip uninstall matplotlib
```

Use pinned versions and a lockfile for reproducible report generation.

## Basic usage

```python
import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt

fig, ax = plt.subplots()
ax.plot([1, 2, 3], [4, 2, 5], marker="o")
ax.set(title="Example trend", xlabel="Period", ylabel="Value")
fig.savefig("trend.png", dpi=150, bbox_inches="tight")
plt.close(fig)
```

For reports, label axes with units, state the date range, distinguish missing data from zero, and avoid misleading scales or truncated axes.

## Verification

- **Environment:** Debian GNU/Linux 13.3 (trixie), x86_64, CPython 3.13.5.
- **Installed Matplotlib version:** 3.10.8; no installation or upgrade was attempted in this runtime.
- **Functional check:** rendered a bar chart with the Agg backend, saved it as PNG, reopened the file, and verified PNG format and dimensions (640 × 480). Passed.
- **Related data preparation:** pandas 2.2.3 grouped and aggregated the input before plotting.
- **CI installation:** Matplotlib 3.11.2 installed successfully from a CPython 3.13 wheel on a GitHub-hosted Ubuntu 26.04 runner (CPython 3.13.18, NumPy 2.5.5).
- **CI functional check:** the Agg backend rendered a PNG; the test verified PNG signature and 640 × 480 dimensions. Passed. Run: https://github.com/HOADF-Team/AI-Toolbox/actions/runs/45843529918
- **Additional local runtime check:** Matplotlib 3.10.8 passed the same headless PNG check on Debian GNU/Linux 13.3, CPython 3.13.5; no installation was performed there.
- **Scope:** confirms headless PNG rendering with the listed versions on Linux. It does not verify GUI backends, interactive windows, animation writers, every output format, or other operating systems.
- **Repeatable test:** `python TESTS/smoke_data_analysis.py` (shared smoke test also exercises pandas).

## Security and limitations

- Treat imported data, labels, annotations, and generated report files as potentially sensitive.
- Avoid rendering untrusted external files or fonts in a privileged environment.
- A chart is a representation of its input, not proof that the source data or statistical method is correct.
- Backend availability differs between headless servers and desktop environments. Use Agg for CI and explicitly test the GUI backend required by a desktop application.
- Matplotlib does not retrieve market data, calculate financial indicators, or validate the semantics of the plotted values.

## Sources

- Official project and current documentation: https://matplotlib.org/stable/
- Official installation and backend guidance: https://matplotlib.org/stable/install/
- Official getting-started guide: https://matplotlib.org/stable/users/getting_started/
- Upstream license: https://github.com/matplotlib/matplotlib/blob/main/LICENSE/LICENSE
- PyPI package metadata, supported Python versions, and release files: https://pypi.org/project/matplotlib/
