from __future__ import annotations

import json
import sys
from copy import deepcopy
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from multiple_agent_finance.agents import company as company_module
from multiple_agent_finance.agents.company_schema import CompanyAnalysis
from multiple_agent_finance.graph import company_technical_parallel as parallel_module
from multiple_agent_finance.graph.state import StockAnalysisState
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

    assert payload["business_model"]["summary"] == ("Consumer hardware and services ecosystem.")
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
    assert result["warnings"] == [
        "yfinance company profile is a current snapshot and is not "
        "point-in-time verified for 2026-07-15"
    ]


def test_get_company_profile_returns_stable_fallback(monkeypatch):
    _install_failing_yfinance(monkeypatch, RuntimeError("offline"))

    result = get_company_profile("aapl", as_of_date="2026-07-15")

    assert result["ticker"] == "AAPL"
    assert result["as_of_date"] == "2026-07-15"
    assert result["financial_evidence"]["total_cash"] is None
    assert result["growth_evidence"]["revenue_growth"] is None
    assert result["warnings"] == ["公司资料获取失败: offline"]


def _company_evidence() -> dict:
    return {
        "ticker": "AAPL",
        "as_of_date": "2026-07-15",
        "company_name": "Apple Inc.",
        "business_summary": "Apple designs devices and services.",
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "main_products": ["iPhone", "Services"],
        "website": "https://www.apple.com",
        "market_cap": 3_000_000_000_000.0,
        "competitive_evidence": {
            "market_cap": 3_000_000_000_000.0,
            "enterprise_value": 3_100_000_000_000.0,
        },
        "financial_evidence": {
            "total_cash": 100.0,
            "total_debt": 75.0,
            "debt_to_equity": 120.0,
            "current_ratio": 0.9,
            "profit_margins": 0.25,
            "operating_cashflow": 110.0,
            "free_cashflow": 90.0,
        },
        "growth_evidence": {
            "revenue_growth": 0.08,
            "earnings_growth": 0.1,
            "earnings_quarterly_growth": 0.12,
        },
        "warnings": [],
        "sources": [{"type": "company_profile", "name": "fixture"}],
    }


def _company_state(*, company_data: dict | None = None) -> dict:
    state = {
        "ticker": "aapl",
        "as_of_date": "2026-07-15",
        "user_request": "Focus on long-term company quality.",
        "planner_tasks": {"company": "Evaluate durable company quality."},
        "knowledge_base_refs": [{"key": "industry-note"}],
        "shared_memory_refs": [{"agent": "planner", "key": "plan"}],
        "audit_log": [],
    }
    if company_data is not None:
        state["company_data"] = company_data
    return state


class _Invoker:
    def __init__(self, result: object, captured: dict) -> None:
        self.result = result
        self.captured = captured

    def invoke(self, messages: object) -> object:
        self.captured["messages"] = messages
        return self.result


class _StructuredLLM:
    def __init__(self, payload: dict, captured: dict) -> None:
        self.payload = payload
        self.captured = captured

    def with_structured_output(self, schema: type) -> _Invoker:
        self.captured["schema"] = schema
        return _Invoker(CompanyAnalysis.model_validate(self.payload), self.captured)

    def invoke(self, messages: object) -> object:
        raise AssertionError("plain fallback should not run")


class _PlainFallbackLLM:
    def __init__(self, payload: dict, *, fenced: bool = False) -> None:
        content = json.dumps(payload, ensure_ascii=False)
        self.content = f"```json\n{content}\n```" if fenced else content
        self.plain_calls = 0

    def with_structured_output(self, schema: type) -> object:
        raise NotImplementedError("structured output unavailable")

    def invoke(self, messages: object) -> object:
        self.plain_calls += 1
        return SimpleNamespace(content=self.content)


class _FailingLLM:
    def with_structured_output(self, schema: type) -> object:
        raise RuntimeError("structured failure")

    def invoke(self, messages: object) -> object:
        raise RuntimeError("plain failure")


def _install_company_llm(monkeypatch, llm: object, captured: dict | None = None) -> None:
    def fake_get_agent_llm(name: str) -> object:
        if captured is not None:
            captured["agent_name"] = name
        return llm

    monkeypatch.setattr(company_module, "get_agent_llm", fake_get_agent_llm, raising=False)


def test_company_agent_uses_shared_llm_and_preloaded_data(monkeypatch):
    captured: dict = {}
    _install_company_llm(
        monkeypatch,
        _StructuredLLM(_valid_company_payload(), captured),
        captured,
    )

    def unexpected_tool_call(*args, **kwargs):
        raise AssertionError("preloaded company_data must take precedence")

    monkeypatch.setattr(company_module, "get_company_profile", unexpected_tool_call)

    result = company_module.company_agent_node(_company_state(company_data=_company_evidence()))

    assert captured["agent_name"] == "company"
    assert captured["schema"] is CompanyAnalysis
    assert result["company_profile"]["status"] == "success"
    assert result["company_profile"]["ticker"] == "AAPL"
    messages_text = str(captured["messages"])
    assert "2026-07-15" in messages_text
    assert "Evaluate durable company quality" in messages_text
    assert "Apple designs devices and services" in messages_text


