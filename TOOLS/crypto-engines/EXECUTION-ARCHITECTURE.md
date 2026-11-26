# Crypto paper-trading architecture

**Status:** proposed implementation blueprint  
**Reviewed:** 2026-11-26  
**Primary exchange:** BingX  
**Secondary exchanges:** Binance, Bybit  
**Exchange adapter:** CCXT (pinned; see TOOLS/crypto/ccxt/TOOL.md)  
**Execution policy:** paper trading only; live order submission is out of scope.

This document defines the boundary between the AI-Toolbox catalog and a future standalone trading application. AI-Toolbox remains a catalog and verification repository; the application itself should live in a separate repository owned by HOADF-Team.

## 1. First release scope

The first usable milestone is a read-only market-data collector plus deterministic paper broker:

- Spot market data for BingX, Binance and Bybit.
- BingX USDT-M perpetual market metadata and public market data.
- Binance and Bybit derivatives remain adapter targets, but are not considered verified until their endpoints pass from an allowed network environment.
- Ticker, order book, trades, OHLCV, market metadata and (where supported) funding-rate reads.
- Local paper portfolio, simulated fills, fees and PnL.
- Historical replay and deterministic tests using recorded fixtures.
- No exchange credentials in the first milestone.

Do not claim an exchange/product combination is supported merely because its CCXT class exists. Track evidence independently for each venue, market type and endpoint.

## 2. Proposed application layout

    app/
      api/                 # REST API; no exchange logic in routes
      core/
        config.py          # validated configuration; safe defaults
        clock.py           # injectable clock for replay/tests
        events.py          # typed domain events
      exchanges/
        base.py            # normalized read-only adapter protocol
        ccxt_adapter.py    # CCXT implementation and symbol mapping
        capabilities.py    # venue/product/endpoint capability matrix
      market_data/
        models.py          # ticker, book, trade, candle, funding models
        collector.py       # throttled polling and reconnect policy
        validation.py      # stale/outlier/incomplete data guards
      portfolio/
        ledger.py          # append-only simulated cash/position ledger
        valuation.py       # marked-to-market portfolio valuation
      paper/
        broker.py          # simulated order lifecycle and fill model
        matching.py        # deterministic fill rules
        fees.py            # configurable fee schedules
      risk/
        limits.py          # exposure, position and loss limits
        guards.py          # stale data, duplicate intents, kill switch
      strategies/
        protocol.py        # strategy interface; strategies emit intents only
      storage/
        repository.py      # persistence abstraction
      tests/
        unit/
        integration/
        fixtures/

The initial implementation should be a modular monolith, not microservices. Keep exchange I/O, strategy decisions, risk validation, simulated execution and persistence as separate modules with explicit interfaces.

## 3. Data flow and safety boundary

1. The collector requests public data through the exchange adapter.
2. The adapter normalizes data while preserving venue, market type, native symbol, retrieval timestamp and raw provenance.
3. Validation rejects stale, malformed, crossed or incomplete market data before it reaches a strategy.
4. A strategy emits an immutable OrderIntent; it cannot call CCXT directly.
5. The risk layer validates the intent and either rejects it with a reason or passes it to the paper broker.
6. The paper broker simulates fills and writes ledger events. It has no exchange order-writing method.
7. Portfolio valuation and audit views are derived from the ledger; they do not mutate balances.

**Hard invariant:** the first release must not expose or call CCXT methods such as create_order, cancel_order, edit_order, transfers, withdrawals, leverage changes or margin-mode changes. The application should not request exchange API keys at all.

A future live-trading capability would require a separate design review, a separate adapter interface, explicit user approval and independent safety tests. It must not be enabled by changing a configuration flag in the paper broker.

## 4. Domain contracts

Minimum normalized records:

