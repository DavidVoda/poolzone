from __future__ import annotations

import dataclasses

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.filters import parse_filter, parse_sort
from app.api.schemas import (
    ProductCategoryIO,
    ProductDetailOut,
    ProductListOut,
    ProductOut,
    ProductUpdate,
)
from app.models import Product, ProductCategory, ProductImage, ProductParam, Supplier
from app.pricing import load_margin_rules, sale_price
from app.sync.suppliers import ADAPTERS

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


def _detail(product: Product, db: Session, rules: dict) -> ProductDetailOut:
    out = ProductDetailOut.model_validate(product)
    if product.price_purchase is not None:
        out.sale_price = sale_price(product, rules)  # same rule as _out; kept inline (different return type)
    out.categories = [
        ProductCategoryIO.model_validate(pc)
        for pc in db.execute(
            select(ProductCategory)
            .where(ProductCategory.product_id == product.id)
            .order_by(ProductCategory.position, ProductCategory.id)
        ).scalars()
    ]
    return out


@router.get("/{product_id}", response_model=ProductDetailOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(404, "product not found")
    return _detail(product, db, load_margin_rules(db))


@router.patch("/{product_id}", response_model=ProductDetailOut)
def update_product(product_id: int, patch: ProductUpdate, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(404, "product not found")
    data = patch.model_dump(exclude_unset=True)
    params = data.pop("params", None)
    images = data.pop("images", None)
    categories = data.pop("categories", None)
    for field, value in data.items():
        setattr(product, field, value)
    if params is not None:
        product.params = [ProductParam(**p) for p in params]
    if images is not None:
        product.images = [ProductImage(**i) for i in images]
    if categories is not None:
        db.execute(delete(ProductCategory).where(ProductCategory.product_id == product.id))
        seen: set[int] = set()  # last wins; avoids the (product_id, category_id) unique-constraint 500
        deduped = [c for c in categories if not (c["category_id"] in seen or seen.add(c["category_id"]))]
        for pos, c in enumerate(deduped):
            db.add(ProductCategory(product_id=product.id, position=pos, **c))
    db.flush()
    db.refresh(product)  # reflect DB-quantized numerics in the response
    return _detail(product, db, load_margin_rules(db))


@router.post("/{product_id}/repull")
def repull_product(product_id: int, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(404, "product not found")
    supplier = db.get(Supplier, product.supplier_id) if product.supplier_id else None
    if supplier is None:
        raise HTTPException(409, "product has no supplier")
    adapter = ADAPTERS.get(supplier.code)
    if adapter is None:
        raise HTTPException(409, f"no adapter for supplier '{supplier.code}'")
    if not supplier.feed_url:
        raise HTTPException(409, f"supplier '{supplier.code}' has no feed_url")
    parsed = next(
        (p for p in adapter.parse(adapter.fetch(supplier.feed_url)) if p.code == product.code),
        None,
    )
    if parsed is None:
        raise HTTPException(404, "product not found in supplier feed")
    return dataclasses.asdict(parsed)
