from __future__ import annotations

from decimal import Decimal, InvalidOperation

from fastapi import HTTPException
from sqlalchemy import Boolean, Integer, Numeric, String
from sqlalchemy.sql import ColumnElement

from app.models import Product

FILTER_COLUMNS = {
    "code": Product.code,
    "title": Product.title,
    "ean": Product.ean,
    "manufacturer": Product.manufacturer,
    "supplier_id": Product.supplier_id,
    "stock": Product.stock,
    "availability": Product.availability,
    "active": Product.active,
    "price_purchase": Product.price_purchase,
    "coefficient": Product.coefficient,
    "margin_pct": Product.margin_pct,
    "long_description": Product.long_description,
    "seo_title": Product.seo_title,
}

SORT_COLUMNS = {**FILTER_COLUMNS, "id": Product.id, "updated_at": Product.updated_at}


def _coerce(col, value: str):
    try:
        if isinstance(col.type, Boolean):
            return value.lower() in ("true", "1", "ano")
        if isinstance(col.type, Integer):
            return int(value)
        if isinstance(col.type, Numeric):
            return Decimal(value)
    except (ValueError, InvalidOperation):
        raise HTTPException(422, f"bad filter value '{value}'")
    return value


def parse_filter(expr: str) -> ColumnElement[bool]:
    """'col:op:value' -> SQLAlchemy condition. Value may itself contain ':'."""
    col_name, _, rest = expr.partition(":")
    op, _, value = rest.partition(":")
    col = FILTER_COLUMNS.get(col_name)
    if col is None:
        raise HTTPException(422, f"unknown filter column '{col_name}'")
    match op:
        case "eq":
            return col == _coerce(col, value)
        case "ne":
            # SQL: NULL != x is UNKNOWN, so "not x" must also keep NULL rows.
            return (col != _coerce(col, value)) | col.is_(None)
        case "gt":
            return col > _coerce(col, value)
        case "lt":
            return col < _coerce(col, value)
        case "contains":
            if not isinstance(col.type, String):
                raise HTTPException(422, f"'contains' needs a text column, not '{col_name}'")
            return col.ilike(f"%{value}%")
        case "empty":
            return col.is_(None)
        case "notempty":
            return col.is_not(None)
        case _:
            raise HTTPException(422, f"unknown filter op '{op}'")


def parse_sort(sort: str | None):
    """'[-]col' -> order_by clauses (id tiebreak for stable pagination)."""
    if not sort:
        return (Product.id,)
    name = sort.removeprefix("-")
    col = SORT_COLUMNS.get(name)
    if col is None:
        raise HTTPException(422, f"unknown sort column '{name}'")
    return (col.desc() if sort.startswith("-") else col.asc(), Product.id)
