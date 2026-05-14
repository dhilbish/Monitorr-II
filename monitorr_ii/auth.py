from __future__ import annotations

import os
import secrets
from typing import Optional

import bcrypt
from fastapi import HTTPException, Request, status
from itsdangerous import BadSignature, URLSafeTimedSerializer

COOKIE_NAME = "monitorr_session"
COOKIE_MAX_AGE = 30 * 24 * 60 * 60  # 30 days

_password_hash: Optional[bytes] = None
_serializer: URLSafeTimedSerializer
_open_mode = False


def _truncate(pw: str) -> bytes:
    # bcrypt is defined for inputs up to 72 bytes; truncate longer passwords rather than rejecting.
    return pw.encode("utf-8")[:72]


def init() -> None:
    global _password_hash, _serializer, _open_mode
    pw = os.environ.get("MONITORR_PASSWORD", "").strip()
    secret = os.environ.get("MONITORR_SESSION_SECRET", "").strip()
    if not secret:
        secret = secrets.token_urlsafe(32)
    _serializer = URLSafeTimedSerializer(secret, salt="monitorr-ii")
    if not pw:
        _open_mode = True
        _password_hash = None
    else:
        _open_mode = False
        _password_hash = bcrypt.hashpw(_truncate(pw), bcrypt.gensalt())


def is_open() -> bool:
    return _open_mode


def verify_password(pw: str) -> bool:
    if _open_mode:
        return True
    if not _password_hash:
        return False
    try:
        return bcrypt.checkpw(_truncate(pw), _password_hash)
    except ValueError:
        return False


def make_cookie() -> str:
    return _serializer.dumps({"v": 1})


def validate_cookie(value: str | None) -> bool:
    if _open_mode:
        return True
    if not value:
        return False
    try:
        _serializer.loads(value, max_age=COOKIE_MAX_AGE)
        return True
    except (BadSignature, Exception):
        return False


def require(request: Request) -> None:
    if _open_mode:
        return
    cookie = request.cookies.get(COOKIE_NAME)
    if not validate_cookie(cookie):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="login required")
