"""Shared helpers for agent nodes."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def audit_event(agent: str, message: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "agent": agent,
        "message": message,
        "payload": payload or {},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
