"""Account Vault — per-user provider credentials, encrypted at rest (KMS-backed).

Phase 3.5 replaces the in-memory store with Postgres + a KMS envelope-encryption scheme.
Keys are never synced to the device; the gateway injects them server-side at request time.
Never log a decrypted credential.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class Connection:
    user_id: str
    kind: str  # "openai_compat" | "anthropic" | "openai" | "gemini"
    model: str
    base_url: str | None = None
    # In production this is an opaque handle to a KMS-encrypted secret, not a raw key.
    secret_ref: str | None = None


class Vault:
    def __init__(self) -> None:
        self._store: dict[str, Connection] = {}

    def connect(self, conn: Connection) -> None:
        self._store[conn.user_id] = conn

    def brain_for(self, user_id: str) -> dict[str, Any] | None:
        conn = self._store.get(user_id)
        if not conn:
            return None
        return {
            "kind": conn.kind,
            "model": conn.model,
            "base_url": conn.base_url,
            # TODO(phase-3.5): resolve+decrypt secret_ref via KMS here, server-side only.
            "api_key": None,
        }
