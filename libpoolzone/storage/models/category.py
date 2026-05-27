from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from libpoolzone.storage.base import Base


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True
    )

    name_i18n: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    description_i18n: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    seo_title_i18n: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    seo_description_i18n: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    seo_keywords_i18n: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    url_i18n: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    show: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    parent: Mapped["Category | None"] = relationship(remote_side="Category.id", back_populates="children")
    children: Mapped[list["Category"]] = relationship(back_populates="parent")


class ProductCategory(Base):
    __tablename__ = "product_categories"
    __table_args__ = (UniqueConstraint("product_id", "category_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id", ondelete="CASCADE"), index=True)
    primary_yn: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
