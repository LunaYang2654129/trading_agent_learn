from __future__ import annotations

import pandas as pd
import pytest

from multiple_agent_finance.tools.backtest_tools import calculate_forward_returns


def _history(rows: int) -> pd.DataFrame:
    dates = pd.date_range("2026-01-01", periods=rows, freq="B")
    closes = pd.Series(range(100, 100 + rows), dtype="float")
    return pd.DataFrame(
        {
            "Date": dates,
            "Open": closes,
            "High": closes,
            "Low": closes,
            "Close": closes,
            "Volume": [1_000_000] * rows,
        }
    )


def test_calculate_forward_returns_for_1_5_10_day_horizons():
    result = calculate_forward_returns(
        "AAPL",
        _history(20),
        as_of_date="2026-02-15",
        lookback_days=60,
        sources=[{"type": "test", "name": "fixture"}],
    )

    first = result["rows"][0]
    assert first["return_1d"] == pytest.approx(0.01)
    assert first["return_5d"] == pytest.approx(0.05)
    assert first["return_10d"] == pytest.approx(0.10)
    assert result["metrics"]["1d"]["count"] == 19
    assert result["metrics"]["5d"]["count"] == 15
    assert result["metrics"]["10d"]["count"] == 10
    assert result["metrics"]["1d"]["win_rate"] == 1.0


def test_calculate_forward_returns_warns_on_short_window():
    result = calculate_forward_returns(
        "AAPL",
        _history(5),
        as_of_date="2026-01-10",
        lookback_days=30,
    )

    assert result["warnings"]
    assert result["metrics"]["10d"]["count"] == 0
    assert result["metrics"]["1d"]["count"] == 4


def test_calculate_forward_returns_for_1_3_5_day_horizons():
    result = calculate_forward_returns(
        "AAPL",
        _history(12),
        as_of_date="2026-01-20",
        lookback_days=14,
        horizons=(1, 3, 5),
        sources=[{"type": "test", "name": "fixture"}],
    )

    assert result["method"] == "14_day_forward_return_event_study"
    assert result["horizons"] == [1, 3, 5]
    assert result["metrics"]["1d"]["count"] > 0
    assert result["metrics"]["3d"]["count"] > 0
    assert result["metrics"]["5d"]["count"] > 0
    assert set(result["metrics"]) == {"1d", "3d", "5d"}


def test_calculate_forward_returns_one_week_warns_for_5_day_horizon():
    result = calculate_forward_returns(
        "AAPL",
        _history(5),
        as_of_date="2026-01-07",
        lookback_days=7,
        horizons=(1, 3, 5),
    )

    assert result["metrics"]["1d"]["count"] == 4
    assert result["metrics"]["3d"]["count"] == 2
    assert result["metrics"]["5d"]["count"] == 0
    assert any("5-day returns" in warning for warning in result["warnings"])
