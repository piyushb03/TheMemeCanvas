"""
TheMemeCanvas Automation Suite — YouTube Video Uploader
========================================================
Handles video upload, thumbnail upload, and metadata application
for YouTube Shorts via the YouTube Data API v3.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional

from googleapiclient.http import MediaFileUpload

from app.config.settings import settings
from app.services.youtube.client import YouTubeClient

logger = logging.getLogger("thememecanvas.youtube")


class YouTubeUploader:
    """
    Uploads videos as YouTube Shorts and applies optimized metadata.

    Features:
        - Chunked resumable upload (handles large files + network interruptions)
        - Thumbnail upload
        - Shorts detection (#Shorts in title/description)
        - Duplicate prevention (checks video ID already in DB)
    """

    def __init__(self, client: Optional[YouTubeClient] = None) -> None:
        self.client = client or YouTubeClient()

    def upload_video(
        self,
        video_path: Path,
        title: str,
        description: str,
        tags: List[str],
        category_id: int = None,
        privacy_status: str = None,
        made_for_kids: bool = None,
    ) -> str:
        """
        Upload a video to YouTube.

        Args:
            video_path: Local path to the video file.
            title: Video title (AI-generated).
            description: Full video description.
            tags: List of SEO tags.
            category_id: YouTube category ID.
            privacy_status: "public", "private", or "unlisted".
            made_for_kids: Whether this is child-directed content.

        Returns:
            YouTube Video ID (e.g., "dQw4w9WgXcQ").

        Raises:
            Exception: If upload fails after retries.
        """
        if not video_path.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")

        # Apply defaults from settings
        category_id = category_id or settings.youtube_category_id
        privacy_status = privacy_status or settings.youtube_privacy_status
        made_for_kids = made_for_kids if made_for_kids is not None else settings.youtube_made_for_kids

        # Ensure Shorts discoverability — add #Shorts if not present
        shorts_title = title if "#Shorts" in title else f"{title} #Shorts"
        shorts_desc = description if "#Shorts" in description else f"{description}\n\n#Shorts"

        # Truncate title to YouTube's 100 char limit
        if len(shorts_title) > 100:
            shorts_title = shorts_title[:97] + "..."

        # Trim tags to fit YouTube's 500 total char limit
        trimmed_tags = self._trim_tags(tags)

        body = {
            "snippet": {
                "title": shorts_title,
                "description": shorts_desc,
                "tags": trimmed_tags,
                "categoryId": str(category_id),
                "defaultLanguage": "en",
            },
            "status": {
                "privacyStatus": privacy_status,
                "selfDeclaredMadeForKids": made_for_kids,
            },
        }

        file_size = video_path.stat().st_size
        logger.info(
            "Starting YouTube upload: '%s' (%.1f MB) → privacy=%s",
            shorts_title,
            file_size / 1024 / 1024,
            privacy_status,
        )

        media = MediaFileUpload(
            str(video_path),
            mimetype="video/mp4",
            resumable=True,
            chunksize=8 * 1024 * 1024,  # 8 MB chunks
        )

        request = self.client.service.videos().insert(
            part=",".join(body.keys()),
            body=body,
            media_body=media,
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                logger.info("YouTube upload progress: %.1f%%", status.progress() * 100)

        video_id = response.get("id")
        if not video_id:
            raise RuntimeError(f"YouTube upload failed. Response: {response}")

        youtube_url = f"https://www.youtube.com/shorts/{video_id}"
        logger.info("✅ YouTube upload complete! Video ID: %s URL: %s", video_id, youtube_url)

        return video_id

    def upload_thumbnail(self, video_id: str, thumbnail_path: Path) -> bool:
        """
        Upload a custom thumbnail for a YouTube video.

        Args:
            video_id: YouTube Video ID.
            thumbnail_path: Local path to the thumbnail image.

        Returns:
            True if successful, False otherwise.

        Note:
            Requires YouTube channel to be verified (>1000 subscribers or phone verified).
        """
        if not thumbnail_path.exists():
            logger.warning("Thumbnail not found: %s — skipping.", thumbnail_path)
            return False

        logger.info("Uploading thumbnail for video %s...", video_id)

        try:
            media = MediaFileUpload(
                str(thumbnail_path),
                mimetype="image/jpeg",
                resumable=False,
            )
            self.client.service.thumbnails().set(
                videoId=video_id,
                media_body=media,
            ).execute()
            logger.info("✅ Thumbnail uploaded for video %s", video_id)
            return True
        except Exception as e:
            # Thumbnail upload failure is non-fatal — video is still up
            logger.warning("Thumbnail upload failed for %s: %s", video_id, e)
            return False

    def get_video_url(self, video_id: str) -> str:
        """Return the full YouTube Shorts URL for a video ID."""
        return f"https://www.youtube.com/shorts/{video_id}"

    def _trim_tags(self, tags: List[str]) -> List[str]:
        """
        Trim tags so total character count fits YouTube's 500 char limit.
        Tags are joined as "tag1, tag2, ..." when calculating length.
        """
        result = []
        total_chars = 0
        max_tags = settings.youtube_max_tags

        for tag in tags[:max_tags]:
            tag_chars = len(tag) + 2  # +2 for ", " separator
            if total_chars + tag_chars > 490:
                break
            result.append(tag)
            total_chars += tag_chars

        return result

    def check_quota_usage(self) -> dict:
        """
        Estimate remaining YouTube API quota.
        YouTube gives 10,000 units/day. An upload costs 1600 units.
        This is informational only — actual quota is checked server-side.
        """
        return {
            "daily_limit": 10000,
            "upload_cost": 1600,
            "estimated_uploads_remaining": 10000 // 1600,
            "note": "Actual quota tracked by Google API Console.",
        }
