"""Anonymous device identity — per-browser, no login.

Each browser gets a random device id in a signed cookie. The signature (HMAC
with a server secret) stops anyone forging another device's id to read its
alerts/positions. No passwords, no email, no account table — the cookie *is* the
identity. Upgrades cleanly to real accounts later (map device -> user on login).

This is the trust boundary for all per-device data, so the signature check is
not optional: an unsigned or tampered cookie is treated as a brand-new device.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

_COOKIE = "algosign_device"
_MAX_AGE = 60 * 60 * 24 * 365  # 1 year
# Persist a secret so cookies survive restarts. Env in prod; dev file fallback.
_SECRET = os.environ.get("DEVICE_SECRET")
if not _SECRET:
    from pathlib import Path
    _f = Path(__file__).resolve().parents[2] / "data" / ".device_secret"
    if _f.exists():
        _SECRET = _f.read_text().strip()
    else:
        _SECRET = secrets.token_hex(32)
        _f.parent.mkdir(parents=True, exist_ok=True)
        _f.write_text(_SECRET)
_SECRET_B = _SECRET.encode()


def _sign(device_id: str) -> str:
    sig = hmac.new(_SECRET_B, device_id.encode(), hashlib.sha256).hexdigest()[:32]
    return f"{device_id}.{sig}"


def _verify(token: str | None) -> str | None:
    """Return the device id if the cookie is intact, else None."""
    if not token or "." not in token:
        return None
    device_id, _, sig = token.rpartition(".")
    if not device_id:
        return None
    expected = hmac.new(_SECRET_B, device_id.encode(), hashlib.sha256).hexdigest()[:32]
    return device_id if hmac.compare_digest(sig, expected) else None


class DeviceMiddleware(BaseHTTPMiddleware):
    """Resolve (or mint) a device id, expose it on request.state.device, and set
    the signed cookie on the way out when it's new."""

    async def dispatch(self, request: Request, call_next):
        device_id = _verify(request.cookies.get(_COOKIE))
        is_new = device_id is None
        if is_new:
            device_id = secrets.token_urlsafe(16)
        request.state.device = device_id

        response = await call_next(request)
        if is_new:
            response.set_cookie(
                _COOKIE, _sign(device_id),
                max_age=_MAX_AGE, httponly=True, samesite="lax",
            )
        return response


def get_device(request: Request) -> str:
    """FastAPI dependency: the caller's device id (always present)."""
    return getattr(request.state, "device", None) or "anonymous"
