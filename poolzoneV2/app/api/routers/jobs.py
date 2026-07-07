from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.schemas import JobRunOut
from app.export.upgates_xml import run_export
from app.job_run import JobBusyError, assert_idle, job_run
from app.models import JobRun, Supplier
from app.sync.pipeline import run_sync
from app.sync.suppliers import ADAPTERS

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

# ponytail: triggers run synchronously — a manual admin click that waits is fine
# at this scale. Move to FastAPI BackgroundTasks when the sync wait annoys.


def _require_idle(db: Session) -> None:
    try:
        assert_idle(db)
    except JobBusyError:
        raise HTTPException(409, "a job is already running") from None


@router.get("", response_model=list[JobRunOut])
def list_jobs(db: Session = Depends(get_db), kind: str | None = None, limit: int = 50):
    stmt = select(JobRun).order_by(JobRun.id.desc()).limit(limit)
    if kind:
        stmt = stmt.where(JobRun.kind == kind)
    return list(db.execute(stmt).scalars())


@router.post("/export")
def trigger_export(db: Session = Depends(get_db)):
    _require_idle(db)
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
    if not supplier.feed_url:
        raise HTTPException(400, f"supplier '{supplier_code}' has no feed URL configured")
    # job_run commits the 'running' row up front — visible for the whole run, INCLUDING the
    # fetch+parse (the slow part), so sync/import/export all show 'running' the same way.
    try:
        with job_run(db, "sync") as job:
            try:
                parsed = adapter.parse(adapter.fetch(supplier.feed_url))
            except Exception as exc:  # network / parse failure — clean 502, records a failed job
                raise HTTPException(502, f"feed fetch/parse failed: {exc}") from exc
            job.stats = run_sync(db, supplier, parsed)
            return job.stats
    except JobBusyError:
        raise HTTPException(409, "a job is already running") from None
