"""Weather skill — real forecast via Open-Meteo, spoken in PT-BR.

Uses the device's location from the user context (lat/lon/city). With no coordinates it
asks the user to share location instead of guessing.
"""

from __future__ import annotations

from pathlib import Path

from skills._sdk import Request, Response, Skill, load_manifest

from .provider import OpenMeteoProvider, WeatherProvider

_MANIFEST = load_manifest(Path(__file__).with_name("manifest.yaml"))


class WeatherSkill(Skill):
    manifest = _MANIFEST

    def __init__(self, provider: WeatherProvider | None = None) -> None:
        self._provider = provider or OpenMeteoProvider()

    def can_handle(self, request: Request) -> bool:
        return request.intent == "GET_WEATHER"

    async def handle(self, request: Request) -> Response:
        lat = request.user.get("latitude")
        lon = request.user.get("longitude")
        city = request.user.get("city", "sua região")
        if lat is None or lon is None:
            return Response.speak(
                "Ainda não sei sua localização. Ative a localização para eu ver o tempo."
            )

        weather = await self._provider.current(float(lat), float(lon))
        if weather is None:
            return Response.speak(f"Não consegui pegar a previsão para {city} agora.")

        return Response.speak(
            f"Em {city} está {round(weather.temp_c)} graus, {weather.description}. "
            f"Máxima de {round(weather.tmax_c)}, mínima de {round(weather.tmin_c)}, "
            f"com {weather.precip_prob}% de chance de chuva."
        )
