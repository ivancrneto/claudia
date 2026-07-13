"""Claudia gateway.

Runs the full voice turn pipeline (audio → STT → hybrid NLU → skills/brain → TTS) behind:
- `POST /dev/handle` — text in, structured out (no audio); quickest way to exercise routing.
- `POST /dev/turn`   — base64 audio in, transcript + base64 reply audio out.
- `WS   /ws/voice`   — binary audio frames in, JSON result + reply audio out.

STT/TTS default to offline stubs so everything runs without models; set STT_BACKEND=whisper
/ TTS_BACKEND=piper to use the real self-hosted adapters in deployment.

Futebol runs cache-first: an ingestion sweep at startup fills a fixtures cache for the
followed teams. With API_FOOTBALL_KEY set it uses the live provider; else the offline stub.
"""

from __future__ import annotations

import base64
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Make the repo root importable (skills/, services/ are top-level packages).
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from services.config import Settings  # noqa: E402
from services.gateway.pipeline import VoicePipeline  # noqa: E402
from services.stt import EchoTextSTT, FasterWhisperSTT  # noqa: E402
from services.tts import PiperTTS, StubTTS  # noqa: E402
from skills._sdk import Dispatcher  # noqa: E402
from skills.futebol.handler import FutebolSkill  # noqa: E402
from skills.futebol.ingestion import FixtureIngestionWorker, InMemoryFixtureCache  # noqa: E402
from skills.futebol.provider import APIFootballProvider, StubProvider  # noqa: E402
from skills.futebol.teams import TEAMS  # noqa: E402
from skills.timer.handler import TimerSkill  # noqa: E402
from skills.weather.handler import WeatherSkill  # noqa: E402

settings = Settings.from_env()
_FUTEBOL_CACHE = InMemoryFixtureCache()


def _football_provider():
    if settings.api_football_key:
        return APIFootballProvider(
            api_key=settings.api_football_key, season=settings.football_season
        )
    return StubProvider()


def _make_stt():
    return FasterWhisperSTT() if settings.stt_backend == "whisper" else EchoTextSTT()


def _make_tts():
    return PiperTTS() if settings.tts_backend == "piper" else StubTTS()


_football = _football_provider()
dispatcher = Dispatcher(
    [TimerSkill(), WeatherSkill(), FutebolSkill(provider=_football, cache=_FUTEBOL_CACHE)]
)
pipeline = VoicePipeline(dispatcher, stt=_make_stt(), tts=_make_tts())


async def _prime_fixtures() -> None:
    # Followed teams default to the full roster; production scopes this to users' follows.
    worker = FixtureIngestionWorker(_football, _FUTEBOL_CACHE, TEAMS)
    await worker.run_once()


@asynccontextmanager
async def _lifespan(_app: "FastAPI"):
    settings.validate()  # fail fast in prod if a required secret is missing
    await _prime_fixtures()
    yield


app = FastAPI(title="Claudia Gateway", version="0.4.0", lifespan=_lifespan)


class HandleIn(BaseModel):
    text: str
    user: dict = {}


class HandleOut(BaseModel):
    transcript: str
    intent: str
    speech: str
    actions: list = []
    source: str  # "skill" | "brain"


class TurnIn(BaseModel):
    audio_b64: str
    user: dict = {}


class TurnOut(HandleOut):
    audio_b64: str


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "skills": [s.name for s in dispatcher.skills],
        "stt": pipeline._stt.name,
        "tts": pipeline._tts.name,
    }


@app.post("/dev/handle", response_model=HandleOut)
async def dev_handle(body: HandleIn) -> HandleOut:
    r = await pipeline.run_text(body.text, body.user)
    return HandleOut(
        transcript=r.transcript,
        intent=r.intent,
        speech=r.speech,
        actions=r.actions,
        source=r.source,
    )


@app.post("/dev/turn", response_model=TurnOut)
async def dev_turn(body: TurnIn) -> TurnOut:
    audio = base64.b64decode(body.audio_b64)
    r = await pipeline.run_audio(audio, body.user)
    return TurnOut(
        transcript=r.transcript,
        intent=r.intent,
        speech=r.speech,
        actions=r.actions,
        source=r.source,
        audio_b64=base64.b64encode(r.audio).decode("ascii"),
    )


@app.websocket("/ws/voice")
async def ws_voice(ws: WebSocket) -> None:
    """Accumulate binary audio frames until a text "end" message, then run one turn.

    Reply is a JSON result message followed by a binary frame carrying the TTS audio.
    """
    await ws.accept()
    buffer = bytearray()
    try:
        while True:
            msg = await ws.receive()
            if msg.get("bytes") is not None:
                buffer.extend(msg["bytes"])
            elif msg.get("text") == "end":
                r = await pipeline.run_audio(bytes(buffer), user={})
                buffer.clear()
                await ws.send_json(
                    {
                        "type": "result",
                        "transcript": r.transcript,
                        "intent": r.intent,
                        "speech": r.speech,
                        "actions": r.actions,
                        "source": r.source,
                    }
                )
                await ws.send_bytes(r.audio)
            elif msg.get("text") == "close":
                break
    except WebSocketDisconnect:
        return
