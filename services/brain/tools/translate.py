"""Translate neutral tool schemas into each provider's tool-calling format.

The neutral shape (from bridge.skills_to_tools) is Anthropic-native:
    {"name", "description", "input_schema": {...}}
so Anthropic passes through; OpenAI and Gemini get their respective wrappers.
"""

from __future__ import annotations

from typing import Any


def translate_tools(tools: list[dict[str, Any]], provider: str) -> list[dict[str, Any]]:
    if not tools:
        return []
    if provider == "anthropic":
        return tools  # neutral shape is already Anthropic's
    if provider == "openai":
        return [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "parameters": t.get("input_schema", {}),
                },
            }
            for t in tools
        ]
    if provider == "gemini":
        return [
            {
                "function_declarations": [
                    {
                        "name": t["name"],
                        "description": t.get("description", ""),
                        "parameters": t.get("input_schema", {}),
                    }
                    for t in tools
                ]
            }
        ]
    raise ValueError(f"unknown provider: {provider}")
