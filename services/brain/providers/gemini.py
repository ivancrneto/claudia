"""GeminiAdapter — Google Gemini via streamGenerateContent (SSE + function calls)."""

from __future__ import annotations

from typing import Any, AsyncIterator

from services.brain.tools.translate import translate_tools

from .base import Delta, Message, ProviderConfig
from .transport import Transport, httpx_transport, iter_sse

DEFAULT_BASE = "https://generativelanguage.googleapis.com"


class GeminiAdapter:
    name = "gemini"

    def __init__(self, config: ProviderConfig, transport: Transport | None = None) -> None:
        self.config = config
        self._transport = transport or httpx_transport()

    def _build(self, messages: list[Message], tools: list[dict[str, Any]] | None):
        contents = [
            {
                "role": "model" if m.role == "assistant" else "user",
                "parts": [{"text": m.content}],
            }
            for m in messages
            if m.role != "system"
        ]
        body: dict[str, Any] = {"contents": contents}
        system = [m.content for m in messages if m.role == "system"]
        if system:
            body["systemInstruction"] = {"parts": [{"text": "\n".join(system)}]}
        if tools:
            body["tools"] = translate_tools(tools, "gemini")
        base = (self.config.base_url or DEFAULT_BASE).rstrip("/")
        url = (
            f"{base}/v1beta/models/{self.config.model}:streamGenerateContent"
            f"?alt=sse&key={self.config.api_key or ''}"
        )
        return url, {"content-type": "application/json"}, body

    @staticmethod
    def _parse(obj: dict[str, Any]) -> list[Delta]:
        out: list[Delta] = []
        for cand in obj.get("candidates", []):
            for part in cand.get("content", {}).get("parts", []):
                if "text" in part:
                    out.append(Delta(text=part["text"]))
                elif "functionCall" in part:
                    fc = part["functionCall"]
                    out.append(
                        Delta(tool_call={"name": fc.get("name"), "args": fc.get("args")})
                    )
        return out

    async def stream(
        self, messages: list[Message], tools: list[dict[str, Any]] | None = None
    ) -> AsyncIterator[Delta]:
        url, headers, body = self._build(messages, tools)
        async for obj in iter_sse(self._transport, url, headers, body):
            for delta in self._parse(obj):
                yield delta
