# Crypto trading engine compatibility

**Reviewed:** 2026-11-26  
**Primary venue:** BingX  
**Secondary venues:** Binance and Bybit  
**Purpose:** separate framework capability from exchange-adapter and product support. This is a research decision record, not approval for live trading.

## Exchange / product matrix

| Framework | BingX Spot | BingX USDT-M Perpetual | Binance Spot / Futures | Bybit Spot / Futures | Current conclusion |
|---|---|---|---|---|---|
| CCXT | Supported adapter; public spot smoke test passed | Supported adapter; public swap metadata smoke test passed | Adapters included; GitHub Runner endpoint tests geo-blocked | Adapters included; GitHub Runner endpoint tests geo-blocked | Exchange API layer only; no strategy engine, risk manager, persistence or UI |
| Hummingbot | Official connector listed | Not listed in upstream connector inventory | Spot and perpetual connectors listed | Spot and perpetual connectors listed | Strong strategy/execution framework, but BingX perpetual gap |
| Freqtrade | Officially supported | Not listed in official futures support table | Spot and futures listed | Spot and futures listed | Strong candle-strategy/backtesting workflow, but BingX perpetual gap |

## What the frameworks solve

### Hummingbot
- Script/controller/executor strategy model and order lifecycle building blocks.
- Strong fit for order-book-aware strategies, market making, arbitrage and execution workflows.
- Apache-2.0.
- Requires a comparatively involved Conda/source or Docker deployment.
- BingX connector is currently Spot only in upstream inventory.

### Freqtrade
- Candle-based strategy engine, backtesting, Hyperopt, dry-run, Telegram/FreqUI and SQLite persistence.
- CCXT is its exchange layer.
- GPL-3.0-only.
- Requires Python >= 3.12 in current project metadata and a substantial dependency set.
- BingX Spot is listed; BingX futures is not listed in the official supported exchange matrix.

### CCXT with a dedicated execution/risk layer
- CCXT already has the broadest documented BingX market coverage in this project: BingX spot and USDT-M swap market metadata passed read-only CI checks.
- It can cover the exchange adapter layer for BingX, Binance and Bybit, subject to per-venue endpoint and product validation.
- It does not supply the strategy engine, durable order state, risk controls, operator UI or recovery logic. Those components would need to be designed and tested separately.
- For a BingX-perpetual-first system, this is currently the only reviewed route in this matrix that does not immediately exclude BingX USDT-M at the adapter layer. It is not yet a tested live execution system.

## Decision gates before choosing an engine

1. Confirm whether the first trading product is spot or USDT-M perpetual.
2. Confirm whether the same strategy must run across all three exchanges or whether BingX is the first venue and others are later adapters.
3. Validate exact product/account semantics: one-way vs hedge mode, isolated/cross margin, leverage, quantity/price precision, minimum notional, reduce-only, trigger/stop orders, funding and liquidation data.
4. Use demo/test environments and read-only checks first. No real order submission during framework evaluation.
5. Define the risk layer independently of the framework: max position and notional, max daily loss, per-symbol exposure, stale-data guard, duplicate-order prevention, kill switch, reconciliation after disconnects, and auditable state transitions.
6. Keep API credentials out of GitHub, CI logs, fixtures and AI prompts. No withdrawal permission.

## Current recommendation

- **If BingX Spot is the first product:** evaluate Freqtrade and Hummingbot in isolated environments; compare candle-strategy workflow (Freqtrade) with order-book/execution workflow (Hummingbot).
- **If BingX USDT-M Perpetual is required from the start:** do not select either framework as-is. Evaluate a CCXT-based custom execution/risk layer or build/maintain a dedicated BingX perpetual connector for a framework. The latter creates an ongoing adapter-maintenance obligation.
- Binance and Bybit remain in scope. Their earlier HTTP 451/403 responses were restrictions on the GitHub Runner's region, not evidence that their CCXT adapters are broken.

## Sources

- CCXT exchange adapters and verification record: `TOOLS/crypto/ccxt/TOOL.md`
- Hummingbot connector inventory: https://github.com/hummingbot/hummingbot#exchange-connectors
- Hummingbot Apache-2.0 license and installation: https://github.com/hummingbot/hummingbot/blob/master/LICENSE and https://hummingbot.org/installation/
- Freqtrade exchange support matrix: https://www.freqtrade.io/en/2026.8/exchanges/
- Freqtrade current Python/dependency metadata: https://github.com/freqtrade/freqtrade/blob/develop/pyproject.toml
- Freqtrade vs CCXT: https://github.com/ccxt/ccxt/blob/master/wiki/comparisons/ccxt-vs-freqtrade.md
