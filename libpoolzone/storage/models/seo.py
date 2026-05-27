from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from libpoolzone.storage.base import Base


class SeoSuggestion(Base):
    """AI-generated content awaiting human review."""

    __tablename__ = "seo_suggestions"

    id: Mapped[int] = mapped_column(primary_key=True)
    target_kind: Mapped[str] = mapped_column(String(16))  # "product" | "category"
    target_id: Mapped[int] = mapped_column(Integer, index=True)
    field_path: Mapped[str] = mapped_column(String(128))
    suggested_value: Mapped[dict] = mapped_column(JSONB)  # text or jsonb payload
    template_used: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    prompt_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    status: Mapped[str] = mapped_column(String(16), default="pending")
    reviewed_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
