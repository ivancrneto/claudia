"""Routes a resolved Request to the first skill that can handle it."""

from __future__ import annotations

import logging

from .models import Request, Response
from .skill import Skill

log = logging.getLogger("claudia.dispatcher")


class Dispatcher:
    def __init__(self, skills: list[Skill] | None = None) -> None:
        self._skills: list[Skill] = list(skills or [])

    def register(self, skill: Skill) -> None:
        self._skills.append(skill)
        log.info("registered skill: %s", skill.name)

    @property
    def skills(self) -> list[Skill]:
        return list(self._skills)

    async def dispatch(self, request: Request) -> Response:
        for skill in self._skills:
            if skill.can_handle(request):
                log.debug("dispatch %s -> %s", request.intent, skill.name)
                return await skill.handle(request)
        # No skill matched: caller falls back to the brain (LLM) for open Q&A.
        return Response.speak("", end_session=False)
