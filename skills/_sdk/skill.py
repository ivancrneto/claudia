"""Base class every skill implements."""

from __future__ import annotations

from abc import ABC, abstractmethod

from .manifest import Manifest
from .models import Request, Response


class Skill(ABC):
    """A pluggable capability. Subclasses declare a manifest and handle matching intents."""

    manifest: Manifest

    @abstractmethod
    def can_handle(self, request: Request) -> bool:
        """Return True if this skill should handle the request's intent."""

    @abstractmethod
    async def handle(self, request: Request) -> Response:
        """Produce a Response (speech + optional device actions)."""

    @property
    def name(self) -> str:
        return self.manifest.name
