"""Scheduled fixture ingestion — pull next fixtures for followed teams into a cache.

Answering "quando o Bahia joga?" must be instant and must not hit the provider's rate
limit on every request. So a worker refreshes the cache periodically (Phase 2 wires this to
Redis + a cron/asyncio schedule); the skill reads cache-first and only falls back to a live
provider call on a miss.
"""

from __future__ import annotations

from typing import Protocol

from .provider import Fixture, FootballProvider
from .teams import Team


class FixtureCache(Protocol):
    def get(self, team_id: int) -> Fixture | None: ...
    def set(self, team_id: int, fixture: Fixture | None) -> None: ...


class InMemoryFixtureCache:
    """Phase 0/2 default. Swap for a Redis-backed cache in production."""

    def __init__(self) -> None:
        self._store: dict[int, Fixture | None] = {}

    def get(self, team_id: int) -> Fixture | None:
        return self._store.get(team_id)

    def set(self, team_id: int, fixture: Fixture | None) -> None:
        self._store[team_id] = fixture


class FixtureIngestionWorker:
    def __init__(
        self,
        provider: FootballProvider,
        cache: FixtureCache,
        followed: list[Team],
    ) -> None:
        self._provider = provider
        self._cache = cache
        self._followed = followed

    async def run_once(self) -> int:
        """Refresh the cache for every followed team. Returns how many were updated."""
        updated = 0
        for team in self._followed:
            try:
                fixture = await self._provider.next_fixture(team)
            except Exception:  # noqa: BLE001 - one bad team must not abort the sweep
                continue
            self._cache.set(team.id, fixture)
            updated += 1
        return updated
