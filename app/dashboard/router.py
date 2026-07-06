"""
TheMemeCanvas Automation Suite — Dashboard REST API Router
==========================================================
Provides all API endpoints for the React dashboard frontend.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config.constants import UploadStage
from app.config.settings import settings
from app.database.base import get_db
from app.models.upload import Upload
from app.models.queue_item import QueueItem
from app.models.notification_log import NotificationLog

logger = logging.getLogger("thememecanvas.dashboard")

router = APIRouter(prefix="/api", tags=["dashboard"])


# ---------------------------------------------------------------------------
# Pydantic Response Models
# ---------------------------------------------------------------------------

class UploadRecord(BaseModel):
    id: int
    filename: str
    title: Optional[str]
    status: str
    youtube_video_id: Optional[str]
    youtube_url: Optional[str]
    youtube_status: Optional[str]
    retry_count: int
    created_at: Optional[datetime]
    completed_at: Optional[datetime]
    last_error: Optional[str]

    class Config:
        from_attributes = True


class QueueItemRecord(BaseModel):
    id: int
    filename: str
    drive_file_id: str
    is_processed: bool
    is_skipped: bool
    has_thumbnail: bool
    file_size_bytes: Optional[int]
    discovered_at: datetime

    class Config:
        from_attributes = True


class DashboardStats(BaseModel):
    total_uploaded: int
    total_failed: int
    total_queue: int
    queue_remaining: int
    days_remaining: int
    uploads_paused: bool
    next_upload_time: Optional[str]
    upload_time_setting: str
    timezone: str
    today_upload: Optional[UploadRecord]


# ---------------------------------------------------------------------------
# Dashboard Stats
# ---------------------------------------------------------------------------

@router.get("/stats", response_model=DashboardStats)
def get_stats(db: Session = Depends(get_db)) -> DashboardStats:
    """Get overall dashboard statistics."""
    total_uploaded = db.query(Upload).filter(Upload.status == UploadStage.COMPLETED).count()
    total_failed = db.query(Upload).filter(Upload.status == UploadStage.FAILED).count()
    total_queue = db.query(QueueItem).count()
    queue_remaining = db.query(QueueItem).filter(QueueItem.is_processed == False).count()

    today = datetime.utcnow().date()
    today_upload = (
        db.query(Upload)
        .filter(
            Upload.completed_at >= datetime(today.year, today.month, today.day),
            Upload.status == UploadStage.COMPLETED,
        )
        .first()
    )

    next_upload_time = None
    try:
        from app.scheduler.runner import get_next_upload_time
        next_upload_time = get_next_upload_time()
    except Exception:
        pass

    return DashboardStats(
        total_uploaded=total_uploaded,
        total_failed=total_failed,
        total_queue=total_queue,
        queue_remaining=queue_remaining,
        days_remaining=queue_remaining,
        uploads_paused=settings.uploads_paused,
        next_upload_time=next_upload_time,
        upload_time_setting=settings.upload_time,
        timezone=settings.timezone,
        today_upload=UploadRecord.from_orm(today_upload) if today_upload else None,
    )


# ---------------------------------------------------------------------------
# Upload History
# ---------------------------------------------------------------------------

@router.get("/uploads", response_model=List[UploadRecord])
def get_uploads(
    limit: int = Query(50, le=500),
    offset: int = Query(0, ge=0),
    status: Optional[str] = None,
    db: Session = Depends(get_db),
) -> List[UploadRecord]:
    """Get paginated upload history."""
    query = db.query(Upload)

    if status:
        query = query.filter(Upload.status == status)

    uploads = query.order_by(Upload.created_at.desc()).offset(offset).limit(limit).all()
    return [UploadRecord.from_orm(u) for u in uploads]


@router.get("/uploads/{upload_id}", response_model=UploadRecord)
def get_upload(upload_id: int, db: Session = Depends(get_db)) -> UploadRecord:
    """Get a specific upload by ID."""
    upload = db.query(Upload).filter(Upload.id == upload_id).first()
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")
    return UploadRecord.from_orm(upload)


# ---------------------------------------------------------------------------
# Queue Management
# ---------------------------------------------------------------------------

@router.get("/queue", response_model=List[QueueItemRecord])
def get_queue(
    limit: int = Query(100, le=500),
    processed: Optional[bool] = None,
    db: Session = Depends(get_db),
) -> List[QueueItemRecord]:
    """Get queue items from the database."""
    query = db.query(QueueItem)
    if processed is not None:
        query = query.filter(QueueItem.is_processed == processed)
    items = query.order_by(QueueItem.discovered_at.asc()).limit(limit).all()
    return [QueueItemRecord.from_orm(item) for item in items]


@router.post("/queue/sync")
def sync_queue(db: Session = Depends(get_db)) -> Dict:
    """Manually trigger a queue sync from Google Drive."""
    try:
        from app.services.drive.queue_manager import QueueManager
        queue = QueueManager()
        new_count, total = queue.sync_queue_to_db(db)
        return {"status": "ok", "new_items": new_count, "total": total}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/queue/skip/{item_id}")
def skip_queue_item(item_id: int, db: Session = Depends(get_db)) -> Dict:
    """Mark a queue item as skipped."""
    item = db.query(QueueItem).filter(QueueItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Queue item not found")
    item.is_skipped = True
    db.commit()
    return {"status": "ok", "item_id": item_id}


# ---------------------------------------------------------------------------
# Scheduler Controls
# ---------------------------------------------------------------------------

@router.post("/scheduler/pause")
def pause_scheduler() -> Dict:
    """Pause daily uploads."""
    try:
        from app.scheduler.runner import pause_uploads
        pause_uploads()
        return {"status": "paused"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scheduler/resume")
def resume_scheduler() -> Dict:
    """Resume daily uploads."""
    try:
        from app.scheduler.runner import resume_uploads
        resume_uploads()
        return {"status": "resumed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scheduler/trigger-now")
def trigger_upload_now() -> Dict:
    """Force an immediate upload."""
    try:
        from app.scheduler.runner import trigger_upload_now as _trigger
        _trigger()
        return {"status": "triggered"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------

@router.get("/health")
def health_check() -> Dict:
    """Run and return a health report for all services."""
    try:
        from app.utils.health_check import run_full_health_check
        report = run_full_health_check()
        return report.to_dict()
    except Exception as e:
        return {"overall_status": "error", "error": str(e)}


# ---------------------------------------------------------------------------
# Logs
# ---------------------------------------------------------------------------

@router.get("/logs")
def get_logs(
    log_file: str = Query("system", description="Log file: system, scheduler, drive, youtube, ai, notifications, errors"),
    lines: int = Query(100, le=1000),
) -> Dict:
    """Read the last N lines of a log file."""
    import os
    from pathlib import Path

    log_files = {
        "system": "logs/system.log",
        "scheduler": "logs/scheduler.log",
        "drive": "logs/drive.log",
        "youtube": "logs/youtube.log",
        "ai": "logs/ai.log",
        "notifications": "logs/notifications.log",
        "pipeline": "logs/pipeline.log",
        "errors": "logs/errors.log",
    }

    filepath = log_files.get(log_file)
    if not filepath:
        raise HTTPException(status_code=400, detail=f"Unknown log file: {log_file}")

    path = Path(filepath)
    if not path.exists():
        return {"log_file": log_file, "lines": [], "total_lines": 0}

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        all_lines = f.readlines()

    last_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
    return {
        "log_file": log_file,
        "lines": [line.rstrip() for line in last_lines],
        "total_lines": len(all_lines),
    }


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------

@router.get("/notifications")
def get_notification_logs(
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
) -> List[Dict]:
    """Get recent notification logs."""
    logs = (
        db.query(NotificationLog)
        .order_by(NotificationLog.sent_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": log.id,
            "provider": log.provider,
            "event_type": log.event_type,
            "success": log.success,
            "error": log.error,
            "sent_at": log.sent_at.isoformat() if log.sent_at else None,
        }
        for log in logs
    ]


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------

@router.get("/charts/upload-history")
def get_upload_history_chart(
    days: int = Query(30, le=365),
    db: Session = Depends(get_db),
) -> Dict:
    """Get daily upload counts for the chart."""
    from sqlalchemy import func, cast, Date

    since = datetime.utcnow() - timedelta(days=days)

    results = (
        db.query(
            func.date(Upload.completed_at).label("date"),
            func.count(Upload.id).label("count"),
        )
        .filter(Upload.completed_at >= since, Upload.status == UploadStage.COMPLETED)
        .group_by(func.date(Upload.completed_at))
        .order_by(func.date(Upload.completed_at))
        .all()
    )

    return {
        "labels": [str(r.date) for r in results],
        "data": [r.count for r in results],
    }


@router.get("/charts/status-breakdown")
def get_status_breakdown(db: Session = Depends(get_db)) -> Dict:
    """Get upload status breakdown for pie chart."""
    from sqlalchemy import func

    results = (
        db.query(Upload.status, func.count(Upload.id).label("count"))
        .group_by(Upload.status)
        .all()
    )

    return {
        "labels": [r.status for r in results],
        "data": [r.count for r in results],
    }
