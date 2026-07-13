"""OpenAIAdapter — ChatGPT models via Chat Completions (streaming + function calling).

`OpenAICompatAdapter` is the same wire format pointed at any OpenAI-compatible endpoint
(OpenRouter, Groq, Together, Ollama, LM Studio) — it just requires an explicit base_url.
"""

from __future__ import annotations

from typing import Any, AsyncIterator

from services.brain.tools.translate import translate_tools

from .base import Delta, Message, ProviderConfig
from .transport import Transport, httpx_transport, iter_sse

DEFAULT_BASE = "https://api.openai.com"


class OpenAIAdapter:
    name = "openai"
    _default_base = DEFAULT_BASE

    def __init__(self, config: ProviderConfig, transport: Transport | None = None) -> None:
        self.config = config
        self._transport = transport or httpx_transport()

    def _build(self, messages: list[Message], tools: list[dict[str, Any]] | None):
        body: dict[str, Any] = {
            "model": self.config.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": True,
        }
        if tools:
            body["tools"] = translate_tools(tools, "openai")
        headers = {
            "Authorization": f"Bearer {self.config.api_key or ''}",
            "content-type": "application/json",
        }
        base = self.config.base_url or self._default_base
        return base.rstrip("/") + "/v1/chat/completions", headers, body

    @staticmethod
    def _parse(obj: dict[str, Any]) -> list[Delta]:
        choices = obj.get("choices") or []
        if not choices:
            return []
        delta = choices[0].get("delta", {})
        out: list[Delta] = []
        if delta.get("content"):
            out.append(Delta(text=delta["content"]))
        for tc in delta.get("tool_calls") or []:
            fn = tc.get("function", {})
            out.append(
                Delta(tool_call={"name": fn.get("name"), "arguments": fn.get("arguments")})
            )
        return out

    async def stream(
        self, messages: list[Message], tools: list[dict[str, Any]] | None = None
    ) -> AsyncIterator[Delta]:
        url, headers, body = self._build(messages, tools)
        async for obj in iter_sse(self._transport, url, headers, body):
            for delta in self._parse(obj):
                yield delta


class OpenAICompatAdapter(OpenAIAdapter):
    """OpenAI-compatible endpoints (OpenRouter/Groq/Together/Ollama/LM Studio)."""

    name = "openai_compat"

    def __init__(self, config: ProviderConfig, transport: Transport | None = None) -> None:
        if not config.base_url:
            raise ValueError("OpenAICompatAdapter requires config.base_url")
        super().__init__(config, transport)
