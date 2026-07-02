from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    ARRAY,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    feed_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Columns the sync is allowed to overwrite on an EXISTING product.
    update_whitelist: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=lambda: ["stock", "price_purchase", "availability"]
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (UniqueConstraint("supplier_id", "code", name="uq_product_supplier_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(128), index=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), nullable=True)
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id"), nullable=True)
    ean: Mapped[str | None] = mapped_column(String(64), nullable=True)
    manufacturer: Mapped[str | None] = mapped_column(String(255), nullable=True)

    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    short_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    long_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    seo_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    seo_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    url_slug: Mapped[str | None] = mapped_column(Text, nullable=True)

    stock: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weight: Mapped[int | None] = mapped_column(Integer, nullable=True)  # grams
    availability: Mapped[str | None] = mapped_column(String(128), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    price_purchase: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    coefficient: Mapped[Decimal] = mapped_column(Numeric(6, 4), default=Decimal("1.0"))
    margin_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    params: Mapped[list[ProductParam]] = relationship(
        cascade="all, delete-orphan", back_populates="product"
    )
    images: Mapped[list[ProductImage]] = relationship(
        cascade="all, delete-orphan", back_populates="product"
    )


class ProductParam(Base):
    __tablename__ = "product_params"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(255))
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
    ord: Mapped[int] = mapped_column(Integer, default=0)

    product: Mapped[Product] = relationship(back_populates="params")


class ProductImage(Base):
    __tablename__ = "product_images"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    url: Mapped[str] = mapped_column(Text)
    alt: Mapped[str | None] = mapped_column(Text, nullable=True)
    ord: Mapped[int] = mapped_column(Integer, default=0)

    product: Mapped[Product] = relationship(back_populates="images")


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(255))
    seo_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    seo_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    upgates_code: Mapped[str | None] = mapped_column(String(255), nullable=True)


class ProductCategory(Base):
    __tablename__ = "product_categories"
    __table_args__ = (
        UniqueConstraint("product_id", "category_id", name="uq_product_category"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id", ondelete="CASCADE"))
    primary_yn: Mapped[bool] = mapped_column(Boolean, default=False)
    position: Mapped[int] = mapped_column(Integer, default=0)


class SupplierCategoryMap(Base):
    __tablename__ = "supplier_category_map"
    __table_args__ = (
        UniqueConstraint("supplier_id", "supplier_path", name="uq_supplier_path"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id", ondelete="CASCADE"))
    supplier_path: Mapped[str] = mapped_column(Text)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id", ondelete="CASCADE"))


class PricingRule(Base):
    __tablename__ = "pricing_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    scope: Mapped[str] = mapped_column(String(32))  # "default" | "manufacturer"
    match_value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    margin_pct: Mapped[Decimal] = mapped_column(Numeric(5, 4))


class JobRun(Base):
    __tablename__ = "job_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(32), index=True)  # "sync" | "export" | ...
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="running")  # running|success|failed|skipped
    stats: Mapped[dict] = mapped_column(JSONB, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
