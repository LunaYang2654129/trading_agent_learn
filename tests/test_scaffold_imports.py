from pathlib import Path

from multiple_agent_finance.config.settings import settings
from multiple_agent_finance.graph.builder import build_graph
from multiple_agent_finance.graph.technical_chain import build_technical_chain_graph
from multiple_agent_finance.reports.final_report import final_report_node


def _assert_full_graph_nodes(graph):
    graph_nodes = set(graph.get_graph().nodes)
    assert "planner" in graph_nodes
    assert "company_agent" in graph_nodes
    assert "financial_agent" in graph_nodes
    assert "news_agent" in graph_nodes
    assert "technical_agent" in graph_nodes
    assert "decision_agent" in graph_nodes
    assert "backtest_agent" in graph_nodes
    assert "reflection_agent" in graph_nodes
    assert "final_report" in graph_nodes
    assert "data_collection_agent" not in graph_nodes
    assert "risk_agent" not in graph_nodes

    graph_edges = {(edge.source, edge.target) for edge in graph.get_graph().edges}
    for node in ("company_agent", "financial_agent", "news_agent", "technical_agent"):
        assert ("planner", node) in graph_edges
        assert (node, "decision_agent") in graph_edges
    assert ("decision_agent", "backtest_agent") in graph_edges
    assert ("backtest_agent", "reflection_agent") in graph_edges


def _assert_technical_graph_nodes(graph):
    graph_nodes = set(graph.get_graph().nodes)
    assert "planner" in graph_nodes
    assert "technical_agent" in graph_nodes
    assert "decision_agent" in graph_nodes
    assert "backtest_agent" in graph_nodes
    assert "reflection_agent" in graph_nodes
    assert "final_report" in graph_nodes
    assert "company_agent" not in graph_nodes
    assert "financial_agent" not in graph_nodes
    assert "news_agent" not in graph_nodes
    assert "data_collection_agent" not in graph_nodes
    assert "risk_agent" not in graph_nodes
    graph_edges = {(edge.source, edge.target) for edge in graph.get_graph().edges}
    assert ("decision_agent", "backtest_agent") in graph_edges
    assert ("backtest_agent", "reflection_agent") in graph_edges


def test_graph_builds():
    graph = build_graph()
    assert graph is not None
    _assert_full_graph_nodes(graph)


def test_technical_chain_graph_builds():
    graph = build_technical_chain_graph()
    assert graph is not None
    _assert_technical_graph_nodes(graph)


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
    assert result["audit_report_path"].endswith(".md")
    assert "TEST 多智能体股票分析报告" in result["final_report"]
    assert "决策摘要" in result["final_report"]
    assert "收益率回测" in result["final_report"]
    assert "完整文档" in result["final_report"]
    assert "```json" not in result["final_report"]
    assert "使用边界" in result["final_report"]
    assert Path(result["final_report_path"]).exists()
    assert Path(result["audit_report_path"]).exists()
