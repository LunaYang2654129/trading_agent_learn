"""Compatibility wrappers for market data.

Technical indicator logic lives in ``technical_tools``. This module remains so
older imports keep working while the main graph uses Technical Agent.
"""

from __future__ import annotations

from multiple_agent_finance.tools.technical_tools import get_market_snapshot

__all__ = ["get_market_snapshot"]
