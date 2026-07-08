"""Decision Agent: aggregate specialist outputs into an initial judgment."""

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
    if sentiment_score > 0.2 and trend == "bullish":
        return "positive_watch"
    return "neutral"


def _risk_level(score: int) -> str:
    if score >= 70:
        return "high"
    if score >= 45:
        return "medium"
    return "low"


def _score_company(company: dict) -> tuple[int, list[str]]:
    points = 0
    risks = list(company.get("key_risks", []))
    if company.get("industry") in (None, "", "unknown"):
        points += 8
        risks.append("Company industry information is missing.")
    if company.get("competitive_position", "").endswith("Requires validation from real data sources."):
        points += 6
    if company.get("warnings"):
        points += min(12, len(company["warnings"]) * 4)
    return points, risks


def _score_financial(financial: dict) -> tuple[int, list[str]]:
    points = 0
    risks = list(financial.get("financial_risks", []))
    debt_to_asset = financial.get("debt_to_asset")
    roe = financial.get("roe")
    cash_flow_quality = financial.get("cash_flow_quality")
    if debt_to_asset is None:
        points += 8
    elif debt_to_asset > 0.65:
        points += 12
    if roe is None:
        points += 6
    elif roe < 0:
        points += 15
    if cash_flow_quality is None:
        points += 6
    elif cash_flow_quality < 0.8:
        points += 10
    if financial.get("warnings"):
        points += min(12, len(financial["warnings"]) * 4)
    return points, risks


def _score_news(news: dict) -> tuple[int, list[str]]:
    points = 0
    risks: list[str] = []
    sentiment = float(news.get("sentiment_score", 0) or 0)
    negative_items = news.get("negative_items", [])
    policy_items = news.get("policy_items", [])
    if sentiment < -0.15:
        points += 10
        risks.append("News sentiment is negative.")
    if negative_items:
        points += min(12, len(negative_items) * 3)
        risks.append("Negative news items are present.")
    if policy_items:
        points += min(8, len(policy_items) * 2)
        risks.append("Policy-related items require further impact review.")
    if news.get("warnings"):
        points += min(10, len(news["warnings"]) * 4)
    return points, risks


def _score_technical(technical: dict) -> tuple[int, list[str]]:
    points = 0
    risks = list(technical.get("technical_risks", []))
    trend = technical.get("trend")
    if trend == "bearish":
        points += 14
    elif trend == "unknown":
        points += 8
    if technical.get("macd_signal") == "bearish":
        points += 8
    if technical.get("rsi_signal") == "overbought":
        points += 6
    if technical.get("volume_signal") == "shrinking" and trend == "bullish":
        points += 5
    snapshot = technical.get("market_snapshot", {})
    indicators = snapshot.get("technical_indicators", {})
    latest_close = indicators.get("latest_close")
    atr14 = indicators.get("atr14")
    if latest_close not in (None, 0) and atr14 is not None and atr14 / latest_close > 0.04:
        points += 6
    if technical.get("warnings"):
        points += min(12, len(technical["warnings"]) * 4)
    return points, risks


def decision_agent_node(state: StockAnalysisState) -> dict:
    company = state.get("company_profile", {})
    financial = state.get("financial_metrics", {})
    news = state.get("news_sentiment", {})
    technical = state.get("technical_indicators", {})
    chain_mode = state.get("chain_mode", "full")

    if chain_mode == "technical":
        required_sections = ("technical_indicators",)
    else:
        required_sections = (
            "company_profile",
            "financial_metrics",
            "news_sentiment",
            "technical_indicators",
        )
    missing = [key for key in required_sections if not state.get(key)]

    company_score, company_risks = (0, []) if chain_mode == "technical" else _score_company(company)
    financial_score, financial_risks = (0, []) if chain_mode == "technical" else _score_financial(financial)
    news_score, news_risks = (0, []) if chain_mode == "technical" else _score_news(news)
    technical_score, technical_risks = _score_technical(technical)

    warning_sections = (technical,) if chain_mode == "technical" else (company, financial, news, technical)
    warnings = _collect_warnings(*warning_sections)
    risk_points = company_risks + financial_risks + news_risks + technical_risks
    if not risk_points:
        risk_points.append("No single prominent risk is detected, but data-source completeness still requires review.")

    base_score = 20 if chain_mode == "technical" else 25
    risk_score = min(
        100,
        base_score + company_score + financial_score + news_score + technical_score + len(missing) * 8,
    )
    sentiment_score = float(news.get("sentiment_score", 0) or 0)
    trend = technical.get("trend")

    confidence = 0.88 if chain_mode == "technical" else 0.9
    confidence -= 0.12 * len(missing)
    confidence -= min(len(warnings) * 0.05, 0.25)
    if chain_mode != "technical" and financial.get("revenue") is None:
        confidence -= 0.06
    if technical.get("market_snapshot", {}).get("price") is None:
        confidence -= 0.08
    confidence = max(0.25, min(confidence, 0.92))

    technical_point = (
        f"Technical trend: {technical.get('trend', 'unknown')}; "
        f"Volume signal: {technical.get('volume_signal', 'unknown')}; "
        f"MACD: {technical.get('macd_signal', 'unknown')}; "
        f"RSI: {technical.get('rsi_signal', 'unknown')}"
    )
    if chain_mode == "technical":
        supporting_points = [technical_point]
        summary_text = (
            "Generated a technical single-link judgment from trend, volume, momentum, "
            "valuation helpers, and risk points."
        )
    else:
        supporting_points = [
            company.get("competitive_position", "Company information is incomplete."),
            financial.get("financial_summary", "Financial information is incomplete."),
            news.get("summary", "News sentiment information is incomplete."),
            technical_point,
        ]
        summary_text = "Aggregated company, financial, news sentiment, and technical specialist outputs."

    summary = {
        "ticker": state.get("ticker"),
        "chain_mode": chain_mode,
        "summary": summary_text,
        "rating": _rating_from_score(risk_score, sentiment_score, trend),
        "risk_score": risk_score,
        "risk_level": _risk_level(risk_score),
        "confidence": confidence,
        "supporting_points": supporting_points,
        "risk_points": risk_points,
        "missing_or_uncertain": missing,
        "warnings": warnings,
        "component_scores": {
            "company": company_score,
            "financial": financial_score,
            "news": news_score,
            "technical": technical_score,
        },
    }
    return {
        "decision_summary": summary,
        "confidence_score": confidence,
        "audit_log": [audit_event("decision_agent", "decision summary generated", summary)],
    }
