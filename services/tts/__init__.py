"""Text-to-speech adapters. Real Piper behind a stub boundary; offline stub for tests."""

from .base import TTS
from .piper import PiperTTS
from .stub import StubTTS

__all__ = ["TTS", "PiperTTS", "StubTTS"]
