"""Hybrid NLU — fast deterministic grammar first, optional LLM classifier for the gap.

The grammar (nlu.route) handles high-frequency commands instantly and deterministically.
On a grammar miss, an optional LLM intent classifier can still map the utterance to a skill
intent; if none is configured the miss stays FALLBACK and the brain answers it as open Q&A.
"""

from __future__ import annotations

from typing import Awaitable, Callable

from . import nlu

# text -> (intent, slots)
IntentClassifier = Callable[[str], Awaitable[tuple[str, dict[str, str]]]]


class HybridRouter:
    def __init__(self, llm_classifier: IntentClassifier | None = None) -> None:
        self._llm = llm_classifier

    async def route(self, text: str) -> tuple[str, dict[str, str]]:
        intent, slots = nlu.route(text)
        if intent != "FALLBACK":
            return intent, slots
        if self._llm is not None:
            return await self._llm(text)
        return "FALLBACK", {}
