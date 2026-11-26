#!/usr/bin/env python3
"""Small offline smoke test for pandas data handling and Matplotlib rendering."""
from __future__ import annotations

import struct
import tempfile
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd


def main() -> int:
    print(f"pandas={pd.__version__}")
    print(f"matplotlib={matplotlib.__version__}")

    frame = pd.DataFrame(
        {
            "asset": ["BTC", "ETH", "BTC", "ETH"],
            "price": [100.0, 50.0, 110.0, 55.0],
            "volume": [2, 4, 3, 5],
        }
    )
    summary = frame.groupby("asset", as_index=False).agg(
        average_price=("price", "mean"),
        total_volume=("volume", "sum"),
    )

    indexed = summary.set_index("asset")
    assert indexed.loc["BTC", "average_price"] == 105.0
    assert indexed.loc["ETH", "total_volume"] == 9

    with tempfile.TemporaryDirectory() as temporary_directory:
        root = Path(temporary_directory)

        csv_path = root / "prices.csv"
        frame.to_csv(csv_path, index=False)
        csv_round_trip = pd.read_csv(csv_path)
        assert csv_round_trip.equals(frame)

        json_path = root / "summary.json"
        summary.to_json(json_path, orient="records")
        json_round_trip = pd.read_json(json_path, orient="records")
        assert len(json_round_trip) == 2
        assert set(json_round_trip["asset"]) == {"BTC", "ETH"}

        png_path = root / "summary.png"
        figure, axis = plt.subplots(figsize=(6.4, 4.8), dpi=100)
        axis.bar(summary["asset"], summary["average_price"])
        axis.set_title("Average price fixture")
        figure.savefig(png_path, format="png")
        plt.close(figure)

        payload = png_path.read_bytes()
        assert payload.startswith(b"\x89PNG\r\n\x1a\n")
        width, height = struct.unpack(">II", payload[16:24])
        assert (width, height) == (640, 480)

    print("pandas groupby/aggregation: PASS")
    print("pandas CSV round-trip: PASS")
    print("pandas JSON round-trip: PASS")
    print("matplotlib Agg PNG rendering (640x480): PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
