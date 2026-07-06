"""
TheMemeCanvas Automation Suite — YouTube Data API v3 Client
===========================================================
Handles authentication and low-level YouTube API calls.
"""

from __future__ import annotations

import logging
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from app.config.settings import settings

logger = logging.getLogger("thememecanvas.youtube")

YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]


class YouTubeClient:
    """
    YouTube Data API v3 client.
    Uses OAuth2 user credentials (required for uploads).
    """

    def __init__(self) -> None:
        self._service = None

    @property
    def service(self):
        if self._service is None:
            self._service = self._build_service()
        return self._service

    def _build_service(self):
        creds = self._get_credentials()
        service = build("youtube", "v3", credentials=creds, cache_discovery=False)
        logger.info("YouTube API service initialized.")
        return service

    def _get_credentials(self) -> Credentials:
        """Authenticate with YouTube via OAuth2."""
        # YouTube uploads require OAuth2 user credentials (not service account)
        token_file = settings.youtube_oauth_token_file or settings.google_oauth_token_file
        client_secrets = settings.youtube_oauth_client_secrets_file or settings.google_oauth_client_secrets_file

        import json
        creds = None

        if settings.youtube_oauth_token_json:
            logger.info("Loading YouTube OAuth token from environment variable.")
            creds = Credentials.from_authorized_user_info(json.loads(settings.youtube_oauth_token_json), YOUTUBE_SCOPES)
        elif token_file and Path(token_file).exists():
            creds = Credentials.from_authorized_user_file(str(token_file), YOUTUBE_SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                logger.info("Refreshing YouTube OAuth token...")
                creds.refresh(Request())
            elif settings.youtube_oauth_client_secrets_json:
                logger.info("Running YouTube OAuth2 authorization flow from environment variable...")
                flow = InstalledAppFlow.from_client_config(
                    json.loads(settings.youtube_oauth_client_secrets_json), YOUTUBE_SCOPES
                )
                creds = flow.run_local_server(port=0)
            elif client_secrets and Path(client_secrets).exists():
                logger.info("Running YouTube OAuth2 authorization flow...")
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(client_secrets), YOUTUBE_SCOPES
                )
                creds = flow.run_local_server(port=0)
            else:
                raise RuntimeError(
                    "YouTube OAuth credentials not found.\n"
                    "Set YOUTUBE_OAUTH_CLIENT_SECRETS_FILE or YOUTUBE_OAUTH_CLIENT_SECRETS_JSON in .env"
                )

            # Save the token to env or file
            if token_file:
                try:
                    Path(token_file).parent.mkdir(parents=True, exist_ok=True)
                    Path(token_file).write_text(creds.to_json())
                    logger.info("YouTube OAuth token saved to %s", token_file)
                except Exception as e:
                    logger.warning("Could not write token file to disk (this is normal in read-only environments like Render free tier): %s", e)

            # Always log the JSON token in case user needs to copy it to Render env vars!
            logger.info("--- YOUR GENERATED YOUTUBE_OAUTH_TOKEN_JSON ---")
            logger.info(creds.to_json())
            logger.info("-----------------------------------------------")

        return creds

    def get_channel_info(self) -> dict:
        """Get authenticated channel info."""
        response = self.service.channels().list(
            part="snippet,statistics",
            mine=True,
        ).execute()
        items = response.get("items", [])
        return items[0] if items else {}
