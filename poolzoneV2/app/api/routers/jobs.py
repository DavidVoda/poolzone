from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.schemas import JobRunOut
from app.export.upgates_xml import run_export
from app.models import JobRun, Supplier
from app.sync.pipeline import run_sync
from app.sync.suppliers import ADAPTERS

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

# ponytail: triggers run synchronously — a manual admin click that waits is fine
# at this scale. Move to FastAPI BackgroundTasks when the sync wait annoys.


@router.get("", response_model=list[JobRunOut])
def list_jobs(db: Session = Depends(get_db), kind: str | None = None, limit: int = 50):
    stmt = select(JobRun).order_by(JobRun.id.desc()).limit(limit)
    if kind:
        stmt = stmt.where(JobRun.kind == kind)
    return list(db.execute(stmt).scalars())


@router.post("/export")
def trigger_export(db: Session = Depends(get_db)):
    return run_export(db, "feeds")


@router.post("/sync/{supplier_code}")
def trigger_sync(supplier_code: str, db: Session = Depends(get_db)):
    adapter = ADAPTERS.get(supplier_code)
    if adapter is None:
        raise HTTPException(404, f"unknown supplier '{supplier_code}'")
    supplier = db.execute(
        select(Supplier).where(Supplier.code == supplier_code)
    ).scalar_one_or_none()
    if supplier is None:
        raise HTTPException(404, f"supplier '{supplier_code}' not seeded")
    parsed = adapter.parse(adapter.fetch(supplier.feed_url))
    return run_sync(db, supplier, parsed)
