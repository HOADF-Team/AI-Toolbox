# Hummingbot

- **ID:** `hummingbot`
- **Category:** crypto-engines
- **Status:** `reviewed`
- **Publisher / maintainer:** Hummingbot Foundation and open-source contributors
- **Official website / documentation:** https://hummingbot.org/
- **Source repository:** https://github.com/hummingbot/hummingbot
- **License:** Apache-2.0
- **Reviewed source:** upstream `master` branch, 2026-11-26
- **Platforms:** Linux and macOS; Windows deployment should use a documented Docker/WSL path and be verified separately
- **Installation:** source/Conda workflow or Docker; upstream currently documents the `hbot` CLI and Docker Compose deployment
- **Last reviewed:** 2026-11-26

## What it provides

Hummingbot is a strategy and execution framework, not just an exchange SDK. Its current codebase includes:
- Python strategy scripts and reusable V2 controllers;
- order lifecycle executors for position, DCA, grid, arbitrage, TWAP and other patterns;
- centralized and decentralized exchange connectors;
- paper-trading connectors and CLI operations for bot lifecycle, status, logs and PnL;
- a web/API-oriented operating model and encrypted exchange-key storage.

The upstream README currently recommends a Conda-based source install for the `hbot` CLI or Docker Compose. The codebase is substantial; installation and operational complexity are higher than installing a single Python package.

## Exchange compatibility relevant to HOADF-Team

The upstream connector inventory reviewed on 2026-11-26 lists:
- **BingX:** Spot connector (`bing_x`) only.
- **Binance:** Spot and perpetual connectors.
- **Bybit:** Spot and perpetual connectors.

Do not infer BingX USDT-M perpetual support from the existence of the BingX spot connector. If BingX perpetuals are required as the primary market, Hummingbot does not currently satisfy the complete exchange/product matrix without a separately developed and maintained connector.

Connector presence is not a guarantee that every product, account mode, order type, region, or API endpoint works. Each exact connector and product must pass public-data and paper/demo tests before any live use.

## Installation and operational notes

- Follow the official installation documentation: https://hummingbot.org/installation/
- Prefer Docker or a disposable Linux VM for initial evaluation.
- Do not install on the user's machine as part of catalog discovery.
- The upstream README describes encrypted key storage; no API keys are required for source review or paper trading.
- Keep live keys outside repositories and CI. Use least-privilege keys and disable withdrawals.
- The current README describes one bot per installation for the `hbot` CLI workflow; verify multi-instance orchestration requirements before planning production deployment.

## License and cost

- Apache License 2.0.
- Open-source software; exchange fees, VPS/cloud costs, and optional external services remain separate.
- Apache-2.0 is materially more permissive than GPL/AGPL for many commercial integration scenarios, subject to preserving notices and reviewing third-party dependencies.

## Verification

- **Source and license review:** completed against upstream README and LICENSE.
- **Connector review:** completed against upstream connector inventory; BingX spot only, Binance and Bybit spot/perpetual.
- **Installation/runtime:** not tested in AI-Toolbox CI. Status remains `reviewed`.
- **Next verification:** isolated install, paper-trading connector checks, and read-only public market-data tests. No real orders or API secrets.

## Sources

- Upstream README and current operating model: https://github.com/hummingbot/hummingbot
- Apache-2.0 license: https://github.com/hummingbot/hummingbot/blob/master/LICENSE
- Connector inventory: https://github.com/hummingbot/hummingbot#exchange-connectors
- Official installation: https://hummingbot.org/installation/
