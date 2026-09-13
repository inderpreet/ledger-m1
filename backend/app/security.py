"""Password hashing, sessions, and login rate limiting."""

from __future__ import annotations

import hashlib
import os
import secrets
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from threading import Lock

import bcrypt
from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AuthSession, AuthUser

COOKIE_NAME = "ledger_session"
SESSION_DAYS = 14
LOGIN_WINDOW = timedelta(minutes=15)
LOGIN_MAX_ATTEMPTS = 8
_DUMMY_HASH = bcrypt.hashpw(b"ledger-dummy-password", bcrypt.gensalt()).decode()

_login_attempts: dict[str, list[datetime]] = defaultdict(list)
_login_lock = Lock()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def generate_password() -> str:
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso_now() -> str:
    return _utcnow().replace(microsecond=0).isoformat()


def iso_expiry() -> str:
    return (_utcnow() + timedelta(days=SESSION_DAYS)).replace(microsecond=0).isoformat()


def secure_cookies() -> bool:
    return os.environ.get("LEDGER_SECURE_COOKIES", "").strip() in {"1", "true", "yes"}


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def check_login_rate(ip: str) -> None:
    now = _utcnow()
    with _login_lock:
        recent = [t for t in _login_attempts[ip] if now - t < LOGIN_WINDOW]
        _login_attempts[ip] = recent
        if len(recent) >= LOGIN_MAX_ATTEMPTS:
            raise HTTPException(status_code=429, detail="Too many login attempts. Try again later.")
        recent.append(now)
        _login_attempts[ip] = recent


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=secure_cookies(),
        max_age=SESSION_DAYS * 24 * 60 * 60,
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/")


def create_session(db: Session, user: AuthUser) -> str:
    token = secrets.token_urlsafe(32)
    db.add(
        AuthSession(
            user_id=user.id,
            token_hash=hash_session_token(token),
            expires_at=iso_expiry(),
        )
    )
    db.commit()
    return token


def revoke_session(db: Session, token: str | None) -> None:
    if not token:
        return
    row = db.query(AuthSession).filter(AuthSession.token_hash == hash_session_token(token)).first()
    if row:
        db.delete(row)
        db.commit()


def revoke_user_sessions(db: Session, user_id: int) -> None:
    db.query(AuthSession).filter(AuthSession.user_id == user_id).delete(synchronize_session=False)
    db.commit()


def authenticate(db: Session, username: str, password: str) -> AuthUser | None:
    user = db.query(AuthUser).filter(AuthUser.username == username).first()
    password_hash = user.password_hash if user else _DUMMY_HASH
    if not verify_password(password, password_hash) or user is None:
        return None
    return user


def user_configured(db: Session) -> bool:
    return db.query(AuthUser).first() is not None


def current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> AuthUser:
    if not user_configured(db):
        raise HTTPException(
            status_code=503,
            detail="Authentication is not configured. Run ./set-password.sh on the server.",
        )
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Not signed in")
    row = db.query(AuthSession).filter(AuthSession.token_hash == hash_session_token(token)).first()
    if row is None or row.expires_at < iso_now():
        if row is not None:
            db.delete(row)
            db.commit()
        raise HTTPException(status_code=401, detail="Not signed in")
    user = db.get(AuthUser, row.user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Not signed in")
    return user
