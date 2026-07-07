"""Shared memory adapter.

The first version keeps memory in LangGraph State. This module is reserved
for SQLite/vector-store persistence.
"""

from __future__ import annotations

from typing import Any


class SharedMemory:
    def __init__(self) -> None:
        self._items: list[dict[str, Any]] = []

    def write(self, item: dict[str, Any]) -> None:
        self._items.append(item)

    def read_all(self) -> list[dict[str, Any]]:
        return list(self._items)
