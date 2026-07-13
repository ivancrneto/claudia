"""TTS interface — text in, audio bytes out."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class TTS(Protocol):
    name: str

    async def synthesize(self, text: str, voice: str = "pt_BR") -> bytes:
        """Synthesize speech audio (WAV/PCM bytes) for the given text."""
        ...
