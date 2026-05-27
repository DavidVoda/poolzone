"""Field-level locks: prevent supplier sync from overwriting human-edited fields."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from libpoolzone.storage.models import Product, ProductFieldLock


def is_locked(session: Session, *, product_id: int, field_path: str) -> bool:
    return (
        session.scalars(
            select(ProductFieldLock).where(
                ProductFieldLock.product_id == product_id,
                ProductFieldLock.field_path == field_path,
            )
        ).first()
        is not None
    )


def lock_field(
    session: Session,
    *,
    product_id: int,
    field_path: str,
    locked_by: str | None = None,
    note: str | None = None,
) -> ProductFieldLock:
    """Idempotent: if already locked, return the existing row (no-op)."""
    existing = (
        session.query(ProductFieldLock)
        .filter_by(product_id=product_id, field_path=field_path)
        .one_or_none()
    )
    if existing is not None:
        return existing

    lock = ProductFieldLock(
        product_id=product_id,
        field_path=field_path,
        locked_by=locked_by,
        note=note,
    )
    session.add(lock)
    session.flush()
    return lock


def unlock_field(session: Session, *, product_id: int, field_path: str) -> None:
    session.query(ProductFieldLock).filter_by(product_id=product_id, field_path=field_path).delete()
    session.flush()


def list_locks_for_product(session: Session, *, product_id: int) -> list[ProductFieldLock]:
    return list(
        session.scalars(select(ProductFieldLock).where(ProductFieldLock.product_id == product_id))
    )


def apply_changes_respecting_locks(
    session: Session,
    *,
    product_id: int,
    changes: dict[str, Any],
    field_path_for: dict[str, str],
) -> dict[str, int]:
    """Apply `changes` to a product, skipping any field whose path is locked.

    `changes`         : {model_attribute_name: new_value}
    `field_path_for`  : {model_attribute_name: logical_field_path}
                         e.g. {"price_common": "price.common"}

    Returns a stats dict: {"updated": N, "locked_skips": M}.
    """
    product = session.get(Product, product_id)
    if product is None:
        raise ValueError(f"product {product_id} not found")

    updated = 0
    locked_skips = 0

    for attr, new_value in changes.items():
        path = field_path_for.get(attr, attr)
        if is_locked(session, product_id=product_id, field_path=path):
            locked_skips += 1
            continue
        setattr(product, attr, new_value)
        updated += 1

    session.flush()
    return {"updated": updated, "locked_skips": locked_skips}
