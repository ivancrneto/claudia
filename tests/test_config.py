"""Tests for the central config: env parsing, prod fail-fast, and secret redaction."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from services.config import ConfigError, Settings  # noqa: E402


def test_defaults_are_dev_and_stubs():
    s = Settings.from_env({})
    assert s.env == "dev" and not s.is_prod
    assert s.stt_backend == "stub" and s.tts_backend == "stub"
    assert s.api_football_key is None and s.vault_key is None
    assert s.missing_required() == []  # dev requires nothing


def test_reads_values_from_env():
    s = Settings.from_env(
        {
            "CLAUDIA_ENV": "prod",
            "STT_BACKEND": "whisper",
            "TTS_BACKEND": "piper",
            "API_FOOTBALL_KEY": "k",
            "FOOTBALL_SEASON": "2027",
            "VAULT_KEY": "v",
            "GATEWAY_PORT": "9000",
        }
    )
    assert s.is_prod and s.stt_backend == "whisper" and s.tts_backend == "piper"
    assert s.football_season == 2027 and s.gateway_port == 9000
    assert s.api_football_key == "k" and s.vault_key == "v"


def test_prod_missing_required_secret_fails_fast():
    s = Settings.from_env({"CLAUDIA_ENV": "prod"})
    assert s.missing_required() == ["VAULT_KEY"]
    with pytest.raises(ConfigError):
        s.validate()


def test_prod_with_secret_validates():
    s = Settings.from_env({"CLAUDIA_ENV": "prod", "VAULT_KEY": "v"})
    assert s.missing_required() == []
    assert s.validate() is s


def test_repr_redacts_secret_values():
    s = Settings.from_env({"CLAUDIA_ENV": "prod", "VAULT_KEY": "super-secret", "API_FOOTBALL_KEY": "abc"})
    text = repr(s)
    assert "super-secret" not in text and "abc" not in text
    assert "VAULT_KEY': 'set'" in text and "API_FOOTBALL_KEY': 'set'" in text


if __name__ == "__main__":
    import traceback

    failures = 0
    for fn in list(globals().values()):
        if callable(fn) and getattr(fn, "__name__", "").startswith("test_"):
            try:
                fn()
                print(f"ok  {fn.__name__}")
            except Exception:
                failures += 1
                traceback.print_exc()
    print("all config tests passed" if not failures else f"{failures} failed")
