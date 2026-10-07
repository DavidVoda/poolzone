from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.schemas import PasswordSet, UserCreate, UserOut, UserPatch
from app.auth import hash_password, require_admin
from app.models import User

# require_admin on every route: admins only (dev/localhost stays open).
router = APIRouter(prefix="/api/users", tags=["users"], dependencies=[Depends(require_admin)])

_ROLES = {"admin", "member"}


def _active_admin_count(db: Session, exclude_id: int | None = None) -> int:
    stmt = select(func.count()).where(User.role == "admin", User.active.is_(True))
    if exclude_id is not None:
        stmt = stmt.where(User.id != exclude_id)
    return db.execute(stmt).scalar_one()


@router.get("", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db)):
    return list(db.execute(select(User).order_by(User.name)).scalars())


@router.post("", response_model=UserOut, status_code=201)
def create_user(body: UserCreate, db: Session = Depends(get_db)):
    if body.role not in _ROLES:
        raise HTTPException(422, f"role must be one of {sorted(_ROLES)}")
    if not body.password:
        raise HTTPException(422, "password required")
    exists = db.execute(select(User).where(User.email == body.email)).scalar_one_or_none()
    if exists:
        raise HTTPException(409, "email already in use")
    user = User(
        email=body.email,
        name=body.name,
        role=body.role,
        password_hash=hash_password(body.password),
    )
    db.add(user)
    db.flush()
    return user


@router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: int, body: UserPatch, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "user not found")
    if body.role is not None and body.role not in _ROLES:
        raise HTTPException(422, f"role must be one of {sorted(_ROLES)}")
    # Guard the last admin: don't let a demote/deactivate lock everyone out.
    demoting = body.role is not None and body.role != "admin" and user.role == "admin"
    deactivating = body.active is False and user.active and user.role == "admin"
    if (demoting or deactivating) and _active_admin_count(db, exclude_id=user.id) == 0:
        raise HTTPException(409, "cannot remove the last active admin")
    if body.name is not None:
        user.name = body.name
    if body.role is not None:
        user.role = body.role
    if body.active is not None:
        user.active = body.active
    db.flush()
    return user


@router.post("/{user_id}/password", status_code=204)
def set_password(user_id: int, body: PasswordSet, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "user not found")
    if not body.password:
        raise HTTPException(422, "password required")
    user.password_hash = hash_password(body.password)
    db.flush()


@router.delete("/{user_id}", status_code=204)
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "user not found")
    if user.role == "admin" and _active_admin_count(db, exclude_id=user.id) == 0:
        raise HTTPException(409, "cannot delete the last active admin")
    db.delete(user)
    db.flush()
