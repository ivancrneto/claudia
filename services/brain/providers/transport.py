"""Shared streaming transport for the native provider adapters.

All three providers can emit Server-Sent-Events (`data: {json}` lines) — Gemini via
`?alt=sse` — so one line-oriented parser serves them all. The transport is a callable so
tests inject canned lines and the adapters never touch the network.
"""

from __future__ import annotations

import json
from typing import Any, AsyncIterator, Callable

# transport(url, headers, body) -> async iterator of raw text lines.
Transport = Callable[[str, dict[str, str], dict[str, Any]], AsyncIterator[str]]


def httpx_transport(timeout: float = 60.0) -> Transport:
    """Default transport: POST and stream response lines with httpx."""

    async def _transport(url: str, headers: dict[str, str], body: dict[str, Any]):
        import httpx  # local import so the module loads without httpx installed

        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream("POST", url, headers=headers, json=body) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    yield line

    return _transport


async def iter_sse(
    transport: Transport, url: str, headers: dict[str, str], body: dict[str, Any]
) -> AsyncIterator[dict[str, Any]]:
    """Yield parsed JSON objects from `data:` lines, stopping at `[DONE]`."""
    async for line in transport(url, headers, body):
        line = line.strip()
        if not line or not line.startswith("data:"):
            continue
        payload = line[len("data:"):].strip()
        if payload == "[DONE]":
            return
        try:
            yield json.loads(payload)
        except json.JSONDecodeError:
            continue
