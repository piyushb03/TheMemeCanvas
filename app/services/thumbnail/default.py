"""
TheMemeCanvas Automation Suite — Default Branded Thumbnail Creator
==================================================================
Creates a high-quality branded default thumbnail using Pillow.
This is used when no video-specific thumbnail can be generated.
"""

from __future__ import annotations

import logging
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from app.config.constants import (
    BRAND_NAME,
    THUMBNAIL_HEIGHT,
    THUMBNAIL_WIDTH,
)

logger = logging.getLogger("thememecanvas.pipeline")

ASSETS_DIR = Path("assets")


def create_default_thumbnail() -> Path:
    """
    Create and save the default branded thumbnail.

    Design:
        - Dark gradient background (brand colors: deep purple → dark blue)
        - Large brand emoji
        - Brand name in white
        - Tagline

    Returns:
        Path to the created default thumbnail.
    """
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = ASSETS_DIR / "default_thumbnail.jpg"

    # Canvas
    img = Image.new("RGB", (THUMBNAIL_WIDTH, THUMBNAIL_HEIGHT), color=(15, 10, 30))
    draw = ImageDraw.Draw(img)

    # --- Background gradient (dark purple → dark navy) ---
    for y in range(THUMBNAIL_HEIGHT):
        r = int(15 + (10 * y / THUMBNAIL_HEIGHT))
        g = int(10 + (5 * y / THUMBNAIL_HEIGHT))
        b = int(30 + (40 * y / THUMBNAIL_HEIGHT))
        draw.line([(0, y), (THUMBNAIL_WIDTH, y)], fill=(r, g, b))

    # --- Decorative circles ---
    for pos, radius, color in [
        ((200, 200), 180, (80, 40, 120, 40)),
        ((1100, 500), 220, (40, 80, 140, 40)),
        ((640, 360), 300, (60, 20, 90, 20)),
    ]:
        circle_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        circle_draw = ImageDraw.Draw(circle_layer)
        x, y = pos
        circle_draw.ellipse(
            [x - radius, y - radius, x + radius, y + radius],
            fill=color,
        )
        img = Image.alpha_composite(img.convert("RGBA"), circle_layer).convert("RGB")
        draw = ImageDraw.Draw(img)

    # --- Load fonts ---
    try:
        font_path = ASSETS_DIR / "fonts" / "Inter-Bold.ttf"
        if font_path.exists():
            emoji_font = ImageFont.truetype(str(font_path), 120)
            title_font = ImageFont.truetype(str(font_path), 80)
            tagline_font = ImageFont.truetype(str(font_path), 36)
        else:
            emoji_font = ImageFont.load_default()
            title_font = ImageFont.load_default()
            tagline_font = ImageFont.load_default()
    except Exception:
        emoji_font = ImageFont.load_default()
        title_font = ImageFont.load_default()
        tagline_font = ImageFont.load_default()

    # --- Emoji ---
    emoji = "🎭"
    try:
        # Emoji in center-top area
        emoji_bbox = draw.textbbox((0, 0), emoji, font=emoji_font)
        emoji_w = emoji_bbox[2] - emoji_bbox[0]
        draw.text(
            ((THUMBNAIL_WIDTH - emoji_w) // 2, 120),
            emoji,
            font=emoji_font,
            fill=(255, 255, 255),
        )
    except Exception:
        pass

    # --- Brand Name ---
    brand_text = BRAND_NAME
    try:
        bbox = draw.textbbox((0, 0), brand_text, font=title_font)
        text_w = bbox[2] - bbox[0]
        x = (THUMBNAIL_WIDTH - text_w) // 2
        y = 310

        # Glow effect
        for offset in [(3, 3), (-3, -3), (3, -3), (-3, 3)]:
            draw.text((x + offset[0], y + offset[1]), brand_text, font=title_font, fill=(120, 60, 200, 180))
        # Main text
        draw.text((x, y), brand_text, font=title_font, fill=(255, 255, 255))
    except Exception:
        draw.text((100, 300), brand_text, font=title_font, fill=(255, 255, 255))

    # --- Tagline ---
    tagline = "Your Daily Dose of Memes 🔥"
    try:
        bbox = draw.textbbox((0, 0), tagline, font=tagline_font)
        text_w = bbox[2] - bbox[0]
        draw.text(
            ((THUMBNAIL_WIDTH - text_w) // 2, 430),
            tagline,
            font=tagline_font,
            fill=(180, 140, 255),
        )
    except Exception:
        pass

    # --- Bottom bar ---
    draw.rectangle([0, THUMBNAIL_HEIGHT - 8, THUMBNAIL_WIDTH, THUMBNAIL_HEIGHT], fill=(120, 60, 200))

    # Save
    img.save(str(output_path), "JPEG", quality=95)
    logger.info("Default thumbnail created: %s", output_path)
    return output_path
