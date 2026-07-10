"""Data collection helpers for the technical single-link workflow."""

from __future__ import annotations

from typing import Any

import pandas as pd

from multiple_agent_finance.config.settings import settings


def _safe_float(value: Any) -> float | None:
    try:
        if value is None or pd.isna(value):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any) -> int | None:
    try:
        if value is None or pd.isna(value):
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def history_to_records(history: pd.DataFrame, as_of_date: str | None = None) -> list[dict[str, Any]]:
    """Normalize OHLCV history to serializable market bar records."""

    if history.empty:
        return []

    df = history.copy()
    df = df.rename(columns={col: str(col).title() for col in df.columns})
    if "Date" not in df.columns:
        df = df.reset_index()

    if "Date" not in df.columns and "Datetime" in df.columns:
        df = df.rename(columns={"Datetime": "Date"})

    if as_of_date and "Date" in df.columns:
        dates = pd.to_datetime(df["Date"], errors="coerce", utc=True).dt.tz_convert(None)
        df = df[dates <= pd.to_datetime(as_of_date)]

    records: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        date_value = pd.to_datetime(row.get("Date"), errors="coerce")
        if pd.isna(date_value):
            continue
        close = _safe_float(row.get("Close"))
        if close is None:
            continue
        records.append(
            {
                "date": date_value.strftime("%Y-%m-%d"),
                "open": _safe_float(row.get("Open")),
                "high": _safe_float(row.get("High")),
                "low": _safe_float(row.get("Low")),
                "close": close,
                "volume": _safe_int(row.get("Volume")),
            }
        )
    return records


def records_to_history(records: list[dict[str, Any]]) -> pd.DataFrame:
    """Convert normalized market bar records back to an OHLCV DataFrame."""

    if not records:
        return pd.DataFrame(columns=["Date", "Open", "High", "Low", "Close", "Volume"])
    df = pd.DataFrame(records)
    df = df.rename(
        columns={
            "date": "Date",
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "volume": "Volume",
        }
    )
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    return df[["Date", "Open", "High", "Low", "Close", "Volume"]].dropna(subset=["Date"])


def collect_market_data(
    ticker: str,
    *,
    as_of_date: str | None = None,
    period: str = "1y",
) -> dict[str, Any]:
    """Fetch yfinance market data and return a stable payload for downstream agents."""

    normalized = ticker.upper()
    sources = [{"type": "market_data", "name": "yfinance", "period": period}]
    warnings: list[str] = []

    try:
        import yfinance as yf

        cache_dir = settings.data_dir / "yfinance_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        yf.set_tz_cache_location(str(cache_dir))

        yf_ticker = yf.Ticker(normalized)
        history = yf_ticker.history(period=period, auto_adjust=True)
        records = history_to_records(history, as_of_date=as_of_date)

        info: dict[str, Any] = {}
        try:
            info = yf_ticker.get_info() or {}
        except Exception as exc:
            warnings.append(f"估值数据获取失败: {exc}")

        valuation_pe = _safe_float(info.get("trailingPE") or info.get("forwardPE"))
        valuation_pb = _safe_float(info.get("priceToBook"))
        if valuation_pe is None:
            warnings.append("PE 数据不可用")
        if valuation_pb is None:
            warnings.append("PB 数据不可用")
        if not records:
            warnings.append("行情历史数据为空")

        return {
            "ticker": normalized,
            "as_of_date": as_of_date,
            "period": period,
            "records": records,
            "valuation_pe": valuation_pe,
            "valuation_pb": valuation_pb,
            "warnings": warnings,
            "sources": sources,
        }
    except Exception as exc:
        return {
            "ticker": normalized,
            "as_of_date": as_of_date,
            "period": period,
            "records": [],
            "valuation_pe": None,
            "valuation_pb": None,
            "warnings": [f"行情数据采集失败: {exc}"],
            "sources": [{"type": "fallback", "name": "market_data_unavailable"}],
        }
