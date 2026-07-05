from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent import runner
from app.api.deps import get_db
from app.api.schemas import (
    FeatureRequestCreate,
    FeatureRequestOut,
    FeatureRequestPatch,
    ReviewNote,
)
from app.models import FeatureRequest

router = APIRouter(prefix="/api/feature-requests", tags=["feature-requests"])


def _get(db: Session, req_id: int) -> FeatureRequest:
    req = db.get(FeatureRequest, req_id)
    if req is None:
        raise HTTPException(404, "feature request not found")
    return req


def _require(req: FeatureRequest, *allowed: str) -> None:
    if req.status not in allowed:
        raise HTTPException(409, f"action not allowed in status '{req.status}'")


@router.get("", response_model=list[FeatureRequestOut])
def list_requests(db: Session = Depends(get_db), status: str | None = None):
    stmt = select(FeatureRequest).order_by(FeatureRequest.updated_at.desc())
    if status:
        stmt = stmt.where(FeatureRequest.status == status)
    return list(db.execute(stmt).scalars())


@router.post("", response_model=FeatureRequestOut, status_code=201)
def create_request(body: FeatureRequestCreate, db: Session = Depends(get_db)):
    req = FeatureRequest(**body.model_dump())
    db.add(req)
    db.flush()
    return req


@router.get("/{req_id}", response_model=FeatureRequestOut)
def get_request(req_id: int, db: Session = Depends(get_db)):
    return _get(db, req_id)


@router.patch("/{req_id}", response_model=FeatureRequestOut)
def patch_request(req_id: int, body: FeatureRequestPatch, db: Session = Depends(get_db)):
    req = _get(db, req_id)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(req, k, v)
    return req


@router.post("/{req_id}/plan", response_model=FeatureRequestOut)
def plan(req_id: int, tasks: BackgroundTasks, db: Session = Depends(get_db)):
    req = _get(db, req_id)
    _require(req, "draft")
    if runner.is_busy():
        raise HTTPException(409, "agent busy")
    req.status = "planning"
    req.error = None
    tasks.add_task(runner.run_plan, req.id)
    return req


@router.post("/{req_id}/approve", response_model=FeatureRequestOut)
def approve(req_id: int, db: Session = Depends(get_db)):
    req = _get(db, req_id)
    _require(req, "planned")
    req.status = "approved"
    return req


@router.post("/{req_id}/reject", response_model=FeatureRequestOut)
def reject(req_id: int, body: ReviewNote, db: Session = Depends(get_db)):
    req = _get(db, req_id)
    _require(req, "planned")
    req.status = "draft"
    req.review_note = body.review_note
    return req


@router.post("/{req_id}/implement", response_model=FeatureRequestOut)
def implement(req_id: int, tasks: BackgroundTasks, db: Session = Depends(get_db)):
    req = _get(db, req_id)
    _require(req, "approved", "failed")
    if runner.is_busy():
        raise HTTPException(409, "agent busy")
    req.status = "implementing"
    req.error = None
    tasks.add_task(runner.run_implement, req.id)
    return req
