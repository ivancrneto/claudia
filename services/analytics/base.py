"""Analytics interface. Events are anonymized — never a transcript or PII, just the intent,
source, and locale — so we can measure the most-used asks without tracking what was said.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Analytics(Protocol):
    async def track(
        self, event: str, properties: dict[str, Any], distinct_id: str = "anonymous"
    ) -> None:
        ...


class NullAnalytics:
    """Default no-op sink."""

    async def track(
        self, event: str, properties: dict[str, Any], distinct_id: str = "anonymous"
    ) -> None:
        return None
