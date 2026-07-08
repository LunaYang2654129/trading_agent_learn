"""Technical-analysis tools for price action, volume, valuation, and indicators."""

from __future__ import annotations

from typing import Any

import pandas as pd

from multiple_agent_finance.tools.data_tools import collect_market_data, records_to_history


def _safe_float(value: Any) -> float | None:
    try:
        if value is None or pd.isna(value):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_history(history: pd.DataFrame) -> pd.DataFrame:
    df = history.copy()
    if df.empty:
        return df
    df = df.rename(columns={col: str(col).title() for col in df.columns})
    if "Date" not in df.columns:
        df = df.reset_index()
    if "Datetime" in df.columns and "Date" not in df.columns:
        df = df.rename(columns={"Datetime": "Date"})
    required = ["Open", "High", "Low", "Close", "Volume"]
    for col in required:
        if col not in df.columns:
            df[col] = pd.NA
    keep = ["Date"] + required if "Date" in df.columns else required
    return df[keep].dropna(subset=["Close"]).reset_index(drop=True)


def _rsi(close: pd.Series, window: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-12)
    return 100 - (100 / (1 + rs))


def _atr(df: pd.DataFrame, window: int = 14) -> pd.Series:
    high = df["High"]
    low = df["Low"]
    close = df["Close"]
    previous_close = close.shift(1)
    true_range = pd.concat(
        [
            high - low,
            (high - previous_close).abs(),
            (low - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return true_range.rolling(window).mean()


def _trend(latest_close: float | None, ma20: float | None, ma60: float | None) -> str:
    if latest_close is None or ma20 is None or ma60 is None:
        return "unknown"
    if latest_close > ma20 > ma60:
        return "bullish"
    if latest_close < ma20 < ma60:
        return "bearish"
    return "sideways"


def _volume_signal(latest_volume: float | None, avg_volume_20d: float | None) -> str:
    if latest_volume is None or avg_volume_20d in (None, 0):
        return "unknown"
    if latest_volume >= avg_volume_20d * 1.2:
        return "expanding"
    if latest_volume <= avg_volume_20d * 0.8:
        return "shrinking"
    return "neutral"


def _macd_signal(macd: float | None, signal: float | None, histogram: float | None) -> str:
    if macd is None or signal is None or histogram is None:
        return "unknown"
    if macd > signal and histogram > 0:
        return "bullish"
    if macd < signal and histogram < 0:
        return "bearish"
    return "neutral"


def _rsi_signal(value: float | None) -> str:
    if value is None:
        return "unknown"
    if value >= 70:
        return "overbought"
    if value <= 30:
        return "oversold"
    return "neutral"


def analyze_ohlcv(
    ticker: str,
    history: pd.DataFrame,
    *,
    as_of_date: str | None = None,
    valuation_pe: float | None = None,
    valuation_pb: float | None = None,
    warnings: list[str] | None = None,
    sources: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Compute the project-standard technical indicator payload from OHLCV data."""

    normalized = ticker.upper()
    warnings = list(warnings or [])
    sources = list(sources or [])
    df = _normalize_history(history)
    if df.empty:
        return _fallback(normalized, as_of_date, "行情历史数据为空", warnings, sources)

    if as_of_date and "Date" in df.columns:
        dates = pd.to_datetime(df["Date"], errors="coerce", utc=True).dt.tz_convert(None)
        cutoff = pd.to_datetime(as_of_date)
        df = df[dates <= cutoff]
        if df.empty:
            return _fallback(
                normalized,
                as_of_date,
                f"没有 {as_of_date} 及之前的行情数据",
                warnings,
                sources,
            )

    close = pd.to_numeric(df["Close"], errors="coerce")
    high = pd.to_numeric(df["High"], errors="coerce")
    low = pd.to_numeric(df["Low"], errors="coerce")
    volume = pd.to_numeric(df["Volume"], errors="coerce")
    df = df.assign(Close=close, High=high, Low=low, Volume=volume).dropna(subset=["Close"])
    if df.empty:
        return _fallback(normalized, as_of_date, "行情收盘价数据为空", warnings, sources)

    latest_close = _safe_float(df["Close"].iloc[-1])
    latest_volume = _safe_float(df["Volume"].iloc[-1])
    ma20 = _safe_float(df["Close"].rolling(20).mean().iloc[-1]) if len(df) >= 20 else None
    ma60 = _safe_float(df["Close"].rolling(60).mean().iloc[-1]) if len(df) >= 60 else None
    ma200 = _safe_float(df["Close"].rolling(200).mean().iloc[-1]) if len(df) >= 200 else None
    return_20d = _safe_float(df["Close"].iloc[-1] / df["Close"].iloc[-21] - 1) if len(df) > 20 else None
    return_60d = _safe_float(df["Close"].iloc[-1] / df["Close"].iloc[-61] - 1) if len(df) > 60 else None

    ema12 = df["Close"].ewm(span=12, adjust=False).mean()
    ema26 = df["Close"].ewm(span=26, adjust=False).mean()
    macd_series = ema12 - ema26
    macd_signal_series = macd_series.ewm(span=9, adjust=False).mean()
    macd_histogram_series = macd_series - macd_signal_series

    rsi_series = _rsi(df["Close"])
    boll_middle = df["Close"].rolling(20).mean()
    boll_std = df["Close"].rolling(20).std()
    atr_series = _atr(df)
    avg_volume_20d = _safe_float(df["Volume"].rolling(20).mean().iloc[-1]) if len(df) >= 20 else None

    macd = _safe_float(macd_series.iloc[-1])
    macd_line_signal = _safe_float(macd_signal_series.iloc[-1])
    macd_histogram = _safe_float(macd_histogram_series.iloc[-1])
    rsi14 = _safe_float(rsi_series.iloc[-1])
    boll = _safe_float(boll_middle.iloc[-1])
    boll_upper = _safe_float((boll_middle + 2 * boll_std).iloc[-1])
    boll_lower = _safe_float((boll_middle - 2 * boll_std).iloc[-1])
    atr14 = _safe_float(atr_series.iloc[-1])

    support = _safe_float(df["Low"].tail(20).min()) if len(df) >= 20 else None
    resistance = _safe_float(df["High"].tail(20).max()) if len(df) >= 20 else None

    trend = _trend(latest_close, ma20, ma60)
    volume_signal = _volume_signal(latest_volume, avg_volume_20d)
    macd_signal = _macd_signal(macd, macd_line_signal, macd_histogram)
    rsi_signal = _rsi_signal(rsi14)

    risks: list[str] = []
    if trend == "bearish":
        risks.append("价格处于弱趋势结构")
    if rsi_signal == "overbought":
        risks.append("RSI 显示短期超买，追高风险上升")
    if rsi_signal == "oversold":
        risks.append("RSI 显示短期超卖，仍需等待趋势确认")
    if atr14 is not None and latest_close not in (None, 0) and atr14 / latest_close > 0.04:
        risks.append("ATR 占价格比例偏高，短期波动风险较大")
    if volume_signal == "shrinking" and trend == "bullish":
        risks.append("上涨趋势中成交量收缩，趋势确认度下降")
    if not risks:
        risks.append("技术面未显示突出的单项风险，但需结合基本面和新闻验证")

    latest_date = None
    if "Date" in df.columns:
        latest_date_value = pd.to_datetime(df["Date"].iloc[-1], errors="coerce")
        if not pd.isna(latest_date_value):
            latest_date = latest_date_value.strftime("%Y-%m-%d")

    indicators = {
        "latest_close": latest_close,
        "latest_volume": latest_volume,
        "return_20d": return_20d,
        "return_60d": return_60d,
        "ma20": ma20,
        "ma60": ma60,
        "ma200": ma200,
        "macd": macd,
        "macd_signal_line": macd_line_signal,
        "macd_histogram": macd_histogram,
        "rsi14": rsi14,
        "boll": boll,
        "boll_ub": boll_upper,
        "boll_lb": boll_lower,
        "atr14": atr14,
        "avg_volume_20d": avg_volume_20d,
        "history_points": int(len(df)),
    }

    return {
        "ticker": normalized,
        "as_of_date": as_of_date,
        "trend": trend,
        "volume_signal": volume_signal,
        "macd_signal": macd_signal,
        "rsi_signal": rsi_signal,
        "valuation_pe": valuation_pe,
        "valuation_pb": valuation_pb,
        "support_resistance": {
            "support": support,
            "resistance": resistance,
            "method": "recent_high_low",
        },
        "market_snapshot": {
            "ticker": normalized,
            "latest_trading_date": latest_date,
            "price": latest_close,
            "volume": latest_volume,
            "technical_indicators": indicators,
            "sources": sources,
        },
        "technical_risks": risks,
        "warnings": warnings,
        "sources": sources,
    }


def _fallback(
    ticker: str,
    as_of_date: str | None,
    reason: str,
    warnings: list[str] | None = None,
    sources: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    merged_warnings = list(warnings or [])
    merged_warnings.append(reason)
    merged_sources = list(sources or [])
    if not merged_sources:
        merged_sources = [{"type": "fallback", "name": "technical_indicators_unavailable"}]
    return {
        "ticker": ticker,
        "as_of_date": as_of_date,
        "trend": "unknown",
        "volume_signal": "unknown",
        "macd_signal": "unknown",
        "rsi_signal": "unknown",
        "valuation_pe": None,
        "valuation_pb": None,
        "support_resistance": {
            "support": None,
            "resistance": None,
            "method": "recent_high_low",
        },
        "market_snapshot": {
            "ticker": ticker,
            "latest_trading_date": None,
            "price": None,
            "volume": None,
            "technical_indicators": {},
            "sources": merged_sources,
        },
        "technical_risks": ["技术指标数据源暂不可用，需要补充行情后再判断"],
        "warnings": merged_warnings,
        "sources": merged_sources,
    }


def get_technical_indicators_from_market_data(
    ticker: str,
    market_data: dict[str, Any],
    *,
    as_of_date: str | None = None,
) -> dict[str, Any]:
    """Calculate indicators from pre-collected market data."""

    records = market_data.get("records", [])
    history = records_to_history(records)
    sources = list(market_data.get("sources", []))
    if not sources:
        sources = [{"type": "state", "name": "market_data"}]
    return analyze_ohlcv(
        ticker,
        history,
        as_of_date=as_of_date or market_data.get("as_of_date"),
        valuation_pe=market_data.get("valuation_pe"),
        valuation_pb=market_data.get("valuation_pb"),
        warnings=list(market_data.get("warnings", [])),
        sources=sources,
    )


def get_technical_indicators(ticker: str, as_of_date: str | None = None, period: str = "1y") -> dict[str, Any]:
    """Fetch yfinance data and return the project-standard technical payload."""

    market_data = collect_market_data(ticker, as_of_date=as_of_date, period=period)
    return get_technical_indicators_from_market_data(
        ticker,
        market_data,
        as_of_date=as_of_date,
    )


def get_market_snapshot(ticker: str, period: str = "1y") -> dict[str, Any]:
    """Compatibility wrapper returning only the technical market snapshot."""

    return get_technical_indicators(ticker, period=period).get("market_snapshot", {})
