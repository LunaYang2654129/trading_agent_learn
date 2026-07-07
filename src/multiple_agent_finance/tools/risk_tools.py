"""Risk analysis tools."""

from __future__ import annotations

from multiple_agent_finance.tools.market_tools import get_market_snapshot


def get_risk_analysis(ticker: str) -> dict:
    """Estimate market risk from recent technical indicators."""

    normalized = ticker.upper()
    market = get_market_snapshot(normalized)
    indicators = market.get("technical_indicators", {})
    warnings = list(market.get("warnings", []))

    risk_score = 40
    risk_points: list[str] = []
    volatility = indicators.get("volatility_20d")
    return_20d = indicators.get("return_20d")
    trend = indicators.get("trend")

    if volatility is None:
        risk_score += 15
        risk_points.append("行情波动率数据缺失，风险评估置信度下降。")
    elif volatility > 0.45:
        risk_score += 25
        risk_points.append("近 20 日年化波动率偏高。")
    elif volatility > 0.28:
        risk_score += 12
        risk_points.append("近 20 日年化波动率处于中等偏高水平。")
    else:
        risk_points.append("近 20 日波动率相对可控。")

    if return_20d is None:
        risk_score += 10
        risk_points.append("近 20 日收益数据不足。")
    elif return_20d < -0.12:
        risk_score += 20
        risk_points.append("近 20 日价格回撤较大。")
    elif return_20d < 0:
        risk_score += 8
        risk_points.append("近 20 日价格表现偏弱。")
    else:
        risk_points.append("近 20 日价格表现未显示明显下行压力。")

    if trend == "below_ma20":
        risk_score += 10
        risk_points.append("最新价格低于 20 日均线。")
    elif trend == "above_ma20":
        risk_points.append("最新价格高于 20 日均线。")

    if warnings:
        risk_score += 10
        risk_points.extend(warnings)

    risk_score = min(max(risk_score, 0), 100)
    if risk_score >= 70:
        level = "high"
    elif risk_score >= 45:
        level = "medium"
    else:
        level = "low"

    return {
        "ticker": normalized,
        "risk_score": risk_score,
        "risk_points": risk_points,
        "risk_level": level,
        "market_snapshot": market,
        "warnings": warnings,
        "sources": market.get("sources", []),
    }
