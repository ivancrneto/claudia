"""BR_FOOTBALL_TEAM slot type — resolve names and nicknames to a canonical team.

The hard part of the futebol skill: "Bahia", "Esquadrão" and "Tricolor de Aço" must all
map to EC Bahia, while ambiguous nicknames ("Tricolor") need disambiguation. This is a
curated seed; Phase 2 expands it to all Série A/B clubs and adds fuzzy matching.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Team:
    id: int
    name: str
    aliases: tuple[str, ...] = field(default_factory=tuple)


# Seed roster (Série A subset). id values align with API-Football team ids.
TEAMS: list[Team] = [
    Team(118, "Bahia", ("esquadrao", "esquadrao de aco", "tricolor de aco")),
    Team(136, "Vitória", ("leao da barra", "rubro negro baiano")),
    Team(127, "Flamengo", ("mengao", "rubro negro")),
    Team(124, "Fortaleza", ("leao do pici")),
    Team(126, "São Paulo", ("tricolor paulista", "soberano")),
    Team(121, "Palmeiras", ("verdao", "porco")),
    Team(131, "Corinthians", ("timao")),
    Team(120, "Botafogo", ("fogao", "glorioso")),
]

# Nicknames that map to more than one club → require a follow-up / favorite team.
AMBIGUOUS = {"tricolor": (118, 126)}  # Bahia vs São Paulo


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.lower().strip())
    return "".join(c for c in s if not unicodedata.combining(c))


_INDEX: dict[str, Team] = {}
for _t in TEAMS:
    _INDEX[_norm(_t.name)] = _t
    for _a in _t.aliases:
        _INDEX[_norm(_a)] = _t


class Ambiguous(Exception):
    def __init__(self, candidates: tuple[int, ...]) -> None:
        self.candidates = candidates
        super().__init__(f"ambiguous team: {candidates}")


def resolve_team(spoken: str, favorite_id: int | None = None) -> Team:
    """Resolve a spoken team name to a Team.

    Raises KeyError if unknown, or Ambiguous if the nickname maps to several clubs
    (unless the user's favorite team disambiguates it).
    """
    key = _norm(spoken)
    if key in _INDEX:
        return _INDEX[key]
    if key in AMBIGUOUS:
        candidates = AMBIGUOUS[key]
        if favorite_id in candidates:
            return next(t for t in TEAMS if t.id == favorite_id)
        raise Ambiguous(candidates)
    raise KeyError(spoken)
