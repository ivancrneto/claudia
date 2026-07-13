"""Provider abstraction: one interface, many backends (Claude, ChatGPT, Gemini, local).

Adapters translate this neutral shape to each provider's API and tool-calling format, so
the brain router and the skill→tool bridge stay provider-agnostic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Protocol, runtime_checkable


@dataclass
class Message:
    role: str  # "system" | "user" | "assistant" | "tool"
    content: str


@dataclass
class Delta:
    """A streamed chunk: text, and/or a tool call the connected brain wants to make."""

    text: str = ""
    tool_call: dict[str, Any] | None = None


@dataclass
class ProviderConfig:
    """Resolved per-user brain config (comes from the Account Vault at request time)."""

    model: str
    base_url: str | None = None
    api_key: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class LLMProvider(Protocol):
    name: str

    async def stream(
        self, messages: list[Message], tools: list[dict[str, Any]] | None = None
    ) -> AsyncIterator[Delta]:
        """Stream a completion. `tools` are skill schemas from the tool bridge."""
        ...
