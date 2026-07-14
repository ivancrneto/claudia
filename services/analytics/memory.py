"""In-memory analytics — powers the /dev/stats "most-used asks" view and the tests."""

from __future__ import annotations

from collections import Counter
from typing import Any


class MemoryAnalytics:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    async def track(
        self, event: str, properties: dict[str, Any], distinct_id: str = "anonymous"
    ) -> None:
        self.events.append(
            {"event": event, "properties": dict(properties), "distinct_id": distinct_id}
        )

    def top_intents(self, n: int = 10) -> list[tuple[str, int]]:
        counter: Counter[str] = Counter(
            e["properties"].get("intent")
            for e in self.events
            if e["event"] == "intent_used" and e["properties"].get("intent")
        )
        return counter.most_common(n)
