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


# (intent, slot_extractors) keyed by simple keyword rules. Order matters.
_RULES = [
    ("PROXIMO_JOGO", re.compile(r"quando\s+(?:o\s+|e\s+o\s+proximo\s+jogo\s+do\s+)?(?P<time>.+?)\s+joga")),
    ("PROXIMO_JOGO", re.compile(r"quando\s+joga\s+(?:o\s+)?(?P<time>.+)")),
    ("SET_TIMER", re.compile(r"(?:poe|coloca|marca).*?timer\s+de\s+(?P<duracao>.+)")),
    ("GET_WEATHER", re.compile(r"(tempo|previsao|chover|temperatura)")),
]


def route(text: str) -> tuple[str, dict[str, str]]:
    """Return (intent, slots). Falls back to FALLBACK for the brain to handle."""
    norm = _norm(text)
    for intent, pattern in _RULES:
        m = pattern.search(norm)
        if m:
            return intent, {k: v.strip() for k, v in m.groupdict().items() if v}
    return "FALLBACK", {}
