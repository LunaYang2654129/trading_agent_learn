"""Build the current weekly single-link LangGraph workflow."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

# Paused for future iterations:
# from multiple_agent_finance.agents.company import company_agent_node
# from multiple_agent_finance.agents.financial import financial_agent_node
# from multiple_agent_finance.agents.news import news_agent_node
# from multiple_agent_finance.agents.data import data_collection_agent_node

from multiple_agent_finance.agents.decision import decision_agent_node
from multiple_agent_finance.agents.planner import planner_agent_node
from multiple_agent_finance.agents.reflection import reflection_agent_node
from multiple_agent_finance.agents.technical import technical_agent_node
from multiple_agent_finance.graph.routes import confidence_route
from multiple_agent_finance.graph.state import StockAnalysisState
from multiple_agent_finance.reports.final_report import final_report_node


def build_graph():
    """Create the weekly feasibility graph.

    Current scope:
    Planner -> Technical -> Decision -> Reflection -> Final Report

    Company, Financial, News, Risk, and in-graph data collection are deliberately
    paused this week. The technical input data should be prepared before graph
    invocation and passed through `state.market_data`.
    """

    workflow = StateGraph(StockAnalysisState)

    workflow.add_node("planner", planner_agent_node)
    workflow.add_node("technical_agent", technical_agent_node)
    workflow.add_node("decision_agent", decision_agent_node)
    workflow.add_node("reflection_agent", reflection_agent_node)
    workflow.add_node("final_report", final_report_node)

    workflow.add_edge(START, "planner")
    workflow.add_edge("planner", "technical_agent")
    workflow.add_edge("technical_agent", "decision_agent")
    workflow.add_edge("decision_agent", "reflection_agent")
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
