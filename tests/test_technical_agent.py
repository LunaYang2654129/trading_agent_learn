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


def test_end_to_end_graph_runs_weekly_technical_link(tmp_path, monkeypatch):
    from multiple_agent_finance.config.settings import settings

    monkeypatch.setattr(settings, "report_dir", tmp_path)

    result = build_graph().invoke(
        {
            "ticker": "AAPL",
            "user_request": "unit test",
            "as_of_date": "2026-07-08",
            "retry_count": 0,
            "max_retries": 1,
            "confidence_threshold": 0.75,
            "chain_mode": "technical",
            "market_data": _market_data(),
            "shared_memory_refs": [],
            "knowledge_base_refs": [],
            "external_data_refs": [],
            "audit_log": [],
        }
    )

    assert "company_profile" not in result
    assert "financial_metrics" not in result
    assert "news_sentiment" not in result
    assert result["technical_indicators"]
    assert result["decision_summary"]
    assert result["reflection_result"]
    assert result["final_report_path"]


def test_technical_single_link_graph_runs_from_preloaded_data(monkeypatch, tmp_path):
    from multiple_agent_finance.config.settings import settings

    monkeypatch.setattr(settings, "report_dir", tmp_path)

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
    assert result["reflection_result"]["chain_mode"] == "technical"
    assert result["final_report_path"]
