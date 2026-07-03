from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    supplier_id: int | None
    ean: str | None
    manufacturer: str | None
    title: str | None
    short_description: str | None
    long_description: str | None
    seo_title: str | None
    seo_description: str | None
    url_slug: str | None
    stock: int | None
    weight: int | None
    availability: str | None
    active: bool
    price_purchase: Decimal | None
    coefficient: Decimal
    margin_pct: Decimal | None
    note: str | None
    sale_price: Decimal | None = None


class ProductUpdate(BaseModel):
    """Owner-editable fields only. Supplier-owned fields (stock, price_purchase, ...) are not here."""

    title: str | None = None
    short_description: str | None = None
    long_description: str | None = None
    seo_title: str | None = None
    seo_description: str | None = None
    url_slug: str | None = None
    active: bool | None = None
    coefficient: Decimal | None = None
    margin_pct: Decimal | None = None
    note: str | None = None
    params: list[ProductParamIO] | None = None
    images: list[ProductImageIO] | None = None
    categories: list[ProductCategoryIO] | None = None


class ProductParamIO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    value: str | None
    ord: int


class ProductImageIO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    url: str
    alt: str | None
    ord: int


class ProductCategoryIO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    category_id: int
    primary_yn: bool


class ProductDetailOut(ProductOut):
    params: list[ProductParamIO] = []
    images: list[ProductImageIO] = []
    categories: list[ProductCategoryIO] = []


class ProductListOut(BaseModel):
    items: list[ProductOut]
    total: int


class MarginRuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    scope: str
    match_value: str | None
    margin_pct: Decimal


class MarginRuleUpdate(BaseModel):
    margin_pct: Decimal


class JobRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: str
    status: str
    started_at: datetime | None
    finished_at: datetime | None
    stats: dict
    error: str | None
