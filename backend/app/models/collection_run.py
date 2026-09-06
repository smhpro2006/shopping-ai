from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.core.database import Base


class CollectionRun(Base):
    __tablename__ = "collection_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    products_processed: Mapped[int] = mapped_column(Integer, default=0)
    offers_stored: Mapped[int] = mapped_column(Integer, default=0)
    calls_made: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    # "success" | "failed"
    status: Mapped[str] = mapped_column(String, nullable=False)
    error_detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
