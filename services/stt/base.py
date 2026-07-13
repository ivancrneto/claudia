"""STT interface — one method, swappable backend."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class STT(Protocol):
    name: str

    async def transcribe(self, audio: bytes, locale: str = "pt-BR") -> str:
        """Transcribe an utterance (Opus/PCM bytes) to text."""
        ...
