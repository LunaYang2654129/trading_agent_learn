"""Simple event-study backtest helpers."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

import pandas as pd
from sqlalchemy import text

from multiple_agent_finance.storage.mysql_store import DatabaseStore
from multiple_agent_finance.tools.data_tools import collect_market_data, records_to_history


HORIZONS = (1, 5, 10)


def _safe_float(value: Any) -> float | None:
    try:
        if value is None or pd.isna(value):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _end_date(as_of_date: str | None = None) -> date:
    if as_of_date:
        try:
            return datetime.fromisoformat(as_of_date).date()
        except ValueError:
            pass
    return date.today()


def _normalize_history(history: pd.DataFrame) -> pd.DataFrame:
    if history.empty:
        return pd.DataFrame(columns=["date", "close"])
    df = history.copy()
    df = df.rename(columns={col: str(col).title() for col in df.columns})
    if "Date" not in df.columns:
        df = df.reset_index()
    if "Datetime" in df.columns and "Date" not in df.columns:
        df = df.rename(columns={"Datetime": "Date"})
    if "Date" not in df.columns or "Close" not in df.columns:
        return pd.DataFrame(columns=["date", "close"])
    df["date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["close"] = pd.to_numeric(df["Close"], errors="coerce")
    return df[["date", "close"]].dropna().sort_values("date").reset_index(drop=True)


def _summarize(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {
            "count": 0,
            "mean": None,
            "median": None,
            "min": None,
            "max": None,
            "win_rate": None,
            "latest_return": None,
        }
    series = pd.Series(values, dtype="float")
    return {
        "count": int(series.count()),
        "mean": _safe_float(series.mean()),
        "median": _safe_float(series.median()),
        "min": _safe_float(series.min()),
        "max": _safe_float(series.max()),
        "win_rate": _safe_float((series > 0).mean()),
        "latest_return": _safe_float(series.iloc[-1]),
    }


def _method_name(lookback_days: int) -> str:
    if lookback_days == 183:
        return "six_month_forward_return_event_study"
    return f"{lookback_days}_day_forward_return_event_study"


def calculate_forward_returns(
    ticker: str,
    history: pd.DataFrame,
    *,
    as_of_date: str | None = None,
    lookback_days: int = 183,
    horizons: tuple[int, ...] = HORIZONS,
    sources: list[dict[str, Any]] | None = None,
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    """Calculate forward returns over the configured lookback window."""

    normalized = ticker.upper()
    warnings = list(warnings or [])
    horizons = tuple(int(horizon) for horizon in horizons)
    df = _normalize_history(history)
    if df.empty:
        return _fallback(
            normalized,
            as_of_date,
            "No OHLCV close data for backtest.",
            sources,
            warnings,
            lookback_days=lookback_days,
            horizons=horizons,
        )

    end = _end_date(as_of_date)
    start = end - timedelta(days=lookback_days)
    df = df[(df["date"].dt.date >= start) & (df["date"].dt.date <= end)].reset_index(drop=True)
    if df.empty:
        return _fallback(
            normalized,
            as_of_date,
            f"No market bars in the {lookback_days}-day window.",
            sources,
            warnings,
            lookback_days=lookback_days,
            horizons=horizons,
        )

    max_horizon = max(horizons)
    if len(df) <= max_horizon:
        warnings.append(
            f"Only {len(df)} bars available; need more than {max_horizon} for "
            f"{max_horizon}-day returns."
        )

    rows: list[dict[str, Any]] = []
    values_by_horizon: dict[int, list[float]] = {horizon: [] for horizon in horizons}
    for idx in range(len(df)):
        base_close = _safe_float(df.loc[idx, "close"])
        if base_close in (None, 0):
            continue
        row = {
            "date": df.loc[idx, "date"].date().isoformat(),
            "close": base_close,
        }
        has_return = False
        for horizon in horizons:
            key = f"return_{horizon}d"
            if idx + horizon < len(df):
                value = _safe_float(df.loc[idx + horizon, "close"] / base_close - 1)
                values_by_horizon[horizon].append(value)
                row[key] = value
                has_return = True
            else:
                row[key] = None
        if has_return:
            rows.append(row)

    metrics = {
        f"{horizon}d": _summarize(values_by_horizon[horizon])
        for horizon in horizons
    }
    return {
        "ticker": normalized,
        "as_of_date": as_of_date,
        "method": _method_name(lookback_days),
        "window": {
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "calendar_days": lookback_days,
            "bar_count": int(len(df)),
        },
        "horizons": list(horizons),
        "metrics": metrics,
        "rows": rows,
        "warnings": warnings,
        "sources": list(sources or []),
    }


def load_market_bars_history(ticker: str, as_of_date: str | None = None, lookback_days: int = 183) -> pd.DataFrame:
    """Load recent market bars from local MySQL."""

    normalized = ticker.upper()
    end = _end_date(as_of_date)
    start = end - timedelta(days=lookback_days + 20)
    with DatabaseStore().engine.connect() as conn:
        rows = (
            conn.execute(
                text(
                    """
                    SELECT bar_date AS date, open_price AS open, high_price AS high,
                           low_price AS low, close_price AS close, volume
                    FROM market_bars
                    WHERE ticker = :ticker
                      AND source = 'yfinance'
                      AND bar_date BETWEEN :start_date AND :end_date
                    ORDER BY bar_date, updated_at DESC, id DESC
                    """
                ),
                {
                    "ticker": normalized,
                    "start_date": start.isoformat(),
                    "end_date": end.isoformat(),
                },
            )
            .mappings()
            .all()
        )
        if not rows:
            rows = (
                conn.execute(
                    text(
                        """
                        SELECT bar_date AS date, open_price AS open, high_price AS high,
                               low_price AS low, close_price AS close, volume
                        FROM market_bars
                        WHERE ticker = :ticker
                          AND bar_date BETWEEN :start_date AND :end_date
                        ORDER BY bar_date, updated_at DESC, id DESC
                        """
                    ),
                    {
                        "ticker": normalized,
                        "start_date": start.isoformat(),
                        "end_date": end.isoformat(),
                    },
                )
                .mappings()
                .all()
            )
    if not rows:
        return pd.DataFrame()
    deduped: dict[str, Any] = {}
    for row in rows:
        deduped.setdefault(str(row.get("date")), row)
    return records_to_history(
        [
            {
                "date": str(row.get("date")),
                "open": _safe_float(row.get("open")),
                "high": _safe_float(row.get("high")),
                "low": _safe_float(row.get("low")),
                "close": _safe_float(row.get("close")),
                "volume": int(row.get("volume")) if row.get("volume") is not None else None,
            }
            for row in deduped.values()
        ]
    )


def get_six_month_forward_return_backtest(
    ticker: str,
    *,
    as_of_date: str | None = None,
    market_data: dict[str, Any] | None = None,
    lookback_days: int = 183,
    horizons: tuple[int, ...] = HORIZONS,
) -> dict[str, Any]:
    """Return forward-return statistics for the configured lookback window."""

    normalized = ticker.upper()
    horizons = tuple(int(horizon) for horizon in horizons)
    warnings: list[str] = []
    try:
        history = load_market_bars_history(normalized, as_of_date, lookback_days=lookback_days)
        if not history.empty:
            return calculate_forward_returns(
                normalized,
                history,
                as_of_date=as_of_date,
                lookback_days=lookback_days,
                horizons=horizons,
                sources=[{"type": "market_bars", "name": "local_mysql"}],
            )
        warnings.append("Local market_bars not found for backtest.")
    except Exception as exc:
        warnings.append(f"Local market_bars unavailable for backtest: {exc}")

    if market_data and market_data.get("records"):
        return calculate_forward_returns(
            normalized,
            records_to_history(market_data.get("records", [])),
            as_of_date=as_of_date or market_data.get("as_of_date"),
            lookback_days=lookback_days,
            horizons=horizons,
            sources=list(market_data.get("sources", [])) or [{"type": "state", "name": "market_data"}],
            warnings=warnings,
        )

    try:
        period = "1mo" if lookback_days <= 31 else "3mo" if lookback_days <= 93 else "6mo"
        collected = collect_market_data(normalized, as_of_date=as_of_date, period=period)
        return calculate_forward_returns(
            normalized,
            records_to_history(collected.get("records", [])),
            as_of_date=as_of_date,
            lookback_days=lookback_days,
            horizons=horizons,
            sources=collected.get("sources", [{"type": "market_data", "name": "yfinance"}]),
            warnings=[*warnings, *collected.get("warnings", [])],
        )
    except Exception as exc:
        return _fallback(
            normalized,
            as_of_date,
            f"Backtest market data unavailable: {exc}",
            [{"type": "fallback", "name": "backtest_unavailable"}],
            warnings,
            lookback_days=lookback_days,
            horizons=horizons,
        )


def _fallback(
    ticker: str,
    as_of_date: str | None,
    reason: str,
    sources: list[dict[str, Any]] | None,
    warnings: list[str] | None,
    *,
    lookback_days: int = 183,
    horizons: tuple[int, ...] = HORIZONS,
) -> dict[str, Any]:
    horizons = tuple(int(horizon) for horizon in horizons)
    return {
        "ticker": ticker,
        "as_of_date": as_of_date,
        "method": _method_name(lookback_days),
        "window": {"start_date": None, "end_date": None, "calendar_days": lookback_days, "bar_count": 0},
        "horizons": list(horizons),
        "metrics": {f"{horizon}d": _summarize([]) for horizon in horizons},
        "rows": [],
        "warnings": [*(warnings or []), reason],
        "sources": list(sources or []),
    }
