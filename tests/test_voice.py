"""Phase 3 tests — wake word, streaming STT partials, and the barge-in state machine."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.gateway.pipeline import VoicePipeline  # noqa: E402
from services.stt import EchoStreamingSTT  # noqa: E402
from services.tts import StubTTS  # noqa: E402
from services.voice.session import SessionState, VoiceSession  # noqa: E402
from services.voice.wakeword import KeywordWakeWord  # noqa: E402
from skills._sdk import Dispatcher  # noqa: E402
from skills.futebol.handler import FutebolSkill  # noqa: E402
from skills.timer.handler import TimerSkill  # noqa: E402
from skills.weather.handler import WeatherSkill  # noqa: E402


def _chunks(items):
    async def gen():
        for it in items:
            yield it

    return gen()


def _pipeline():
    d = Dispatcher([TimerSkill(), WeatherSkill(), FutebolSkill()])
    return VoicePipeline(d, stt=None, tts=StubTTS())  # session drives STT itself


# --- wake word ---------------------------------------------------------------------

def test_keyword_wakeword_matches_accent_insensitive():
    w = KeywordWakeWord("Ei Claudia")
    assert w.detect("EI CLÁUDIA, tudo bem".encode("utf-8")) is True
    assert w.detect("qualquer coisa".encode("utf-8")) is False


# --- streaming STT partials --------------------------------------------------------

def test_streaming_stt_accumulates_and_finalizes():
    async def run():
        out = []
        async for p in EchoStreamingSTT().stream(_chunks([b"quando o ", b"Bahia ", b"joga"])):
            out.append((p.text, p.is_final))
        return out

    out = asyncio.run(run())
    assert out[0] == ("quando o", False)
    assert out[-1] == ("quando o Bahia joga", True)
    assert sum(1 for _, final in out if final) == 1


# --- full turn with wake gating ----------------------------------------------------

def test_full_turn_states_and_result():
    session = VoiceSession(
        _pipeline(), EchoStreamingSTT(), wakeword=KeywordWakeWord("ei claudia")
    )
    # Wake frame first, then the command in streamed chunks.
    result = asyncio.run(
        session.run_turn(_chunks([b"ei claudia", b"quando o ", b"Bahia ", b"joga"]))
    )
    assert result.intent == "PROXIMO_JOGO" and "Bahia" in result.speech
    assert session.state == SessionState.IDLE
    assert session.partials  # captured live partials
    assert session.emitted_chunks > 0  # spoke the reply


def test_turn_without_wakeword_starts_listening():
    session = VoiceSession(_pipeline(), EchoStreamingSTT())  # no wake word
    result = asyncio.run(
        session.run_turn(_chunks(["põe um timer de ".encode("utf-8"), b"5 minutos"]))
    )
    assert result.intent == "SET_TIMER"
    assert result.actions and result.actions[0]["type"] == "set_os_timer"


# --- barge-in ----------------------------------------------------------------------

def test_barge_in_interrupts_playback():
    calls = {"n": 0}

    def on_audio(_chunk):
        calls["n"] += 1
        # Interrupt right after the first emitted audio chunk.
        session.barge_in()

    session = VoiceSession(
        _pipeline(),
        EchoStreamingSTT(),
        on_audio=on_audio,
        chunk_size=4,  # small chunks so a long reply has many
    )
    result = asyncio.run(session.run_turn(_chunks([b"quando o Bahia joga"])))

    # Reply audio is long; barge-in after chunk 1 must stop the rest.
    total_chunks = (len(result.audio) + 3) // 4
    assert calls["n"] == 1
    assert session.emitted_chunks == 1 < total_chunks
    assert session.state == SessionState.LISTENING  # yielded the floor, not IDLE


if __name__ == "__main__":
    for fn in list(globals().values()):
        if callable(fn) and getattr(fn, "__name__", "").startswith("test_"):
            fn()
            print(f"ok  {fn.__name__}")
    print("all voice tests passed")
