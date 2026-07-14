"""Profiles resolved by user id and merged into the request's user context.

Voice-match / spoken-PIN identification (Phase 4 follow-up) resolves the user id; here the
id is provided by the caller. Phase 4 swaps the in-memory store for Postgres.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class Profile:
    user_id: str
    locale: str = "pt-BR"
    favorite_team_id: int | None = None
    city: str | None = None
    latitude: float | None = None
    longitude: float | None = None

    def to_context(self) -> dict[str, Any]:
        """The subset merged into Request.user (skills read favorite_team_id, city, coords)."""
        ctx: dict[str, Any] = {"user_id": self.user_id, "locale": self.locale}
        if self.favorite_team_id is not None:
            ctx["favorite_team_id"] = self.favorite_team_id
        if self.city:
            ctx["city"] = self.city
        if self.latitude is not None and self.longitude is not None:
            ctx["latitude"] = self.latitude
            ctx["longitude"] = self.longitude
        return ctx


class ProfileStore(Protocol):
    def get(self, user_id: str) -> Profile | None: ...
    def save(self, profile: Profile) -> Profile: ...


class InMemoryProfileStore:
    def __init__(self) -> None:
        self._profiles: dict[str, Profile] = {}

    def get(self, user_id: str) -> Profile | None:
        return self._profiles.get(user_id)

    def save(self, profile: Profile) -> Profile:
        self._profiles[profile.user_id] = profile
        return profile

    def set_favorite_team(self, user_id: str, team_id: int) -> Profile:
        profile = self.get(user_id) or Profile(user_id=user_id)
        profile.favorite_team_id = team_id
        return self.save(profile)
