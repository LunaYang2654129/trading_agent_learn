from pathlib import Path

from multiple_agent_finance.graph.builder import build_graph
from multiple_agent_finance.config.settings import settings
from multiple_agent_finance.reports.final_report import final_report_node


def test_graph_builds():
    graph = build_graph()
    assert graph is not None


def test_final_report_node_writes_file(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "report_dir", tmp_path)
    result = final_report_node(
        {
            "ticker": "TEST",
            "user_request": "unit test",
            "as_of_date": "2026-07-06",
            "confidence_score": 0.8,
            "decision_summary": {"rating": "neutral", "risk_score": 50, "risk_level": "medium"},
            "reflection_result": {"review_comment": "ok"},
            "audit_log": [],
        }
    )
    assert result["final_report_path"].endswith(".md")
    assert "TEST 多智能体股票分析报告" in result["final_report"]
    assert Path(result["final_report_path"]).exists()
