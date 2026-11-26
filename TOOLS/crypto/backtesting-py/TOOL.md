# backtesting.py

- **ID:** `backtesting-py`
- **Category:** crypto
- **Status:** `reviewed` (runtime test pending)
- **Publisher / maintainer:** kernc / backtesting.py contributors
- **Official documentation:** https://kernc.github.io/backtesting.py/
- **Source repository:** https://github.com/kernc/backtesting.py
- **PyPI package:** https://pypi.org/project/backtesting/
- **License:** AGPL-3.0-or-later (AGPLv3+)
- **Platforms:** Windows, Linux, macOS where supported Python dependencies are available
- **Version reviewed:** 0.6.6 (PyPI release 2026-07-22)
- **Requirements:** Python >= 3.9; pandas, NumPy, and Bokeh are among the runtime dependencies
- **Last reviewed:** 2026-11-26

## Why it is selected

The project needs a reproducible way to evaluate a strategy against historical candles before any live execution layer is considered. backtesting.py provides an event-driven strategy API, OHLC data handling, trade/equity statistics, commissions, spread, and parameter optimization.

It complements rather than replaces CCXT:
- CCXT retrieves exchange market data.
- pandas prepares and audits time-series data.
- ta.py calculates indicators.
- backtesting.py simulates strategy decisions against historical OHLC data.
- Matplotlib renders analysis charts.
- Python's standard-library sqlite3 can persist local research metadata/results when a database is needed; a separate SQLite server is unnecessary.

## Important license condition

The project is licensed under AGPL-3.0-or-later. This is materially different from MIT/BSD libraries. Use in an internal research environment is not the same as incorporating or modifying it in a distributed or network-accessible product. Before embedding, modifying, or offering a service based on it, obtain a license review for the intended deployment and distribution model. Do not assume this is a permissive dependency.

## Installation

Install a pinned version in an isolated research environment:

```bash
python -m pip install "backtesting==0.6.6"
```

With uv:

```bash
uv add "backtesting==0.6.6"
```

A strategy is implemented by subclassing `Strategy` and defining `init()` and `next()`. Input data should be an OHLC DataFrame with a datetime index and the required Open, High, Low, Close columns; Volume is optional.

## Backtesting limitations and controls

- It is a historical simulation framework, not an exchange connector or live trading bot.
- Its core model is bar/OHLC-oriented; it does not automatically reproduce queue position, order-book depth, partial fills, exchange latency, funding payments, liquidation engines, or every venue-specific contract rule.
- Do not infer USDT-M perpetual support or exchange integration from the package's general ability to model long/short positions. Derivatives accounting must be modeled and validated separately.
- Configure commission, spread, and assumptions explicitly. Add conservative slippage and execution assumptions where appropriate.
- Prevent look-ahead bias: indicators/signals must use only data available at the simulated decision time.
- Separate in-sample and out-of-sample periods; account for parameter overfitting and survivorship/data-selection bias.
- A positive historical result is not evidence of future profitability.
- No live orders, API credentials, or exchange write permissions are needed for backtesting.

## Verification

- **Source/license review:** completed; AGPL-3.0-or-later reviewed from upstream documentation and PyPI metadata.
- **Installation/runtime:** not yet tested in AI-Toolbox CI.
- **Repeatable smoke test:** `python TESTS/smoke_crypto_research.py` (shared test covers ta.py and backtesting.py).
- Status must remain `reviewed` until the isolated CI installation and deterministic synthetic-data backtest pass.

## Sources

- Official documentation and API guide: https://kernc.github.io/backtesting.py/doc/backtesting/
- Upstream source and license: https://github.com/kernc/backtesting.py
- PyPI version, Python requirement, release files and AGPL license: https://pypi.org/project/backtesting/
