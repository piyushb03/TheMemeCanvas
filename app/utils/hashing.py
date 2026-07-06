"""
TheMemeCanvas Automation Suite — SHA256 Hashing & Duplicate Detection
======================================================================
Provides fast content-based deduplication for uploaded videos.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

logger = logging.getLogger("thememecanvas.pipeline")

CHUNK_SIZE = 8 * 1024 * 1024  # 8 MB chunks for large video files


def compute_sha256(filepath: Path) -> str:
    """
    Compute SHA256 hash of a file efficiently using chunked reading.

    Args:
        filepath: Path to the file to hash.

    Returns:
        Lowercase hex string of the SHA256 digest.

    Raises:
        FileNotFoundError: If the file does not exist.
        IOError: If the file cannot be read.
    """
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    sha256 = hashlib.sha256()
    file_size = filepath.stat().st_size

    logger.debug("Computing SHA256 for %s (%.1f MB)", filepath.name, file_size / 1024 / 1024)

    with open(filepath, "rb") as f:
        while chunk := f.read(CHUNK_SIZE):
            sha256.update(chunk)

    digest = sha256.hexdigest()
    logger.debug("SHA256 for %s: %s", filepath.name, digest)
    return digest


def is_duplicate(
    sha256: str,
    filename: str,
    drive_file_id: str | None,
    db_session,
) -> bool:
    """
    Check if a video has already been uploaded using multiple signals.

    Checks:
        1. SHA256 hash
        2. Filename
        3. Drive File ID

    Args:
        sha256: SHA256 hash of the video file.
        filename: Original filename.
        drive_file_id: Google Drive file ID (optional).
        db_session: Active SQLAlchemy session.

    Returns:
        True if this content has already been uploaded.
    """
    from app.models.upload import Upload

    # Check by SHA256 (most reliable)
    existing = db_session.query(Upload).filter(Upload.sha256 == sha256).first()
    if existing:
        logger.warning(
            "Duplicate detected by SHA256! filename=%s matches existing id=%d (%s)",
            filename,
            existing.id,
            existing.filename,
        )
        return True

    # Check by Drive File ID
    if drive_file_id:
        existing = db_session.query(Upload).filter(Upload.drive_file_id == drive_file_id).first()
        if existing:
            logger.warning(
                "Duplicate detected by Drive File ID! drive_id=%s matches existing id=%d",
                drive_file_id,
                existing.id,
            )
            return True

    # Check by filename (weakest signal — filenames can be reused, but worth flagging)
    from app.config.constants import UploadStage
    existing = (
        db_session.query(Upload)
        .filter(Upload.filename == filename, Upload.status == UploadStage.COMPLETED)
        .first()
    )
    if existing:
        logger.warning(
            "Duplicate detected by filename! filename=%s matches completed upload id=%d",
            filename,
            existing.id,
        )
        return True

    return False
