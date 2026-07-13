"""Offline STT stubs so the voice pipeline is exercisable without a model."""

from __future__ import annotations


class EchoTextSTT:
    """Dev/test: treats the audio payload as UTF-8 text.

    Lets the full audio path (STT → NLU → skills/brain → TTS) run deterministically by
    sending a transcript as the "audio" bytes.
    """

    name = "echo"

    async def transcribe(self, audio: bytes, locale: str = "pt-BR") -> str:
        return audio.decode("utf-8", errors="ignore").strip()


class FixedSTT:
    """Always returns a preset transcript, regardless of input."""

    name = "fixed"

    def __init__(self, transcript: str) -> None:
        self._transcript = transcript

    async def transcribe(self, audio: bytes, locale: str = "pt-BR") -> str:
        return self._transcript
