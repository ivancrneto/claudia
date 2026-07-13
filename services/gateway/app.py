"""Claudia gateway (Phase 0).

Wires the skill dispatcher, NLU and brain fallback behind a text endpoint so the whole
routing path is exercisable without the audio pipeline. Phase 1 adds the WebSocket voice
path (STT in / TTS out).
"""

from __future__ import annotations

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
from skills.timer.handler import TimerSkill  # noqa: E402
from skills.weather.handler import WeatherSkill  # noqa: E402

app = FastAPI(title="Claudia Gateway", version="0.1.0")

dispatcher = Dispatcher([TimerSkill(), WeatherSkill(), FutebolSkill()])


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
