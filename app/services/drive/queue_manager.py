"""
TheMemeCanvas Automation Suite — Google Drive Queue Manager
============================================================
Handles reading the upload queue, downloading files, and moving
processed files to the Uploaded or Failed folders.
"""

from __future__ import annotations

import io
import logging
import random
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from googleapiclient.http import MediaIoBaseDownload

from app.config.constants import SUPPORTED_IMAGE_EXTENSIONS, SUPPORTED_VIDEO_EXTENSIONS
from app.config.settings import settings
from app.services.drive.client import DriveClient

logger = logging.getLogger("thememecanvas.drive")

VIDEO_MIME_TYPES = [
    "video/mp4",
    "video/quicktime",
    "video/x-msvideo",
    "video/x-matroska",
    "video/webm",
]


class QueueManager:
    """
    Manages the Google Drive video queue.

    Responsibilities:
        - List videos in the queue folder
        - Respect ordering (oldest_first, newest_first, random)
        - Download videos to local temp directory
        - Look for matching thumbnail files
        - Move processed files to Uploaded or Failed folders
    """

    def __init__(self, client: Optional[DriveClient] = None) -> None:
        self.client = client or DriveClient()
        self.temp_dir = settings.temp_download_dir
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def get_queue(self, db_session) -> List[Dict]:
        """
        Return list of unprocessed video files from Drive, ordered by settings.

        Filters out any files already in the database (by Drive File ID).

        Args:
            db_session: Active SQLAlchemy session for duplicate checks.

        Returns:
            Ordered list of Drive file metadata dicts.
        """
        from app.models.queue_item import QueueItem

        # Fetch all video files from Drive
        all_files = self.client.list_files(
            folder_id=settings.drive_queue_folder_id,
            mime_types=VIDEO_MIME_TYPES,
        )

        # Also check by file extension for edge cases
        all_files_by_ext = self.client.list_files(
            folder_id=settings.drive_queue_folder_id,
        )
        ext_videos = [
            f for f in all_files_by_ext
            if Path(f["name"]).suffix.lower() in SUPPORTED_VIDEO_EXTENSIONS
            and f not in all_files
        ]
        all_files.extend(ext_videos)

        # Deduplicate
        seen_ids = set()
        unique_files = []
        for f in all_files:
            if f["id"] not in seen_ids:
                seen_ids.add(f["id"])
                unique_files.append(f)

        # Filter out already-processed files
        processed_ids = {
            item.drive_file_id
            for item in db_session.query(QueueItem).filter(QueueItem.is_processed == True).all()
        }
        from app.models.upload import Upload
        uploaded_ids = {
            u.drive_file_id
            for u in db_session.query(Upload).filter(Upload.drive_file_id.isnot(None)).all()
        }
        skip_ids = processed_ids | uploaded_ids

        queue = [f for f in unique_files if f["id"] not in skip_ids]

        # Apply ordering
        queue = self._apply_ordering(queue)

        logger.info(
            "Drive queue: %d total videos, %d unprocessed.",
            len(unique_files),
            len(queue),
        )
        return queue

    def _apply_ordering(self, files: List[Dict]) -> List[Dict]:
        """Sort files according to configured upload order."""
        order = settings.upload_order

        if order == "oldest_first":
            return sorted(files, key=lambda f: f.get("createdTime", ""))
        elif order == "newest_first":
            return sorted(files, key=lambda f: f.get("createdTime", ""), reverse=True)
        elif order == "random":
            shuffled = files.copy()
            random.shuffle(shuffled)
            return shuffled
        else:
            logger.warning("Unknown upload_order '%s', defaulting to oldest_first.", order)
            return sorted(files, key=lambda f: f.get("createdTime", ""))

    def get_next_video(self, db_session) -> Optional[Dict]:
        """
        Return the next video to process from the queue.

        Returns:
            Drive file metadata dict, or None if queue is empty.
        """
        queue = self.get_queue(db_session)
        if not queue:
            logger.info("Queue is empty. No video to process.")
            return None
        return queue[0]

    def queue_size(self, db_session) -> int:
        """Return the number of videos remaining in the queue."""
        return len(self.get_queue(db_session))

    def find_thumbnail(self, video_filename: str, folder_id: str) -> Optional[Dict]:
        """
        Look for a matching thumbnail file in the same folder.

        Matching strategy:
            - Same stem name, different image extension
            - E.g., video001.mp4 → video001.jpg

        Returns:
            Drive file metadata for thumbnail, or None.
        """
        stem = Path(video_filename).stem

        all_files = self.client.list_files(folder_id=folder_id)

        for f in all_files:
            file_stem = Path(f["name"]).stem
            ext = Path(f["name"]).suffix.lower()

            if file_stem == stem and ext in SUPPORTED_IMAGE_EXTENSIONS:
                logger.info("Found matching thumbnail: %s", f["name"])
                return f

        return None

    def download_file(self, file_id: str, filename: str) -> Path:
        """
        Download a file from Google Drive to the local temp directory.

        Args:
            file_id: Google Drive file ID.
            filename: Local filename to save as.

        Returns:
            Path to the downloaded file.

        Raises:
            IOError: If download fails.
        """
        dest_path = self.temp_dir / filename

        logger.info("Downloading %s from Drive...", filename)

        request = self.client.service.files().get_media(fileId=file_id)
        fh = io.FileIO(str(dest_path), "wb")
        downloader = MediaIoBaseDownload(fh, request, chunksize=8 * 1024 * 1024)

        done = False
        while not done:
            status, done = downloader.next_chunk()
            if status:
                logger.debug("Download progress: %.1f%%", status.progress() * 100)

        fh.close()

        file_size = dest_path.stat().st_size
        logger.info(
            "Downloaded %s (%.1f MB) to %s",
            filename,
            file_size / 1024 / 1024,
            dest_path,
        )

        return dest_path

    def move_to_uploaded(self, file_id: str) -> None:
        """Move a successfully uploaded file to the Uploaded folder."""
        logger.info("Moving file %s to Uploaded folder...", file_id)
        self.client.move_file(file_id, settings.drive_uploaded_folder_id)

    def move_to_failed(self, file_id: str) -> None:
        """Move a permanently failed file to the Failed folder."""
        logger.info("Moving file %s to Failed folder...", file_id)
        self.client.move_file(file_id, settings.drive_failed_folder_id)

    def cleanup_temp_file(self, filepath: Path) -> None:
        """Delete a temporary downloaded file to free disk space."""
        if filepath and filepath.exists():
            filepath.unlink()
            logger.debug("Deleted temp file: %s", filepath)

    def sync_queue_to_db(self, db_session) -> Tuple[int, int]:
        """
        Sync the Drive queue folder to the local database.
        Adds newly discovered files; marks missing ones as processed.

        Returns:
            Tuple of (new_items_added, total_in_db).
        """
        from app.models.queue_item import QueueItem

        # Get all files (videos and images) in a single API call
        all_folder_files = self.client.list_files(
            folder_id=settings.drive_queue_folder_id,
        )

        drive_videos = []
        thumbnail_by_stem = {}

        # Categorize files and build thumbnail map
        for f in all_folder_files:
            name = f["name"]
            suffix = Path(name).suffix.lower()
            mime = f.get("mimeType", "")
            
            is_video = (mime in VIDEO_MIME_TYPES) or (suffix in SUPPORTED_VIDEO_EXTENSIONS)
            if is_video:
                drive_videos.append(f)
            elif suffix in SUPPORTED_IMAGE_EXTENSIONS:
                stem = Path(name).stem
                thumbnail_by_stem[stem] = f

        drive_ids = {f["id"] for f in drive_videos}
        new_count = 0

        # Query all existing drive_file_ids from the database in a single query
        existing_ids = {
            r[0] for r in db_session.query(QueueItem.drive_file_id).all()
        }

        # Only add new ones
        for f in drive_videos:
            if f["id"] not in existing_ids:
                stem = Path(f["name"]).stem
                thumbnail = thumbnail_by_stem.get(stem)
                
                item = QueueItem(
                    drive_file_id=f["id"],
                    filename=f["name"],
                    file_size_bytes=int(f.get("size", 0)) if f.get("size") else None,
                    drive_created_time=datetime.fromisoformat(
                        f["createdTime"].replace("Z", "+00:00")
                    ) if f.get("createdTime") else None,
                    drive_modified_time=datetime.fromisoformat(
                        f["modifiedTime"].replace("Z", "+00:00")
                    ) if f.get("modifiedTime") else None,
                    mime_type=f.get("mimeType"),
                    has_thumbnail=thumbnail is not None,
                    thumbnail_drive_file_id=thumbnail["id"] if thumbnail else None,
                )
                db_session.add(item)
                new_count += 1
                logger.debug("Added to queue DB: %s", f["name"])

        db_session.commit()
        total = db_session.query(QueueItem).count()
        logger.info("Queue sync: +%d new items. Total in DB: %d", new_count, total)
        return new_count, total


