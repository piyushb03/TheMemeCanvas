"""
TheMemeCanvas Automation Suite — Brand Constants & Templates
============================================================
All brand-specific values, description templates, and base tag lists
are stored here so they can be updated without touching business logic.
"""

from typing import List

# ---------------------------------------------------------------------------
# Brand Identity
# ---------------------------------------------------------------------------

BRAND_NAME = "TheMemeCanvas"
BRAND_HANDLE_YOUTUBE = "@TheMemeCanvas"

# ---------------------------------------------------------------------------
# Base Tags — Always included in every YouTube upload
# ---------------------------------------------------------------------------

BASE_YOUTUBE_TAGS: List[str] = [
    "TheMemeCanvas",
    "thememecanvas",
    "The Meme Canvas",
    "anime",
    "anime memes",
    "cartoon",
    "cartoon memes",
    "funny",
    "funny memes",
    "viral memes",
    "shorts",
    "youtube shorts",
    "daily memes",
    "comedy",
    "lol",
    "meme",
    "memes",
    "trending memes",
    "best memes",
    "funniest memes",
]

# ---------------------------------------------------------------------------
# YouTube Description Template
# ---------------------------------------------------------------------------
# {ai_opening} — replaced with AI-generated first sentence per video
# {tags_line} — replaced with comma-separated tags
# ---------------------------------------------------------------------------

YOUTUBE_DESCRIPTION_TEMPLATE = """\
{ai_opening}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎭 Welcome to {brand_name} — Your Daily Dose of Memes!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

We post the funniest anime memes, cartoon memes, and viral content every day.
Hit the 🔔 Subscribe button so you never miss a meme!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📱 Find Us Everywhere:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
▶ YouTube: {youtube_url}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏷️ Tags:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{tags_line}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
© {brand_name} — All content used under fair use / commentary.
"""

# ---------------------------------------------------------------------------
# Notification Message Templates
# ---------------------------------------------------------------------------

NOTIF_UPLOAD_STARTED = """\
🚀 *Upload Started*

📁 File: `{filename}`
📺 Uploading to YouTube...
🕒 Time: {timestamp}
"""

NOTIF_UPLOAD_SUCCESS = """\
✅ *Upload Successful!*

📁 File: `{filename}`
🎬 Title: {title}
📺 YouTube: {youtube_url}
📊 Queue Remaining: {queue_remaining} videos (~{days_remaining} days)
🕒 Time: {timestamp}
"""

NOTIF_UPLOAD_FAILED = """\
❌ *Upload Failed!*

📁 File: `{filename}`
💥 Error: {error}
🔄 Retry #{retry_count} scheduled in {next_retry_mins} min
🕒 Time: {timestamp}
"""

NOTIF_RETRY_STARTED = """\
🔄 *Retry Started*

📁 File: `{filename}`
🔁 Attempt #{attempt} of {max_attempts}
🕒 Time: {timestamp}
"""

NOTIF_ALL_RETRIES_FAILED = """\
🚫 *All Retries Exhausted!*

📁 File: `{filename}`
💥 Final Error: {error}
📂 Moved to Failed folder.
🕒 Time: {timestamp}
"""

NOTIF_DAILY_SUMMARY = """\
📊 *TheMemeCanvas Daily Report*

📅 Date: {date}
━━━━━━━━━━━━━━━━━━━━
📁 Today's Upload: `{filename}`
🎬 Title: {title}
📺 YouTube: {youtube_status}
━━━━━━━━━━━━━━━━━━━━
📦 Queue Remaining: {queue_remaining} videos
⏳ Est. Days Left: {days_remaining}
📅 Next Upload: {next_upload_time}
━━━━━━━━━━━━━━━━━━━━
✅ Total Uploaded: {total_uploaded}
❌ Total Failed: {total_failed}
"""

