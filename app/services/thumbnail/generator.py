"""
TheMemeCanvas Automation Suite — Automatic Thumbnail Generator
==============================================================
Generates branded thumbnail images using Pillow + FFmpeg.

Strategy:
    1. If matching thumbnail file exists (e.g., video001.jpg) → use it
    2. Extract frame from video using FFmpeg → overlay branding
    3. If FFmpeg fails → use branded default thumbnail
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

from app.config.constants import (
    BRAND_NAME,
    THUMBNAIL_BRAND_FONT_SIZE,
    THUMBNAIL_FONT_SIZE,
    THUMBNAIL_HEIGHT,
    THUMBNAIL_WIDTH,
)
from app.config.settings import settings

logger = logging.getLogger("thememecanvas.pipeline")

THUMBNAIL_DIR = Path("temp_thumbnails")


class ThumbnailGenerator:
    """
    Generates YouTube thumbnail images with branding overlays.

    Output: 1280x720 JPEG (YouTube recommended size)
    """

    def __init__(self) -> None:
        THUMBNAIL_DIR.mkdir(parents=True, exist_ok=True)

    def get_thumbnail(
        self,
        video_path: Path,
        video_filename: str,
        provided_thumbnail: Optional[Path] = None,
    ) -> Path:
        """
        Get or generate a thumbnail for the given video.

        Priority:
            1. Use provided thumbnail (already downloaded from Drive)
            2. Extract frame from video + add branding
            3. Use default branded thumbnail

        Args:
            video_path: Path to the downloaded video file.
            video_filename: Original filename (for output naming).
            provided_thumbnail: Pre-downloaded thumbnail if available.

        Returns:
            Path to the final thumbnail JPEG file.
        """
        stem = Path(video_filename).stem

        # 1. Use provided thumbnail
        if provided_thumbnail and provided_thumbnail.exists():
            output_path = THUMBNAIL_DIR / f"{stem}_thumb.jpg"
            branded = self._add_branding(provided_thumbnail, output_path)
            if branded:
                return branded

        # 2. Extract frame from video
        extracted = self._extract_frame(video_path, stem)
        if extracted:
            output_path = THUMBNAIL_DIR / f"{stem}_thumb.jpg"
            branded = self._add_branding(extracted, output_path)
            if branded:
                extracted.unlink(missing_ok=True)  # Clean up raw frame
                return branded

        # 3. Fallback to default branded thumbnail
        logger.warning("Using default thumbnail for %s", video_filename)
        return self._get_default_thumbnail()

    def _extract_frame(self, video_path: Path, stem: str) -> Optional[Path]:
        """
        Extract a frame from the video at 1 second using FFmpeg.

        Args:
            video_path: Path to video file.
            stem: Base name for output file.

        Returns:
            Path to extracted frame PNG, or None if FFmpeg fails.
        """
        output_path = THUMBNAIL_DIR / f"{stem}_frame.png"

        try:
            result = subprocess.run(
                [
                    "ffmpeg",
                    "-y",  # Overwrite
                    "-i", str(video_path),
                    "-ss", "00:00:01",  # 1 second in
                    "-vframes", "1",
                    "-vf", f"scale={THUMBNAIL_WIDTH}:{THUMBNAIL_HEIGHT}:force_original_aspect_ratio=increase,crop={THUMBNAIL_WIDTH}:{THUMBNAIL_HEIGHT}",
                    "-q:v", "2",
                    str(output_path),
                ],
                capture_output=True,
                timeout=30,
                check=True,
            )

            if output_path.exists():
                logger.debug("Extracted frame: %s", output_path)
                return output_path

        except subprocess.CalledProcessError as e:
            logger.warning("FFmpeg frame extraction failed: %s", e.stderr.decode()[:500])
        except FileNotFoundError:
            logger.warning("FFmpeg not found. Install FFmpeg for auto-thumbnail generation.")
        except subprocess.TimeoutExpired:
            logger.warning("FFmpeg timeout during frame extraction.")

        return None

    def _add_branding(self, source_path: Path, output_path: Path) -> Optional[Path]:
        """
        Add TheMemeCanvas branding overlay to an image.

        Branding elements:
            - Semi-transparent gradient bar at bottom
            - Brand name text
            - Optional emoji decoration

        Args:
            source_path: Input image path.
            output_path: Where to save the branded image.

        Returns:
            Path to branded image, or None if processing fails.
        """
        try:
            img = Image.open(source_path).convert("RGB")
            img = img.resize((THUMBNAIL_WIDTH, THUMBNAIL_HEIGHT), Image.LANCZOS)

            draw = ImageDraw.Draw(img, "RGBA")

            # --- Gradient overlay at bottom ---
            overlay_height = 120
            for i in range(overlay_height):
                alpha = int(180 * (i / overlay_height))
                draw.rectangle(
                    [0, THUMBNAIL_HEIGHT - overlay_height + i, THUMBNAIL_WIDTH, THUMBNAIL_HEIGHT - overlay_height + i + 1],
                    fill=(0, 0, 0, alpha),
                )

            # --- Brand text ---
            try:
                # Try to load a nice font (will use default if not found)
                font_path = Path("assets/fonts/Inter-Bold.ttf")
                if font_path.exists():
                    font = ImageFont.truetype(str(font_path), THUMBNAIL_BRAND_FONT_SIZE)
                else:
                    font = ImageFont.load_default()
            except Exception:
                font = ImageFont.load_default()

            brand_text = f"🎭 {BRAND_NAME}"
            text_x = 20
            text_y = THUMBNAIL_HEIGHT - 60

            # Drop shadow
            draw.text((text_x + 2, text_y + 2), brand_text, fill=(0, 0, 0, 180), font=font)
            # Main text
            draw.text((text_x, text_y), brand_text, fill=(255, 255, 255, 255), font=font)

            # Save
            img.save(str(output_path), "JPEG", quality=95)
            logger.debug("Branded thumbnail saved: %s", output_path)
            return output_path

        except Exception as e:
            logger.warning("Failed to add branding to thumbnail: %s", e)
            return None

    def _get_default_thumbnail(self) -> Path:
        """
        Return the default branded thumbnail.
        Creates it if it doesn't exist.
        """
        from app.services.thumbnail.default import create_default_thumbnail

        default_path = settings.default_thumbnail_path
        if not default_path.exists():
            default_path = create_default_thumbnail()

        return default_path

    def cleanup(self, thumbnail_path: Path) -> None:
        """Delete a generated thumbnail after upload."""
        if thumbnail_path and thumbnail_path.exists():
            if THUMBNAIL_DIR in thumbnail_path.parents:
                thumbnail_path.unlink(missing_ok=True)
                logger.debug("Deleted temp thumbnail: %s", thumbnail_path)
