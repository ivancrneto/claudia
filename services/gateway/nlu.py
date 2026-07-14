"""Phase 0 NLU — a tiny deterministic intent router over the skill manifests.

Enough to exercise the dispatcher from text. Phase 1 replaces this with the hybrid router
(fast intent grammar → local-LLM fallback) fed by streaming STT.
"""

from __future__ import annotations

import re
import unicodedata


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.lower().strip())
    return "".join(c for c in s if not unicodedata.combining(c))


# (intent, pattern). Order matters — more specific rules first. YouTube must beat the
# generic "toca {consulta}" music rule, and the timer rule (needs "timer de") is safe first.
_RULES = [
    ("PROXIMO_JOGO", re.compile(r"quando\s+(?:o\s+|e\s+o\s+proximo\s+jogo\s+do\s+)?(?P<time>.+?)\s+joga")),
    ("PROXIMO_JOGO", re.compile(r"quando\s+joga\s+(?:o\s+)?(?P<time>.+)")),
    ("SET_TIMER", re.compile(r"(?:poe|coloca|marca).*?timer\s+de\s+(?P<duracao>.+)")),
    # YouTube (before music)
    ("OPEN_YOUTUBE", re.compile(r"(?:toca|tocar|procura|coloca)\s+(?P<consulta>.+?)\s+no\s+youtube")),
    ("OPEN_YOUTUBE", re.compile(r"(?:abre|abrir)\s+(?:o\s+)?youtube")),
    ("OPEN_YOUTUBE", re.compile(r"youtube\s+(?P<consulta>.+)")),
    ("OPEN_YOUTUBE", re.compile(r"youtube")),
    ("GET_WEATHER", re.compile(r"(tempo|previsao|chover|temperatura)")),
    # Music (generic "toca …" last, so it doesn't swallow the more specific intents)
    ("PLAY_MUSIC", re.compile(r"coloca\s+(?P<consulta>.+?)\s+pra\s+tocar")),
    ("PLAY_MUSIC", re.compile(r"poe\s+uma\s+musica\s+do\s+(?P<consulta>.+)")),
    ("PLAY_MUSIC", re.compile(r"(?:toca|tocar)\s+(?P<consulta>.+)")),
]


def route(text: str) -> tuple[str, dict[str, str]]:
    """Return (intent, slots). Falls back to FALLBACK for the brain to handle."""
    norm = _norm(text)
    for intent, pattern in _RULES:
        m = pattern.search(norm)
        if m:
            return intent, {k: v.strip() for k, v in m.groupdict().items() if v}
    return "FALLBACK", {}
