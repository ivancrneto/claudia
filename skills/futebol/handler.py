"""Futebol skill — "quando o Bahia joga?" → next fixture for a Brazilian club."""

from __future__ import annotations

from pathlib import Path

from skills._sdk import Request, Response, Skill, load_manifest

from .provider import FootballProvider, StubProvider
from .teams import Ambiguous, resolve_team

_MANIFEST = load_manifest(Path(__file__).with_name("manifest.yaml"))


class FutebolSkill(Skill):
    manifest = _MANIFEST

    def __init__(self, provider: FootballProvider | None = None) -> None:
        self._provider = provider or StubProvider()

    def can_handle(self, request: Request) -> bool:
        return request.intent == "PROXIMO_JOGO"

    async def handle(self, request: Request) -> Response:
        spoken = request.slot("time")
        favorite = request.user.get("favorite_team_id")
        try:
            team = resolve_team(spoken, favorite_id=favorite)
        except Ambiguous:
            return Response.speak(
                "Você quis dizer o Bahia ou o São Paulo?", end_session=False
            )
        except KeyError:
            return Response.speak(f"Não conheço o time {spoken}.")

        fx = await self._provider.next_fixture(team)
        if fx is None:
            return Response.speak(f"Não achei o próximo jogo do {team.name}.")
        return Response.speak(
            f"O {team.name} joga {fx.human_pt}, contra o {fx.opponent}, pelo {fx.competition}."
        )
