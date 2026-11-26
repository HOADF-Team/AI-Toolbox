# pandas

- **ID:** `pandas`
- **Category:** python
- **Status:** `tested`
- **Publisher / maintainer:** pandas development team and community contributors
- **Official website:** https://pandas.pydata.org/
- **Source repository:** https://github.com/pandas-dev/pandas
- **Documentation:** https://pandas.pydata.org/docs/
- **License:** BSD 3-Clause
- **Platforms:** Windows, macOS, and Linux on supported Python versions and architectures
- **Latest version reviewed:** 3.1.1 (released 2026-11-04)
- **Runtime version tested:** 2.2.3
- **Last reviewed:** 2026-11-26

## What it does

pandas is a Python library for tabular and time-series data. Its main structures, `DataFrame` and `Series`, support data loading, cleaning, filtering, joining, grouping, aggregation, reshaping, missing-value handling, time-series operations, and export to common formats.

It is a data manipulation and analysis library, not a database server, exchange connector, or chart renderer. It works with NumPy and can connect to many file formats and external systems through optional dependencies.

## When an AI agent should use it

Use pandas when a task involves structured datasets that benefit from labeled columns and rows, such as:

- CSV, JSON, Excel, and Parquet analysis;
- joining and reconciling data from multiple sources;
- time-series preparation and resampling;
- grouping, aggregation, filtering, and missing-data handling;
- preparing data for Matplotlib or other visualization tools;
- transforming logs and tabular exports for audit or reporting.

For small, simple inputs, Python's standard library may be sufficient. For datasets larger than available memory, use a database, chunked processing, or a distributed/dataframe engine rather than assuming a DataFrame will scale without limits.

## Requirements and costs

- **Python:** current pandas 3.1.x requires Python 3.11 or later.
- **Core dependencies:** NumPy 2.0.2 or later and python-dateutil 2.9.0 or later; tzdata is additionally required on Windows and Pyodide.
- **Optional dependencies:** separate extras enable Excel, Parquet, SQL, cloud storage, performance, plotting, and other integrations. Install only the extras needed for the task.
- **Account / API key:** none for local data processing. A remote data provider may require credentials.
- **Cost:** open source; no per-row, per-file, or API fee.
- **Network:** not required for local files after installation. Network access is needed to install packages or read remote sources.
- **Permissions:** reads input files and writes only to destinations explicitly used by the calling program. It may use optional engines for specific file formats.

## Installation

Install the base package in the project's isolated environment:

```bash
python -m pip install pandas
```

With uv:

```bash
uv add pandas
```

Install optional capabilities only when required. For example, the `excel` and `parquet` extras provide format-specific integrations:

```bash
python -m pip install "pandas[excel,parquet]"
```

Verify:

```bash
python -c "import pandas as pd; print(pd.__version__)"
```

Remove from the active environment with:

```bash
python -m pip uninstall pandas
```

Use a project lockfile and pin versions for reproducible analysis. Do not upgrade a project's dependency set automatically without checking compatibility with its other libraries.

## Basic usage

```python
import pandas as pd

df = pd.read_csv("prices.csv")
df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)

summary = (
    df.groupby("symbol", as_index=False)
      .agg(
          average_price=("price", "mean"),
          total_volume=("volume", "sum"),
      )
)
summary.to_csv("summary.csv", index=False)
```

For financial or operational analysis, preserve source timestamps, units, timezone, missing-value policy, and provenance. Never silently forward-fill or drop records if that changes the meaning of the result.

## Verification

- **Environment:** Debian GNU/Linux 13.3 (trixie), x86_64, CPython 3.13.5.
- **Installed dependencies observed:** NumPy 2.3.5.
- **Installed pandas version:** 2.2.3; no installation or upgrade was attempted in this runtime.
- **Functional checks:** created a DataFrame; grouped and aggregated rows; checked expected average and total values; wrote and re-read CSV; wrote and re-read JSON. All assertions passed.
- **CI installation:** pandas 3.1.1 installed successfully from a CPython 3.13 wheel on a GitHub-hosted Ubuntu 26.04 runner (CPython 3.13.18, NumPy 2.5.5).
- **CI functional checks:** DataFrame grouping/aggregation, expected values, CSV round-trip, and JSON round-trip all passed. Run: https://github.com/HOADF-Team/AI-Toolbox/actions/runs/45843529918
- **Additional local runtime check:** pandas 2.2.3 passed the same data operations on Debian GNU/Linux 13.3, CPython 3.13.5, NumPy 2.3.5; no installation was performed there.
- **Scope:** confirms the listed versions and operations on Linux. It does not verify every optional file engine, database connector, or every operating system.
- **Repeatable test:** `python TESTS/smoke_data_analysis.py` (shared smoke test also exercises Matplotlib).

## Security and limitations

- Treat imported files, downloaded datasets, spreadsheet cells, and API responses as untrusted data.
- Do not execute code or shell commands derived from DataFrame contents. Avoid unsafe deserialization formats such as untrusted pickle files.
- CSV and spreadsheet exports may contain formula-like cell values. Sanitize data when producing files intended to be opened in spreadsheet applications.
- Large joins, object-heavy columns, and copies can consume substantial memory. Inspect dtypes and row counts before scaling up.
- Preserve timezone and numeric-unit semantics. pandas will not determine whether a price is USD, EUR, a token unit, or whether timestamps are exchange-local.
- pandas does not validate the provenance, correctness, or completeness of source data.

## Sources

- Official project and current release: https://pandas.pydata.org/
- Official installation and dependency requirements: https://pandas.pydata.org/docs/getting_started/install
- Official user guide and API reference: https://pandas.pydata.org/docs/
- Upstream source and BSD-3-Clause license: https://github.com/pandas-dev/pandas
- PyPI package metadata and release provenance: https://pypi.org/project/pandas/
