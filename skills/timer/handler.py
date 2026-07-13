"""Timer skill — the actual countdown runs on-device (OS timer), voice just sets it."""

from __future__ import annotations

from pathlib import Path

from skills._sdk import Request, Response, Skill, load_manifest

_MANIFEST = load_manifest(Path(__file__).with_name("manifest.yaml"))


class TimerSkill(Skill):
    manifest = _MANIFEST

    def can_handle(self, request: Request) -> bool:
        return request.intent == "SET_TIMER"

    async def handle(self, request: Request) -> Response:
        spoken = request.slot("duracao", "alguns minutos")
        # Emit a device action; the client sets the native OS timer for reliability.
        return Response.speak(f"Ok, timer de {spoken}.").with_action(
            "set_os_timer", spoken_duration=spoken
        )
