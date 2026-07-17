from __future__ import annotations

import pandas as pd

from multiple_agent_finance.agents.decision import decision_agent_node
from multiple_agent_finance.agents.reflection import reflection_agent_node
from multiple_agent_finance.graph.builder import build_graph
from multiple_agent_finance.graph.technical_chain import build_technical_chain_graph
from multiple_agent_finance.tools.data_tools import history_to_records
from multiple_agent_finance.tools.technical_tools import analyze_ohlcv


def _history(rows: int = 240) -> pd.DataFrame:
    dates = pd.date_range("2025-01-01", periods=rows, freq="B")
    close = pd.Series(range(100, 100 + rows), dtype="float")
    return pd.DataFrame(
        {
            "Date": dates,
            "Open": close - 0.5,
            "High": close + 1.0,
            "Low": close - 1.0,
            "Close": close,
            "Volume": [1_000_000 + i * 1000 for i in range(rows)],
        }
    )


def _market_data() -> dict:
    return {
        "ticker": "AAPL",
        "as_of_date": "2025-12-01",
        "period": "1y",
        "records": history_to_records(_history(), as_of_date="2025-12-01"),
        "valuation_pe": 30.0,
        "valuation_pb": 8.0,
        "warnings": [],
        "sources": [{"type": "test", "name": "fixture"}],
    }


def test_analyze_ohlcv_computes_required_technical_fields():
    result = analyze_ohlcv(
        "AAPL",
        _history(),
        as_of_date="2025-12-31",
        valuation_pe=30.0,
        valuation_pb=8.0,
        sources=[{"type": "test", "name": "fixture"}],
    )

    assert result["trend"] == "bullish"
    assert result["volume_signal"] in {"expanding", "neutral", "shrinking"}
    assert result["macd_signal"] in {"bullish", "bearish", "neutral"}
    assert result["rsi_signal"] in {"overbought", "oversold", "neutral"}
    indicators = result["market_snapshot"]["technical_indicators"]
    for key in (
        "ma20",
        "ma60",
        "ma200",
        "macd",
        "rsi14",
        "boll",
        "boll_ub",
        "boll_lb",
        "atr14",
    ):
        assert key in indicators
    assert result["support_resistance"]["method"] == "recent_high_low"


def test_analyze_ohlcv_fallback_on_empty_history():
    result = analyze_ohlcv("AAPL", pd.DataFrame(), as_of_date="2026-07-08")

    assert result["trend"] == "unknown"
    assert result["macd_signal"] == "unknown"
    assert result["warnings"]
    assert result["technical_risks"]


def test_history_to_records_normalizes_ohlcv():
    records = history_to_records(_history(3), as_of_date="2025-01-03")

    assert len(records) == 3
    assert records[0]["date"] == "2025-01-01"
    assert set(records[0]) == {"date", "open", "high", "low", "close", "volume"}


def test_decision_reads_technical_indicators_into_risk_points():
    state = {
        "ticker": "AAPL",
        "company_profile": {"competitive_position": "strong", "key_risks": []},
        "financial_metrics": {
            "financial_summary": "ok",
            "revenue": 100,
            "roe": 0.2,
            "debt_to_asset": 0.3,
            "cash_flow_quality": 1.2,
            "financial_risks": [],
        },
        "news_sentiment": {"summary": "neutral", "sentiment_score": 0, "negative_items": []},
        "technical_indicators": {
            "trend": "bearish",
            "volume_signal": "neutral",
            "macd_signal": "bearish",
            "rsi_signal": "neutral",
            "technical_risks": ["Price is in a weak trend structure."],
            "market_snapshot": {"price": 100, "technical_indicators": {}},
        },
    }

    result = decision_agent_node(state)

    assert "Price is in a weak trend structure." in result["decision_summary"]["risk_points"]
    assert result["decision_summary"]["component_scores"]["technical"] > 0


