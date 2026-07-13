"""FootballProvider — pluggable fixtures source.

Phase 2 backs this with API-Football and a scheduled ingestion worker writing to
Postgres/Redis (so answers are instant and rate limits aren't hit per request). The
in-memory stub lets the skill and dispatcher be exercised end-to-end today.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .teams import Team


@dataclass
class Fixture:
    opponent: str
    competition: str
    human_pt: str  # e.g. "no próximo sábado, dia 19, às 18h30"


class FootballProvider(Protocol):
    async def next_fixture(self, team: Team) -> Fixture | None: ...


class StubProvider:
    """Deterministic stub for Phase 0 — no network."""

    async def next_fixture(self, team: Team) -> Fixture | None:
        return Fixture(
            opponent="Fortaleza",
            competition="Brasileirão",
            human_pt="no próximo sábado, às 18h30",
        )
