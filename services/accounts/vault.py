"""Account Vault — per-user provider credentials, encrypted at rest.

Keys are never synced to the device; the gateway injects them server-side at request time
and never logs a decrypted credential. The cipher is pluggable: production uses
`FernetCipher` (symmetric key from a KMS/env secret); tests inject their own so the vault
logic is verifiable without the crypto dependency. Phase 4 swaps the in-memory store for
Postgres with KMS envelope encryption.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class Cipher(Protocol):
    def encrypt(self, plaintext: str) -> str: ...
    def decrypt(self, token: str) -> str: ...


class FernetCipher:
    """Production cipher. `cryptography` is imported lazily so module load never fails."""

    def __init__(self, key: str | bytes | None = None) -> None:
        from cryptography.fernet import Fernet  # lazy: optional heavy dep

        self._fernet = Fernet(key or Fernet.generate_key())

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode("utf-8")).decode("ascii")

    def decrypt(self, token: str) -> str:
        return self._fernet.decrypt(token.encode("ascii")).decode("utf-8")


@dataclass
class Connection:
    user_id: str
    kind: str  # "openai_compat" | "anthropic" | "openai" | "gemini"
    model: str
    base_url: str | None = None
    secret_ref: str | None = None  # encrypted api key, never plaintext


class Vault:
    def __init__(self, cipher: Cipher | None = None) -> None:
        self._cipher = cipher
        self._store: dict[str, Connection] = {}

    def _cipher_or_default(self) -> Cipher:
        if self._cipher is None:
            self._cipher = FernetCipher()  # prod default; requires `cryptography`
        return self._cipher

    def connect(
        self,
        user_id: str,
        kind: str,
        model: str,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        secret_ref = self._cipher_or_default().encrypt(api_key) if api_key else None
        self._store[user_id] = Connection(
            user_id=user_id,
            kind=kind,
            model=model,
            base_url=base_url,
            secret_ref=secret_ref,
        )

    def brain_for(self, user_id: str) -> dict[str, Any] | None:
        """Return the resolved brain config (with decrypted key) for the gateway to use."""
        conn = self._store.get(user_id)
        if not conn:
            return None
        api_key = (
            self._cipher_or_default().decrypt(conn.secret_ref) if conn.secret_ref else None
        )
        return {
            "kind": conn.kind,
            "model": conn.model,
            "base_url": conn.base_url,
            "api_key": api_key,
        }