- MarketKey(venue, market_type, symbol)
- Ticker(market_key, bid, ask, last, timestamp, received_at)
- OrderBook(market_key, bids, asks, timestamp, received_at)
- Candle(market_key, timeframe, open_time, OHLCV, is_closed)
- FundingRate(market_key, rate, next_funding_at, received_at)
- OrderIntent(id, strategy_id, market_key, side, order_type, quantity, limit_price, created_at)
- RiskDecision(intent_id, accepted, reason_codes, checked_at)
- PaperOrder(id, intent_id, status, filled_quantity, average_price, fee)
- LedgerEvent(id, event_type, asset, amount, reference, occurred_at)

Use Decimal for prices, quantities, fees and balances. Floats are allowed only at external parsing boundaries and must be converted with explicit decimal-string handling. All timestamps are UTC internally.

## 5. Minimum risk controls for paper mode

Even simulated execution must exercise the same controls expected in a production-grade system:

- maximum position quantity and notional per symbol;
- maximum portfolio gross exposure;
- maximum daily realized loss and drawdown;
- per-venue and per-market exposure caps;
- stale-data and missing-book guards;
- price-deviation and spread guards;
- duplicate-intent/idempotency protection;
- quantity, tick-size, lot-size and minimum-notional validation;
- deterministic kill switch that rejects all new intents;
- explicit rejection reasons and append-only audit events.

Risk limits must fail closed. Missing configuration, missing price, unknown market rules or invalid timestamps must reject an intent rather than silently use permissive defaults.

## 6. Paper fill model

The first fill model should be deliberately conservative and deterministic:

- Market buys consume ask-side depth; market sells consume bid-side depth.
- Limit orders fill only when subsequent observed trades or book conditions satisfy the documented matching rule.
- If available depth is insufficient, the remainder stays unfilled or expires according to explicit time-in-force.
- Apply configurable maker/taker fees; never assume zero fees.
- Include configurable slippage and latency assumptions for replay.
- Record the exact market-data event IDs used to simulate every fill.

Do not use a single ticker's last price as a realistic fill price. Do not describe paper results as actual exchange execution or expected profitability.

## 7. Test gates

Before calling the first milestone usable:

1. Unit tests for Decimal arithmetic, market normalization, symbol mapping, risk limits and ledger invariants.
2. Deterministic paper-broker tests for partial fills, fees, slippage, rejected orders and idempotency.
3. Replay tests against frozen fixtures; no network required.
4. Public integration smoke tests for BingX Spot and BingX USDT-M.
5. Independent Binance and Bybit tests. A regional/network block is reported as blocked, never passed or adapter broken.
6. Static check that the paper application contains no exchange order-writing call paths.
7. CI must run without secrets and without write permissions to exchange accounts.

## 8. Implementation sequence

- **M0 — Contracts and safety:** domain models, configuration, adapter protocol, capability matrix and static safety checks.
- **M1 — Market data:** CCXT read-only adapter, BingX-first integration and independent secondary-venue reporting.
- **M2 — Paper broker:** deterministic order lifecycle, fills, fees, ledger and portfolio valuation.
- **M3 — Risk layer:** limits, stale-data guards, idempotency and kill switch.
- **M4 — Replay and API:** historical replay, read-only status endpoints and minimal operator interface.
- **M5 — Hardening:** persistence recovery, observability, packaging and deployment documentation.

Each milestone must be a pull request with tests and an explicit verification report. No live trading is included in this roadmap.

## 9. Current evidence and unresolved items

- CCXT 4.5.94 is pinned in AI-Toolbox.
- BingX Spot public ticker and BingX USDT-M swap market metadata have passed the recorded smoke test.
- Binance and Bybit adapters are present in CCXT, but the current GitHub Runner's regional restrictions prevented endpoint verification.
- The existing smoke workflow includes OKX as an extra catalog check; OKX is not part of the initial product scope in this blueprint.
- Private account reads, demo-account semantics, fees, funding, position mode, margin mode and liquidation data have not been validated for the intended application.
- No exchange credentials have been requested or used. No orders have been submitted.

## Related records

- CCXT tool record: ../crypto/ccxt/TOOL.md
- CCXT exchange matrix: ../crypto/ccxt/EXCHANGE-MATRIX.md
- Engine compatibility decision: ENGINE-COMPATIBILITY.md
