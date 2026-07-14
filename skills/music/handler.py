"""Music skill — emits a play_music device action; the client hands off to the music app."""

from __future__ import annotations

from pathlib import Path

from skills._sdk import Request, Response, Skill, load_manifest

_MANIFEST = load_manifest(Path(__file__).with_name("manifest.yaml"))


class MusicSkill(Skill):
    manifest = _MANIFEST

    def can_handle(self, request: Request) -> bool:
        return request.intent == "PLAY_MUSIC"

    async def handle(self, request: Request) -> Response:
        query = request.slot("consulta").strip()
        if not query:
            return Response.speak("O que você quer ouvir?", end_session=False)
        return Response.speak(f"Tocando {query}.").with_action("play_music", query=query)
