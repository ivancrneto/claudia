"""Core request/response types passed between the gateway, dispatcher and skills."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Request:
    """A resolved intent handed to a skill.

    `intent` and `slots` come from the NLU router; `text` is the raw transcript;
    `user` carries session/profile context (favorite team, locale, connected brain).
    """

    text: str
    intent: str = "FALLBACK"
    slots: dict[str, str] = field(default_factory=dict)
    user: dict[str, Any] = field(default_factory=dict)
    locale: str = "pt-BR"

    def slot(self, name: str, default: str = "") -> str:
        return self.slots.get(name, default)


@dataclass
class DeviceAction:
    """A native action the client executes locally (open YouTube, set OS timer, ...)."""

    type: str
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class Response:
    """What a skill returns: speech (for TTS) plus optional client-side device actions."""

    speech: str = ""
    actions: list[DeviceAction] = field(default_factory=list)
    end_session: bool = True

    @classmethod
    def speak(cls, text: str, end_session: bool = True) -> "Response":
        return cls(speech=text, end_session=end_session)

    def with_action(self, type: str, **params: Any) -> "Response":
        self.actions.append(DeviceAction(type=type, params=params))
        return self
