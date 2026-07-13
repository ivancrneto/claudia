"""AnthropicAdapter — Claude via the Messages API (streaming + tool use)."""

from __future__ import annotations

from typing import Any, AsyncIterator

from services.brain.tools.translate import translate_tools

from .base import Delta, Message, ProviderConfig
from .transport import Transport, httpx_transport, iter_sse

DEFAULT_BASE = "https://api.anthropic.com"


class AnthropicAdapter:
    name = "anthropic"

    def __init__(self, config: ProviderConfig, transport: Transport | None = None) -> None:
        self.config = config
        self._transport = transport or httpx_transport()

    def _build(self, messages: list[Message], tools: list[dict[str, Any]] | None):
        system = "\n".join(m.content for m in messages if m.role == "system")
        msgs = [
            {"role": m.role, "content": m.content}
            for m in messages
            if m.role in ("user", "assistant")
        ]
        body: dict[str, Any] = {
            "model": self.config.model,
            "max_tokens": self.config.extra.get("max_tokens", 1024),
            "messages": msgs,
            "stream": True,
        }
        if system:
            body["system"] = system
        if tools:
            body["tools"] = translate_tools(tools, "anthropic")
        headers = {
            "x-api-key": self.config.api_key or "",
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        return (self.config.base_url or DEFAULT_BASE) + "/v1/messages", headers, body

    @staticmethod
    def _parse(obj: dict[str, Any]) -> list[Delta]:
        t = obj.get("type")
        if t == "content_block_delta":
            d = obj.get("delta", {})
            if d.get("type") == "text_delta":
                return [Delta(text=d.get("text", ""))]
            if d.get("type") == "input_json_delta":
                return [Delta(tool_call={"partial_json": d.get("partial_json", "")})]
        elif t == "content_block_start":
            block = obj.get("content_block", {})
            if block.get("type") == "tool_use":
                return [Delta(tool_call={"name": block.get("name"), "id": block.get("id")})]
        return []

    async def stream(
        self, messages: list[Message], tools: list[dict[str, Any]] | None = None
    ) -> AsyncIterator[Delta]:
        url, headers, body = self._build(messages, tools)
        async for obj in iter_sse(self._transport, url, headers, body):
            for delta in self._parse(obj):
                yield delta
