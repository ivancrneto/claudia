"""Phase 1 tests — the voice turn pipeline end-to-end with offline STT/TTS stubs."""

import asyncio
import base64
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.gateway.hybrid import HybridRouter  # noqa: E402
from services.gateway.pipeline import VoicePipeline  # noqa: E402
from services.stt import EchoTextSTT, FixedSTT  # noqa: E402
from services.tts import StubTTS  # noqa: E402
from skills._sdk import Dispatcher  # noqa: E402
from skills.futebol.handler import FutebolSkill  # noqa: E402
from skills.timer.handler import TimerSkill  # noqa: E402
from skills.weather.handler import WeatherSkill  # noqa: E402


def _pipeline(stt=None, router=None):
    d = Dispatcher([TimerSkill(), WeatherSkill(), FutebolSkill()])
    return VoicePipeline(d, stt=stt or EchoTextSTT(), tts=StubTTS(), router=router)


def test_run_text_skill_with_action():
    r = asyncio.run(_pipeline().run_text("põe um timer de 5 minutos"))
    assert r.source == "skill" and r.intent == "SET_TIMER"
    assert r.actions and r.actions[0]["type"] == "set_os_timer"
    assert r.audio == b"AUDIO:" + r.speech.encode("utf-8")


def test_run_audio_transcribes_then_routes():
    r = asyncio.run(_pipeline().run_audio("quando o Bahia joga".encode("utf-8")))
    assert r.transcript == "quando o Bahia joga"
    assert r.intent == "PROXIMO_JOGO" and r.source == "skill"
    assert "Bahia" in r.speech
    assert r.audio.startswith(b"AUDIO:")


def test_brain_fallback_path():
    r = asyncio.run(_pipeline().run_text("qual a capital da França"))
    assert r.source == "brain" and r.intent == "FALLBACK"
    assert r.speech and r.audio.startswith(b"AUDIO:")


def test_fixed_stt_backend():
    r = asyncio.run(_pipeline(stt=FixedSTT("como está o tempo")).run_audio(b"\x00\x01raw"))
    assert r.transcript == "como está o tempo" and r.intent == "GET_WEATHER"


def test_hybrid_llm_classifier_fills_grammar_miss():
    async def classifier(text):
        return "SET_TIMER", {"duracao": "3 minutos"}

    router = HybridRouter(llm_classifier=classifier)
    r = asyncio.run(_pipeline(router=router).run_text("me lembra daqui a pouco"))
    assert r.intent == "SET_TIMER" and r.source == "skill"
    assert r.actions[0]["params"]["spoken_duration"] == "3 minutos"


def test_dev_turn_endpoint_and_startup_ingestion():
    # Call the endpoint coroutines directly — avoids TestClient's transport dependency.
    from services.gateway.app import (
        TurnIn,
        _FUTEBOL_CACHE,
        _prime_fixtures,
        dev_turn,
        health,
    )

    asyncio.run(_prime_fixtures())
    assert _FUTEBOL_CACHE.get(118) is not None  # Bahia primed at startup

    audio_b64 = base64.b64encode("quando o Bahia joga".encode("utf-8")).decode("ascii")
    out = asyncio.run(dev_turn(TurnIn(audio_b64=audio_b64)))
    assert out.intent == "PROXIMO_JOGO"
    assert "Bahia" in out.speech
    assert base64.b64decode(out.audio_b64).startswith(b"AUDIO:")

    h = asyncio.run(health())
    assert h["stt"] == "echo" and h["tts"] == "stub"


if __name__ == "__main__":
    for fn in list(globals().values()):
        if callable(fn) and getattr(fn, "__name__", "").startswith("test_"):
            fn()
            print(f"ok  {fn.__name__}")
    print("all pipeline tests passed")
