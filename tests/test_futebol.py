"""Phase 2 tests for the futebol skill: resolver, formatter, provider, cache/ingestion."""

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from skills._sdk import Request  # noqa: E402
from skills.futebol.format import humanize_kickoff  # noqa: E402
from skills.futebol.handler import FutebolSkill  # noqa: E402
from skills.futebol.ingestion import (  # noqa: E402
    FixtureIngestionWorker,
    InMemoryFixtureCache,
)
from skills.futebol.provider import APIFootballProvider, Fixture, StubProvider  # noqa: E402
from skills.futebol.teams import Ambiguous, resolve_team, team_by_id  # noqa: E402


# --- team resolution ---------------------------------------------------------------

def test_resolve_exact_and_alias():
    assert resolve_team("Bahia").name == "Bahia"
    assert resolve_team("Esquadrão").name == "Bahia"
    assert resolve_team("o Galo").name == "Atlético Mineiro"


def test_resolve_strips_article():
    assert resolve_team("o São Paulo").name == "São Paulo"


def test_resolve_fuzzy_typo():
    assert resolve_team("flamengu").name == "Flamengo"
    assert resolve_team("sao paolo").name == "São Paulo"


def test_resolve_ambiguous_tricolor():
    try:
        resolve_team("Tricolor")
        assert False, "expected Ambiguous"
    except Ambiguous as exc:
        assert 118 in exc.candidates and 126 in exc.candidates


def test_resolve_ambiguous_resolved_by_favorite():
    assert resolve_team("Tricolor", favorite_id=129).name == "Grêmio"


def test_resolve_unknown():
    try:
        resolve_team("Barcelona")
        assert False, "expected KeyError"
    except KeyError:
        pass


# --- formatting --------------------------------------------------------------------

def _dt(y, mo, d, h, mi=0):
    return datetime(y, mo, d, h, mi)


def test_humanize_today_tomorrow():
    now = _dt(2026, 7, 13, 10)
    assert humanize_kickoff(_dt(2026, 7, 13, 18, 30), now) == "hoje às 18h30"
    assert humanize_kickoff(_dt(2026, 7, 14, 16), now) == "amanhã às 16h"


def test_humanize_weekday_and_far():
    now = _dt(2026, 7, 13, 10)  # a Monday
    assert "sábado" in humanize_kickoff(_dt(2026, 7, 18, 21), now)
    assert humanize_kickoff(_dt(2026, 8, 2, 16), now).startswith("no dia 02/08")


# --- provider (offline, injected fetch) --------------------------------------------

_API_TEAMS = {"response": [{"team": {"id": 118, "name": "Bahia"}}]}
_API_FIXTURES = {
    "response": [
        {
            "fixture": {"date": "2026-07-18T21:30:00+00:00", "venue": {"name": "Fonte Nova"}},
            "teams": {"home": {"name": "Bahia"}, "away": {"name": "Fortaleza"}},
            "league": {"name": "Brasileirão", "round": "Regular Season - 20"},
        }
    ]
}


def test_api_football_provider_offline():
    async def fake_fetch(url, params):
        return _API_TEAMS if url.endswith("/teams") else _API_FIXTURES

    provider = APIFootballProvider(api_key="x", season=2026, fetch=fake_fetch)
    fx = asyncio.run(provider.next_fixture(team_by_id(118)))
    assert fx is not None
    assert fx.opponent == "Fortaleza"
    assert fx.home is True
    assert fx.competition == "Brasileirão"


def test_parse_fixture_away_game():
    payload = {
        "fixture": {"date": "2026-07-20T20:00:00+00:00"},
        "teams": {"home": {"name": "Fortaleza"}, "away": {"name": "Bahia"}},
        "league": {"name": "Brasileirão"},
    }
    fx = APIFootballProvider.parse_fixture(payload, "Bahia")
    assert fx.home is False and fx.opponent == "Fortaleza"


# --- cache + ingestion + handler ---------------------------------------------------

def test_ingestion_populates_cache_and_handler_reads_it():
    cache = InMemoryFixtureCache()
    fixture = Fixture(
        opponent="Vitória",
        competition="Brasileirão",
        kickoff_utc=datetime(2026, 7, 13, 21, 0, tzinfo=timezone.utc),
        home=True,
    )
    worker = FixtureIngestionWorker(StubProvider(fixture), cache, [team_by_id(118)])
    updated = asyncio.run(worker.run_once())
    assert updated == 1
    assert cache.get(118) is fixture

    # Handler with a provider that would explode if called → proves it read the cache.
    class Boom:
        async def next_fixture(self, team):
            raise AssertionError("should not hit provider on cache hit")

    skill = FutebolSkill(provider=Boom(), cache=cache)
    req = Request(text="quando o Bahia joga", intent="PROXIMO_JOGO", slots={"time": "Bahia"})
    resp = asyncio.run(skill.handle(req))
    assert "Bahia" in resp.speech and "Vitória" in resp.speech and "em casa" in resp.speech


def test_handler_ambiguous_message_lists_options():
    skill = FutebolSkill()
    req = Request(text="quando o Tricolor joga", intent="PROXIMO_JOGO", slots={"time": "Tricolor"})
    resp = asyncio.run(skill.handle(req))
    assert "Você quis dizer" in resp.speech and resp.end_session is False


if __name__ == "__main__":
    for fn in list(globals().values()):
        if callable(fn) and getattr(fn, "__name__", "").startswith("test_"):
            fn()
            print(f"ok  {fn.__name__}")
    print("all futebol tests passed")
