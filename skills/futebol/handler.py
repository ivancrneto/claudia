"""Futebol skill — "quando o Bahia joga?" → next fixture for a Brazilian club.

Reads cache-first (populated by the ingestion worker) and falls back to a live provider
call on a miss, so the common case is instant and rate-limit-safe.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from skills._sdk import Request, Response, Skill, load_manifest

from .ingestion import FixtureCache
from .provider import FootballProvider, StubProvider
from .teams import Ambiguous, names_for, resolve_team

_MANIFEST = load_manifest(Path(__file__).with_name("manifest.yaml"))


class FutebolSkill(Skill):
    manifest = _MANIFEST

    def __init__(
        self,
        provider: FootballProvider | None = None,
        cache: FixtureCache | None = None,
    ) -> None:
        self._provider = provider or StubProvider()
        self._cache = cache

    def can_handle(self, request: Request) -> bool:
        return request.intent == "PROXIMO_JOGO"

    async def handle(self, request: Request) -> Response:
        spoken = request.slot("time")
        favorite = request.user.get("favorite_team_id")
        try:
            team = resolve_team(spoken, favorite_id=favorite)
        except Ambiguous as exc:
            options = names_for(exc.candidates)
            joined = ", ".join(options[:-1]) + f" ou o {options[-1]}"
            return Response.speak(f"Você quis dizer o {joined}?", end_session=False)
        except KeyError:
            return Response.speak(f"Não conheço o time {spoken}.")

        fx = self._cache.get(team.id) if self._cache else None
        if fx is None:
            fx = await self._provider.next_fixture(team)
            if self._cache is not None:
                self._cache.set(team.id, fx)

        if fx is None:
            return Response.speak(f"Não achei o próximo jogo do {team.name}.")

        now = datetime.now(timezone.utc)
        local = "em casa" if fx.home else "fora de casa"
        return Response.speak(
            f"O {team.name} joga {fx.human_pt(now)}, {local}, "
            f"contra o {fx.opponent}, pelo {fx.competition}."
        )
