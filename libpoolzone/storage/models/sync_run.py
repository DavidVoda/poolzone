from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from libpoolzone.storage.base import Base


class SyncRun(Base):
    """Audit row for every import / export / SEO / scrape batch."""

    __tablename__ = "sync_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(32))  # "import" | "export" | "seo" | "scrape"
    source: Mapped[str | None] = mapped_column(String(64), nullable=True)  # supplier code etc.
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="running")  # "running" | "ok" | "failed"
    stats: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    log_path: Mapped[str | None] = mapped_column(Text, nullable=True)
