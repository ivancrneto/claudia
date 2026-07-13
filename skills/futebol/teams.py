"""BR_FOOTBALL_TEAM slot type — resolve names and nicknames to a canonical team.

The hard part of the futebol skill: "Bahia", "Esquadrão" and "Tricolor de Aço" must all
map to EC Bahia, while ambiguous nicknames ("Tricolor", "Galo") need disambiguation.

`id` is Claudia's *internal* canonical id (stable, ours). External provider ids are NOT
hardcoded here — the FootballProvider resolves them by name at ingestion and caches the
mapping (see provider.py), so we never ship a stale third-party id.
"""

from __future__ import annotations

import difflib
import unicodedata
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Team:
    id: int
    name: str
    aliases: tuple[str, ...] = field(default_factory=tuple)


# Série A roster (2024/2025). Nicknames are the ones people actually say to a voice
# assistant. Expand freely — the resolver and fuzzy matcher pick them up automatically.
TEAMS: list[Team] = [
    Team(118, "Bahia", ("esquadrao", "esquadrao de aco", "tricolor de aco", "bahea")),
    Team(136, "Vitória", ("leao da barra", "rubro negro baiano")),
    Team(127, "Flamengo", ("mengao", "mengo", "rubro negro carioca", "fla")),
    Team(124, "Fluminense", ("flu", "tricolor carioca", "tricolor das laranjeiras")),
    Team(120, "Botafogo", ("fogao", "glorioso", "estrela solitaria")),
    Team(133, "Vasco", ("vasco da gama", "gigante da colina", "cruzmaltino")),
    Team(126, "São Paulo", ("tricolor paulista", "soberano", "spfc")),
    Team(121, "Palmeiras", ("verdao", "porco", "alviverde", "palestra")),
    Team(131, "Corinthians", ("timao", "coringao")),
    Team(119, "Santos", ("peixe", "alvinegro praiano")),
    Team(128, "Cruzeiro", ("raposa", "cabuloso")),
    Team(135, "Atlético Mineiro", ("galo", "atletico mg", "atletico galo")),
    Team(129, "Grêmio", ("tricolor gaucho", "imortal")),
    Team(130, "Internacional", ("inter", "colorado", "clube do povo")),
    Team(134, "Fortaleza", ("leao do pici", "tricolor do pici")),
    Team(154, "Ceará", ("vozao", "alvinegro de porangabussu")),
    Team(1062, "Atlético Goianiense", ("dragao", "atletico go")),
    Team(794, "Bragantino", ("massa bruta", "red bull bragantino", "braga")),
    Team(140, "Juventude", ("ju", "papo", "verdao da serra")),
    Team(144, "Mirassol", ("amarelao",)),
]

# Nicknames that map to more than one club → require a follow-up or the user's favorite team.
AMBIGUOUS: dict[str, tuple[int, ...]] = {
    "tricolor": (118, 126, 129, 124),  # Bahia / São Paulo / Grêmio / Fluminense
    "leao": (134, 144, 136),           # Fortaleza / Mirassol / Vitória
    "alvinegro": (119, 154),           # Santos / Ceará
}

_FUZZY_CUTOFF = 0.82


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.lower().strip())
    s = "".join(c for c in s if not unicodedata.combining(c))
    # Drop common filler so "o sao paulo" == "sao paulo".
    for filler in ("o ", "a ", "do ", "da ", "time do ", "time da "):
        if s.startswith(filler):
            s = s[len(filler):]
    return s.strip()


_INDEX: dict[str, Team] = {}
for _t in TEAMS:
    _INDEX[_norm(_t.name)] = _t
    for _a in _t.aliases:
        _INDEX[_norm(_a)] = _t


class Ambiguous(Exception):
    def __init__(self, candidates: tuple[int, ...]) -> None:
        self.candidates = candidates
        super().__init__(f"ambiguous team: {candidates}")


def team_by_id(team_id: int) -> Team:
    return next(t for t in TEAMS if t.id == team_id)


def names_for(ids: tuple[int, ...]) -> list[str]:
    return [team_by_id(i).name for i in ids]


def resolve_team(spoken: str, favorite_id: int | None = None) -> Team:
    """Resolve a spoken team name to a Team.

    Order: exact/alias → ambiguous (favorite disambiguates) → fuzzy (typos/ASR errors).
    Raises KeyError if unknown, or Ambiguous if a nickname maps to several clubs.
    """
    key = _norm(spoken)
    if not key:
        raise KeyError(spoken)

    if key in _INDEX:
        return _INDEX[key]

    if key in AMBIGUOUS:
        candidates = AMBIGUOUS[key]
        if favorite_id in candidates:
            return team_by_id(favorite_id)
        raise Ambiguous(candidates)

    # Fuzzy fallback for misspellings / speech-to-text noise ("flamengu", "sao paolo").
    match = difflib.get_close_matches(key, _INDEX.keys(), n=1, cutoff=_FUZZY_CUTOFF)
    if match:
        return _INDEX[match[0]]

    raise KeyError(spoken)
