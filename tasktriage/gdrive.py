"""
Google Drive integration for TaskTriage.

Provides functionality to read task notes from a Google Drive folder
as an alternative to the local USB directory.
"""

import io
import os
from datetime import datetime
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# Google Drive API scopes (read and write access for uploading analysis files)
SCOPES = ["https://www.googleapis.com/auth/drive"]

# Supported MIME types for notes files
TEXT_MIME_TYPES = {"text/plain"}
IMAGE_MIME_TYPES = {"image/png"}
ALL_MIME_TYPES = TEXT_MIME_TYPES | IMAGE_MIME_TYPES

# Map MIME types to file extensions
MIME_TO_EXT = {
    "text/plain": ".txt",
    "image/png": ".png",
}


class GoogleDriveClient:
    """Client for interacting with Google Drive API."""

    def __init__(self, credentials_path: str | None = None, folder_id: str | None = None):
        """Initialize the Google Drive client.

        Args:
            credentials_path: Path to the service account JSON credentials file.
                             Falls back to GOOGLE_CREDENTIALS_PATH env var.
            folder_id: ID of the root Google Drive folder containing daily/weekly subdirs.
                      Falls back to GOOGLE_DRIVE_FOLDER_ID env var.

        Raises:
            ValueError: If credentials path or folder ID is not provided.
            FileNotFoundError: If credentials file does not exist.
        """
        self.credentials_path = credentials_path or os.getenv("GOOGLE_CREDENTIALS_PATH")
        self.folder_id = folder_id or os.getenv("GOOGLE_DRIVE_FOLDER_ID")

        if not self.credentials_path:
            raise ValueError(
                "Google Drive credentials path not set. "
                "Set GOOGLE_CREDENTIALS_PATH in .env or pass credentials_path."
            )

        if not self.folder_id:
            raise ValueError(
                "Google Drive folder ID not set. "
                "Set GOOGLE_DRIVE_FOLDER_ID in .env or pass folder_id."
            )

        credentials_file = Path(self.credentials_path)
        if not credentials_file.exists():
            raise FileNotFoundError(
                f"Google credentials file not found: {self.credentials_path}"
            )

        self._service = None
        self._folder_cache = {}

    @property
    def service(self):
        """Lazily initialize and return the Google Drive service."""
        if self._service is None:
            credentials = service_account.Credentials.from_service_account_file(
                self.credentials_path, scopes=SCOPES
            )
            self._service = build("drive", "v3", credentials=credentials)
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
    """Check if Google Drive integration is configured.

    Returns:
        True if both credentials path and folder ID are set in environment.
    """
    credentials_path = os.getenv("GOOGLE_CREDENTIALS_PATH")
    folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")

    if not credentials_path or not folder_id:
        return False

    # Also check if credentials file exists
    return Path(credentials_path).exists()


def parse_filename_datetime(filename: str) -> datetime | None:
    """Parse datetime from a notes filename.

    Supports formats:
        - YYYYMMDD_HHMMSS.ext (e.g., 20251225_073454.txt)
        - YYYYMMDD_HHMMSS_Page_N.ext (e.g., 20251225_073454_Page_1.png)
        - YYYYMMDD_HHMMSS.daily_analysis.txt (analysis files)

    Args:
        filename: Filename with timestamp prefix

    Returns:
        Parsed datetime, or None if parsing fails
    """
    try:
        # Remove extension and parse
        stem = Path(filename).stem
        # Handle analysis files (e.g., 20251225_074353.daily_analysis)
        if "." in stem:
            stem = stem.split(".")[0]

        # Handle page identifiers (e.g., 20251225_073454_Page_1)
        # Extract just the timestamp portion (first 15 chars: YYYYMMDD_HHMMSS)
        if "_Page_" in stem:
            stem = stem.split("_Page_")[0]

        return datetime.strptime(stem, "%Y%m%d_%H%M%S")
    except ValueError:
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