def test_decision_technical_mode_does_not_require_full_specialists():
    state = {
        "ticker": "AAPL",
        "chain_mode": "technical",
        "technical_indicators": {
            "trend": "bullish",
            "volume_signal": "neutral",
            "macd_signal": "bullish",
            "rsi_signal": "neutral",
            "technical_risks": [],
            "market_snapshot": {"price": 100, "technical_indicators": {}},
        },
    }

    result = decision_agent_node(state)

    assert result["decision_summary"]["missing_or_uncertain"] == []
    assert result["decision_summary"]["component_scores"]["company"] == 0


def test_reflection_returns_actionable_retry_task_for_missing_technical():
    result = reflection_agent_node(
        {
            "decision_summary": {"missing_or_uncertain": ["technical_indicators"], "warnings": []},
            "confidence_score": 0.5,
            "confidence_threshold": 0.75,
            "retry_count": 0,
            "max_retries": 1,
        }
    )

    assert result["reflection_result"]["passed"] is False
    assert any("Backfill technical_indicators" in task for task in result["reflection_result"]["retry_tasks"])
    assert result["retry_count"] == 1


def test_end_to_end_full_graph_runs_parallel_specialists(tmp_path, monkeypatch):
    from multiple_agent_finance.config.settings import settings
    import multiple_agent_finance.agents.backtest as backtest_agent
    import multiple_agent_finance.agents.company as company_agent
    import multiple_agent_finance.agents.financial as financial_agent
    import multiple_agent_finance.agents.news as news_agent

    monkeypatch.setattr(settings, "report_dir", tmp_path)
    monkeypatch.setattr(
        backtest_agent,
        "get_six_month_forward_return_backtest",
        lambda ticker, as_of_date=None, market_data=None: {
            "ticker": ticker,
            "method": "six_month_forward_return_event_study",
            "window": {"start_date": "2025-07-01", "end_date": "2026-01-01", "bar_count": 120},
            "metrics": {
                "1d": {"count": 1, "mean": 0.01, "median": 0.01, "min": 0.01, "max": 0.01, "win_rate": 1.0, "latest_return": 0.01},
                "5d": {"count": 1, "mean": 0.02, "median": 0.02, "min": 0.02, "max": 0.02, "win_rate": 1.0, "latest_return": 0.02},
                "10d": {"count": 1, "mean": 0.03, "median": 0.03, "min": 0.03, "max": 0.03, "win_rate": 1.0, "latest_return": 0.03},
            },
            "rows": [],
            "warnings": [],
            "sources": [{"type": "test", "name": "fixture"}],
        },
    )
    monkeypatch.setattr(
        company_agent,
        "get_company_profile",
        lambda ticker, as_of_date=None: {
            "ticker": ticker,
            "as_of_date": as_of_date,
            "company_name": "Apple Inc.",
            "industry": "Consumer Electronics",
            "sector": "Technology",
            "main_products": ["iPhone"],
            "competitive_position": "strong",
            "key_risks": [],
            "warnings": [],
            "sources": [{"type": "test", "name": "fixture"}],
        },
    )
    monkeypatch.setattr(
        financial_agent,
        "get_financial_metrics",
        lambda ticker: {
            "ticker": ticker,
            "revenue": 100,
            "net_income": 20,
            "roe": 0.2,
            "debt_to_asset": 0.3,
            "gross_margin": 0.4,
            "operating_cashflow": 25,
            "cash_flow_quality": 1.25,
            "financial_summary": "ok",
            "financial_risks": [],
            "quarterly_metrics": {"quarters": ["2026-03-31"]},
            "warnings": [],
            "sources": [{"type": "test", "name": "fixture"}],
        },
    )
    monkeypatch.setattr(
        news_agent,
        "get_news_analysis",
        lambda ticker, as_of_date=None: {
            "ticker": ticker,
            "as_of_date": as_of_date,
            "items": [{"title": "Apple growth outlook", "sentiment": "positive", "labels": ["positive"]}],
            "positive_items": [{"title": "Apple growth outlook"}],
            "negative_items": [],
            "policy_items": [],
            "broker_research_items": [],
            "sentiment_score": 1.0,
            "summary": "positive",
            "coverage": {"days_with_results": 1, "items": 1},
            "warnings": [],
            "sources": [{"type": "test", "name": "fixture"}],
        },
    )

    result = build_graph().invoke(
        {
            "ticker": "AAPL",
            "user_request": "unit test",
            "as_of_date": "2026-07-08",
            "retry_count": 0,
            "max_retries": 1,
            "confidence_threshold": 0.75,
            "chain_mode": "full",
            "market_data": _market_data(),
            "shared_memory_refs": [],
            "knowledge_base_refs": [],
            "external_data_refs": [],
            "audit_log": [],
        }
    )

    assert result["company_profile"]
    assert result["financial_metrics"]
    assert result["news_sentiment"]
    assert result["technical_indicators"]
    assert result["decision_summary"]
    assert result["decision_summary"]["chain_mode"] == "full"
    assert result["backtest_result"]["metrics"]["1d"]["mean"] == 0.01
    assert result["reflection_result"]
    assert result["final_report_path"]
    assert result["audit_report_path"]


