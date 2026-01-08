"""
Google Drive integration for TaskTriage.

Provides functionality to read task notes from a Google Drive folder
as an alternative to the local USB directory.
"""

import io
import os
import re
from datetime import datetime
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# Google Drive API scopes (read and write access for uploading analysis files)
SCOPES = ["https://www.googleapis.com/auth/drive"]

# Supported MIME types for notes files
TEXT_MIME_TYPES = {"text/plain"}
IMAGE_MIME_TYPES = {"image/png"}
PDF_MIME_TYPES = {"application/pdf"}
VISUAL_MIME_TYPES = IMAGE_MIME_TYPES | PDF_MIME_TYPES
ALL_MIME_TYPES = TEXT_MIME_TYPES | VISUAL_MIME_TYPES

# Map MIME types to file extensions
MIME_TO_EXT = {
    "text/plain": ".txt",
    "image/png": ".png",
    "application/pdf": ".pdf",
}


class GoogleDriveClient:
    """Client for interacting with Google Drive API using OAuth 2.0."""

    def __init__(self, credentials: Credentials | None = None, folder_id: str | None = None):
        """Initialize the Google Drive client.

        Args:
            credentials: OAuth 2.0 credentials object (required)
            folder_id: ID of the root Google Drive folder containing daily/weekly subdirs.
                      Falls back to GOOGLE_DRIVE_FOLDER_ID env var.

        Raises:
            ValueError: If credentials or folder ID is not provided.
        """
        if credentials is None:
            raise ValueError(
                "OAuth credentials required. Please authenticate with Google Drive first."
            )

        self.credentials = credentials
        self.folder_id = folder_id or os.getenv("GOOGLE_DRIVE_FOLDER_ID")

        if not self.folder_id:
            raise ValueError(
                "Google Drive folder ID not set. "
                "Set GOOGLE_DRIVE_FOLDER_ID in .env or pass folder_id."
            )

        self._service = None
        self._folder_cache = {}

    @property
    def service(self):
        """Lazily initialize and return the Google Drive service."""
        if self._service is None:
            # Refresh if expired
            if self.credentials.expired and self.credentials.refresh_token:
                self.credentials.refresh(Request())

            self._service = build("drive", "v3", credentials=self.credentials)
        return self._service

    def get_subfolder_id(self, subfolder_name: str) -> str | None:
        """Get the ID of a subfolder within the root folder.

        Args:
            subfolder_name: Name of the subfolder (e.g., "daily", "Deekly")

        Returns:
            The folder ID, or None if not found.
        """
        if subfolder_name in self._folder_cache:
            return self._folder_cache[subfolder_name]

        query = (
            f"'{self.folder_id}' in parents and "
            f"name = '{subfolder_name}' and "
            f"mimeType = 'application/vnd.google-apps.folder' and "
            f"trashed = false"
        )

        results = self.service.files().list(
            q=query,
            fields="files(id, name)",
            pageSize=1
        ).execute()

        files = results.get("files", [])
        if files:
            folder_id = files[0]["id"]
            self._folder_cache[subfolder_name] = folder_id
            return folder_id

        return None

    def list_notes_files(self, subfolder_name: str) -> list[dict]:
        """List all notes files in a subfolder.

        Args:
            subfolder_name: Name of the subfolder (e.g., "daily", "weekly")

        Returns:
            List of file metadata dicts with keys: id, name, mimeType, modifiedTime

        Raises:
            FileNotFoundError: If the subfolder doesn't exist.
        """
        folder_id = self.get_subfolder_id(subfolder_name)
        if not folder_id:
            raise FileNotFoundError(
                f"Subfolder '{subfolder_name}' not found in Google Drive folder"
            )

        # Build query for supported file types
        mime_conditions = " or ".join(
            f"mimeType = '{mime}'" for mime in ALL_MIME_TYPES
        )
        query = (
            f"'{folder_id}' in parents and "
            f"({mime_conditions}) and "
            f"trashed = false"
        )

        all_files = []
        page_token = None

        while True:
            results = self.service.files().list(
                q=query,
                fields="nextPageToken, files(id, name, mimeType, modifiedTime)",
                pageSize=100,
                pageToken=page_token,
                orderBy="name desc"
            ).execute()

            all_files.extend(results.get("files", []))
            page_token = results.get("nextPageToken")

            if not page_token:
                break

        return all_files

    def download_file(self, file_id: str) -> bytes:
        """Download a file's content.

        Args:
            file_id: The Google Drive file ID

        Returns:
            The file content as bytes
        """
        request = self.service.files().get_media(fileId=file_id)
        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)

        done = False
        while not done:
            _, done = downloader.next_chunk()

        buffer.seek(0)
        return buffer.read()

    def download_file_text(self, file_id: str) -> str:
        """Download a text file's content as a string.

        Args:
            file_id: The Google Drive file ID

        Returns:
            The file content as a string
        """
        content = self.download_file(file_id)
        return content.decode("utf-8")

    def file_exists(self, subfolder_name: str, filename: str) -> bool:
        """Check if a specific file exists in a subfolder.

        Args:
            subfolder_name: Name of the subfolder (e.g., "daily")
            filename: Name of the file to check

        Returns:
            True if the file exists, False otherwise
        """
        folder_id = self.get_subfolder_id(subfolder_name)
        if not folder_id:
            return False

        query = (
            f"'{folder_id}' in parents and "
            f"name = '{filename}' and "
            f"trashed = false"
        )

        results = self.service.files().list(
            q=query,
            fields="files(id)",
            pageSize=1
        ).execute()

        return len(results.get("files", [])) > 0

    def upload_file(self, subfolder_name: str, filename: str, content: str) -> str:
        """Upload a text file to a subfolder.

        Args:
            subfolder_name: Name of the subfolder (e.g., "daily")
            filename: Name for the uploaded file
            content: Text content to upload

        Returns:
            The ID of the uploaded file

        Raises:
            FileNotFoundError: If the subfolder doesn't exist.
        """
        from googleapiclient.http import MediaInMemoryUpload

        folder_id = self.get_subfolder_id(subfolder_name)
        if not folder_id:
            raise FileNotFoundError(
                f"Subfolder '{subfolder_name}' not found in Google Drive folder"
            )

        file_metadata = {
            "name": filename,
            "parents": [folder_id],
            "mimeType": "text/plain",
        }

        media = MediaInMemoryUpload(
            content.encode("utf-8"),
            mimetype="text/plain",
            resumable=True
        )

        file = self.service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id"
        ).execute()

        return file.get("id")


