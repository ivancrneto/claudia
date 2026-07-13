"""Wake-word detection — runs on-device so audio isn't streamed 24/7.

`OpenWakeWord` is the real self-hosted detector (custom "Ei Claudia" model); the inference
call is a deployment TODO behind a lazy-load boundary. `KeywordWakeWord` is an offline
detector (matches a phrase in decoded text) so the session state machine is testable.
"""

from __future__ import annotations

import unicodedata
from typing import Protocol, runtime_checkable


@runtime_checkable
class WakeWord(Protocol):
    def detect(self, audio: bytes) -> bool:
        """Return True if the wake word is present in this audio frame."""
        ...


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.lower())
    return "".join(c for c in s if not unicodedata.combining(c)).strip()


class KeywordWakeWord:
    """Offline/dev detector: treats the frame as UTF-8 text and matches a phrase."""

    def __init__(self, phrase: str = "ei claudia") -> None:
        self._phrase = _norm(phrase)

    def detect(self, audio: bytes) -> bool:
        return self._phrase in _norm(audio.decode("utf-8", errors="ignore"))


class OpenWakeWord:
    name = "openwakeword"

    def __init__(self, model_path: str = "ei_claudia.onnx", threshold: float = 0.5) -> None:
        self.model_path = model_path
        self.threshold = threshold
        self._model = None

    def _load(self):
        if self._model is None:
            from openwakeword.model import Model  # local import — optional dep

            self._model = Model(wakeword_models=[self.model_path])
        return self._model

    def detect(self, audio: bytes) -> bool:
        # TODO(phase-3): feed PCM frames to the model, compare score >= threshold.
        raise NotImplementedError("Wire openWakeWord inference in Phase 3 deployment")
