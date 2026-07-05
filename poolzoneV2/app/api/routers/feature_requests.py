from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.schemas import (
    FeatureRequestCreate,
    FeatureRequestOut,
    FeatureRequestPatch,
    Transition,
)
from app.models import FeatureRequest

router = APIRouter(prefix="/api/feature-requests", tags=["feature-requests"])

# Guarded state machine. Agent execution is external now (a local claude session
# runs the `feature-runner` skill, which dispatches a subagent per request and
# writes changes to the CURRENT working tree — no commit). The backend only owns
# status. Operator sets the two `ready_*`; the agent sets planning/planned/
# implementing/implemented via this same endpoint.
#
# from -> {to: required_body_field_or_None}
TRANSITIONS: dict[str, dict[str, str | None]] = {
    "draft": {"ready_for_plan": None},
    "ready_for_plan": {"planning": None, "draft": None},  # agent claims / operator cancels
    "planning": {"planned": "plan", "ready_for_plan": None},  # done / failed-retry
    "planned": {"ready_for_impl": None, "draft": None},  # operator approves / re-plans
    "ready_for_impl": {"implementing": None, "planned": None},  # agent claims / cancels
    "implementing": {"implemented": None, "ready_for_impl": None},  # done / failed-retry
    "implemented": {"draft": None},  # redo from scratch if needed
}


def _get(db: Session, req_id: int) -> FeatureRequest:
    req = db.get(FeatureRequest, req_id)
    if req is None:
        raise HTTPException(404, "feature request not found")
    return req


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
    """Edit content fields (title/description/priority/tag/plan). Not status — use /transition."""
    req = _get(db, req_id)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(req, k, v)
    return req


@router.post("/{req_id}/transition", response_model=FeatureRequestOut)
def transition(req_id: int, body: Transition, db: Session = Depends(get_db)):
    req = _get(db, req_id)
    allowed = TRANSITIONS.get(req.status, {})
    if body.to not in allowed:
        raise HTTPException(409, f"illegal transition {req.status} -> {body.to}")
    required = allowed[body.to]
    if required and getattr(body, required) is None:
        raise HTTPException(422, f"'{required}' required for -> {body.to}")

    req.status = body.to
    if body.plan is not None:
        req.plan = body.plan
    if body.execution_log is not None:
        req.execution_log = body.execution_log
    if body.review_note is not None:
        req.review_note = body.review_note
    req.error = body.error  # provided value or None (clears)
    return req
