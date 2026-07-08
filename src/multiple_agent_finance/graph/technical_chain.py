"""Compatibility entry point for the weekly technical single-link graph."""

from __future__ import annotations

from multiple_agent_finance.graph.builder import build_graph


def build_technical_chain_graph():
    """Return the current weekly single-link graph.

    The graph intentionally contains only:
    planner -> technical_agent -> decision_agent -> reflection_agent -> final_report
    """

    return build_graph()
