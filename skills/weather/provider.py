"""WeatherProvider — Open-Meteo (free, no API key). Injectable HTTP so it's tested offline.

Open-Meteo returns WMO weather codes; `describe_wmo` maps them to PT-BR phrases.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Protocol

BASE = "https://api.open-meteo.com/v1/forecast"

# WMO weather-code → PT-BR description (common codes; unknown falls back to "tempo instável").
_WMO = {
    0: "céu limpo",
    1: "predominantemente limpo",
    2: "parcialmente nublado",
    3: "nublado",
    45: "com nevoeiro",
    48: "com nevoeiro",
    51: "com garoa leve",
    53: "com garoa",
    55: "com garoa forte",
    61: "com chuva fraca",
    63: "com chuva",
    65: "com chuva forte",
    71: "com neve fraca",
    73: "com neve",
    75: "com neve forte",
    80: "com pancadas de chuva",
    81: "com pancadas de chuva",
    82: "com pancadas fortes de chuva",
    95: "com trovoadas",
    96: "com trovoadas e granizo",
    99: "com trovoadas e granizo",
}


def describe_wmo(code: int) -> str:
    return _WMO.get(code, "tempo instável")


@dataclass
class Weather:
    temp_c: float
    code: int
    tmax_c: float
    tmin_c: float
    precip_prob: int

    @property
    def description(self) -> str:
        return describe_wmo(self.code)


Fetch = Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]


class WeatherProvider(Protocol):
    async def current(self, lat: float, lon: float) -> Weather | None: ...


class StubWeatherProvider:
    def __init__(self, weather: Weather | None = None) -> None:
        self._weather = weather

    async def current(self, lat: float, lon: float) -> Weather | None:
        return self._weather or Weather(
            temp_c=28.0, code=0, tmax_c=30.0, tmin_c=24.0, precip_prob=10
        )


class OpenMeteoProvider:
    def __init__(self, fetch: Fetch | None = None) -> None:
        self._fetch = fetch or self._httpx_fetch

    async def _httpx_fetch(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        import httpx

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            return resp.json()

    @staticmethod
    def parse(data: dict[str, Any]) -> Weather | None:
        current = data.get("current") or {}
        daily = data.get("daily") or {}
        if "temperature_2m" not in current:
            return None

        def first(key: str, default: float = 0.0) -> float:
            seq = daily.get(key) or []
            return seq[0] if seq else default

        return Weather(
            temp_c=float(current["temperature_2m"]),
            code=int(current.get("weather_code", 0)),
            tmax_c=float(first("temperature_2m_max")),
            tmin_c=float(first("temperature_2m_min")),
            precip_prob=int(first("precipitation_probability_max")),
        )

    async def current(self, lat: float, lon: float) -> Weather | None:
        data = await self._fetch(
            BASE,
            {
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,weather_code",
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
                "timezone": "auto",
                "forecast_days": 1,
            },
        )
        return self.parse(data)
