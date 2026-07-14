"""Voice turn pipeline: audio → STT → hybrid NLU → skills/brain → TTS → audio + actions.

Adapters (STT/TTS/router/brain) are injected so the whole turn is testable offline with
stubs, and swapped for faster-whisper/Piper/LLM in deployment. Streaming partials and
barge-in are Phase 3; this runs a full utterance per turn.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from services.analytics.base import Analytics, NullAnalytics
from services.brain.providers.base import Message
from services.brain.router import select_brain
from services.gateway.hybrid import HybridRouter
from services.stt.base import STT
from services.tts.base import TTS
from skills._sdk import Dispatcher, Request


@dataclass
class TurnResult:
    transcript: str
    intent: str
    speech: str
    audio: bytes
    actions: list[dict[str, Any]]
    source: str  # "skill" | "brain"


class VoicePipeline:
    def __init__(
        self,
        dispatcher: Dispatcher,
        stt: STT,
        tts: TTS,
        router: HybridRouter | None = None,
        brain_selector: Callable[[dict], Any] = select_brain,
        analytics: Analytics | None = None,
    ) -> None:
        self._dispatcher = dispatcher
        self._stt = stt
        self._tts = tts
        self._router = router or HybridRouter()
        self._select_brain = brain_selector
        self._analytics = analytics or NullAnalytics()

    async def run_audio(self, audio: bytes, user: dict | None = None) -> TurnResult:
        transcript = await self._stt.transcribe(audio)
        return await self._run(transcript, user or {})

    async def run_text(self, text: str, user: dict | None = None) -> TurnResult:
        """Text-in path (no STT); still synthesizes the spoken reply."""
        return await self._run(text, user or {})

    async def _run(self, transcript: str, user: dict) -> TurnResult:
        intent, slots = await self._router.route(transcript)
        req = Request(text=transcript, intent=intent, slots=slots, user=user)
        resp = await self._dispatcher.dispatch(req)

        if resp.speech:
            speech = resp.speech
            actions = [{"type": a.type, "params": a.params} for a in resp.actions]
            source = "skill"
        else:
            # No skill produced speech → open Q&A via the connected/local brain.
            brain = self._select_brain(user)
            chunks = [
                d.text
                async for d in brain.stream([Message(role="user", content=transcript)])
            ]
            speech = "".join(chunks)
            actions = []
            source = "brain"

        audio = await self._tts.synthesize(speech) if speech else b""

        # Anonymized: intent/source/locale only — no transcript, no PII.
        await self._analytics.track(
            "intent_used",
            {"intent": intent, "source": source, "locale": user.get("locale", "pt-BR")},
            distinct_id=user.get("user_id", "anonymous"),
        )

        return TurnResult(
            transcript=transcript,
            intent=intent,
            speech=speech,
            audio=audio,
            actions=actions,
            source=source,
        )
