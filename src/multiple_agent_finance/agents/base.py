"""Shared helpers for agent nodes."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from multiple_agent_finance.llm.base import get_base_llm_metadata


def audit_event(agent: str, message: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "agent": agent,
        "message": message,
        "payload": payload or {},
        "llm": get_base_llm_metadata(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
