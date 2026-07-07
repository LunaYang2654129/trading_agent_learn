"""Company profile data tools."""

from __future__ import annotations

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
    found = []
    lowered = summary.lower()
    for keyword in PRODUCT_KEYWORDS:
        if keyword.lower() in lowered:
            found.append(keyword)
    return found[:8]


def get_company_profile(ticker: str) -> dict:
    """Return a normalized company profile with graceful fallback."""

    normalized = ticker.upper()
    try:
        import yfinance as yf

        info = yf.Ticker(normalized).get_info()
        if not info:
            raise ValueError("empty company profile")

        summary = info.get("longBusinessSummary") or "公司业务摘要暂不可用。"
        industry = info.get("industry") or "未知行业"
        sector = info.get("sector") or "未知板块"
        company_name = info.get("longName") or info.get("shortName") or normalized

        risks = []
        if info.get("trailingPE") and info.get("trailingPE", 0) > 60:
            risks.append("估值倍数偏高，需要结合成长性验证。")
        if info.get("debtToEquity") and info.get("debtToEquity", 0) > 150:
            risks.append("债务权益比偏高，需要关注偿债压力。")
        if not risks:
            risks.append("公司层面风险需要结合行业资料和财报进一步验证。")

        main_products = _extract_products(summary)

        return {
            "ticker": normalized,
            "company_name": company_name,
            "business_summary": summary,
            "industry": industry,
            "sector": sector,
            "main_products": main_products,
            "competitive_position": f"{company_name} 位于 {sector}/{industry}，需结合市场份额和同业估值进一步比较。",
            "shareholder_structure": "股权结构需接入交易所、年报或专业数据库后补全。",
            "market_cap": info.get("marketCap"),
            "website": info.get("website"),
            "key_risks": risks,
            "warnings": [],
            "sources": [{"type": "company_profile", "name": "yfinance"}],
        }
    except Exception as exc:
        return {
            "ticker": normalized,
            "company_name": normalized,
            "business_summary": "公司资料暂不可用，当前使用离线降级结果。",
            "industry": "未知行业",
            "sector": "未知板块",
            "main_products": [],
            "competitive_position": "公司竞争地位待接入真实数据源验证。",
            "shareholder_structure": "股权结构待接入交易所、年报或专业数据库。",
            "market_cap": None,
            "website": None,
            "key_risks": ["公司资料源暂不可用，结论需保守处理。"],
            "warnings": [f"公司资料获取失败: {exc}"],
            "sources": [{"type": "fallback", "name": "company_profile_unavailable"}],
        }
