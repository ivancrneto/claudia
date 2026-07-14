"""Tests for the release version deriver."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from tools.android_version import parse_version  # noqa: E402


def test_parses_tag_with_v_prefix():
    assert parse_version("v1.4.2") == ("1.4.2", 10402)


def test_parses_tag_without_prefix():
    assert parse_version("0.1.0") == ("0.1.0", 100)


def test_version_code_is_monotonic_across_bumps():
    assert parse_version("v1.0.0")[1] < parse_version("v1.0.1")[1]
    assert parse_version("v1.0.99")[1] < parse_version("v1.1.0")[1]
    assert parse_version("v1.99.99")[1] < parse_version("v2.0.0")[1]


@pytest.mark.parametrize("bad", ["v1.2", "v1.2.3.4", "vx.y.z", "", "1.2.a"])
def test_rejects_malformed_tags(bad):
    with pytest.raises(ValueError):
        parse_version(bad)


def test_rejects_out_of_range_parts():
    with pytest.raises(ValueError):
        parse_version("v1.100.0")
    with pytest.raises(ValueError):
        parse_version("v1.0.100")


if __name__ == "__main__":
    import traceback

    failures = 0
    for _name, fn in list(globals().items()):
        if callable(fn) and _name.startswith("test_") and not hasattr(fn, "pytestmark"):
            try:
                fn()
                print(f"ok  {_name}")
            except Exception:
                failures += 1
                traceback.print_exc()
    print("done" if not failures else f"{failures} failed")
