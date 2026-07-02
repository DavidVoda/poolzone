from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import JobRun, Product, ProductImage, ProductParam, Supplier
from app.sync.types import ParsedProduct

# Fields copied verbatim onto a NEW product (create-full). Whitelist controls updates.
_CREATE_FIELDS = (
    "title",
    "ean",
    "manufacturer",
    "price_purchase",
    "stock",
    "weight",
    "availability",
)


def _apply_create(product: Product, parsed: ParsedProduct) -> None:
    for f in _CREATE_FIELDS:
        setattr(product, f, getattr(parsed, f))
    product.images = [ProductImage(url=u, ord=i) for i, u in enumerate(parsed.image_urls)]
    product.params = [
        ProductParam(name=p.name, value=p.value, ord=i) for i, p in enumerate(parsed.params)
    ]


def _apply_update(product: Product, parsed: ParsedProduct, whitelist: list[str]) -> None:
    for field_name in whitelist:
        if hasattr(parsed, field_name):
            setattr(product, field_name, getattr(parsed, field_name))


def run_sync(session: Session, supplier: Supplier, parsed_products: list[ParsedProduct]) -> dict:
    """Create-full for new products, update-whitelist for existing. Records a JobRun."""
    job = JobRun(kind="sync", status="running", stats={})
    session.add(job)
    session.flush()

    stats = {"products_seen": 0, "created": 0, "updated": 0, "errors": []}
    whitelist = supplier.update_whitelist or ["stock", "price_purchase", "availability"]

    for parsed in parsed_products:
        stats["products_seen"] += 1
        try:
            existing = session.execute(
                select(Product).where(
                    Product.supplier_id == supplier.id, Product.code == parsed.code
                )
            ).scalar_one_or_none()
            if existing is None:
                product = Product(code=parsed.code, supplier_id=supplier.id)
                _apply_create(product, parsed)
                session.add(product)
                stats["created"] += 1
            else:
                _apply_update(existing, parsed, whitelist)
                stats["updated"] += 1
        except Exception as exc:  # per-product isolation: one bad row never aborts the run
            stats["errors"].append({"code": parsed.code, "error": str(exc)})

    session.flush()
    supplier.last_synced_at = datetime.now(timezone.utc)
    job.status = "success"
    job.finished_at = datetime.now(timezone.utc)
    job.stats = stats
    session.flush()
    return stats
