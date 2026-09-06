"""Collection health endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import get_current_user
from backend.app.models.collection_run import CollectionRun

router = APIRouter(tags=["health"])

# No successful production run within this window → stale.
# Two 12-hour cycles plus 2 hours margin.
STALE_HOURS = 26.0


class CollectionHealthResponse(BaseModel):
    status: str  # "healthy" | "stale" | "failed" | "unknown"
    last_successful_run_at: Optional[str] = None
    hours_since_last_run: Optional[float] = None
    offers_in_last_run: Optional[int] = None
    last_run_error: Optional[str] = None


class RunSummary(BaseModel):
    id: int
    started_at: str
    finished_at: Optional[str]
    products_processed: int
    offers_stored: int
    calls_made: int
    error_count: int
    status: str
    error_detail: Optional[str]
    duration_seconds: Optional[float]


def _get_collection_status(db: Session) -> CollectionHealthResponse:
    # Most recent successful run (any time).
    last_success = (
        db.query(CollectionRun)
        .filter(CollectionRun.status == "success")
        .order_by(CollectionRun.finished_at.desc())
        .first()
    )

    if last_success is None:
        return CollectionHealthResponse(status="unknown")

    now = datetime.now(timezone.utc)
    finished = last_success.finished_at
    # SQLite stores naive datetimes; coerce to UTC-aware for arithmetic.
    if finished.tzinfo is None:
        finished = finished.replace(tzinfo=timezone.utc)
    hours_since = (now - finished).total_seconds() / 3600

    # Most recent run of any status to check for a terminal failure.
    last_run = (
        db.query(CollectionRun)
        .order_by(CollectionRun.finished_at.desc())
        .first()
    )

    if last_run and last_run.status == "failed" and last_run.id != last_success.id:
        status = "failed"
    elif hours_since > STALE_HOURS:
        status = "stale"
    else:
        status = "healthy"

    return CollectionHealthResponse(
        status=status,
        last_successful_run_at=finished.isoformat(),
        hours_since_last_run=round(hours_since, 1),
        offers_in_last_run=last_success.offers_stored,
        last_run_error=(
            last_run.error_detail
            if last_run and last_run.status == "failed" and last_run.id != last_success.id
            else None
        ),
    )


@router.get("/health/collection", response_model=CollectionHealthResponse)
def collection_health(db: Session = Depends(get_db)):
    """Return the health of the background data collection process."""
    return _get_collection_status(db)


@router.get("/admin/collection/runs", response_model=list[RunSummary])
def list_collection_runs(
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """Return the last 20 collection runs for admin monitoring."""
    runs = (
        db.query(CollectionRun)
        .order_by(CollectionRun.started_at.desc())
        .limit(20)
        .all()
    )
    result = []
    for r in runs:
        started = r.started_at
        finished = r.finished_at
        if started and started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        if finished and finished.tzinfo is None:
            finished = finished.replace(tzinfo=timezone.utc)
        duration = (
            (finished - started).total_seconds()
            if started and finished
            else None
        )
        result.append(RunSummary(
            id=r.id,
            started_at=started.isoformat(),
            finished_at=finished.isoformat() if finished else None,
            products_processed=r.products_processed,
            offers_stored=r.offers_stored,
            calls_made=r.calls_made,
            error_count=r.error_count,
            status=r.status,
            error_detail=r.error_detail,
            duration_seconds=round(duration, 1) if duration is not None else None,
        ))
    return result
