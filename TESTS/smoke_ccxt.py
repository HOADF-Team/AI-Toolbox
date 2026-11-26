#!/usr/bin/env python3
"""Public-only CCXT smoke checks; never places or modifies orders."""
from __future__ import annotations

import json
import sys
import time

import ccxt


VENUES = ("bingx", "binance", "bybit", "okx")
RESULTS: list[dict[str, object]] = []


def check_spot(exchange_id: str) -> dict[str, object]:
    exchange_class = getattr(ccxt, exchange_id)
    exchange = exchange_class({
        "enableRateLimit": True,
        "timeout": 25000,
        "options": {"defaultType": "spot"},
    })
    try:
        markets = exchange.load_markets()
        if "BTC/USDT" not in markets:
            raise RuntimeError("BTC/USDT spot market is not listed by this adapter")
        ticker = exchange.fetch_ticker("BTC/USDT")
        last = ticker.get("last")
        if not isinstance(last, (int, float)) or last <= 0:
            raise RuntimeError(f"Ticker returned invalid last price: {last!r}")
        return {
            "venue": exchange_id,
            "market_type": "spot",
            "status": "passed",
            "symbol": ticker.get("symbol"),
            "last_price_present": True,
            "markets_loaded": len(markets),
        }
    finally:
        exchange.close()


def check_bingx_swap() -> dict[str, object]:
    exchange = ccxt.bingx({
        "enableRateLimit": True,
        "timeout": 25000,
        "options": {"defaultType": "swap"},
    })
    try:
        markets = exchange.load_markets()
        candidates = [
            symbol for symbol, market in markets.items()
            if symbol in ("BTC/USDT:USDT", "BTC/USDT") and market.get("swap")
        ]
        if not candidates:
            raise RuntimeError("No BTC/USDT swap market found in BingX market metadata")
        return {
            "venue": "bingx",
            "market_type": "swap",
            "status": "passed",
            "symbol": candidates[0],
            "markets_loaded": len(markets),
        }
    finally:
        exchange.close()


def main() -> int:
    print(f"CCXT version: {ccxt.__version__}")
    required_version = "4.5.94"
    if ccxt.__version__ != required_version:
        raise SystemExit(f"Expected CCXT {required_version}, got {ccxt.__version__}")

    for index, venue in enumerate(VENUES):
        try:
            result = check_spot(venue)
        except Exception as error:  # report exchange/network errors per venue
            result = {
                "venue": venue,
                "market_type": "spot",
                "status": "failed",
                "error_type": type(error).__name__,
                "error": str(error)[:500],
            }
        RESULTS.append(result)
        print(json.dumps(result, ensure_ascii=False))
        if index < len(VENUES) - 1:
            time.sleep(1)

    try:
        swap_result = check_bingx_swap()
    except Exception as error:
        swap_result = {
            "venue": "bingx",
            "market_type": "swap",
            "status": "failed",
            "error_type": type(error).__name__,
            "error": str(error)[:500],
        }
    RESULTS.append(swap_result)
    print(json.dumps(swap_result, ensure_ascii=False))

    # The primary venue must be reachable for this integration check to pass.
    primary_ok = any(
        item["venue"] == "bingx" and item["market_type"] == "spot"
        and item["status"] == "passed" for item in RESULTS
    )
    if not primary_ok:
        print("Primary venue BingX spot test failed.", file=sys.stderr)
        return 1

    print("BingX primary spot smoke test: PASS")
    print("Secondary venue results are reported individually; failures are not marked tested.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
