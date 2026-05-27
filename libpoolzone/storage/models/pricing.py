from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from libpoolzone.storage.base import Base


class PricingRule(Base):
    """Margin + coefficient applied during export. Scope = supplier or product."""

    __tablename__ = "pricing_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    scope: Mapped[str] = mapped_column(String(16))  # "supplier" | "product"
    supplier_id: Mapped[int | None] = mapped_column(
        ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=True, index=True
    )
    product_code: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    margin_pct: Mapped[Decimal] = mapped_column(Numeric(5, 4))  # e.g. 0.35
    coefficient: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=1)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class CompetitorPrice(Base):
    __tablename__ = "competitor_prices"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    competitor_name: Mapped[str] = mapped_column(String(64))
    url: Mapped[str] = mapped_column(Text)
    price_with_vat: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
