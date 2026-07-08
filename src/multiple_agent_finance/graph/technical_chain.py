"""Technical single-link graph from the weekly implementation plan."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from multiple_agent_finance.agents.data import data_collection_agent_node
from multiple_agent_finance.agents.decision import decision_agent_node
from multiple_agent_finance.agents.planner import planner_agent_node
from multiple_agent_finance.agents.reflection import reflection_agent_node
from multiple_agent_finance.agents.technical import technical_agent_node
from multiple_agent_finance.graph.state import StockAnalysisState
from multiple_agent_finance.reports.final_report import final_report_node


def technical_chain_route(state: StockAnalysisState) -> str:
    """Retry technical single-link from data collection, otherwise finalize."""

    reflection = state.get("reflection_result", {})
    passed = bool(reflection.get("passed", False))
    confidence = float(state.get("confidence_score", 0.0))
    threshold = float(state.get("confidence_threshold", 0.75))
    retry_count = int(state.get("retry_count", 0))
    max_retries = int(state.get("max_retries", 1))

    if passed and confidence >= threshold:
        return "final_report"
    if retry_count < max_retries:
        return "data_collection_agent"
    return "final_report"


def build_technical_chain_graph():
    """Create the single-link workflow.

    Flow:
    Data Collection/Ingestion -> Planner -> Technical -> Decision -> Reflection
    -> Final Report or retry to Data Collection.
    """

    workflow = StateGraph(StockAnalysisState)

    workflow.add_node("data_collection_agent", data_collection_agent_node)
    workflow.add_node("planner", planner_agent_node)
    workflow.add_node("technical_agent", technical_agent_node)
    workflow.add_node("decision_agent", decision_agent_node)
    workflow.add_node("reflection_agent", reflection_agent_node)
    workflow.add_node("final_report", final_report_node)

    workflow.add_edge(START, "data_collection_agent")
    workflow.add_edge("data_collection_agent", "planner")
    workflow.add_edge("planner", "technical_agent")
    workflow.add_edge("technical_agent", "decision_agent")
    workflow.add_edge("decision_agent", "reflection_agent")
    workflow.add_conditional_edges(
        "reflection_agent",
        technical_chain_route,
        {
            "data_collection_agent": "data_collection_agent",
            "final_report": "final_report",
        },
    )
    workflow.add_edge("final_report", END)

    return workflow.compile()
