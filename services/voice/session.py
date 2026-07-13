"""VoiceSession — the wake→listen→think→speak turn with barge-in.

State machine:

    IDLE ──wake word──▶ LISTENING ──endpoint──▶ THINKING ──reply──▶ SPEAKING ──done──▶ IDLE
      ▲                                                                 │
      └──────────────────────── barge-in cancels TTS ◀─────────────────┘  (→ LISTENING)

The heavy pieces (wake model, streaming STT, TTS) are injected; the state transitions and
barge-in cancellation are pure and unit-tested. Audio out is emitted in chunks so a
barge-in can interrupt playback mid-reply.
"""

from __future__ import annotations

import asyncio
import inspect
from enum import Enum
from typing import Any, AsyncIterator, Awaitable, Callable

from services.gateway.pipeline import TurnResult, VoicePipeline
from services.stt.streaming import StreamingSTT
from services.voice.wakeword import WakeWord

AudioSink = Callable[[bytes], Any | Awaitable[Any]]


class SessionState(Enum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"


class VoiceSession:
    def __init__(
        self,
        pipeline: VoicePipeline,
        streaming_stt: StreamingSTT,
        wakeword: WakeWord | None = None,
        on_audio: AudioSink | None = None,
        user: dict | None = None,
        chunk_size: int = 16,
    ) -> None:
        self._pipeline = pipeline
        self._stt = streaming_stt
        self._wake = wakeword
        self._on_audio = on_audio
        self._user = user or {}
        self._chunk_size = chunk_size
        self.state = SessionState.IDLE
        self._interrupt = asyncio.Event()
        self.partials: list[str] = []
        self.emitted_chunks = 0

    def barge_in(self) -> None:
        """Interrupt an in-progress reply; playback stops and we return to LISTENING."""
        self._interrupt.set()

    async def run_turn(self, chunks: AsyncIterator[bytes]) -> TurnResult:
        self._interrupt.clear()
        self.partials = []
        self.emitted_chunks = 0

        captured = await self._listen(chunks)
        transcript = await self._transcribe(captured)

        self.state = SessionState.THINKING
        result = await self._pipeline.run_text(transcript, self._user)

        self.state = SessionState.SPEAKING
        await self._speak(result.audio)
        if not self._interrupt.is_set():
            self.state = SessionState.IDLE
        return result

    async def _listen(self, chunks: AsyncIterator[bytes]) -> list[bytes]:
        """Gate on the wake word (if any), then capture the command frames."""
        woken = self._wake is None
        if woken:
            self.state = SessionState.LISTENING
        captured: list[bytes] = []
        async for chunk in chunks:
            if not woken:
                if self._wake.detect(chunk):
                    woken = True
                    self.state = SessionState.LISTENING
                continue  # the wake frame itself isn't part of the command
            captured.append(chunk)
        return captured

    async def _transcribe(self, captured: list[bytes]) -> str:
        async def gen():
            for c in captured:
                yield c

        text = ""
        async for partial in self._stt.stream(gen()):
            text = partial.text
            if not partial.is_final:
                self.partials.append(partial.text)
        return text

    async def _speak(self, audio: bytes) -> None:
        for i in range(0, len(audio), self._chunk_size):
            if self._interrupt.is_set():
                self.state = SessionState.LISTENING  # barge-in: yield the floor
                return
            chunk = audio[i : i + self._chunk_size]
            self.emitted_chunks += 1
            if self._on_audio is not None:
                res = self._on_audio(chunk)
                if inspect.isawaitable(res):
                    await res
