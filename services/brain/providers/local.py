"""LocalAdapter — the self-hosted PT-BR model (default/guest brain).

Always available so Claudia works with no account connected. Phase 1 points this at an
Ollama/vLLM endpoint; the Phase 0 stub echoes so the pipeline is exercisable offline.
"""

from __future__ import annotations

from typing import Any, AsyncIterator

from .base import Delta, Message


class LocalAdapter:
    name = "local"

    def __init__(self, model: str = "qwen2.5:7b-instruct") -> None:
        self.model = model

    async def stream(
        self, messages: list[Message], tools: list[dict[str, Any]] | None = None
    ) -> AsyncIterator[Delta]:
        last = messages[-1].content if messages else ""
        yield Delta(text=f"(brain local: {self.model}) você disse: {last}")
