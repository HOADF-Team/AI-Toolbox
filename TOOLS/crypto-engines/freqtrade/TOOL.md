# Freqtrade

- **ID:** `freqtrade`
- **Category:** crypto-engines
- **Status:** `reviewed`
- **Publisher / maintainer:** Freqtrade open-source project and contributors
- **Official website / documentation:** https://www.freqtrade.io/
- **Source repository:** https://github.com/freqtrade/freqtrade
- **License:** GPL-3.0-only
- **Reviewed source:** upstream `develop` branch and versioned exchange documentation, 2026-11-26
- **Runtime:** Python >= 3.12 in the reviewed current project metadata
- **Platforms:** Linux, macOS and Windows through Docker-supported workflows
- **Last reviewed:** 2026-11-26

## What it provides

Freqtrade is a candle-based strategy engine built on CCXT. It adds functionality that CCXT itself does not provide:
- strategy lifecycle and signal processing using pandas DataFrames;
- historical backtesting and result analysis;
- Hyperopt strategy parameter optimization;
- dry-run mode before live execution;
- Telegram, REST API, CLI and FreqUI control surfaces;
- SQLite persistence for bot state and trades;
- optional FreqAI features.

Freqtrade and CCXT are complementary layers: Freqtrade uses CCXT underneath for exchange API calls. Adding Freqtrade does not replace or invalidate the existing CCXT record.

## Exchange compatibility relevant to HOADF-Team

The official exchange-specific support table reviewed on 2026-11-26 lists:
- **BingX:** Spot only.
- **Binance:** Spot and futures (isolated and cross margin modes listed).
- **Bybit:** Spot and futures (isolated margin mode listed).

BingX is not listed in the supported futures table. Do not treat the general presence of a CCXT BingX adapter as proof that Freqtrade supports BingX USDT-M perpetual trading.

Freqtrade's documentation says other CCXT exchanges may sometimes work, but they are not part of the explicitly supported list and may lack exchange-specific protections such as on-exchange stoploss. That is not sufficient evidence for production use.

## Installation and dependencies

- Current project metadata requires Python >= 3.12.
- Core dependencies include CCXT, SQLAlchemy, pandas, NumPy, TA-Lib, FastAPI and other packages; this is a substantial environment, not a lightweight SDK.
- Official installation guide: https://www.freqtrade.io/en/stable/installation/
- Docker is a documented deployment option and is the preferred evaluation path for a disposable environment.
- Do not install on the user's computer during discovery.

## License and cost

- GPL-3.0-only. Review copyleft obligations before embedding, modifying, distributing, or offering a network-accessible derivative service.
- No license fee for the open-source software itself; hosting, exchange fees and optional infrastructure are separate.

## Verification

- **Source/license review:** completed against upstream `LICENSE` and `pyproject.toml`.
- **Exchange support review:** completed against the official exchange matrix.
- **Installation/runtime:** not tested in AI-Toolbox CI. Status remains `reviewed`.
- **Next verification:** isolated Docker install, dry-run/paper workflow and read-only public market-data checks. No API keys or real orders.

## Sources

- Official exchange support matrix: https://www.freqtrade.io/en/2026.8/exchanges/
- Official current project metadata and dependencies: https://github.com/freqtrade/freqtrade/blob/develop/pyproject.toml
- GPL-3.0 license: https://github.com/freqtrade/freqtrade/blob/develop/LICENSE
- Freqtrade vs CCXT architecture comparison: https://github.com/ccxt/ccxt/blob/master/wiki/comparisons/ccxt-vs-freqtrade.md
- Official installation: https://www.freqtrade.io/en/stable/installation/
