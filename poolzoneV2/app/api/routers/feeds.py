from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.schemas import FeedConfigOut, FeedConfigUpdate
from app.models import FeedConfig, JobRun
from app.sync import poolzone

router = APIRouter(prefix="/api/feeds", tags=["feeds"])

# kind -> (default url, whitelist-able fields, importer). Default whitelist = all fields.
_KINDS = {
    "products": (poolzone.DEFAULT_PRODUCTS_URL, poolzone.PRODUCT_FIELDS, poolzone.import_products),
    "categories": (
        poolzone.DEFAULT_CATEGORIES_URL,
        poolzone.CATEGORY_FIELDS,
        poolzone.import_categories,
    ),
}


def _get_or_create(db: Session, kind: str) -> FeedConfig:
    cfg = db.execute(select(FeedConfig).where(FeedConfig.kind == kind)).scalar_one_or_none()
    if cfg is None:
        url, fields, _ = _KINDS[kind]
        cfg = FeedConfig(kind=kind, feed_url=url, update_whitelist=list(fields))
        db.add(cfg)
        db.flush()
    return cfg


def _out(cfg: FeedConfig) -> FeedConfigOut:
    out = FeedConfigOut.model_validate(cfg)
    out.available_fields = list(_KINDS[cfg.kind][1])
    return out


@router.get("", response_model=list[FeedConfigOut])
def list_feeds(db: Session = Depends(get_db)):
    return [_out(_get_or_create(db, kind)) for kind in _KINDS]


@router.patch("/{kind}", response_model=FeedConfigOut)
def update_feed(kind: str, patch: FeedConfigUpdate, db: Session = Depends(get_db)):
    if kind not in _KINDS:
        raise HTTPException(404, f"unknown feed '{kind}'")
    cfg = _get_or_create(db, kind)
    data = patch.model_dump(exclude_unset=True)
    if "update_whitelist" in data:
        allowed = set(_KINDS[kind][1])
        bad = [f for f in data["update_whitelist"] if f not in allowed]
        if bad:
            raise HTTPException(422, f"unknown fields: {bad}")
    for field, value in data.items():
        setattr(cfg, field, value)
    db.flush()
    return _out(cfg)


@router.post("/{kind}/run")
def run_feed(kind: str, db: Session = Depends(get_db)):
    if kind not in _KINDS:
        raise HTTPException(404, f"unknown feed '{kind}'")
    cfg = _get_or_create(db, kind)
    if not cfg.feed_url:
        raise HTTPException(409, f"feed '{kind}' has no URL")
    _, _, importer = _KINDS[kind]

    # ponytail: synchronous — a manual admin click that waits is fine at this scale.
    # On failure the request rolls back (get_db), so no partial import or job row —
    # matches the supplier trigger_sync behaviour; only successful runs are recorded.
    raw = poolzone.fetch(cfg.feed_url)
    job = JobRun(kind="sync", status="running", stats={})
    db.add(job)
    db.flush()
    stats = importer(db, raw, cfg.update_whitelist)
    job.status = "success"
    job.stats = stats
    job.finished_at = datetime.now(timezone.utc)
    cfg.last_run_at = datetime.now(timezone.utc)
    db.flush()
    return stats
