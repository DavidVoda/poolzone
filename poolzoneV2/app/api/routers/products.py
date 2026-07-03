from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.filters import parse_filter, parse_sort
from app.api.schemas import ProductListOut, ProductOut, ProductUpdate
from app.models import Product
from app.pricing import load_margin_rules, sale_price

router = APIRouter(prefix="/api/products", tags=["products"])


def _out(product: Product, rules: dict) -> ProductOut:
    out = ProductOut.model_validate(product)
    if product.price_purchase is not None:
        out.sale_price = sale_price(product, rules)
    return out


@router.get("", response_model=ProductListOut)
def list_products(
    db: Session = Depends(get_db),
    q: str | None = None,
    filter: list[str] = Query(default=[]),
    sort: str | None = None,
    overrides: bool = False,
    limit: int = Query(50, le=500),
    offset: int = 0,
):
    stmt = select(Product)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            Product.title.ilike(like) | Product.code.ilike(like) | Product.ean.ilike(like)
        )
    for expr in filter:
        stmt = stmt.where(parse_filter(expr))
    if overrides:
        stmt = stmt.where((Product.coefficient != 1) | (Product.margin_pct.is_not(None)))
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    stmt = stmt.order_by(*parse_sort(sort)).limit(limit).offset(offset)
    rules = load_margin_rules(db)
    return ProductListOut(items=[_out(p, rules) for p in db.execute(stmt).scalars()], total=total)


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