NOTIF_QUEUE_EMPTY = """\
🎉 *Queue Empty!*

All queued videos have been uploaded successfully.
{brand_name} will continue checking periodically for new content.

📦 Total Uploaded: {total_uploaded}
🕒 Time: {timestamp}

Please add new videos to the Google Drive Queue folder to continue!
"""

NOTIF_HEALTH_CHECK_FAILED = """\
⚠️ *Health Check Alert!*

🔴 Failed Component: {component}
💥 Error: {error}
🕒 Time: {timestamp}

Please check your configuration immediately.
"""

NOTIF_SCHEDULER_STARTED = """\
🟢 *TheMemeCanvas Scheduler Started*

⏰ Next upload: {next_upload_time}
📦 Queue size: {queue_size} videos
⏳ Est. Days: {days_remaining}
🕒 Started at: {timestamp}
"""

NOTIF_AUTH_FAILURE = """\
🔐 *Authentication Failure!*

🔑 Service: {service}
💥 Error: {error}
🕒 Time: {timestamp}

Action required: Refresh your OAuth token.
"""

NOTIF_API_QUOTA_WARNING = """\
⚡ *API Quota Warning!*

📡 Service: {service}
📊 Usage: {usage}
🕒 Time: {timestamp}

Uploads may be delayed.
"""

# ---------------------------------------------------------------------------
# AI Prompt Templates
# ---------------------------------------------------------------------------

AI_TITLE_PROMPT = """\
You are a viral YouTube Shorts content strategist for the brand "{brand_name}".

Generate {num_titles} highly clickable, SEO-optimized YouTube Short titles for a meme video.

Rules:
- Maximum 60 characters each
- Use emojis strategically (1-2 per title)
- Create curiosity or humor
- Include power words (Epic, Hilarious, Impossible, Wait For It, etc.)
- Do NOT use generic phrases like "Funny Video" or "Watch This"
- Vary the style: questions, statements, reactions, challenges
- Avoid repeating themes from: {recent_titles}

Video filename: {filename}

Return ONLY a JSON array of strings. No explanation. No markdown.
Example: ["Title 1", "Title 2", "Title 3"]
"""

AI_DESCRIPTION_OPENING_PROMPT = """\
You are a YouTube content creator for "{brand_name}" — a meme channel featuring anime and cartoon memes.

Write a single engaging opening sentence (max 150 characters) for the video description.

Rules:
- Funny, punchy, or intriguing
- References the video content if possible
- Can use 1 emoji
- No hashtags in this sentence

Video filename: {filename}
Video title: {title}

Return ONLY the opening sentence. No explanation.
"""

AI_TAGS_PROMPT = """\
You are an SEO expert for YouTube Shorts.

Generate {num_tags} additional specific tags for a meme video.

Base tags already included: {base_tags}

Rules:
- Return tags NOT already in the base tags list
- Be specific to the video content
- Mix trending keywords with niche terms
- Each tag: 1-4 words
- No # symbols
- Think about what people search for when looking for this type of content

Video filename: {filename}
Video title: {title}

Return ONLY a JSON array of strings. No explanation.
Example: ["tag one", "tag two", "tag three"]
"""

# ---------------------------------------------------------------------------
# Thumbnail Constants
# ---------------------------------------------------------------------------

THUMBNAIL_WIDTH = 1280
THUMBNAIL_HEIGHT = 720
THUMBNAIL_FONT_SIZE = 72
THUMBNAIL_BRAND_FONT_SIZE = 36

# ---------------------------------------------------------------------------
# File Extensions
# ---------------------------------------------------------------------------

SUPPORTED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

# ---------------------------------------------------------------------------
# Upload Pipeline Stages
# ---------------------------------------------------------------------------

class UploadStage:
    PENDING = "pending"
    DOWNLOADING = "downloading"
    GENERATING_METADATA = "generating_metadata"
    UPLOADING_YOUTUBE = "uploading_youtube"
    UPLOADING_THUMBNAIL = "uploading_thumbnail"
    MOVING_FILE = "moving_file"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    SKIPPED = "skipped"
