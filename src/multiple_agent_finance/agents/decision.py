"""Decision Agent: aggregate parallel results into an initial judgment."""

from __future__ import annotations

from multiple_agent_finance.agents.base import audit_event
from multiple_agent_finance.graph.state import StockAnalysisState


def _collect_warnings(*sections: dict) -> list[str]:
    warnings: list[str] = []
    for section in sections:
        warnings.extend(str(item) for item in section.get("warnings", []) if item)
    return warnings


def _rating_from_score(risk_score: int, sentiment_score: float, trend: str | None) -> str:
    if risk_score >= 75:
        return "avoid"
    if risk_score >= 60:
        return "watch"
    if sentiment_score > 0.2 and trend == "above_ma20":
        return "positive_watch"
    return "neutral"


def decision_agent_node(state: StockAnalysisState) -> dict:
    company = state.get("company_profile", {})
    financial = state.get("financial_metrics", {})
    news = state.get("news_analysis", {})
    risk = state.get("risk_analysis", {})
    market = state.get("market_snapshot", {})

    missing = [
        key
        for key in ("company_profile", "financial_metrics", "news_analysis", "risk_analysis")
        if not state.get(key)
    ]
    warnings = _collect_warnings(company, financial, news, risk, market)
    risk_score = int(risk.get("risk_score", 65 if warnings else 50))
    sentiment_score = float(news.get("sentiment_score", 0) or 0)
    trend = market.get("technical_indicators", {}).get("trend")

    confidence = 0.88
    confidence -= 0.12 * len(missing)
    confidence -= min(len(warnings) * 0.06, 0.24)
    if market.get("price") is None:
        confidence -= 0.08
    if financial.get("revenue") is None:
        confidence -= 0.08
    confidence = max(0.25, min(confidence, 0.92))

    summary = {
        "ticker": state.get("ticker"),
        "rating": _rating_from_score(risk_score, sentiment_score, trend),
        "risk_score": risk_score,
        "risk_level": risk.get("risk_level", "unknown"),
        "confidence": confidence,
        "supporting_points": [
            company.get("competitive_position", "公司信息待补充。"),
            financial.get("financial_summary", "财务信息待补充。"),
            news.get("summary", "新闻信息待补充。"),
        ],
        "risk_points": risk.get("risk_points", []),
        "market_snapshot": market,
        "missing_or_uncertain": missing,
        "warnings": warnings,
    }
    return {
        "decision_summary": summary,
        "confidence_score": confidence,
        "audit_log": [audit_event("decision_agent", "decision summary generated", summary)],
    }
