"""YouTube skill — emits an open_youtube device action; the client deep-links natively."""

from __future__ import annotations

from pathlib import Path

from skills._sdk import Request, Response, Skill, load_manifest

_MANIFEST = load_manifest(Path(__file__).with_name("manifest.yaml"))


class YouTubeSkill(Skill):
    manifest = _MANIFEST

    def can_handle(self, request: Request) -> bool:
        return request.intent == "OPEN_YOUTUBE"

    async def handle(self, request: Request) -> Response:
        query = request.slot("consulta").strip()
        if query:
            return Response.speak(f"Procurando {query} no YouTube.").with_action(
                "open_youtube", query=query
            )
        return Response.speak("Abrindo o YouTube.").with_action("open_youtube", query="")
