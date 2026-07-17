"""Independent Planner -> Company/Technical parallel analysis graph."""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from multiple_agent_finance.agents.company import company_agent_node
from multiple_agent_finance.agents.planner import planner_agent_node
from multiple_agent_finance.agents.technical import technical_agent_node
from multiple_agent_finance.graph.state import StockAnalysisState


def _warnings(section: dict[str, Any]) -> list[str]:
    return [str(item) for item in section.get("warnings", []) if item]


def collect_parallel_results(state: StockAnalysisState) -> dict[str, Any]:
    """Join unchanged Technical output and structured Company output."""

    technical = dict(state.get("technical_indicators", {}))
    company = dict(state.get("company_profile", {}))
    return {
        "parallel_analysis_result": {
            "ticker": state.get("ticker"),
            "as_of_date": state.get("as_of_date"),
            "technical_result": technical,
            "company_result": company,
            "warnings": [*_warnings(technical), *_warnings(company)],
        }
    }


def build_company_technical_parallel_graph():
    """Compile an isolated graph that stops before Decision and Reflection."""

    workflow = StateGraph(StockAnalysisState)
    workflow.add_node("planner", planner_agent_node)
    workflow.add_node("technical_agent", technical_agent_node)
    workflow.add_node("company_agent", company_agent_node)
    workflow.add_node("result_collector", collect_parallel_results)

    workflow.add_edge(START, "planner")
    workflow.add_edge("planner", "technical_agent")
    workflow.add_edge("planner", "company_agent")
    workflow.add_edge(["technical_agent", "company_agent"], "result_collector")
    workflow.add_edge("result_collector", END)

    return workflow.compile()
