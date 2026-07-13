"""Streaming STT — emit partial transcripts as audio arrives, plus a final result.

Phase 3 lets the pipeline fire intent on a stable prefix and show live captions.
`EchoStreamingSTT` is the offline stub (each chunk is text); the real faster-whisper
streaming decode is a deployment TODO.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import AsyncIterator, Protocol, runtime_checkable


@dataclass
class Partial:
    text: str
    is_final: bool = False


@runtime_checkable
class StreamingSTT(Protocol):
    name: str

    def stream(self, chunks: AsyncIterator[bytes], locale: str = "pt-BR") -> AsyncIterator[Partial]:
        """Consume audio chunks, yield growing partials, end with is_final=True."""
        ...


class EchoStreamingSTT:
    """Offline: each chunk is UTF-8 text; yields the cumulative transcript per chunk."""

    name = "echo-stream"

    async def stream(
        self, chunks: AsyncIterator[bytes], locale: str = "pt-BR"
    ) -> AsyncIterator[Partial]:
        text = ""
        async for chunk in chunks:
            piece = chunk.decode("utf-8", errors="ignore")
            text = (text + piece)
            yield Partial(text=text.strip(), is_final=False)
        yield Partial(text=text.strip(), is_final=True)
