from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from libpoolzone.storage.base import Base


class Product(Base):
    """Master catalog row. Standalone product when parent_id is NULL, variant when set."""

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Identity
    ean: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    supplier_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    manufacturer: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Logistics
    stock: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weight: Mapped[int | None] = mapped_column(Integer, nullable=True)  # grams
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    show: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Multilingual content as JSONB ({"cs": "..."} etc.)
    titles: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    short_descriptions: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    long_descriptions: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    urls: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    seo_titles: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    seo_descriptions: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    seo_keywords: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # Pricing (excl VAT)
    price_purchase: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    price_common: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    price_original: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)

    # Provenance
    primary_supplier_id: Mapped[int | None] = mapped_column(
        ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    parent: Mapped[Product | None] = relationship(
        remote_side="Product.id", back_populates="variants"
    )
    variants: Mapped[list[Product]] = relationship(back_populates="parent")
    images: Mapped[list[ProductImage]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )
    parameters: Mapped[list[ProductParameter]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )
    files: Mapped[list[ProductFile]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )


class ProductImage(Base):
    __tablename__ = "product_images"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    alt: Mapped[str | None] = mapped_column(Text, nullable=True)
    ord: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    product: Mapped[Product] = relationship(back_populates="images")


class ProductParameter(Base):
    __tablename__ = "product_parameters"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    name_i18n: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    value_i18n: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    product: Mapped[Product] = relationship(back_populates="parameters")


class ProductFile(Base):
    __tablename__ = "product_files"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)  # "pdf_manual", "datasheet", …

    product: Mapped[Product] = relationship(back_populates="files")
