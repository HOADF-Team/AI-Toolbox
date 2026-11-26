# Initial exchange integration matrix

**Reviewed:** 2026-11-26  
**Adapter:** CCXT 4.5.94  
**Policy:** public market-data validation first; no private credentials or order-writing calls.

| Priority | Venue | CCXT id | Initial scope | Current evidence |
|---|---|---|---|---|
| Primary | BingX | `bingx` | Spot ticker/markets; USDT-M swap metadata | **Passed** public spot ticker and USDT-M swap metadata checks in isolated CI |
| Secondary | Binance | `binance` | Spot ticker/markets | Adapter is listed; public test blocked by HTTP 451 restricted-location response from GitHub runner; not marked tested |
| Secondary | Bybit | `bybit` | Spot ticker/markets | Adapter is listed; public test blocked by CloudFront HTTP 403 runner-region restriction; not marked tested |
| Secondary | OKX | `okx` | Spot ticker/markets | **Passed** public spot ticker and market metadata check in isolated CI |

## Interpretation

- “Supported by CCXT” means an adapter exists in the upstream supported-exchange list. It does not mean every endpoint, order type, account mode, derivatives contract, or region is supported.
- Each venue's public test is reported independently. A network or regional restriction is a blocked test, not proof that the adapter is broken.
- BingX is the priority reference venue. Secondary venues are compatibility targets, not a requirement to open accounts or trade on them.
- Do not store exchange credentials in this repository or CI.
- No order placement, cancellation, transfer, withdrawal, leverage change, or account mutation is allowed in the smoke suite.

## Expansion gates

Before enabling any private account integration, verify the venue's official API documentation, current product and regional availability, API-key permission model, IP restrictions, rate limits, precision/lot rules, and sandbox/demo behavior. Start with read-only credentials. Trading permissions require a separate explicit project decision and isolated tests.
