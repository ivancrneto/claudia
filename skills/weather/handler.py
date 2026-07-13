"""Weather skill — stub. Phase 1 wires Open-Meteo (free, no key) using device location."""

from __future__ import annotations

from pathlib import Path

from skills._sdk import Request, Response, Skill, load_manifest

_MANIFEST = load_manifest(Path(__file__).with_name("manifest.yaml"))


class WeatherSkill(Skill):
    manifest = _MANIFEST

    def can_handle(self, request: Request) -> bool:
        return request.intent == "GET_WEATHER"

    async def handle(self, request: Request) -> Response:
        # TODO(phase-1): call Open-Meteo with the device's geolocation.
        city = request.user.get("city", "sua região")
        return Response.speak(
            f"A previsão para {city} ainda não está conectada — chega na Fase 1."
        )
