"""Brain router — pick which brain answers, and fall back to local when none is connected.

Direct commands are handled by skills (never reach here). This decides, for open Q&A, whether
to use the user's connected provider or the local default brain.
"""

from __future__ import annotations

from typing import Any

from .providers import LLMProvider, LocalAdapter, OpenAICompatAdapter
from .providers.base import ProviderConfig


def select_brain(user: dict[str, Any]) -> LLMProvider:
    """Return the LLMProvider for this user.

    `user["brain"]` is resolved from the Account Vault (never contains a raw key on the
    device — the gateway injects it server-side). With nothing connected, use local.
    """
    brain = user.get("brain")
    if not brain:
        return LocalAdapter()

    kind = brain.get("kind", "openai_compat")
    if kind == "openai_compat":
        return OpenAICompatAdapter(
            ProviderConfig(
                model=brain["model"],
                base_url=brain.get("base_url"),
                api_key=brain.get("api_key"),
            )
        )
    # Phase 3.5: "anthropic" | "openai" | "gemini" native adapters.
    return LocalAdapter()