def test_technical_single_link_graph_runs_from_preloaded_data(monkeypatch, tmp_path):
    from multiple_agent_finance.config.settings import settings
    import multiple_agent_finance.agents.backtest as backtest_agent

    monkeypatch.setattr(settings, "report_dir", tmp_path)
    monkeypatch.setattr(
        backtest_agent,
        "get_six_month_forward_return_backtest",
        lambda ticker, as_of_date=None, market_data=None, lookback_days=183, horizons=(1, 5, 10): {
            "ticker": ticker,
            "method": f"{lookback_days}_day_forward_return_event_study",
            "window": {"start_date": "2025-07-01", "end_date": "2025-12-01", "bar_count": 100},
            "horizons": list(horizons),
            "metrics": {
                "1d": {"count": 1, "mean": 0.01, "median": 0.01, "min": 0.01, "max": 0.01, "win_rate": 1.0, "latest_return": 0.01},
                "3d": {"count": 1, "mean": 0.02, "median": 0.02, "min": 0.02, "max": 0.02, "win_rate": 1.0, "latest_return": 0.02},
                "5d": {"count": 1, "mean": 0.03, "median": 0.03, "min": 0.03, "max": 0.03, "win_rate": 1.0, "latest_return": 0.03},
            },
            "rows": [],
            "warnings": [],
            "sources": [{"type": "test", "name": "fixture"}],
        },
    )

    result = build_technical_chain_graph().invoke(
        {
            "ticker": "AAPL",
            "user_request": "unit test technical chain",
            "as_of_date": "2025-12-01",
            "retry_count": 0,
            "max_retries": 1,
            "confidence_threshold": 0.75,
            "chain_mode": "technical",
            "market_period": "1y",
            "persist_data": False,
            "backtest_horizons": [1, 3, 5],
            "backtest_lookback_days": 14,
            "market_data": _market_data(),
            "shared_memory_refs": [],
            "knowledge_base_refs": [],
            "external_data_refs": [],
            "audit_log": [],
        }
    )

    assert result["market_data"]["records"]
    assert result["planner_tasks"]["technical"]
    assert result["technical_indicators"]["trend"] == "bullish"
    assert result["decision_summary"]["chain_mode"] == "technical"
    assert result["backtest_result"]["method"] == "14_day_forward_return_event_study"
    assert result["backtest_result"]["horizons"] == [1, 3, 5]
    assert result["backtest_result"]["metrics"]["5d"]["mean"] == 0.03
    assert result["reflection_result"]["chain_mode"] == "technical"
    assert result["final_report_path"]
    assert result["audit_report_path"]
