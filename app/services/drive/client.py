"""
TheMemeCanvas Automation Suite — Google Drive API Client
=========================================================
Handles authentication and low-level Drive API calls.
Supports both Service Account and OAuth2 user authentication.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Optional

from google.auth.transport.requests import Request
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from app.config.settings import settings

logger = logging.getLogger("thememecanvas.drive")

SCOPES = [
    "https://www.googleapis.com/auth/drive",  # Full access for move/delete operations
]


class DriveClient:
    """
    Google Drive API client with lazy initialization.

    Authentication priority:
        1. Service Account (recommended for server deployments)
        2. OAuth2 user credentials
    """

    def __init__(self) -> None:
        self._service = None

    @property
    def service(self):
        """Lazy-load the Drive service."""
        if self._service is None:
            self._service = self._build_service()
        return self._service

    def _build_service(self):
        """Build and return an authenticated Drive API service."""
        creds = self._get_credentials()
        service = build("drive", "v3", credentials=creds, cache_discovery=False)
        logger.info("Google Drive service initialized.")
        return service

    def _get_credentials(self) -> Credentials:
        """Get valid credentials using Service Account or OAuth2 flow."""
        # --- Option 1: Service Account (preferred for headless servers) ---
        if settings.google_service_account_file and Path(settings.google_service_account_file).exists():
            logger.info("Using Google Service Account credentials.")
            creds = service_account.Credentials.from_service_account_file(
                str(settings.google_service_account_file),
                scopes=SCOPES,
            )
            return creds
        elif settings.google_service_account_json:
            import json
            logger.info("Using Google Service Account credentials from environment variable.")
            info = json.loads(settings.google_service_account_json)
            creds = service_account.Credentials.from_service_account_info(
                info,
                scopes=SCOPES,
            )
            return creds

        # --- Option 2: OAuth2 User Credentials ---
        token_file = settings.google_oauth_token_file
        client_secrets = settings.google_oauth_client_secrets_file

        creds = None

        # Load existing token
        if token_file and Path(token_file).exists():
            creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)

        # Refresh or run OAuth flow
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                logger.info("Refreshing Google OAuth token...")
                creds.refresh(Request())
            elif client_secrets and Path(client_secrets).exists():
                logger.info("Running Google OAuth2 authorization flow...")
                flow = InstalledAppFlow.from_client_secrets_file(str(client_secrets), SCOPES)
                creds = flow.run_local_server(port=0)
            else:
                raise RuntimeError(
                    "No Google credentials found. Provide either:\n"
                    "  - GOOGLE_SERVICE_ACCOUNT_FILE (recommended)\n"
                    "  - GOOGLE_OAUTH_CLIENT_SECRETS_FILE for user OAuth"
                )

            # Save the token for next run
            if token_file:
                Path(token_file).parent.mkdir(parents=True, exist_ok=True)
                Path(token_file).write_text(creds.to_json())
                logger.info("OAuth token saved to %s", token_file)

        return creds

    # ---------------------------------------------------------------------------
    # Low-level Drive API calls
    # ---------------------------------------------------------------------------

    def list_files(
        self,
        folder_id: str,
        mime_types: Optional[List[str]] = None,
        order_by: str = "createdTime",
    ) -> List[Dict]:
        """
        List all files in a folder.

        Args:
            folder_id: Google Drive folder ID.
            mime_types: Optional list of MIME types to filter by.
            order_by: Drive API orderBy string (e.g., "createdTime", "createdTime desc", "name").

        Returns:
            List of file metadata dicts.
        """
        query = f"'{folder_id}' in parents and trashed=false"
        if mime_types:
            mime_filter = " or ".join(f"mimeType='{m}'" for m in mime_types)
            query += f" and ({mime_filter})"

        all_files = []
        page_token = None

        while True:
            params = {
                "q": query,
                "spaces": "drive",
                "fields": "nextPageToken, files(id, name, size, mimeType, createdTime, modifiedTime)",
                "orderBy": order_by,
                "pageSize": 100,
            }
            if page_token:
                params["pageToken"] = page_token

            response = self.service.files().list(**params).execute()
            all_files.extend(response.get("files", []))
            page_token = response.get("nextPageToken")

            if not page_token:
                break

        logger.debug("Listed %d files in folder %s", len(all_files), folder_id)
        return all_files

    def get_file_metadata(self, file_id: str) -> Dict:
        """Get metadata for a single file."""
        return self.service.files().get(
            fileId=file_id,
            fields="id, name, size, mimeType, createdTime, modifiedTime, parents",
        ).execute()

    def move_file(self, file_id: str, destination_folder_id: str) -> Dict:
        """
        Move a file to a different folder.

        Args:
            file_id: ID of the file to move.
            destination_folder_id: ID of the destination folder.

        Returns:
            Updated file metadata.
        """
        # Get current parents
        file = self.service.files().get(fileId=file_id, fields="parents").execute()
        previous_parents = ",".join(file.get("parents", []))

        # Move by updating parents
        result = self.service.files().update(
            fileId=file_id,
            addParents=destination_folder_id,
            removeParents=previous_parents,
            fields="id, parents",
        ).execute()

        logger.info("Moved file %s to folder %s", file_id, destination_folder_id)
        return result

    def delete_file(self, file_id: str) -> None:
        """Permanently delete a file (moves to trash if preferred)."""
        self.service.files().delete(fileId=file_id).execute()
        logger.info("Deleted file %s", file_id)

    def create_folder(self, name: str, parent_id: Optional[str] = None) -> str:
        """Create a folder and return its ID."""
        metadata = {
            "name": name,
            "mimeType": "application/vnd.google-apps.folder",
        }
        if parent_id:
            metadata["parents"] = [parent_id]

        folder = self.service.files().create(body=metadata, fields="id").execute()
        folder_id = folder.get("id")
        logger.info("Created folder '%s' with ID %s", name, folder_id)
        return folder_id
