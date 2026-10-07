"""Password hashing + session-based auth dependencies.

bcrypt directly (passlib is unmaintained and breaks with bcrypt 5). bcrypt caps
input at 72 bytes, so we sha256+base64 the password first — that also means any
length works. Sessions are Starlette signed cookies (see SessionMiddleware in
app.api.main); we only stash the user id.
"""

from __future__ import annotations

import base64
import hashlib
from datetime import datetime, timezone

import bcrypt
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models import User
from app.settings import IS_PRODUCTION


def _pre(password: str) -> bytes:
    # 44-byte digest keeps us under bcrypt's 72-byte limit for any password length.
    return base64.b64encode(hashlib.sha256(password.encode("utf-8")).digest())


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_pre(password), bcrypt.gensalt()).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(_pre(password), password_hash.encode("ascii"))
    except (ValueError, TypeError):
        return False


def login_session(request: Request, user: User) -> None:
    request.session["user_id"] = user.id


def logout_session(request: Request) -> None:
    request.session.clear()


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    """The logged-in user, or None. Never raises — that's the guards' job."""
    uid = request.session.get("user_id")
    if not uid:
        return None
    user = db.get(User, uid)
    return user if user and user.active else None


def require_user(user: User | None = Depends(get_current_user)) -> User | None:
    """Gate for app routes: 401 in production when anonymous; open in dev."""
    if user is None and IS_PRODUCTION:
        raise HTTPException(401, "Authentication required")
    return user


def require_admin(user: User | None = Depends(get_current_user)) -> User | None:
    """Gate for user-management: admins only. Dev stays open (localhost)."""
    if user is None:
        if IS_PRODUCTION:
            raise HTTPException(401, "Authentication required")
        return None  # dev: localhost open
    if user.role != "admin":
        raise HTTPException(403, "Admin role required")
    return user


def touch_last_active(db: Session, user: User) -> None:
    user.last_active_at = datetime.now(timezone.utc)
    db.flush()
