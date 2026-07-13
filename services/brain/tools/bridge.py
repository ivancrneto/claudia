"""Turn registered skills into tool schemas the connected brain can call.

Defined once here, then each provider adapter translates to its own format (Anthropic tool
use / MCP, OpenAI function calling, Gemini function declarations). Modeling the registry as
an MCP server (Phase 3.5) means new skills need no per-provider work.
"""

from __future__ import annotations

from typing import Any


def skills_to_tools(skills: list[Any]) -> list[dict[str, Any]]:
    """Build neutral JSON-schema tool definitions from skill manifests."""
    tools: list[dict[str, Any]] = []
    for skill in skills:
        for intent in skill.manifest.intents:
            properties = {
                slot: {"type": "string", "description": meta.get("type", "string")}
                for slot, meta in intent.slots.items()
            }
            tools.append(
                {
                    "name": f"{skill.name}.{intent.name}",
                    "description": (intent.utterances[0] if intent.utterances else intent.name),
                    "input_schema": {
                        "type": "object",
                        "properties": properties,
                        "required": list(properties),
                    },
                }
            )
    return tools
