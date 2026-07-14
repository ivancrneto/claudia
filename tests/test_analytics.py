"""Phase 4 tests — analytics sinks, pipeline emission, and favorite-team personalization."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.analytics import MemoryAnalytics, NullAnalytics, PostHogAnalytics  # noqa: E402
from services.gateway.pipeline import VoicePipeline  # noqa: E402
from services.tts import StubTTS  # noqa: E402
from skills._sdk import Dispatcher  # noqa: E402
from skills.futebol.handler import FutebolSkill  # noqa: E402
from skills.timer.handler import TimerSkill  # noqa: E402


def _pipeline(analytics):
    d = Dispatcher([TimerSkill(), FutebolSkill()])
    return VoicePipeline(d, stt=None, tts=StubTTS(), analytics=analytics)


# --- sinks -------------------------------------------------------------------------

def test_memory_top_intents_ordering():
    a = MemoryAnalytics()

    async def run():
        await a.track("intent_used", {"intent": "PROXIMO_JOGO"})
        await a.track("intent_used", {"intent": "SET_TIMER"})
        await a.track("intent_used", {"intent": "PROXIMO_JOGO"})
        await a.track("other", {"intent": "IGNORED"})

    asyncio.run(run())
    assert a.top_intents() == [("PROXIMO_JOGO", 2), ("SET_TIMER", 1)]


def test_null_analytics_is_noop():
    asyncio.run(NullAnalytics().track("intent_used", {"intent": "X"}))  # must not raise


def test_posthog_builds_payload_and_swallows_errors():
    captured = {}

    async def fake_post(url, payload):
        captured["url"] = url
        captured["payload"] = payload

    ph = PostHogAnalytics("phc_key", host="https://us.i.posthog.com", post=fake_post)
    asyncio.run(ph.track("intent_used", {"intent": "SET_TIMER"}, distinct_id="ivan"))
    assert captured["url"].endswith("/capture/")
    assert captured["payload"]["api_key"] == "phc_key"
    assert captured["payload"]["event"] == "intent_used"
    assert captured["payload"]["distinct_id"] == "ivan"
    assert captured["payload"]["properties"]["intent"] == "SET_TIMER"

    async def boom(url, payload):
        raise RuntimeError("network down")

    # A transport error must never propagate out of track().
    asyncio.run(PostHogAnalytics("k", post=boom).track("intent_used", {"intent": "X"}))


# --- pipeline emission (anonymized) ------------------------------------------------

def test_pipeline_emits_anonymized_intent_used():
    a = MemoryAnalytics()
    p = _pipeline(a)
    asyncio.run(p.run_text("põe um timer de 5 minutos", user={"user_id": "ivan", "locale": "pt-BR"}))
    assert len(a.events) == 1
    ev = a.events[0]
    assert ev["event"] == "intent_used"
    assert ev["distinct_id"] == "ivan"
    assert ev["properties"] == {"intent": "SET_TIMER", "source": "skill", "locale": "pt-BR"}
    assert "transcript" not in ev["properties"] and "text" not in ev["properties"]


def test_pipeline_anonymous_when_no_user():
    a = MemoryAnalytics()
    asyncio.run(_pipeline(a).run_text("qual a capital da França"))
    assert a.events[0]["distinct_id"] == "anonymous"
    assert a.events[0]["properties"]["source"] == "brain"


# --- personalization: favorite team disambiguates ----------------------------------

def test_favorite_team_from_context_disambiguates_futebol():
    a = MemoryAnalytics()
    r = asyncio.run(
        _pipeline(a).run_text("quando o Tricolor joga", user={"favorite_team_id": 129})
    )
    assert "Grêmio" in r.speech  # 129 = Grêmio, resolved without asking
    assert a.top_intents() == [("PROXIMO_JOGO", 1)]


if __name__ == "__main__":
    for fn in list(globals().values()):
        if callable(fn) and getattr(fn, "__name__", "").startswith("test_"):
            fn()
            print(f"ok  {fn.__name__}")
    print("all analytics tests passed")
