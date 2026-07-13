"""OpenAICompatAdapter — one adapter, dozens of providers.

Any OpenAI-compatible /chat/completions endpoint: OpenRouter, Groq, Together, Ollama,
LM Studio, or a user's own OpenAI API key. This is the fastest way to support "connect
Claude/ChatGPT/other" — a single integration covering most of the market. Native
Anthropic/OpenAI/Gemini adapters are added in Phase 3.5 for first-class tool use.

The network call is intentionally left as a Phase 3.5 TODO; the shape is fixed here.
"""

from __future__ import annotations

from typing import Any, AsyncIterator

from .base import Delta, Message, ProviderConfig


class OpenAICompatAdapter:
    name = "openai_compat"

    def __init__(self, config: ProviderConfig) -> None:
        # base_url e.g. https://openrouter.ai/api/v1 ; api_key comes from the Account Vault.
        self.config = config

    async def stream(
        self, messages: list[Message], tools: list[dict[str, Any]] | None = None
    ) -> AsyncIterator[Delta]:
        # TODO(phase-3.5): POST {base_url}/chat/completions with stream=true, map
        # choices[].delta.content -> Delta.text and tool_calls -> Delta.tool_call.
        raise NotImplementedError(
            "Wire an httpx streaming call to the OpenAI-compatible endpoint in Phase 3.5"
        )
        yield  # pragma: no cover - marks this as an async generator
