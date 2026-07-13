"""Central config — 12-factor. Everything comes from the environment; nothing sensitive
lives in this (public) repo.

Secrets are injected at runtime from an external secret manager (see docs/DEPLOYMENT.md):
Docker/K8s secrets, a cloud secret manager, or an env file mounted outside the repo. In
production the app fails fast if a required secret is missing, and never logs secret values.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

# Env vars that hold secrets — redacted in logs and required in production.
SECRET_KEYS = ("VAULT_KEY", "API_FOOTBALL_KEY")
# Subset that MUST be present in production (others are optional features).
REQUIRED_IN_PROD = ("VAULT_KEY",)


class ConfigError(RuntimeError):
    pass


@dataclass
class Settings:
    env: str = "dev"
    stt_backend: str = "stub"        # "stub" | "whisper"
    tts_backend: str = "stub"        # "stub" | "piper"
    api_football_key: str | None = None
    football_season: int = 2026
    vault_key: str | None = None     # Fernet key from the secret manager
    gateway_host: str = "0.0.0.0"
    gateway_port: int = 8000
    _present_secrets: set[str] = field(default_factory=set, repr=False)

    @property
    def is_prod(self) -> bool:
        return self.env == "prod"

    @classmethod
    def from_env(cls, environ: dict[str, str] | None = None) -> "Settings":
        e = environ if environ is not None else os.environ
        present = {k for k in SECRET_KEYS if e.get(k)}
        return cls(
            env=e.get("CLAUDIA_ENV", "dev").lower(),
            stt_backend=e.get("STT_BACKEND", "stub").lower() or "stub",
            tts_backend=e.get("TTS_BACKEND", "stub").lower() or "stub",
            api_football_key=e.get("API_FOOTBALL_KEY") or None,
            football_season=int(e.get("FOOTBALL_SEASON", "2026")),
            vault_key=e.get("VAULT_KEY") or None,
            gateway_host=e.get("GATEWAY_HOST", "0.0.0.0"),
            gateway_port=int(e.get("GATEWAY_PORT", "8000")),
            _present_secrets=present,
        )

    def missing_required(self) -> list[str]:
        """Required-in-prod secrets that are absent (empty in dev)."""
        if not self.is_prod:
            return []
        return [k for k in REQUIRED_IN_PROD if k not in self._present_secrets]

    def validate(self) -> "Settings":
        missing = self.missing_required()
        if missing:
            raise ConfigError(
                "Missing required secrets in production: "
                + ", ".join(missing)
                + " (inject them from your secret manager — see docs/DEPLOYMENT.md)"
            )
        return self

    def __repr__(self) -> str:  # never leak secret values in logs
        secrets = {k: ("set" if k in self._present_secrets else "unset") for k in SECRET_KEYS}
        return (
            f"Settings(env={self.env!r}, stt_backend={self.stt_backend!r}, "
            f"tts_backend={self.tts_backend!r}, football_season={self.football_season}, "
            f"gateway={self.gateway_host}:{self.gateway_port}, secrets={secrets})"
        )
