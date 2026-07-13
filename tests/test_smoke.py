"""Phase 0 smoke tests — routing path works end-to-end without the audio pipeline."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.gateway import nlu  # noqa: E402
from skills._sdk import Dispatcher, Request  # noqa: E402
from skills.futebol.handler import FutebolSkill  # noqa: E402
from skills.timer.handler import TimerSkill  # noqa: E402
from skills.weather.handler import WeatherSkill  # noqa: E402

dispatcher = Dispatcher([TimerSkill(), WeatherSkill(), FutebolSkill()])


def _handle(text: str, user: dict | None = None):
    intent, slots = nlu.route(text)
    req = Request(text=text, intent=intent, slots=slots, user=user or {})
    return intent, asyncio.run(dispatcher.dispatch(req))


def test_futebol_bahia():
    intent, resp = _handle("quando o Bahia joga?")
    assert intent == "PROXIMO_JOGO"
    assert "Bahia" in resp.speech
    assert "Fortaleza" in resp.speech


def test_futebol_nickname():
    _, resp = _handle("quando joga o Esquadrão")
    assert "Bahia" in resp.speech


def test_futebol_ambiguous_tricolor():
    _, resp = _handle("quando o Tricolor joga")
    assert "Bahia ou o São Paulo" in resp.speech


def test_futebol_ambiguous_resolved_by_favorite():
    _, resp = _handle("quando o Tricolor joga", user={"favorite_team_id": 126})
    assert "São Paulo" in resp.speech


def test_timer_action():
    _, resp = _handle("põe um timer de 10 minutos")
    assert resp.actions and resp.actions[0].type == "set_os_timer"


def test_weather_intent():
    intent, resp = _handle("como está o tempo hoje")
    assert intent == "GET_WEATHER"
    assert resp.speech


if __name__ == "__main__":
    for fn in list(globals().values()):
        if callable(fn) and getattr(fn, "__name__", "").startswith("test_"):
            fn()
            print(f"ok  {fn.__name__}")
    print("all smoke tests passed")
