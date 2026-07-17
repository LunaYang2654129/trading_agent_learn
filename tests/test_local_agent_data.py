from __future__ import annotations

from multiple_agent_finance.tools.company_tools import get_company_profile
from multiple_agent_finance.tools.financial_tools import get_financial_metrics
from multiple_agent_finance.tools.news_tools import get_news_analysis


def test_company_profile_prefers_local_payload(monkeypatch):
    import multiple_agent_finance.tools.local_data_tools as local_data

    monkeypatch.setattr(
        local_data,
        "load_latest_company_profile",
        lambda ticker: {
            "ticker": ticker,
            "company_name": "Apple Inc.",
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "business_summary": "Local company profile.",
            "main_products": ["iPhone"],
            "key_risks": [],
            "warnings": [],
            "sources": [{"type": "company_profile", "name": "local_mysql"}],
        },
    )

    result = get_company_profile("AAPL")

    assert result["company_name"] == "Apple Inc."
    assert result["sources"][0]["name"] == "local_mysql"


def test_financial_metrics_include_local_four_quarter_payload(monkeypatch):
    import multiple_agent_finance.tools.local_data_tools as local_data

    monkeypatch.setattr(
        local_data,
        "load_latest_quarterly_financials",
        lambda ticker: {
            "run_id": "run-1",
            "quarters": ["2026-03-31", "2025-12-31", "2025-09-30", "2025-06-30"],
            "statements": {
                "income_statement": {
                    "2026-03-31": {
                        "Total Revenue": 100.0,
                        "Net Income": 20.0,
                        "Gross Profit": 45.0,
                    }
                },
                "balance_sheet": {
                    "2026-03-31": {
                        "Total Assets": 200.0,
                        "Total Liabilities Net Minority Interest": 80.0,
                        "Stockholders Equity": 100.0,
                    }
                },
                "cash_flow": {"2026-03-31": {"Operating Cash Flow": 30.0}},
            },
            "rows": [],
            "row_count": 1,
            "sources": [{"type": "financial_quarterly_metrics", "name": "local_mysql"}],
        },
    )

    result = get_financial_metrics("AAPL")

    assert result["revenue"] == 100.0
    assert result["net_income"] == 20.0
    assert result["roe"] == 0.2
    assert result["debt_to_asset"] == 0.4
    assert result["gross_margin"] == 0.45
    assert result["cash_flow_quality"] == 1.5
    assert len(result["quarterly_metrics"]["quarters"]) == 4


def test_news_analysis_uses_local_daily_top_items(monkeypatch):
    import multiple_agent_finance.tools.local_data_tools as local_data

    items = [
        {
            "news_date": f"2025-01-{day:02d}",
            "rank_no": 1,
            "title": "Apple growth upgrade",
            "publisher": "Fixture",
            "link": "https://example.com",
            "published_at": f"2025-01-{day:02d}T00:00:00",
        }
        for day in range(1, 4)
    ]
    monkeypatch.setattr(
        local_data,
        "load_daily_top_news",
        lambda ticker, as_of_date: {
            "run_id": "run-1",
            "items": items,
            "coverage": {
                "start_date": "2025-01-01",
                "end_date": "2025-01-03",
                "days_with_results": 3,
                "items": 3,
            },
            "sources": [{"type": "news_daily_top_items", "name": "local_mysql"}],
        },
    )

    result = get_news_analysis("AAPL", "2025-01-03")

    assert len(result["items"]) == 3
    assert len(result["positive_items"]) == 3
    assert result["sentiment_score"] == 1.0
    assert result["coverage"]["days_with_results"] == 3
