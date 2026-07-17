"""Build the full parallel specialist LangGraph workflow."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from multiple_agent_finance.agents.backtest import backtest_agent_node
from multiple_agent_finance.agents.company import company_agent_node
from multiple_agent_finance.agents.decision import decision_agent_node
from multiple_agent_finance.agents.financial import financial_agent_node
from multiple_agent_finance.agents.news import news_agent_node
from multiple_agent_finance.agents.planner import planner_agent_node
from multiple_agent_finance.agents.reflection import reflection_agent_node
from multiple_agent_finance.agents.technical import technical_agent_node
from multiple_agent_finance.graph.routes import confidence_route
from multiple_agent_finance.graph.state import StockAnalysisState
from multiple_agent_finance.reports.final_report import final_report_node


def build_graph():
    """Create the full graph with parallel specialist agents."""

    workflow = StateGraph(StockAnalysisState)

    workflow.add_node("planner", planner_agent_node)
    workflow.add_node("company_agent", company_agent_node)
    workflow.add_node("financial_agent", financial_agent_node)
    workflow.add_node("news_agent", news_agent_node)
    workflow.add_node("technical_agent", technical_agent_node)
    workflow.add_node("decision_agent", decision_agent_node)
    workflow.add_node("backtest_agent", backtest_agent_node)
    workflow.add_node("reflection_agent", reflection_agent_node)
    workflow.add_node("final_report", final_report_node)

    workflow.add_edge(START, "planner")
    workflow.add_edge("planner", "company_agent")
    workflow.add_edge("planner", "financial_agent")
    workflow.add_edge("planner", "news_agent")
    workflow.add_edge("planner", "technical_agent")
    workflow.add_edge(
        ["company_agent", "financial_agent", "news_agent", "technical_agent"],
        "decision_agent",
    )
    workflow.add_edge("decision_agent", "backtest_agent")
    workflow.add_edge("backtest_agent", "reflection_agent")
    workflow.add_conditional_edges(
        "reflection_agent",
        confidence_route,
        {
            "planner": "planner",
            "final_report": "final_report",
        },
    )
    workflow.add_edge("final_report", END)

    return workflow.compile()