def test_company_agent_uses_tool_when_preloaded_data_is_missing(monkeypatch):
    captured: dict = {}
    calls: dict = {}
    _install_company_llm(
        monkeypatch,
        _StructuredLLM(_valid_company_payload(), captured),
    )

    def fake_profile(ticker: str, as_of_date: str | None = None) -> dict:
        calls.update(ticker=ticker, as_of_date=as_of_date)
        return _company_evidence()

    monkeypatch.setattr(company_module, "get_company_profile", fake_profile)

    result = company_module.company_agent_node(_company_state())

    assert calls == {"ticker": "AAPL", "as_of_date": "2026-07-15"}
    assert result["company_profile"]["company_name"] == "Apple Inc."


@pytest.mark.parametrize("fenced", [False, True])
def test_company_agent_falls_back_to_plain_json(monkeypatch, fenced):
    llm = _PlainFallbackLLM(_valid_company_payload(), fenced=fenced)
    _install_company_llm(monkeypatch, llm)

    result = company_module.company_agent_node(_company_state(company_data=_company_evidence()))

    assert result["company_profile"]["status"] == "success"
    assert llm.plain_calls == 1


def test_company_agent_returns_degraded_json_when_llm_fails(monkeypatch):
    _install_company_llm(monkeypatch, _FailingLLM())

    result = company_module.company_agent_node(_company_state(company_data=_company_evidence()))

    profile = result["company_profile"]
    assert profile["status"] == "degraded"
    assert profile["confidence"] <= 0.3
    assert profile["company_name"] == "Apple Inc."
    assert profile["business_model"]["summary"] == "Apple designs devices and services."
    assert profile["financial_health"]["assessment"] == "insufficient_evidence"
    assert profile["growth"]["assessment"] == "insufficient_evidence"
    assert profile["warnings"]
    assert result["shared_memory_refs"] == [{"agent": "company_agent", "key": "company_profile"}]
    audit = result["audit_log"][0]
    assert audit["agent"] == "company_agent"
    assert "api_key" not in audit["llm"]
    assert "MAF_LLM_API_KEY" not in json.dumps(audit)


def _parallel_state() -> dict:
    return {
        "ticker": "AAPL",
        "as_of_date": "2026-07-15",
        "user_request": "Analyze technical and company evidence.",
        "planner_tasks": {},
        "market_data": {"records": []},
        "company_data": _company_evidence(),
        "shared_memory_refs": [],
        "knowledge_base_refs": [],
        "external_data_refs": [],
        "audit_log": [],
    }


def _install_graph_fakes(monkeypatch, *, degraded_company: bool = False) -> None:
    def fake_planner(state: dict) -> dict:
        return {
            "ticker": state["ticker"].upper(),
            "planner_tasks": {
                "technical": "Analyze technical evidence.",
                "company": "Analyze company evidence.",
            },
        }

    def fake_technical(state: dict) -> dict:
        return {
            "technical_indicators": {
                "trend": "bullish",
                "warnings": ["technical warning"] if degraded_company else [],
            }
        }

    def fake_company(state: dict) -> dict:
        profile = _valid_company_payload()
        if degraded_company:
            profile["status"] = "degraded"
            profile["warnings"] = ["company warning"]
        return {"company_profile": profile}

    monkeypatch.setattr(parallel_module, "planner_agent_node", fake_planner)
    monkeypatch.setattr(parallel_module, "technical_agent_node", fake_technical)
    monkeypatch.setattr(parallel_module, "company_agent_node", fake_company)


def test_parallel_state_declares_company_inputs_and_joined_output():
    assert "company_data" in StockAnalysisState.__annotations__
    assert "parallel_analysis_result" in StockAnalysisState.__annotations__


def test_company_technical_parallel_graph_has_expected_nodes():
    graph = parallel_module.build_company_technical_parallel_graph()

    assert set(graph.get_graph().nodes) == {
        "__start__",
        "planner",
        "technical_agent",
        "company_agent",
        "result_collector",
        "__end__",
    }


def test_company_technical_parallel_graph_collects_both_results(monkeypatch):
    _install_graph_fakes(monkeypatch)
    graph = parallel_module.build_company_technical_parallel_graph()

    result = graph.invoke(_parallel_state())

    joined = result["parallel_analysis_result"]
    assert joined["ticker"] == "AAPL"
    assert joined["as_of_date"] == "2026-07-15"
    assert joined["technical_result"] == {"trend": "bullish", "warnings": []}
    assert joined["company_result"]["status"] == "success"
    assert joined["warnings"] == []


def test_parallel_graph_preserves_technical_result_when_company_is_degraded(monkeypatch):
    _install_graph_fakes(monkeypatch, degraded_company=True)
    graph = parallel_module.build_company_technical_parallel_graph()

    result = graph.invoke(_parallel_state())

    joined = result["parallel_analysis_result"]
    assert joined["technical_result"]["trend"] == "bullish"
    assert joined["company_result"]["status"] == "degraded"
    assert joined["warnings"] == ["technical warning", "company warning"]
