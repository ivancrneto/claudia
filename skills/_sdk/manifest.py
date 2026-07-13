"""Skill manifest loading — intents, sample utterances and slot types (Alexa-style)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - yaml is a runtime dependency
    yaml = None


@dataclass
class Intent:
    name: str
    utterances: list[str] = field(default_factory=list)
    slots: dict[str, dict[str, Any]] = field(default_factory=dict)


@dataclass
class Manifest:
    name: str
    locale: str = "pt-BR"
    intents: list[Intent] = field(default_factory=list)

    @property
    def intent_names(self) -> set[str]:
        return {i.name for i in self.intents}


def load_manifest(path: str | Path) -> Manifest:
    if yaml is None:
        raise RuntimeError("PyYAML is required to load skill manifests")
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    intents = [
        Intent(
            name=i["name"],
            utterances=i.get("utterances", []),
            slots=i.get("slots", {}),
        )
        for i in data.get("intents", [])
    ]
    return Manifest(name=data["name"], locale=data.get("locale", "pt-BR"), intents=intents)
