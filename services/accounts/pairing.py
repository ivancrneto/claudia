"""Kiosk-safe device pairing — the tablet never handles raw API keys.

The companion web/phone portal signs in, adds the provider key (or does OAuth), and shows a
QR / short code. The tablet scans it; the server links device_id -> user_id. Phase 3.5 makes
codes single-use and short-lived with signed tokens.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PairingCode:
    code: str
    user_id: str


class PairingService:
    def __init__(self) -> None:
        self._pending: dict[str, str] = {}  # code -> user_id
        self._devices: dict[str, str] = {}  # device_id -> user_id

    def issue(self, code: str, user_id: str) -> PairingCode:
        self._pending[code] = user_id
        return PairingCode(code=code, user_id=user_id)

    def redeem(self, device_id: str, code: str) -> bool:
        user_id = self._pending.pop(code, None)
        if user_id is None:
            return False
        self._devices[device_id] = user_id
        return True

    def user_for_device(self, device_id: str) -> str | None:
        return self._devices.get(device_id)
