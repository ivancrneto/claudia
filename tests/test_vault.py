"""Phase 3.5 tests — Account Vault encryption + resolution into a brain config."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.accounts.vault import Vault  # noqa: E402
from services.brain.router import select_brain  # noqa: E402


class ReverseCipher:
    """Deterministic reversible transform — enough to prove the vault stores ciphertext."""

    def encrypt(self, plaintext: str) -> str:
        return "enc:" + plaintext[::-1]

    def decrypt(self, token: str) -> str:
        return token[len("enc:"):][::-1]


def test_vault_encrypts_and_resolves():
    v = Vault(cipher=ReverseCipher())
    v.connect("u1", kind="openai", model="gpt-x", api_key="secret-key")
    stored = v._store["u1"].secret_ref
    assert stored is not None and "secret-key" not in stored  # not plaintext at rest
    brain = v.brain_for("u1")
    assert brain["api_key"] == "secret-key"
    assert brain["kind"] == "openai" and brain["model"] == "gpt-x"


def test_vault_no_key_stays_none():
    v = Vault(cipher=ReverseCipher())
    v.connect("u2", kind="anthropic", model="claude-x")
    assert v._store["u2"].secret_ref is None
    assert v.brain_for("u2")["api_key"] is None


def test_vault_unknown_user():
    assert Vault(cipher=ReverseCipher()).brain_for("nope") is None


def test_vault_feeds_router():
    v = Vault(cipher=ReverseCipher())
    v.connect("u", kind="anthropic", model="claude-x", api_key="k", base_url=None)
    provider = select_brain({"brain": v.brain_for("u")})
    assert provider.name == "anthropic"
    assert provider.config.api_key == "k"


def test_fernet_cipher_roundtrip_if_available():
    # Skips gracefully where `cryptography` can't load (sandbox rust-binding bug raises
    # pyo3 PanicException, which derives from BaseException, not Exception).
    try:
        from services.accounts.vault import FernetCipher

        cipher = FernetCipher()
    except BaseException:  # noqa: BLE001
        return
    assert cipher.decrypt(cipher.encrypt("secret")) == "secret"


if __name__ == "__main__":
    for fn in list(globals().values()):
        if callable(fn) and getattr(fn, "__name__", "").startswith("test_"):
            fn()
            print(f"ok  {fn.__name__}")
    print("all vault tests passed")
