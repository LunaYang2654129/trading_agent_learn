"""Central tool registry."""

from __future__ import annotations

from multiple_agent_finance.tools.company_tools import get_company_profile
from multiple_agent_finance.tools.financial_tools import get_financial_metrics
from multiple_agent_finance.tools.news_tools import get_news_analysis
from multiple_agent_finance.tools.risk_tools import get_risk_analysis

TOOL_REGISTRY = {
    "get_company_profile": get_company_profile,
    "get_financial_metrics": get_financial_metrics,
    "get_news_analysis": get_news_analysis,
    "get_risk_analysis": get_risk_analysis,
}
