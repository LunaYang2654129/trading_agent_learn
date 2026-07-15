from __future__ import annotations

import json
import sys
from copy import deepcopy
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from multiple_agent_finance.agents.company_schema import CompanyAnalysis
from multiple_agent_finance.tools.company_tools import get_company_profile


def _valid_company_payload() -> dict:
    return {
        "ticker": "AAPL",
        "as_of_date": "2026-07-15",
        "company_name": "Apple Inc.",
        "status": "success",
        "business_model": {
            "summary": "Consumer hardware and services ecosystem.",
            "products_services": ["iPhone", "Services"],
            "revenue_drivers": ["Installed base", "Services attach rate"],
            "evidence": ["Company profile describes devices and services."],
        },
        "industry_position": {
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "position": "Global category leader.",
            "market_position_evidence": ["Premium-device brand and ecosystem."],
        },
        "competitive_advantages": [
            {
                "advantage": "Integrated ecosystem",
                "durability": "high",
                "evidence": "Hardware, software, and services are integrated.",
            }
        ],
        "financial_health": {
            "assessment": "healthy",
            "strengths": ["Positive free cash flow"],
            "concerns": ["Debt requires monitoring"],
            "evidence": ["Free cash flow is positive in the supplied evidence."],
        },
        "growth": {
            "assessment": "moderate",
            "growth_drivers": ["Services"],
            "constraints": ["Mature handset market"],
            "evidence": ["Revenue growth is positive in the supplied evidence."],
        },
        "risk_factors": [
            {
                "risk": "Supply-chain concentration",
                "severity": "medium",
                "evidence": "The supplied profile identifies concentrated manufacturing.",
            }
        ],
        "confidence": 0.82,
        "warnings": [],
        "sources": [{"type": "company_profile", "name": "fixture"}],
        "business_summary": "Consumer hardware and services ecosystem.",
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "main_products": ["iPhone", "Services"],
        "competitive_position": "Global category leader.",
        "key_risks": ["Supply-chain concentration"],
    }


def _set_nested(payload: dict, path: tuple, value: object) -> None:
    target = payload
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value


def test_company_analysis_schema_serializes_six_dimensions():
    analysis = CompanyAnalysis.model_validate(_valid_company_payload())

    payload = analysis.model_dump(mode="json")

    assert payload["business_model"]["summary"] == (
        "Consumer hardware and services ecosystem."
    )
    assert payload["industry_position"]["position"] == "Global category leader."
    assert payload["competitive_advantages"][0]["durability"] == "high"
    assert payload["financial_health"]["assessment"] == "healthy"
    assert payload["growth"]["assessment"] == "moderate"
    assert payload["risk_factors"][0]["severity"] == "medium"
    assert payload["competitive_position"]
    assert payload["key_risks"]
    json.dumps(payload)


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("confidence",), 1.5),
        (("competitive_advantages", 0, "durability"), "permanent"),
        (("risk_factors", 0, "severity"), "critical"),
    ],
)
def test_company_analysis_schema_rejects_invalid_control_values(path, value):
    payload = deepcopy(_valid_company_payload())
    _set_nested(payload, path, value)

    with pytest.raises(ValidationError):
        CompanyAnalysis.model_validate(payload)


def _raw_company_info() -> dict:
    return {
        "longName": "Apple Inc.",
        "longBusinessSummary": "Apple designs iPhone, Mac, and subscription services.",
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "website": "https://www.apple.com",
        "marketCap": 3_000_000_000_000,
        "enterpriseValue": 3_100_000_000_000,
        "totalCash": 100,
        "totalDebt": 75,
        "debtToEquity": 120,
        "currentRatio": 0.9,
        "profitMargins": 0.25,
        "operatingCashflow": 110,
        "freeCashflow": 90,
        "revenueGrowth": 0.08,
        "earningsGrowth": 0.1,
        "earningsQuarterlyGrowth": 0.12,
    }


def _install_fake_yfinance(monkeypatch, info: dict) -> None:
    class FakeTicker:
        def __init__(self, ticker: str) -> None:
            self.ticker = ticker

        def get_info(self) -> dict:
            return info

    monkeypatch.setitem(sys.modules, "yfinance", SimpleNamespace(Ticker=FakeTicker))


def _install_failing_yfinance(monkeypatch, error: Exception) -> None:
    class FailingTicker:
        def __init__(self, ticker: str) -> None:
            self.ticker = ticker

        def get_info(self) -> dict:
            raise error

    monkeypatch.setitem(sys.modules, "yfinance", SimpleNamespace(Ticker=FailingTicker))


def test_get_company_profile_returns_normalized_company_evidence(monkeypatch):
    _install_fake_yfinance(monkeypatch, _raw_company_info())

    result = get_company_profile("aapl", as_of_date="2026-07-15")

    assert result["ticker"] == "AAPL"
    assert result["as_of_date"] == "2026-07-15"
    assert result["company_name"] == "Apple Inc."
    assert result["main_products"] == ["iPhone", "Mac", "subscription"]
    assert result["financial_evidence"]["total_cash"] == 100.0
    assert result["growth_evidence"]["revenue_growth"] == 0.08
    assert result["competitive_evidence"]["enterprise_value"] == 3_100_000_000_000.0
    assert result["sources"] == [{"type": "company_profile", "name": "yfinance"}]


def test_get_company_profile_returns_stable_fallback(monkeypatch):
    _install_failing_yfinance(monkeypatch, RuntimeError("offline"))

    result = get_company_profile("aapl", as_of_date="2026-07-15")

    assert result["ticker"] == "AAPL"
    assert result["as_of_date"] == "2026-07-15"
    assert result["financial_evidence"]["total_cash"] is None
    assert result["growth_evidence"]["revenue_growth"] is None
    assert result["warnings"] == ["公司资料获取失败: offline"]
