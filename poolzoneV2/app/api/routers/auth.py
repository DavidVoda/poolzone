from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.schemas import LoginIn, MeOut, UserOut
from app.auth import (
    get_current_user,
    login_session,
    logout_session,
    touch_last_active,
    verify_password,
)
from app.models import User
from app.settings import IS_PRODUCTION

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=UserOut)
def login(body: LoginIn, request: Request, db: Session = Depends(get_db)):
    user = db.execute(select(User).where(User.email == body.email)).scalar_one_or_none()
    # Same error whether the email is unknown or the password is wrong — don't leak
    # which accounts exist. verify_password still runs to keep timing roughly even.
    if user is None or not user.active or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")
    login_session(request, user)
    touch_last_active(db, user)
    return user


@router.post("/logout")
def logout(request: Request):
    logout_session(request)
    return {"ok": True}


@router.get("/me", response_model=MeOut)
def me(user: User | None = Depends(get_current_user)):
    return MeOut(auth_required=IS_PRODUCTION, user=user)
