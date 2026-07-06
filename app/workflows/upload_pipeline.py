"""
TheMemeCanvas Automation Suite — Full Upload Pipeline Orchestrator
=================================================================
This is the heart of the application. Orchestrates the complete
workflow from Drive queue → YouTube + Instagram → notification.

Pipeline stages:
    1. Pick next video from Drive queue
    2. Duplicate check (SHA256, filename, Drive ID)
    3. Download video to temp
    4. Generate AI metadata (title, description, tags, captions)
    5. Generate or fetch thumbnail
    6. Upload to YouTube Shorts
    7. Upload thumbnail to YouTube
    8. Upload to Instagram Reels (using YouTube URL as video source)
    9. Move file to Uploaded folder in Drive
    10. Save record to database
    11. Cleanup temp files
    12. Send success notification
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.config.constants import UploadStage
from app.config.settings import settings
from app.database.base import db_session as get_db_session
from app.models.upload import Upload
from app.services.ai.metadata_gen import MetadataGenerator
from app.services.drive.client import DriveClient
from app.services.drive.queue_manager import QueueManager
from app.services.notifications.dispatcher import NotificationDispatcher
from app.services.thumbnail.generator import ThumbnailGenerator
from app.services.youtube.uploader import YouTubeUploader
from app.utils.hashing import compute_sha256, is_duplicate

logger = logging.getLogger("thememecanvas.pipeline")


class UploadPipeline:
    """
    Orchestrates the complete video upload workflow.

    Designed for reliability:
        - Each stage is isolated and logged
        - Failures at any stage are caught and handled
        - Partial failures are recorded
        - Retry count and error logs are maintained in the database
    """

    def __init__(self) -> None:
        self.drive_client = DriveClient()
        self.queue_manager = QueueManager(self.drive_client)
        self.youtube_uploader = YouTubeUploader()
        self.thumbnail_generator = ThumbnailGenerator()
        self.metadata_gen = MetadataGenerator()
        self.notifier = NotificationDispatcher()

    def run(self, force_file_id: Optional[str] = None) -> bool:
        """
        Execute one complete upload cycle.

        Args:
            force_file_id: If provided, upload this specific Drive file ID
                           instead of picking the next from the queue.

        Returns:
            True if the upload completed successfully, False otherwise.
        """
        logger.info("=" * 60)
        logger.info("TheMemeCanvas Upload Pipeline — Starting")
        logger.info("=" * 60)

        with get_db_session() as db:
            # --- STAGE 1: Pick video ---
            drive_file = self._pick_next_video(db, force_file_id)
            if not drive_file:
                self._handle_empty_queue(db)
                return False

            filename = drive_file["name"]
            file_id = drive_file["id"]
            logger.info("Processing video: %s (Drive ID: %s)", filename, file_id)

            # Create upload record
            upload = Upload(
                filename=filename,
                sha256="pending",
                drive_file_id=file_id,
                status=UploadStage.PENDING,
                started_at=datetime.utcnow(),
            )
            db.add(upload)
            db.commit()
            db.refresh(upload)

            # Notify upload starting
            self.notifier.notify_upload_started(filename, db_session=db)

            temp_video: Optional[Path] = None
            temp_thumbnail: Optional[Path] = None

            try:
                # --- STAGE 2: Download ---
                temp_video = self._download_video(upload, file_id, filename, db)

                # --- STAGE 3: Duplicate check ---
                if not self._check_duplicate(upload, temp_video, filename, file_id, db):
                    return False

                # --- STAGE 4: Generate AI metadata ---
                metadata = self._generate_metadata(upload, filename, db)

                # --- STAGE 5: Fetch/generate thumbnail ---
                temp_thumbnail = self._get_thumbnail(
                    upload, temp_video, filename, drive_file, db
                )

                # --- STAGE 6: Upload to YouTube ---
                youtube_id = self._upload_to_youtube(upload, temp_video, metadata, db)

                # --- STAGE 7: Upload thumbnail ---
                if youtube_id and temp_thumbnail:
                    self._upload_thumbnail(upload, youtube_id, temp_thumbnail, db)

                # --- STAGE 8: Move file in Drive ---
                self._move_to_uploaded(upload, file_id, db)

                # --- STAGE 9: Mark complete ---
                upload.status = UploadStage.COMPLETED
                upload.completed_at = datetime.utcnow()
                
                from app.models.queue_item import QueueItem
                q_item = db.query(QueueItem).filter(QueueItem.drive_file_id == file_id).first()
                if q_item:
                    q_item.is_processed = True
                    q_item.processed_at = datetime.utcnow()
                    q_item.upload_id = upload.id
                
                db.commit()

                # --- STAGE 10: Cleanup ---
                self._cleanup(temp_video, temp_thumbnail)

                # --- STAGE 11: Notify success ---
                queue_remaining = self.queue_manager.queue_size(db)
                days_remaining = queue_remaining  # 1 video per day

                self.notifier.notify_upload_success(
                    filename=filename,
                    title=metadata.title,
                    youtube_url=upload.youtube_url or f"https://youtube.com/shorts/{youtube_id}",
                    queue_remaining=queue_remaining,
                    days_remaining=days_remaining,
                    upload_id=upload.id,
                    db_session=db,
                )

                logger.info("✅ Pipeline complete for: %s", filename)
                return True

            except Exception as exc:
                logger.error("Pipeline failed for %s: %s", filename, exc, exc_info=True)

                upload.status = UploadStage.FAILED
                upload.add_error(upload.current_stage or "unknown", str(exc))
                upload.retry_count = (upload.retry_count or 0) + 1
                db.commit()

                # Move to failed folder in Drive and mark processed
                try:
                    self.queue_manager.move_to_failed(file_id)
                    upload.moved_to_failed = True
                    
                    from app.models.queue_item import QueueItem
                    q_item = db.query(QueueItem).filter(QueueItem.drive_file_id == file_id).first()
                    if q_item:
                        q_item.is_processed = True
                        q_item.processed_at = datetime.utcnow()
                        q_item.upload_id = upload.id
                    
                    db.commit()
                except Exception as move_exc:
                    logger.error("Failed to move file to Failed folder: %s", move_exc)

                # Cleanup temp files even on failure
                self._cleanup(temp_video, temp_thumbnail)

                # Notify failure
                delays = settings.retry_delays
                next_retry = delays[min(upload.retry_count - 1, len(delays) - 1)] if delays else 60
                self.notifier.notify_upload_failed(
                    filename=filename,
                    error=str(exc),
                    retry_count=upload.retry_count,
                    next_retry_mins=next_retry,
                    upload_id=upload.id,
                    db_session=db,
                )

                return False

    # ---------------------------------------------------------------------------
    # Stage Implementations
    # ---------------------------------------------------------------------------

    def _pick_next_video(self, db, force_file_id: Optional[str]) -> Optional[dict]:
        """Pick the next video from Drive queue."""
        if settings.uploads_paused:
            logger.info("Uploads are paused. Skipping.")
            return None

        if force_file_id:
            logger.info("Forced file ID: %s", force_file_id)
            try:
                return self.drive_client.get_file_metadata(force_file_id)
            except Exception as e:
                logger.error("Failed to get forced file: %s", e)
                return None

        return self.queue_manager.get_next_video(db)

    def _download_video(self, upload: Upload, file_id: str, filename: str, db) -> Path:
        """Stage: Download video from Drive."""
        upload.current_stage = UploadStage.DOWNLOADING
        upload.status = UploadStage.DOWNLOADING
        db.commit()

        temp_path = self.queue_manager.download_file(file_id, filename)
        upload.file_size_bytes = temp_path.stat().st_size
        db.commit()

        return temp_path

    def _check_duplicate(
        self, upload: Upload, temp_video: Path, filename: str, file_id: str, db
    ) -> bool:
        """Stage: Compute SHA256 and check for duplicates."""
        sha256 = compute_sha256(temp_video)
        upload.sha256 = sha256
        db.commit()

        if is_duplicate(sha256, filename, file_id, db):
            logger.warning("Duplicate content detected — skipping upload.")
            upload.status = UploadStage.SKIPPED
            db.commit()
            self.queue_manager.move_to_uploaded(file_id)
            
            from app.models.queue_item import QueueItem
            q_item = db.query(QueueItem).filter(QueueItem.drive_file_id == file_id).first()
            if q_item:
                q_item.is_processed = True
                q_item.processed_at = datetime.utcnow()
                q_item.upload_id = upload.id
                db.commit()
            return False

        return True

    def _generate_metadata(self, upload: Upload, filename: str, db):
        """Stage: Generate AI metadata."""
        upload.current_stage = UploadStage.GENERATING_METADATA
        upload.status = UploadStage.GENERATING_METADATA
        db.commit()

        # Get recent titles for repetition avoidance
        from app.models.upload import Upload as UploadModel
        recent = (
            db.query(UploadModel.title)
            .filter(UploadModel.title.isnot(None))
            .order_by(UploadModel.created_at.desc())
            .limit(20)
            .all()
        )
        recent_titles = [r.title for r in recent if r.title]

        metadata = self.metadata_gen.generate(filename, recent_titles)

        # Persist metadata
        upload.title = metadata.title
        upload.description = metadata.description
        upload.ai_opening = metadata.ai_opening
        upload.caption = metadata.caption
        upload.tags = metadata.tags
        upload.hashtags = metadata.hashtags
        db.commit()

        return metadata

    def _get_thumbnail(
        self, upload: Upload, temp_video: Path, filename: str, drive_file: dict, db
    ) -> Optional[Path]:
        """Stage: Fetch or generate thumbnail."""
        provided_thumb = None

        # Download thumbnail from Drive if available
        if drive_file.get("_thumbnail_id"):
            thumb_id = drive_file["_thumbnail_id"]
            thumb_filename = f"{Path(filename).stem}_thumb.jpg"
            try:
                provided_thumb = self.queue_manager.download_file(thumb_id, thumb_filename)
            except Exception as e:
                logger.warning("Thumbnail download failed: %s", e)

        # Generate thumbnail
        thumbnail_path = self.thumbnail_generator.get_thumbnail(
            video_path=temp_video,
            video_filename=filename,
            provided_thumbnail=provided_thumb,
        )

        upload.thumbnail_path = str(thumbnail_path) if thumbnail_path else None
        db.commit()

        # Cleanup provided thumb if it was temporary
        if provided_thumb and provided_thumb.exists() and provided_thumb != thumbnail_path:
            provided_thumb.unlink(missing_ok=True)

        return thumbnail_path

    def _upload_to_youtube(self, upload: Upload, temp_video: Path, metadata, db) -> Optional[str]:
        """Stage: Upload video to YouTube Shorts."""
        upload.current_stage = UploadStage.UPLOADING_YOUTUBE
        upload.status = UploadStage.UPLOADING_YOUTUBE
        db.commit()

        try:
            youtube_id = self.youtube_uploader.upload_video(
                video_path=temp_video,
                title=metadata.title,
                description=metadata.description,
                tags=metadata.tags,
            )

            upload.youtube_video_id = youtube_id
            upload.youtube_url = self.youtube_uploader.get_video_url(youtube_id)
            upload.youtube_status = "uploaded"
            db.commit()

            logger.info("YouTube upload successful: %s", youtube_id)
            return youtube_id

        except Exception as e:
            upload.youtube_status = "failed"
            upload.add_error(UploadStage.UPLOADING_YOUTUBE, str(e))
            db.commit()
            logger.error("YouTube upload failed: %s", e)
            raise  # Re-raise to trigger pipeline failure handling

    def _upload_thumbnail(
        self, upload: Upload, youtube_id: str, thumbnail_path: Path, db
    ) -> None:
        """Stage: Upload thumbnail to YouTube."""
        upload.current_stage = UploadStage.UPLOADING_THUMBNAIL
        db.commit()

        success = self.youtube_uploader.upload_thumbnail(youtube_id, thumbnail_path)
        upload.thumbnail_uploaded = success
        db.commit()



    def _move_to_uploaded(self, upload: Upload, file_id: str, db) -> None:
        """Stage: Move Drive file to Uploaded folder."""
        upload.current_stage = UploadStage.MOVING_FILE
        db.commit()

        try:
            self.queue_manager.move_to_uploaded(file_id)
            upload.moved_to_uploaded = True
            db.commit()
        except Exception as e:
            logger.warning("Failed to move file to Uploaded folder: %s", e)
            upload.add_error(UploadStage.MOVING_FILE, str(e))
            db.commit()

    def _cleanup(
        self, temp_video: Optional[Path], temp_thumbnail: Optional[Path]
    ) -> None:
        """Clean up all temporary files."""
        if temp_video:
            self.queue_manager.cleanup_temp_file(temp_video)
        if temp_thumbnail:
            self.thumbnail_generator.cleanup(temp_thumbnail)

    def _handle_empty_queue(self, db) -> None:
        """Handle the case when the queue is empty."""
        from app.models.upload import Upload as UploadModel
        total_uploaded = (
            db.query(UploadModel)
            .filter(UploadModel.status == UploadStage.COMPLETED)
            .count()
        )
        logger.info("Queue empty. Total uploaded: %d", total_uploaded)
        self.notifier.notify_queue_empty(total_uploaded, db_session=db)
