"""Offline smoke tests for technical indicators and historical strategy simulation."""
from __future__ import annotations

import math

import pandas as pd
import ta_py as ta
from backtesting import Backtest, Strategy


def test_ta_py_indicators() -> None:
    closes = [1, 2, 3, 4, 5, 6]
    assert ta.sma(closes, 3) == [2.0, 3.0, 4.0, 5.0]
    rsi_values = ta.rsi(closes, 3)
    assert rsi_values, "RSI should produce values after its warm-up period"
    assert all(math.isfinite(float(value)) for value in rsi_values)


def test_backtesting_engine_on_synthetic_ohlcv() -> None:
    index = pd.date_range("2025-01-01", periods=12, freq="h", tz="UTC")
    close = [100, 101, 100, 102, 103, 102, 104, 105, 104, 106, 107, 108]
    data = pd.DataFrame(
        {
            "Open": close,
            "High": [value + 1 for value in close],
            "Low": [value - 1 for value in close],
            "Close": close,
            "Volume": [1000] * len(close),
        },
        index=index,
    )

    class BuyAndHoldOnce(Strategy):
        def init(self) -> None:
            pass

        def next(self) -> None:
            if not self.position:
                self.buy()

    result = Backtest(
        data,
        BuyAndHoldOnce,
        cash=10_000,
        commission=0.001,
        spread=0.0005,
        finalize_trades=True,
    ).run()

    assert result["# Trades"] == 1
    assert math.isfinite(float(result["Equity Final [$]"]))
    assert result["_trades"].shape[0] == 1
    assert result["_equity_curve"].shape[0] == len(data)


if __name__ == "__main__":
    test_ta_py_indicators()
    test_backtesting_engine_on_synthetic_ohlcv()
    print("ta_py indicators and backtesting.py synthetic OHLCV smoke tests passed")
