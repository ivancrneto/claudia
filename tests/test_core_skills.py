"""Tests for the rounded-out core asks: weather (Open-Meteo), YouTube, music, and routing."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.gateway import nlu  # noqa: E402
from skills._sdk import Request  # noqa: E402
from skills.music.handler import MusicSkill  # noqa: E402
from skills.weather.handler import WeatherSkill  # noqa: E402
from skills.weather.provider import OpenMeteoProvider, StubWeatherProvider, Weather  # noqa: E402
from skills.youtube.handler import YouTubeSkill  # noqa: E402


def _handle(skill, intent, slots=None, user=None):
    req = Request(text="", intent=intent, slots=slots or {}, user=user or {})
    return asyncio.run(skill.handle(req))


# --- NLU routing -------------------------------------------------------------------

def test_routing_youtube_before_music():
    assert nlu.route("toca Bruno Mars no YouTube") == ("OPEN_YOUTUBE", {"consulta": "bruno mars"})
    assert nlu.route("abre o YouTube")[0] == "OPEN_YOUTUBE"
    assert nlu.route("youtube receita de bolo") == ("OPEN_YOUTUBE", {"consulta": "receita de bolo"})


def test_routing_music_generic():
    assert nlu.route("toca Bruno Mars") == ("PLAY_MUSIC", {"consulta": "bruno mars"})
    assert nlu.route("coloca pagode pra tocar") == ("PLAY_MUSIC", {"consulta": "pagode"})


def test_routing_weather_and_timer_unaffected():
    assert nlu.route("como está o tempo")[0] == "GET_WEATHER"
    assert nlu.route("põe um timer de 10 minutos")[0] == "SET_TIMER"


# --- Open-Meteo provider parse -----------------------------------------------------

_OPEN_METEO = {
    "current": {"temperature_2m": 27.4, "weather_code": 2},
    "daily": {
        "temperature_2m_max": [30.1],
        "temperature_2m_min": [23.6],
        "precipitation_probability_max": [40],
    },
}


def test_open_meteo_parse():
    w = OpenMeteoProvider.parse(_OPEN_METEO)
    assert w is not None
    assert round(w.temp_c) == 27 and w.code == 2
    assert w.description == "parcialmente nublado"
    assert round(w.tmax_c) == 30 and round(w.tmin_c) == 24 and w.precip_prob == 40


def test_open_meteo_parse_missing_returns_none():
    assert OpenMeteoProvider.parse({}) is None


def test_open_meteo_provider_offline():
    async def fake_fetch(url, params):
        assert params["latitude"] == -12.97
        return _OPEN_METEO

    provider = OpenMeteoProvider(fetch=fake_fetch)
    w = asyncio.run(provider.current(-12.97, -38.51))
    assert w and round(w.temp_c) == 27


# --- weather skill -----------------------------------------------------------------

def test_weather_skill_speaks_forecast():
    skill = WeatherSkill(
        provider=StubWeatherProvider(Weather(temp_c=28.0, code=0, tmax_c=31.0, tmin_c=24.0, precip_prob=10))
    )
    resp = _handle(skill, "GET_WEATHER", user={"city": "Salvador", "latitude": -12.97, "longitude": -38.51})
    assert "Salvador" in resp.speech and "28 graus" in resp.speech
    assert "céu limpo" in resp.speech and "10% de chance" in resp.speech


def test_weather_skill_needs_location():
    resp = _handle(WeatherSkill(provider=StubWeatherProvider()), "GET_WEATHER", user={})
    assert "localização" in resp.speech


# --- youtube + music actions -------------------------------------------------------

def test_youtube_with_and_without_query():
    r1 = _handle(YouTubeSkill(), "OPEN_YOUTUBE", slots={"consulta": "gatos"})
    assert r1.actions[0].type == "open_youtube" and r1.actions[0].params["query"] == "gatos"
    r2 = _handle(YouTubeSkill(), "OPEN_YOUTUBE")
    assert r2.actions[0].type == "open_youtube" and r2.actions[0].params["query"] == ""


def test_music_action_and_empty_prompt():
    r1 = _handle(MusicSkill(), "PLAY_MUSIC", slots={"consulta": "Bruno Mars"})
    assert r1.actions[0].type == "play_music" and r1.actions[0].params["query"] == "Bruno Mars"
    r2 = _handle(MusicSkill(), "PLAY_MUSIC")
    assert not r2.actions and r2.end_session is False


if __name__ == "__main__":
    for fn in list(globals().values()):
        if callable(fn) and getattr(fn, "__name__", "").startswith("test_"):
            fn()
            print(f"ok  {fn.__name__}")
    print("all core-skill tests passed")
