from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.schemas import SupplierOut, SupplierUpdate
from app.models import Supplier

router = APIRouter(prefix="/api/suppliers", tags=["suppliers"])


@router.get("", response_model=list[SupplierOut])
def list_suppliers(db: Session = Depends(get_db)):
    return list(db.execute(select(Supplier).order_by(Supplier.id)).scalars())


@router.patch("/{code}", response_model=SupplierOut)
def update_supplier(code: str, body: SupplierUpdate, db: Session = Depends(get_db)):
    supplier = db.execute(
        select(Supplier).where(Supplier.code == code)
    ).scalar_one_or_none()
    if supplier is None:
        raise HTTPException(404, f"supplier '{code}' not found")
    if body.feed_url is not None:
        supplier.feed_url = body.feed_url
    return supplier
