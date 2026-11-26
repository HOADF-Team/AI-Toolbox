# ta.py (ta_py)

- **ID:** `ta-py`
- **Category:** crypto
- **Status:** `reviewed`
- **Publisher / maintainer:** Nino Kroesen; upstream repository identifies a single maintainer
- **PyPI package:** https://pypi.org/project/ta_py/
- **Source repository:** https://github.com/Bitvested/ta.py
- **Documentation / examples:** https://github.com/Bitvested/ta.py
- **License:** MIT
- **Platforms:** CPython-compatible platforms; pure Python package
- **Version reviewed:** 2.1.0 (PyPI release 2026-10-10)
- **Requirements:** Python >= 3.10; no runtime dependencies
- **Last reviewed:** 2026-11-26

## Why it is selected

The crypto workflow already has CCXT for exchange market data, pandas for time-series preparation, and Matplotlib for charts. A dedicated indicator library fills the missing calculation layer without introducing native extensions or another large numerical stack.

The upstream project describes 151 indicators and statistical/time-series functions, including SMA/EMA, RSI, MACD, ATR, Bollinger Bands, ADX, VWAP, Ichimoku, CCI, SuperTrend, and related utilities.

## Installation

Use a pinned version in an isolated project environment:

```bash
python -m pip install "ta_py==2.1.0"
```

With uv:

```bash
uv add "ta_py==2.1.0"
```

Basic usage:

```python
import ta_py as ta

closes = [100, 101, 102, 101, 103, 105, 104]
sma = ta.sma(closes, 3)
rsi = ta.rsi(closes, 3)
```

The library accepts ordinary Python sequences. Convert DataFrame columns explicitly when working with pandas:

```python
rsi_values = ta.rsi(df["close"].tolist(), 14)
```

## Safety and data semantics

- This library calculates indicators; it does not retrieve exchange data, execute trades, or validate market-data quality.
- Preserve candle order, timestamp, timezone, symbol, market type, and source venue.
- Decide explicitly whether a candle is closed before using its values. An in-progress candle can change and can create look-ahead or signal-repainting errors if treated as final.
- Check each indicator's warm-up length and output alignment before joining results back to candle timestamps.
- Do not assume all indicators use identical smoothing conventions or match TradingView/TA-Lib outputs without parity tests.
- Version 2.0 introduced documented output/algorithm changes for several functions, including ATR, SMMA, MFI, RSI, and Stochastic. Pin the version and review upstream migration notes before upgrades.
- PyPI currently reports one maintainer and no release provenance for the reviewed files; this is a supply-chain review note, not evidence of malicious behavior.

## Verification

- **Source/license review:** completed; MIT license and package metadata reviewed.
- **Installation/runtime:** not yet tested in AI-Toolbox CI.
- **Repeatable smoke test:** `python TESTS/smoke_crypto_research.py` (shared test covers ta.py and backtesting.py).
- Status must remain `reviewed` until the isolated CI installation and indicator assertions pass.

## Sources

- PyPI package, version, Python requirement, release date and MIT license: https://pypi.org/project/ta_py/
- Upstream source and README: https://github.com/Bitvested/ta.py
- Upstream migration notes: https://github.com/Bitvested/ta.py/blob/master/MIGRATION.md