def is_gdrive_configured() -> bool:
    """Check if Google Drive is configured with OAuth.

    Returns:
        True if Google Drive OAuth credentials are configured
    """
    client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")
    folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")

    return bool(client_id and client_secret and folder_id)


def parse_filename_datetime(filename: str) -> datetime | None:
    """Parse datetime from filename in various formats.

    Supports:
        - YYYYMMDD_HHMMSS (daily notes with timestamps)
        - YYYYMMDD (weekly/analysis files)
        - YYYYMM (monthly files)
        - YYYY (annual files)

    Handles variations like:
        - YYYYMMDD_HHMMSS.ext (e.g., 20251225_073454.txt)
        - YYYYMMDD_HHMMSS_Page_N.ext (e.g., 20251225_073454_Page_1.png)
        - DD_MM_YYYY.triaged.txt (daily analysis files)

    Args:
        filename: Filename with timestamp prefix

    Returns:
        Parsed datetime, or None if parsing fails
    """
    patterns = [
        r"(\d{8}_\d{6})",  # YYYYMMDD_HHMMSS
        r"(\d{8})",  # YYYYMMDD for weekly
        r"(\d{6})",  # YYYYMM for monthly
        r"(\d{4})",  # YYYY for annual
    ]

    for pattern in patterns:
        match = re.search(pattern, filename)
        if match:
            ts = match.group(1)
            try:
                if len(ts) == 15:  # YYYYMMDD_HHMMSS
                    return datetime.strptime(ts, "%Y%m%d_%H%M%S")
                elif len(ts) == 8:  # YYYYMMDD
                    return datetime.strptime(ts, "%Y%m%d")
                elif len(ts) == 6:  # YYYYMM
                    return datetime.strptime(ts, "%Y%m")
                elif len(ts) == 4:  # YYYY
                    return datetime.strptime(ts, "%Y")
            except ValueError:
                continue
    return None


def extract_timestamp_from_filename(filename: str) -> str | None:
    """Extract the timestamp portion from a notes filename.

    Handles filenames with optional page identifiers.

    Args:
        filename: Filename with timestamp prefix

    Returns:
        Timestamp string (YYYYMMDD_HHMMSS) or None if not found
    """
    stem = Path(filename).stem

    # Handle analysis files
    if "." in stem:
        stem = stem.split(".")[0]

    # Handle page identifiers
    if "_Page_" in stem:
        stem = stem.split("_Page_")[0]

    # Validate it looks like a timestamp
    if len(stem) == 15 and stem[8] == "_":
        return stem

    return None


def get_file_extension(mime_type: str) -> str:
    """Get file extension for a MIME type.

    Args:
        mime_type: The MIME type string

    Returns:
        File extension including the dot (e.g., ".txt")
    """
    return MIME_TO_EXT.get(mime_type, ".txt")
