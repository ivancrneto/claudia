"""Speech-to-text adapters. Real model behind a stub boundary; offline stubs for tests."""

from .base import STT
from .stub import EchoTextSTT, FixedSTT
from .whisper import FasterWhisperSTT

__all__ = ["STT", "EchoTextSTT", "FixedSTT", "FasterWhisperSTT"]
