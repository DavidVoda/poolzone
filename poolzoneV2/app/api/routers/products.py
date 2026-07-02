from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.schemas import ProductOut, ProductUpdate
from app.models import Product
from app.pricing import load_margin_rules, sale_price

router = APIRouter(prefix="/api/products", tags=["products"])


def _out(product: Product, rules: dict) -> ProductOut:
    out = ProductOut.model_validate(product)
    if product.price_purchase is not None:
        out.sale_price = sale_price(product, rules)
    return out


@router.get("", response_model=list[ProductOut])
def list_products(
    db: Session = Depends(get_db),
    q: str | None = None,
    active: bool | None = None,
    limit: int = Query(50, le=500),
    offset: int = 0,
):
    stmt = select(Product)
    if q:
        stmt = stmt.where(Product.title.ilike(f"%{q}%") | Product.code.ilike(f"%{q}%"))
    if active is not None:
        stmt = stmt.where(Product.active.is_(active))
    stmt = stmt.order_by(Product.id).limit(limit).offset(offset)
    rules = load_margin_rules(db)
    return [_out(p, rules) for p in db.execute(stmt).scalars()]


@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(404, "product not found")
    return _out(product, load_margin_rules(db))


@router.patch("/{product_id}", response_model=ProductOut)
def update_product(product_id: int, patch: ProductUpdate, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(404, "product not found")
    for field, value in patch.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    db.flush()
    db.refresh(product)  # reflect DB-quantized numerics in the response
    return _out(product, load_margin_rules(db))
