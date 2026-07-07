"""Financial data tools."""

from __future__ import annotations

from typing import Any


def _row_latest(frame: Any, *names: str) -> float | None:
    for name in names:
        try:
            if name in frame.index and not frame.loc[name].dropna().empty:
                return float(frame.loc[name].dropna().iloc[0])
        except Exception:
            continue
    return None


def _ratio(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator in (None, 0):
        return None
    return numerator / denominator


def get_financial_metrics(ticker: str) -> dict:
    """Fetch and normalize core financial metrics."""

    normalized = ticker.upper()
    try:
        import yfinance as yf

        yf_ticker = yf.Ticker(normalized)
        financials = yf_ticker.financials
        balance_sheet = yf_ticker.balance_sheet
        cashflow = yf_ticker.cashflow

        if financials.empty and balance_sheet.empty and cashflow.empty:
            raise ValueError("empty financial statements")

        revenue = _row_latest(financials, "Total Revenue")
        net_income = _row_latest(financials, "Net Income")
        gross_profit = _row_latest(financials, "Gross Profit")
        total_assets = _row_latest(balance_sheet, "Total Assets")
        total_liabilities = _row_latest(
            balance_sheet, "Total Liabilities Net Minority Interest", "Total Liab"
        )
        equity = _row_latest(
            balance_sheet, "Stockholders Equity", "Total Stockholder Equity"
        )
        operating_cashflow = _row_latest(
            cashflow, "Operating Cash Flow", "Total Cash From Operating Activities"
        )

        gross_margin = _ratio(gross_profit, revenue)
        roe = _ratio(net_income, equity)
        debt_to_asset = _ratio(total_liabilities, total_assets)
        cash_flow_quality_ratio = _ratio(operating_cashflow, net_income)

        risks = []
        if debt_to_asset is not None and debt_to_asset > 0.65:
            risks.append("资产负债率偏高。")
        if roe is not None and roe < 0:
            risks.append("ROE 为负，盈利质量需要重点核查。")
        if cash_flow_quality_ratio is not None and cash_flow_quality_ratio < 0.8:
            risks.append("经营现金流对利润覆盖不足。")
        if not risks:
            risks.append("财务风险未见明显异常，但仍需结合完整财报验证。")

        return {
            "ticker": normalized,
            "revenue": revenue,
            "net_income": net_income,
            "roe": roe,
            "debt_to_asset": debt_to_asset,
            "gross_margin": gross_margin,
            "operating_cashflow": operating_cashflow,
            "cash_flow_quality": cash_flow_quality_ratio,
            "financial_summary": "已从财务报表提取收入、利润、ROE、资产负债率和现金流质量。",
            "financial_risks": risks,
            "warnings": [],
            "sources": [{"type": "financial_statement", "name": "yfinance"}],
        }
    except Exception as exc:
        return {
            "ticker": normalized,
            "revenue": None,
            "net_income": None,
            "roe": None,
            "debt_to_asset": None,
            "gross_margin": None,
            "operating_cashflow": None,
            "cash_flow_quality": None,
            "financial_summary": "财务指标暂不可用，当前使用离线降级结果。",
            "financial_risks": ["财务数据源暂不可用，需补充年报或三方数据库。"],
            "warnings": [f"财务数据获取失败: {exc}"],
            "sources": [{"type": "fallback", "name": "financial_metrics_unavailable"}],
        }
