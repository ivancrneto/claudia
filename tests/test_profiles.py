"""Phase 4 tests — per-user profiles and context resolution."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.profiles import InMemoryProfileStore, Profile  # noqa: E402


def test_to_context_includes_set_fields_only():
    ctx = Profile("u", favorite_team_id=118, city="Salvador", latitude=-12.9, longitude=-38.5).to_context()
    assert ctx["favorite_team_id"] == 118 and ctx["city"] == "Salvador"
    assert ctx["latitude"] == -12.9 and ctx["longitude"] == -38.5

    bare = Profile("u").to_context()
    assert "favorite_team_id" not in bare and "city" not in bare and "latitude" not in bare
    assert bare["user_id"] == "u" and bare["locale"] == "pt-BR"


def test_store_save_get_and_set_favorite():
    store = InMemoryProfileStore()
    assert store.get("u") is None
    store.save(Profile("u", city="Salvador"))
    assert store.get("u").city == "Salvador"

    store.set_favorite_team("u", 118)
    assert store.get("u").favorite_team_id == 118
    # set_favorite_team creates a profile if none exists
    store.set_favorite_team("new", 127)
    assert store.get("new").favorite_team_id == 127


def test_resolve_context_merges_profile_then_request_overrides():
    from services.gateway.app import _resolve_context, profiles

    profiles.save(Profile("ivan", favorite_team_id=118, city="Salvador"))
    ctx = _resolve_context({"user_id": "ivan"})
    assert ctx["favorite_team_id"] == 118 and ctx["city"] == "Salvador"

    # request values win over the stored profile
    ctx2 = _resolve_context({"user_id": "ivan", "city": "Rio"})
    assert ctx2["city"] == "Rio"

    # unknown user → just the request context
    assert _resolve_context({"city": "X"}) == {"city": "X"}


if __name__ == "__main__":
    for fn in list(globals().values()):
        if callable(fn) and getattr(fn, "__name__", "").startswith("test_"):
            fn()
            print(f"ok  {fn.__name__}")
    print("all profile tests passed")
