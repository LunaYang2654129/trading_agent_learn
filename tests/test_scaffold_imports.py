from pathlib import Path

from multiple_agent_finance.config.settings import settings
from multiple_agent_finance.graph.builder import build_graph
from multiple_agent_finance.graph.technical_chain import build_technical_chain_graph
from multiple_agent_finance.reports.final_report import final_report_node


def _assert_weekly_graph_nodes(graph):
    graph_nodes = set(graph.get_graph().nodes)
    assert "planner" in graph_nodes
    assert "technical_agent" in graph_nodes
    assert "decision_agent" in graph_nodes
    assert "reflection_agent" in graph_nodes
    assert "final_report" in graph_nodes
    assert "company_agent" not in graph_nodes
    assert "financial_agent" not in graph_nodes
    assert "news_agent" not in graph_nodes
    assert "data_collection_agent" not in graph_nodes
    assert "risk_agent" not in graph_nodes


def test_graph_builds():
    graph = build_graph()
    assert graph is not None
    _assert_weekly_graph_nodes(graph)


def test_technical_chain_graph_builds():
    graph = build_technical_chain_graph()
    assert graph is not None
    _assert_weekly_graph_nodes(graph)


def test_final_report_node_writes_chinese_file(tmp_path, monkeypatch):
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
    assert "TEST 单链路多智能体技术预测报告" in result["final_report"]
    assert "单股预测结论" in result["final_report"]
    assert "使用边界" in result["final_report"]
    assert Path(result["final_report_path"]).exists()
