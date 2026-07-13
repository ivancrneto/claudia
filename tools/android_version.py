"""Derive Android versionName / versionCode from a release git tag.

Used by the release CI so versions are reproducible from the tag, not hand-edited.
Scheme: tag `vMAJOR.MINOR.PATCH` → versionName "MAJOR.MINOR.PATCH",
versionCode = MAJOR*10000 + MINOR*100 + PATCH (each part 0..99).

    $ python tools/android_version.py v1.4.2
    VERSION_NAME=1.4.2
    VERSION_CODE=10402
"""

from __future__ import annotations

import sys


def parse_version(tag: str) -> tuple[str, int]:
    name = tag.strip()
    if name.startswith("v"):
        name = name[1:]
    parts = name.split(".")
    if len(parts) != 3:
        raise ValueError(f"expected vMAJOR.MINOR.PATCH, got {tag!r}")
    try:
        major, minor, patch = (int(p) for p in parts)
    except ValueError as exc:
        raise ValueError(f"non-numeric version part in {tag!r}") from exc
    for label, value in (("minor", minor), ("patch", patch)):
        if not 0 <= value <= 99:
            raise ValueError(f"{label} must be 0..99 in {tag!r}")
    if major < 0:
        raise ValueError(f"major must be >= 0 in {tag!r}")
    code = major * 10000 + minor * 100 + patch
    return f"{major}.{minor}.{patch}", code


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: android_version.py <tag>", file=sys.stderr)
        return 2
    name, code = parse_version(argv[1])
    print(f"VERSION_NAME={name}")
    print(f"VERSION_CODE={code}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
