# 🎭 TheMemeCanvas Automation Suite

<div align="center">

![TheMemeCanvas](https://img.shields.io/badge/TheMemeCanvas-Automation-7c3aed?style=for-the-badge&logo=youtube)
![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi)
![React](https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker)

**A production-grade, fully automated content distribution platform for YouTube Shorts & Instagram Reels.**

*Set it once. Run it forever. Publish daily without lifting a finger.* 🚀

</div>

---

## 📋 Table of Contents

- [Architecture](#architecture)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [API Credentials Setup](#api-credentials-setup)
  - [Google Drive](#google-drive-setup)
  - [YouTube](#youtube-api-setup)
  - [Instagram](#instagram-api-setup)
  - [Google Gemini](#google-gemini-setup)
  - [Groq](#groq-setup)
  - [Telegram Bot](#telegram-bot-setup)
- [Deployment](#deployment)
  - [Docker (Recommended)](#docker-deployment)
  - [Windows](#windows-deployment)
  - [Linux](#linux-deployment)
- [Dashboard](#dashboard)
- [Troubleshooting](#troubleshooting)
- [FAQ](#faq)
- [Future Roadmap](#future-roadmap)
- [Information Required From User](#-information-required-from-user)

---

## Architecture

```
TheMemeCanvas/
├── app/                          # Python backend (FastAPI)
│   ├── main.py                   # Application entry point
│   ├── config/
│   │   ├── settings.py           # Pydantic settings (reads .env)
│   │   └── constants.py          # Brand templates, AI prompts
│   ├── database/
│   │   └── base.py               # SQLAlchemy engine + session
│   ├── models/
│   │   ├── upload.py             # Upload record ORM model
│   │   ├── queue_item.py         # Queue item ORM model
│   │   └── notification_log.py   # Notification log ORM model
│   ├── services/
│   │   ├── drive/                # Google Drive API
│   │   ├── youtube/              # YouTube Data API v3
│   │   ├── instagram/            # Instagram Graph API
│   │   ├── ai/                   # AI metadata generation (Gemini/Groq/etc.)
│   │   ├── thumbnail/            # Auto thumbnail generation
│   │   └── notifications/        # Telegram, Email
│   ├── scheduler/                # APScheduler jobs
│   ├── workflows/                # Upload pipeline orchestrator
│   ├── utils/                    # Logging, hashing, retry, health
│   └── dashboard/                # FastAPI REST API routes
├── frontend/                     # React dashboard (Vite + TypeScript)
├── tests/                        # Unit tests
├── credentials/                  # OAuth tokens (gitignored)
├── data/                         # SQLite database (gitignored)
├── logs/                         # Rotating log files (gitignored)
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

### Upload Pipeline Flow

```
Google Drive Queue Folder
        ↓
Pick next unprocessed video (oldest/newest/random)
        ↓
Download to temp directory
        ↓
SHA256 duplicate check → skip if already uploaded
        ↓
AI generates: title (5 candidates, scored) + description + tags + caption + hashtags
        ↓
Thumbnail: existing file → FFmpeg extract → branded default
        ↓
Upload to YouTube Shorts (resumable chunked upload)
        ↓
Upload thumbnail to YouTube
        ↓
Upload to Instagram Reels (via YouTube public URL)
        ↓
Move video to Uploaded/ folder in Drive
        ↓
Save complete record to SQLite database
        ↓
Delete temp files
        ↓
Send success notification (Telegram/Email)
        ↓
Repeat tomorrow at 9:00 PM (configurable)
```

---

## Features

| Feature | Status |
|---------|--------|
| 📂 Google Drive queue monitoring | ✅ |
| 🤖 AI title generation (5 candidates, scored) | ✅ |
| 📝 AI description & tags | ✅ |
| 📸 AI Instagram caption & hashtags | ✅ |
| 📺 YouTube Shorts upload (resumable) | ✅ |
| 🖼️ Thumbnail upload & auto-generation | ✅ |
| 📱 Instagram Reels upload | ✅ |
| 🔁 Exponential retry with backoff | ✅ |
| 🚫 SHA256 duplicate prevention | ✅ |
| 🔔 Telegram / Email notifications | ✅ |
| 📊 Premium dark-mode dashboard | ✅ |
| 🕒 Configurable daily upload time | ✅ |
| ⏸️ Pause/resume/force upload controls | ✅ |
| 📈 Charts: upload history, status breakdown | ✅ |
| 🩺 Daily health checks | ✅ |
| 📋 Rotating log files per service | ✅ |
| 🐳 Docker + Docker Compose | ✅ |
| 🧪 Unit test structure | ✅ |

---

## Prerequisites

- Python 3.11+
- FFmpeg (for auto-thumbnail generation)
- Node.js 20+ (for building the React dashboard)
- Docker + Docker Compose (for containerized deployment)
- Google Cloud Platform account
- Meta Developer account (for Instagram)
- Google AI Studio (Gemini) or Groq account

---

## Installation

### 1. Clone / Download

```bash
# Navigate to project directory
cd TheMemeCanvas
```

### 2. Configure Environment

```bash
# Copy the example config
cp .env.example .env

# Edit .env with your credentials
notepad .env       # Windows
nano .env          # Linux/Mac
```

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 4. Build the Frontend (optional for local dev)

```bash
cd frontend
npm install
npm run build
cd ..
```

### 5. First Run

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open http://localhost:8000 in your browser.

---

## Configuration

All configuration is done through the `.env` file. See `.env.example` for all available options.

### Key Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `UPLOAD_TIME` | `21:00` | Daily upload time (HH:MM, 24h) |
| `TIMEZONE` | `Asia/Kolkata` | Your local timezone |
| `UPLOAD_ORDER` | `oldest_first` | `oldest_first` / `newest_first` / `random` |
| `AI_PROVIDER` | `gemini` | AI provider: `gemini` / `groq` / `openai` / `anthropic` |
| `NOTIFICATION_PROVIDERS` | `telegram` | Comma-separated: `telegram,email` |

---

## API Credentials Setup

### Google Drive Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or use existing)
3. Enable **Google Drive API**
4. Go to **Credentials** → **Create Credentials** → **OAuth 2.0 Client IDs**
5. Choose **Desktop application**
6. Download the JSON file → save as `credentials/google_oauth_client_secrets.json`
7. Set `GOOGLE_OAUTH_CLIENT_SECRETS_FILE=credentials/google_oauth_client_secrets.json`
8. Create 3 folders in Google Drive:
   - **Queue** — add your videos here
   - **Uploaded** — processed videos go here automatically
   - **Failed** — failed videos go here
9. Get each folder's ID from the browser URL (the part after `/folders/`)
10. Set `DRIVE_QUEUE_FOLDER_ID`, `DRIVE_UPLOADED_FOLDER_ID`, `DRIVE_FAILED_FOLDER_ID`

**First Run OAuth**: On first run, a browser window will open for Google authorization. After authorizing, the token is saved automatically.

---

### YouTube API Setup

1. In your Google Cloud project, enable **YouTube Data API v3**
2. Create OAuth 2.0 credentials (same process as Drive above)
3. Download → save as `credentials/youtube_oauth_client_secrets.json`
4. Set `YOUTUBE_OAUTH_CLIENT_SECRETS_FILE=credentials/youtube_oauth_client_secrets.json`
5. Find your Channel ID:
   - Go to [YouTube Studio](https://studio.youtube.com)
   - Settings → Channel → Advanced Settings → Channel ID
6. Set `YOUTUBE_CHANNEL_ID=UCxxxxxxxxxxxxxxxxxx`

> ⚠️ **YouTube API Quota**: You get 10,000 units/day. Each upload costs ~1,600 units. This means you can upload ~6 videos per day before hitting quota. Since we only upload 1/day, this is more than sufficient.

> ⚠️ **Custom Thumbnails**: Requires a verified YouTube channel (phone number verified or 1000+ subscribers).

---

### Instagram API Setup

Instagram Reels uploads require a Meta Business Developer setup:

1. Go to [Meta for Developers](https://developers.facebook.com/)
2. Create a new app → **Business** type
3. Add **Instagram Graph API** product
4. Connect your **Facebook Page** that is linked to your Instagram account
5. Your Instagram account must be a **Professional/Business/Creator** account
6. Get your **Instagram Account ID**:
   - Graph API Explorer: `GET /{ig-username}?fields=id&access_token={token}`
7. Generate a **Long-Lived Access Token** (valid 60 days):
   - Exchange short-lived token: `GET /oauth/access_token?grant_type=fb_exchange_token&...`
8. Set:
   - `INSTAGRAM_ACCESS_TOKEN=your_long_lived_token`
   - `INSTAGRAM_ACCOUNT_ID=your_ig_account_id`
   - `FACEBOOK_PAGE_ID=your_page_id`

> ⚠️ **Token Refresh**: Long-lived tokens expire after 60 days. The app can refresh them automatically via the `/api/refresh-instagram-token` endpoint, or set up the refresh cron job.

---

### Google Gemini Setup

1. Go to [Google AI Studio](https://aistudio.google.com/)
2. Create a new API key
3. Set `GEMINI_API_KEY=AIzaSy...`
4. Set `GEMINI_MODEL=gemini-1.5-flash`

---

### Groq Setup

1. Go to [Groq Console](https://console.groq.com/keys)
2. Create an API key
3. Set `GROQ_API_KEY=gsk_...`
4. Set `GROQ_MODEL=llama3-70b-8192`

---

### Telegram Bot Setup

1. Open Telegram → search for **@BotFather**
2. Send `/newbot`
3. Choose a name and username for your bot
4. Copy the **Bot Token**: `123456789:ABCdefGhI...`
5. Set `TELEGRAM_BOT_TOKEN=your_token`
6. Get your **Chat ID**:
   - Search for **@userinfobot** on Telegram
   - Send `/start`
   - Copy your **Id** (the number)
7. Set `TELEGRAM_CHAT_ID=your_chat_id`
8. Start your bot: open Telegram → search your bot → click **Start**

---

### Discord Webhook Setup (Optional)

1. Open your Discord server
2. Go to **Channel Settings** → **Integrations** → **Webhooks**
3. Click **New Webhook** → copy the URL
4. Set `DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...`

---

## Deployment

### Docker Deployment (Recommended)

```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f thememecanvas

# Stop
docker-compose down

# Rebuild after code changes
docker-compose up -d --build
```

The dashboard will be available at http://localhost:8000

### Windows Deployment

```powershell
# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Run (keep this terminal open or run as a Windows Service)
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# Or use the provided batch script
# (create start.bat with the above command)
```

**To run as a Windows Service** (keeps running after reboot):
```powershell
# Install NSSM (Non-Sucking Service Manager)
# Download from https://nssm.cc/
nssm install TheMemeCanvas "python" "-m uvicorn app.main:app --host 0.0.0.0 --port 8000"
nssm set TheMemeCanvas AppDirectory "C:\path\to\TheMemeCanvas"
nssm start TheMemeCanvas
```

### Linux Deployment

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install
pip install -r requirements.txt

# Run with systemd (create /etc/systemd/system/thememecanvas.service)
sudo systemctl enable thememecanvas
sudo systemctl start thememecanvas
sudo systemctl status thememecanvas
```

**Systemd service file** (`/etc/systemd/system/thememecanvas.service`):
```ini
[Unit]
Description=TheMemeCanvas Automation Suite
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/TheMemeCanvas
ExecStart=/path/to/venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

---

## Dashboard

Open **http://localhost:8000** in your browser.

### Pages

| Page | Description |
|------|-------------|
| 📊 Dashboard | Stats, charts, today's upload, health status |
| 📋 Queue | View queue, sync from Drive, skip videos |
| 📜 History | All uploads with filter, search, pagination |
| 📋 Logs | Live log viewer for all service logs |
| ⚙️ Settings | Configuration reference and setup guide |

### Quick Controls (Sidebar)

- **Upload Now** — Force an immediate upload
- **Pause Uploads** — Stop the daily schedule
- **Resume Uploads** — Resume the daily schedule
- **Sync Queue** — Refresh queue from Google Drive

---

## Troubleshooting

### "No Google credentials found"
- Ensure `credentials/google_oauth_client_secrets.json` exists
- Or set `GOOGLE_SERVICE_ACCOUNT_FILE` to a service account JSON path

### YouTube upload fails with 403
- Check your OAuth token is valid (run OAuth flow again)
- Ensure YouTube Data API v3 is enabled in Google Cloud

### Instagram upload fails
- Verify your access token is not expired (60-day limit)
- Ensure the Instagram account is a Business/Creator account
- Check `INSTAGRAM_ACCOUNT_ID` is the numeric ID, not @username

### Queue is empty but Drive has videos
- Click "Sync Queue" in the dashboard or sidebar
- Verify `DRIVE_QUEUE_FOLDER_ID` is correct (check browser URL)

### Thumbnails not uploading
- YouTube requires a verified channel for custom thumbnails
- Ensure `ffmpeg` is installed and in PATH

### Scheduler not triggering
- Check `UPLOAD_TIME` is in HH:MM 24h format
- Verify `TIMEZONE` is a valid pytz timezone string
- Check `logs/scheduler.log` for details

---

## FAQ

**Q: What video formats are supported?**  
A: `.mp4`, `.mov`, `.avi`, `.mkv`, `.webm`

**Q: Can I change the upload time?**  
A: Yes — set `UPLOAD_TIME=21:00` in `.env`. Change `21:00` to your preferred time. Restart after.

**Q: What if a video fails to upload?**  
A: It's retried at 5, 15, 30, and 60 minutes. After all retries fail, it's moved to the Failed folder and you get a notification.

**Q: Will it ever upload the same video twice?**  
A: No. Every video is checked against SHA256 hash, filename, and Drive File ID before upload.

**Q: Can I add more platforms?**  
A: Yes! The architecture is designed for this. Create a new service in `app/services/` implementing the same interface. See `app/services/youtube/uploader.py` as a template.

**Q: The AI titles are too generic. Can I customize them?**  
A: Yes — edit the `AI_TITLE_PROMPT` in `app/config/constants.py`.

**Q: How much does it cost to run per month?**  
A: ~$1–3/month for OpenAI (at 1 video/day). Google APIs are free within quota. The server cost depends on your hosting.

---

## Future Roadmap

Planned features (architecture already supports):
- 🎬 Facebook Reels
- 🎵 TikTok
- 📌 Pinterest
- 🧵 Threads
- 🐦 X (Twitter)
- 💼 LinkedIn
- 👻 Snapchat Spotlight
- 📺 Multiple YouTube channels
- 📸 Multiple Instagram accounts
- 💬 AI subtitles (FFmpeg + Whisper)
- 🗣️ AI voiceover
- 📈 Analytics dashboard
- 🔍 Trending keyword research
- 📋 Auto playlists
- 💬 Auto comments
- 🧪 A/B title testing
- ☁️ Cloud storage integration (S3, R2, Backblaze)

---

## 📋 Information Required From User

Before the application can be deployed, provide the following values in your `.env` file:

### 🔴 Required

| Value | .env Variable | How to Get |
|-------|---------------|------------|
| Google Drive Queue Folder ID | `DRIVE_QUEUE_FOLDER_ID` | Browser URL when viewing folder |
| Google Drive Uploaded Folder ID | `DRIVE_UPLOADED_FOLDER_ID` | Browser URL when viewing folder |
| Google Drive Failed Folder ID | `DRIVE_FAILED_FOLDER_ID` | Browser URL when viewing folder |
| Google OAuth Client Secrets JSON | `GOOGLE_OAUTH_CLIENT_SECRETS_FILE` | Google Cloud Console |
| YouTube Channel ID | `YOUTUBE_CHANNEL_ID` | YouTube Studio → Settings → Channel |
| YouTube OAuth Client Secrets JSON | `YOUTUBE_OAUTH_CLIENT_SECRETS_FILE` | Google Cloud Console (with YouTube API) |
| Instagram Long-Lived Access Token | `INSTAGRAM_ACCESS_TOKEN` | Meta Developer Console |
| Instagram Business Account ID | `INSTAGRAM_ACCOUNT_ID` | Graph API Explorer |
| Facebook Page ID | `FACEBOOK_PAGE_ID` | Facebook Page settings |
| Google Gemini API Key | `GEMINI_API_KEY` | aistudio.google.com |
| Groq API Key | `GROQ_API_KEY` | console.groq.com/keys |

### 🟡 Strongly Recommended

| Value | .env Variable | Purpose |
|-------|---------------|---------|
| Telegram Bot Token | `TELEGRAM_BOT_TOKEN` | Upload notifications |
| Telegram Chat ID | `TELEGRAM_CHAT_ID` | Upload notifications |

### 🟢 Optional

| Value | .env Variable | Purpose |
|-------|---------------|---------|
| SMTP credentials | `SMTP_HOST`, `SMTP_USERNAME`, etc. | Email notifications |
| Upload Time | `UPLOAD_TIME` | Change from default 21:00 |
| Timezone | `TIMEZONE` | Change from Asia/Kolkata |
| OpenAI API Key | `OPENAI_API_KEY` | Optional alternative AI key |

---

<div align="center">

Made with ❤️ for **TheMemeCanvas**

*"Your Daily Dose of Memes 🎭"*

</div>
