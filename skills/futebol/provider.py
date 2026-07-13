"""FootballProvider — pluggable fixtures source.

`APIFootballProvider` talks to API-Football (api-sports.io). It resolves each club's
external team id by name once and caches it (we never hardcode third-party ids), then
fetches the next fixture. The HTTP call is injected so the parser is unit-testable offline.

`StubProvider` keeps the skill/dispatcher exercisable with no network (Phase 0 behaviour).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Protocol
from zoneinfo import ZoneInfo

from .format import humanize_kickoff
from .teams import Team

# Kickoff times are spoken in the club's local time; default to São Paulo (covers Bahia too
# in practice for user-facing phrasing — Phase 2.1 can map per-club timezones).
DEFAULT_TZ = ZoneInfo("America/Sao_Paulo")


@dataclass
class Fixture:
    opponent: str
    competition: str
    kickoff_utc: datetime
    home: bool = True
    round: str | None = None
    venue: str | None = None

    def human_pt(self, now: datetime | None = None, tz: ZoneInfo = DEFAULT_TZ) -> str:
        local = self.kickoff_utc.astimezone(tz)
        ref = (now or datetime.now(timezone.utc)).astimezone(tz)
        return humanize_kickoff(local, ref)


class FootballProvider(Protocol):
    async def next_fixture(self, team: Team) -> Fixture | None: ...


# --- Stub (offline) -----------------------------------------------------------------

class StubProvider:
    """Deterministic stub for local/dev — no network."""

    def __init__(self, fixture: Fixture | None = None) -> None:
        self._fixture = fixture

    async def next_fixture(self, team: Team) -> Fixture | None:
        if self._fixture is not None:
            return self._fixture
        return Fixture(
            opponent="Fortaleza",
            competition="Brasileirão",
            kickoff_utc=datetime(2026, 7, 18, 21, 30, tzinfo=timezone.utc),
            home=True,
            round="20ª rodada",
        )


# --- API-Football -------------------------------------------------------------------

# fetch(url, params) -> parsed JSON dict. Injected so tests never hit the network.
Fetch = Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]


class APIFootballProvider:
    BASE = "https://v3.football.api-sports.io"

    def __init__(self, api_key: str, season: int, fetch: Fetch | None = None) -> None:
        self._api_key = api_key
        self._season = season
        self._fetch = fetch or self._httpx_fetch
        self._team_id_cache: dict[int, int] = {}  # internal id -> API-Football id

    async def _httpx_fetch(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        import httpx  # local import so the module loads without httpx installed

        headers = {"x-apisports-key": self._api_key}
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params=params, headers=headers)
            resp.raise_for_status()
            return resp.json()

    async def _resolve_api_id(self, team: Team) -> int | None:
        if team.id in self._team_id_cache:
            return self._team_id_cache[team.id]
        data = await self._fetch(
            f"{self.BASE}/teams", {"search": team.name, "country": "Brazil"}
        )
        results = data.get("response", [])
        if not results:
            return None
        api_id = results[0]["team"]["id"]
        self._team_id_cache[team.id] = api_id
        return api_id

    @staticmethod
    def parse_fixture(payload: dict[str, Any], team_name: str) -> Fixture | None:
        """Parse one API-Football /fixtures item into a Fixture. Pure — unit-testable."""
        fx = payload.get("fixture", {})
        teams = payload.get("teams", {})
        league = payload.get("league", {})
        date_str = fx.get("date")
        if not date_str:
            return None
        kickoff = datetime.fromisoformat(date_str.replace("Z", "+00:00")).astimezone(
            timezone.utc
        )
        home_name = teams.get("home", {}).get("name", "")
        away_name = teams.get("away", {}).get("name", "")
        is_home = _matches(home_name, team_name)
        opponent = away_name if is_home else home_name
        return Fixture(
            opponent=opponent,
            competition=league.get("name", "Brasileirão"),
            kickoff_utc=kickoff,
            home=is_home,
            round=league.get("round"),
            venue=fx.get("venue", {}).get("name"),
        )

    async def next_fixture(self, team: Team) -> Fixture | None:
        api_id = await self._resolve_api_id(team)
        if api_id is None:
            return None
        data = await self._fetch(
            f"{self.BASE}/fixtures", {"team": api_id, "next": 1, "season": self._season}
        )
        results = data.get("response", [])
        if not results:
            return None
        return self.parse_fixture(results[0], team.name)


def _matches(a: str, b: str) -> bool:
    import unicodedata

    def norm(s: str) -> str:
        s = unicodedata.normalize("NFKD", s.lower())
        return "".join(c for c in s if not unicodedata.combining(c)).strip()

    na, nb = norm(a), norm(b)
    return na == nb or nb in na or na in nb
