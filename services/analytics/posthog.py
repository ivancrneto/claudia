"""PostHogAnalytics — send anonymized events to PostHog's capture API.

The HTTP POST is injected so it's tested offline. Tracking must never break a turn, so any
transport error is swallowed. The project key is a write-only capture key, injected from the
environment (see config.py) — never committed.
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable

Post = Callable[[str, dict[str, Any]], Awaitable[None]]


class PostHogAnalytics:
    def __init__(
        self,
        api_key: str,
        host: str = "https://us.i.posthog.com",
        post: Post | None = None,
    ) -> None:
        self._api_key = api_key
        self._host = host.rstrip("/")
        self._post = post or self._httpx_post

    async def _httpx_post(self, url: str, payload: dict[str, Any]) -> None:
        import httpx

        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(url, json=payload)

    async def track(
        self, event: str, properties: dict[str, Any], distinct_id: str = "anonymous"
    ) -> None:
        payload = {
            "api_key": self._api_key,
            "event": event,
            "distinct_id": distinct_id,
            "properties": dict(properties),
        }
        try:
            await self._post(f"{self._host}/capture/", payload)
        except Exception:  # noqa: BLE001 - analytics must never break a turn
            return None
