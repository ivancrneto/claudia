"""Claudia gateway.

Wires the skill dispatcher, NLU and brain fallback behind a text endpoint so the whole
routing path is exercisable without the audio pipeline. Phase 1 adds the WebSocket voice
path (STT in / TTS out).

Futebol runs cache-first: an ingestion sweep at startup fills a fixtures cache for the
followed teams (see skills/futebol/ingestion.py). With API_FOOTBALL_KEY set it uses the
live provider; otherwise it falls back to the offline stub.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Make the repo root importable (skills/, services/ are top-level packages).
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from fastapi import FastAPI  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from services.brain.providers.base import Message  # noqa: E402
from services.brain.router import select_brain  # noqa: E402
from services.gateway import nlu  # noqa: E402
from skills._sdk import Dispatcher, Request  # noqa: E402
from skills.futebol.handler import FutebolSkill  # noqa: E402
from skills.futebol.ingestion import FixtureIngestionWorker, InMemoryFixtureCache  # noqa: E402
from skills.futebol.provider import APIFootballProvider, StubProvider  # noqa: E402
from skills.futebol.teams import TEAMS  # noqa: E402
from skills.timer.handler import TimerSkill  # noqa: E402
from skills.weather.handler import WeatherSkill  # noqa: E402

app = FastAPI(title="Claudia Gateway", version="0.2.0")

_FUTEBOL_CACHE = InMemoryFixtureCache()


def _football_provider():
    key = os.environ.get("API_FOOTBALL_KEY")
    if key:
        season = int(os.environ.get("FOOTBALL_SEASON", "2026"))
        return APIFootballProvider(api_key=key, season=season)
    return StubProvider()


_football = _football_provider()
dispatcher = Dispatcher(
    [TimerSkill(), WeatherSkill(), FutebolSkill(provider=_football, cache=_FUTEBOL_CACHE)]
)


@app.on_event("startup")
async def _prime_fixtures() -> None:
    # Followed teams default to the full roster; production scopes this to users' follows.
    worker = FixtureIngestionWorker(_football, _FUTEBOL_CACHE, TEAMS)
    await worker.run_once()


class HandleIn(BaseModel):
    text: str
    user: dict = {}


class HandleOut(BaseModel):
    intent: str
    speech: str
    actions: list = []
    source: str  # "skill" | "brain"


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "skills": [s.name for s in dispatcher.skills]}


@app.post("/dev/handle", response_model=HandleOut)
async def dev_handle(body: HandleIn) -> HandleOut:
    intent, slots = nlu.route(body.text)
    req = Request(text=body.text, intent=intent, slots=slots, user=body.user)
    resp = await dispatcher.dispatch(req)

    if resp.speech:
        return HandleOut(
            intent=intent,
            speech=resp.speech,
            actions=[{"type": a.type, "params": a.params} for a in resp.actions],
            source="skill",
        )

    # No skill produced speech → open Q&A: fall back to the (connected or local) brain.
    brain = select_brain(body.user)
    chunks = [d.text async for d in brain.stream([Message(role="user", content=body.text)])]
    return HandleOut(intent=intent, speech="".join(chunks), actions=[], source="brain")
