"""Market data tools for price snapshots and technical indicators."""

from __future__ import annotations

from math import sqrt
from typing import Any


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def get_market_snapshot(ticker: str, period: str = "6mo") -> dict:
    """Fetch market data from yfinance and compute lightweight indicators.

    The tool intentionally returns a structured fallback instead of raising. This
    keeps the LangGraph workflow usable in offline or restricted-network runs.
    """

    normalized = ticker.upper()
    try:
        import yfinance as yf

        history = yf.Ticker(normalized).history(period=period, auto_adjust=True)
        if history.empty:
            raise ValueError("empty market history")

        close = history["Close"].dropna()
        volume = history["Volume"].dropna()
        latest_close = _safe_float(close.iloc[-1])
        latest_volume = _safe_float(volume.iloc[-1]) if not volume.empty else None
        returns = close.pct_change().dropna()

        ma20 = _safe_float(close.tail(20).mean()) if len(close) >= 20 else None
        ma60 = _safe_float(close.tail(60).mean()) if len(close) >= 60 else None
        return_20d = _safe_float(close.iloc[-1] / close.iloc[-21] - 1) if len(close) > 20 else None
        volatility_20d = (
            _safe_float(returns.tail(20).std() * sqrt(252)) if len(returns) >= 20 else None
        )

        if ma20 is None or latest_close is None:
            trend = "unknown"
        elif latest_close >= ma20:
            trend = "above_ma20"
        else:
            trend = "below_ma20"

        return {
            "ticker": normalized,
            "price": latest_close,
            "volume": latest_volume,
            "technical_indicators": {
                "ma20": ma20,
                "ma60": ma60,
                "return_20d": return_20d,
                "volatility_20d": volatility_20d,
                "trend": trend,
                "history_points": int(len(history)),
            },
            "warnings": [],
            "sources": [{"type": "market_data", "name": "yfinance", "period": period}],
        }
    except Exception as exc:  # yfinance can fail for network, ticker, or rate-limit reasons.
        return {
            "ticker": normalized,
            "price": None,
            "volume": None,
            "technical_indicators": {},
            "warnings": [f"行情数据暂不可用: {exc}"],
            "sources": [{"type": "fallback", "name": "market_snapshot_unavailable"}],
        }
