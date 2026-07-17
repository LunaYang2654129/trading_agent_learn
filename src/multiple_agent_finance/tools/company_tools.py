"""Company-profile evidence tools used by Company Agent."""

from __future__ import annotations

from typing import Any


PRODUCT_KEYWORDS = [
    "iPhone",
    "Mac",
    "iPad",
    "AirPods",
    "Apple Watch",
    "Apple TV",
    "Apple Vision Pro",
    "cloud services",
    "subscription",
    "advertising",
    "software",
    "semiconductor",
    "data center",
    "cloud",
    "search",
    "e-commerce",
    "electric vehicles",
    "payments",
]


def _extract_products(summary: str) -> list[str]:
    found: list[str] = []
    lowered = summary.lower()
    for keyword in PRODUCT_KEYWORDS:
        if keyword.lower() in lowered:
            found.append(keyword)
    return found[:8]


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _empty_financial_evidence() -> dict[str, float | None]:
    return {
        "total_cash": None,
        "total_debt": None,
        "debt_to_equity": None,
        "current_ratio": None,
        "profit_margins": None,
        "operating_cashflow": None,
        "free_cashflow": None,
    }


def _empty_growth_evidence() -> dict[str, float | None]:
    return {
        "revenue_growth": None,
        "earnings_growth": None,
        "earnings_quarterly_growth": None,
    }


def get_company_profile(ticker: str, as_of_date: str | None = None) -> dict[str, Any]:
    """Return normalized company evidence with a stable offline fallback."""

    normalized = ticker.upper()
    try:
        from multiple_agent_finance.tools.local_data_tools import load_latest_company_profile

        local_profile = load_latest_company_profile(normalized)
        if local_profile:
            return local_profile
    except Exception as exc:
        local_warning = f"Local company profile unavailable: {exc}"
    else:
        local_warning = "Local company profile not found."

    try:
        import yfinance as yf

        info = yf.Ticker(normalized).get_info()
        if not info:
            raise ValueError("empty company profile")

        summary = info.get("longBusinessSummary") or "公司业务摘要暂不可用。"
        company_name = info.get("longName") or info.get("shortName") or normalized
        sector = info.get("sector") or "unknown"
        industry = info.get("industry") or "unknown"
        market_cap = _safe_float(info.get("marketCap"))
        warnings = []
        if as_of_date:
            warnings.append(
                "yfinance company profile is a current snapshot and is not "
                f"point-in-time verified for {as_of_date}"
            )
        risks = []
        if info.get("trailingPE") and info.get("trailingPE", 0) > 60:
            risks.append("估值倍数偏高，需要结合成长性验证。")
        if info.get("debtToEquity") and info.get("debtToEquity", 0) > 150:
            risks.append("债务权益比偏高，需要关注偿债压力。")
        if not risks:
            risks.append("公司层面风险需要结合行业资料和财报进一步验证。")

        return {
            "ticker": normalized,
            "as_of_date": as_of_date,
            "company_name": company_name,
            "business_summary": summary,
            "sector": sector,
            "industry": industry,
            "main_products": _extract_products(summary),
            "website": info.get("website"),
            "market_cap": market_cap,
            "competitive_position": f"{company_name} 位于 {sector}/{industry}，需结合市场份额和同业估值进一步比较。",
            "shareholder_structure": "股权结构需接入交易所、年报或专业数据库后补全。",
            "competitive_evidence": {
                "market_cap": market_cap,
                "enterprise_value": _safe_float(info.get("enterpriseValue")),
            },
            "financial_evidence": {
                "total_cash": _safe_float(info.get("totalCash")),
                "total_debt": _safe_float(info.get("totalDebt")),
                "debt_to_equity": _safe_float(info.get("debtToEquity")),
                "current_ratio": _safe_float(info.get("currentRatio")),
                "profit_margins": _safe_float(info.get("profitMargins")),
                "operating_cashflow": _safe_float(info.get("operatingCashflow")),
                "free_cashflow": _safe_float(info.get("freeCashflow")),
            },
            "growth_evidence": {
                "revenue_growth": _safe_float(info.get("revenueGrowth")),
                "earnings_growth": _safe_float(info.get("earningsGrowth")),
                "earnings_quarterly_growth": _safe_float(info.get("earningsQuarterlyGrowth")),
            },
            "key_risks": risks,
            "warnings": warnings,
            "sources": [{"type": "company_profile", "name": "yfinance"}],
        }
    except Exception as exc:
        return {
            "ticker": normalized,
            "as_of_date": as_of_date,
            "company_name": normalized,
            "business_summary": "公司资料暂不可用。",
            "sector": "unknown",
            "industry": "unknown",
            "main_products": [],
            "website": None,
            "market_cap": None,
            "competitive_position": "公司竞争地位待接入真实数据源验证。",
            "shareholder_structure": "股权结构待接入交易所、年报或专业数据库。",
            "competitive_evidence": {
                "market_cap": None,
                "enterprise_value": None,
            },
            "financial_evidence": _empty_financial_evidence(),
            "growth_evidence": _empty_growth_evidence(),
            "key_risks": ["公司资料源暂不可用，结论需保守处理。"],
            "warnings": [f"公司资料获取失败: {exc}"],
            "sources": [{"type": "fallback", "name": "company_profile_unavailable"}],
        }
