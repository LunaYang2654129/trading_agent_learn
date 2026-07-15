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
        import yfinance as yf

        info = yf.Ticker(normalized).get_info()
        if not info:
            raise ValueError("empty company profile")

        summary = info.get("longBusinessSummary") or "公司业务摘要暂不可用。"
        company_name = info.get("longName") or info.get("shortName") or normalized
        sector = info.get("sector") or "unknown"
        industry = info.get("industry") or "unknown"
        market_cap = _safe_float(info.get("marketCap"))

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
                "earnings_quarterly_growth": _safe_float(
                    info.get("earningsQuarterlyGrowth")
                ),
            },
            "warnings": [],
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
            "competitive_evidence": {
                "market_cap": None,
                "enterprise_value": None,
            },
            "financial_evidence": _empty_financial_evidence(),
            "growth_evidence": _empty_growth_evidence(),
            "warnings": [f"公司资料获取失败: {exc}"],
            "sources": [{"type": "fallback", "name": "company_profile_unavailable"}],
        }
