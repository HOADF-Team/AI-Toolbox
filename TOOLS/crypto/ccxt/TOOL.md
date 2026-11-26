# CCXT

- **ID:** `ccxt`
- **Category:** crypto
- **Status:** `reviewed`
- **Verification note:** promote to `tested` only after the multi-exchange CI smoke test passes.
- **Publisher / maintainer:** CCXT project maintainers; independent open-source project
- **Official website / documentation:** https://docs.ccxt.com/
- **Source repository:** https://github.com/ccxt/ccxt
- **Package:** https://pypi.org/project/ccxt/
- **License:** MIT
- **Platforms:** OS-independent Python package; requires Python 3.10 or later for the reviewed release
- **Version reviewed:** 4.5.94 (PyPI release 2026-11-23)
- **Last reviewed:** 2026-11-26

## Why it is selected

CCXT provides one normalized API for public market data and private exchange operations across many centralized and decentralized exchanges. The current supported-exchange list includes BingX, Binance, Bybit, and OKX. One library therefore covers the selected initial exchange group; separate community SDKs for each venue are not required for the common workflows.

**Priority order for this project:**
1. **BingX — primary venue.** First integration to validate and the default reference implementation.
2. Binance — secondary compatibility target.
3. Bybit — secondary compatibility target.
4. OKX — secondary compatibility target.

The exchange matrix in `TOOLS/crypto/ccxt/EXCHANGE-MATRIX.md` records scope and test evidence separately. Support in CCXT's exchange list is not proof that every endpoint or product works identically.

## Capabilities

- Public spot market data: markets, tickers, order books, trades, OHLCV candles.
- Derivatives market data where implemented: swap/futures markets, funding rates, open interest and contract metadata.
- Private account and trading methods when correctly configured with exchange API credentials.
- Unified order, balance, position and trade structures, with exchange-specific differences retained where necessary.
- Built-in per-instance rate limiting; enable it explicitly in application code.
- Sandbox/test/demo environments only where supported by the specific exchange adapter. Sandbox APIs and product coverage are not uniform.
- WebSocket streaming is available through CCXT Pro functionality in the package; availability and method coverage vary by exchange.

## Installation

Use an isolated Python environment and pin the version used by the project:

```bash
python -m pip install "ccxt==4.5.94"
```

With uv:

```bash
uv add "ccxt==4.5.94"
```

Verify:

```bash
python -c "import ccxt; print(ccxt.__version__); print([x for x in ('bingx', 'binance', 'bybit', 'okx') if x in ccxt.exchanges])"
```

## Safe first-run policy

- Begin with public market-data endpoints only; no API key is needed for public market data.
- Do not request, create, store, or transmit exchange secrets during discovery or smoke tests.
- Do not call `create_order`, `cancel_order`, transfer, withdrawal, leverage, margin-mode, or other write/private methods during validation.
- If private access is later needed, create a dedicated API key with read-only permissions first; restrict IPs where the exchange supports it. Never enable withdrawals.
- Enable CCXT's rate limiter and respect the venue's documented limits. Do not run concurrent polling loops without explicit per-exchange throttling.
- Keep credentials outside the repository, logs, test fixtures, prompts, and generated reports. Use environment variables or a dedicated secrets manager.
- Verify symbol notation, contract type, settlement currency, quantity/price precision, minimum order sizes, fees, funding intervals, and market status per venue. Never assume that a unified symbol makes product rules identical.

Example — public-only ticker request:

```python
import ccxt

exchange = ccxt.bingx({"enableRateLimit": True, "timeout": 20000})
try:
    ticker = exchange.fetch_ticker("BTC/USDT")
    print({"symbol": ticker["symbol"], "last": ticker["last"], "timestamp": ticker["timestamp"]})
finally:
    exchange.close()
```

## Requirements and cost

- Python >= 3.10 for the reviewed release.
- No account or API key for public market-data endpoints.
- No paid CCXT subscription for the standard unified REST API.
- Network access is required to contact exchange APIs.
- Exchange account, API-key permissions, regional availability, product eligibility, and trading fees are controlled by each exchange, not by CCXT.
- WebSocket streaming and exchange coverage depend on implemented methods and the chosen exchange.

## Known limitations

- CCXT is a third-party adapter, not an official BingX/Binance/Bybit/OKX SDK.
- Unified method names do not erase exchange-specific behavior, parameters, rate limits, symbol formats, account modes, or order semantics.
- Some exchange endpoints or product lines may be unsupported, incomplete, unstable, region-restricted, or changed upstream.
- Public data may be delayed, incomplete, revised, or unavailable; retain source venue, symbol, market type, retrieval timestamp, and raw provenance for research.
- Sandbox/demo support is venue-specific. Confirm the exact host and API-key environment before using it.
- CCXT does not provide a trading strategy, profitability guarantee, portfolio risk model, tax report, or investment advice.
- Do not treat an API response or a successful test as permission to trade real funds.

## Verification plan

A GitHub Actions smoke test will install the pinned release in a disposable runner and use public endpoints only for:
- BingX spot (primary);
- BingX USDT-margined perpetual/swap market metadata, where supported;
- Binance spot;
- Bybit spot;
- OKX spot.

The test must report each venue independently. A failure or geo-block for a secondary venue must not be represented as a successful integration. No private keys or order-writing calls are part of this test.

## Sources

- CCXT supported exchanges: https://docs.ccxt.com/docs/exchange-markets
- CCXT manual and unified API: https://docs.ccxt.com/docs/manual
- CCXT installation: https://docs.ccxt.com/docs/install
- CCXT BingX integration comparison: https://docs.ccxt.com/docs/comparisons/ccxt-vs-bingx-api
- CCXT Bybit integration comparison: https://docs.ccxt.com/docs/comparisons/ccxt-vs-bybit-api
- PyPI release metadata, version, Python requirement, and MIT license: https://pypi.org/project/ccxt/
- BingX official API/AI skill references: https://github.com/BingX-API/api-ai-skills
