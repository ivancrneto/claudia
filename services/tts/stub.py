"""Offline TTS stub — returns a recognizable marker instead of real audio."""

from __future__ import annotations


class StubTTS:
    name = "stub"

    async def synthesize(self, text: str, voice: str = "pt_BR") -> bytes:
        # Recognizable, deterministic "audio" so the pipeline and clients can be tested.
        return b"AUDIO:" + text.encode("utf-8")
