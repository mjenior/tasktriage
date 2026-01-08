"""
Tests for tasktriage.gdrive module.
"""

import io
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch, PropertyMock

import pytest


@pytest.fixture
def mock_oauth_credentials():
    """Create mock OAuth credentials for testing."""
    from google.oauth2.credentials import Credentials

    creds = Mock(spec=Credentials)
    creds.token = "mock_access_token"
    creds.refresh_token = "mock_refresh_token"
    creds.token_uri = "https://oauth2.googleapis.com/token"
    creds.client_id = "mock_client_id"
    creds.client_secret = "mock_client_secret"
    creds.scopes = ["https://www.googleapis.com/auth/drive"]
    creds.valid = True
    creds.expired = False
    return creds


class TestGoogleDriveClientInit:
    """Tests for GoogleDriveClient initialization."""

    def test_init_with_oauth_credentials(self, mock_oauth_credentials):
        """Should initialize with OAuth credentials."""
        from tasktriage.gdrive import GoogleDriveClient

        client = GoogleDriveClient(
            credentials=mock_oauth_credentials,
            folder_id="test-folder-id"
        )
        assert client.credentials == mock_oauth_credentials
        assert client.folder_id == "test-folder-id"

    def test_raises_when_credentials_not_provided(self):
        """Should raise ValueError when credentials are not provided."""
        from tasktriage.gdrive import GoogleDriveClient

        with pytest.raises(ValueError, match="OAuth credentials required"):
            GoogleDriveClient(credentials=None, folder_id="test-folder-id")

    def test_init_with_env_var_folder_id(self, mock_oauth_credentials, monkeypatch):
        """Should use GOOGLE_DRIVE_FOLDER_ID from environment when not provided."""
        monkeypatch.setenv("GOOGLE_DRIVE_FOLDER_ID", "env-folder-id")

        from tasktriage.gdrive import GoogleDriveClient

        client = GoogleDriveClient(credentials=mock_oauth_credentials)
        assert client.folder_id == "env-folder-id"

    def test_explicit_folder_id_overrides_env(self, mock_oauth_credentials, monkeypatch):
        """Explicit folder_id parameter should override environment variable."""
        monkeypatch.setenv("GOOGLE_DRIVE_FOLDER_ID", "env-folder-id")

        from tasktriage.gdrive import GoogleDriveClient

        client = GoogleDriveClient(
            credentials=mock_oauth_credentials,
            folder_id="explicit-folder-id"
        )
        assert client.folder_id == "explicit-folder-id"


class TestGoogleDriveClientService:
    """Tests for GoogleDriveClient service property."""

    def test_service_lazily_initialized(self, mock_oauth_credentials):
        """Service should be lazily initialized on first access."""
        with patch("tasktriage.gdrive.build") as mock_build:
            mock_service = MagicMock()
            mock_build.return_value = mock_service

            from tasktriage.gdrive import GoogleDriveClient

            client = GoogleDriveClient(credentials=mock_oauth_credentials)
            assert client._service is None

            # Access service property
            _ = client.service

            mock_build.assert_called_once_with("drive", "v3", credentials=mock_oauth_credentials)
            assert client._service == mock_service

    def test_service_cached_after_first_access(self, mock_oauth_credentials):
        """Service should be cached after first initialization."""
        with patch("tasktriage.gdrive.build") as mock_build:
            mock_service = MagicMock()
            mock_build.return_value = mock_service

            from tasktriage.gdrive import GoogleDriveClient

            client = GoogleDriveClient(credentials=mock_oauth_credentials)

            # Access service multiple times
            service1 = client.service
            service2 = client.service

            assert service1 is service2
            assert mock_build.call_count == 1

    def test_service_refreshes_expired_credentials(self, mock_oauth_credentials):
        """Service property should refresh expired credentials before building."""
        mock_oauth_credentials.expired = True
        mock_oauth_credentials.refresh_token = "refresh_token"

        with patch("tasktriage.gdrive.build") as mock_build, \
             patch("tasktriage.gdrive.Request") as mock_request_class:
            mock_service = MagicMock()
            mock_build.return_value = mock_service
            mock_request = MagicMock()
            mock_request_class.return_value = mock_request

            from tasktriage.gdrive import GoogleDriveClient

            client = GoogleDriveClient(credentials=mock_oauth_credentials)

            # Access service
            _ = client.service

            # Verify refresh was called
            mock_oauth_credentials.refresh.assert_called_once_with(mock_request)
            mock_build.assert_called_once()


class TestGoogleDriveClientOperations:
    """Tests for GoogleDriveClient file operations."""

    @pytest.fixture
    def mock_client(self, mock_oauth_credentials):
        """Create a mock GoogleDriveClient with mocked service."""
        with patch("tasktriage.gdrive.build") as mock_build:
            mock_service = MagicMock()
            mock_build.return_value = mock_service

            from tasktriage.gdrive import GoogleDriveClient

            client = GoogleDriveClient(
                credentials=mock_oauth_credentials,
                folder_id="root-folder-id"
            )
            # Force service initialization
            _ = client.service
            return client, mock_service

    def test_get_subfolder_id_returns_folder_id(self, mock_client):
        """Should return folder ID for existing subfolder."""
        client, mock_service = mock_client

        mock_files = mock_service.files.return_value
        mock_list = mock_files.list.return_value
        mock_list.execute.return_value = {
            "files": [{"id": "daily-folder-id", "name": "daily"}]
        }

        result = client.get_subfolder_id("daily")

        assert result == "daily-folder-id"

    def test_get_subfolder_id_returns_none_when_not_found(self, mock_client):
        """Should return None when subfolder doesn't exist."""
        client, mock_service = mock_client

        mock_files = mock_service.files.return_value
        mock_list = mock_files.list.return_value
        mock_list.execute.return_value = {"files": []}

        result = client.get_subfolder_id("nonexistent")

        assert result is None

    def test_get_subfolder_id_caches_results(self, mock_client):
        """Should cache subfolder IDs after first lookup."""
        client, mock_service = mock_client

        mock_files = mock_service.files.return_value
        mock_list = mock_files.list.return_value
        mock_list.execute.return_value = {
            "files": [{"id": "daily-folder-id", "name": "daily"}]
        }

        # Call twice
        client.get_subfolder_id("daily")
        client.get_subfolder_id("daily")

        # Should only call API once
        assert mock_list.execute.call_count == 1

    def test_list_notes_files_returns_files(self, mock_client):
        """Should return list of files in subfolder."""
        client, mock_service = mock_client

        # Mock get_subfolder_id
        client._folder_cache["daily"] = "daily-folder-id"

        mock_files = mock_service.files.return_value
        mock_list = mock_files.list.return_value
        mock_list.execute.return_value = {
            "files": [
                {"id": "file1", "name": "20251231_143000.txt", "mimeType": "text/plain", "modifiedTime": "2025-12-31"},
                {"id": "file2", "name": "20251230_090000.png", "mimeType": "image/png", "modifiedTime": "2025-12-30"},
            ],
            "nextPageToken": None
        }

        result = client.list_notes_files("daily")

        assert len(result) == 2
        assert result[0]["name"] == "20251231_143000.txt"

    def test_list_notes_files_raises_when_folder_not_found(self, mock_client):
        """Should raise FileNotFoundError when subfolder doesn't exist."""
        client, mock_service = mock_client

        mock_files = mock_service.files.return_value
        mock_list = mock_files.list.return_value
        mock_list.execute.return_value = {"files": []}

        with pytest.raises(FileNotFoundError, match="not found"):
            client.list_notes_files("nonexistent")

    def test_download_file_returns_bytes(self, mock_client):
        """Should download and return file content as bytes."""
        client, mock_service = mock_client

        mock_files = mock_service.files.return_value
        mock_request = MagicMock()
        mock_files.get_media.return_value = mock_request

        # Mock MediaIoBaseDownload
        with patch("tasktriage.gdrive.MediaIoBaseDownload") as mock_downloader_class:
            mock_downloader = MagicMock()
            mock_downloader.next_chunk.side_effect = [(None, False), (None, True)]
            mock_downloader_class.return_value = mock_downloader

            # We need to simulate writing to the buffer
            def setup_buffer(buffer, request):
                buffer.write(b"file content")
                return mock_downloader

            mock_downloader_class.side_effect = setup_buffer

            result = client.download_file("file-id")

            mock_files.get_media.assert_called_with(fileId="file-id")

    def test_download_file_text_returns_string(self, mock_client):
        """Should download and return text file content as string."""
        client, mock_service = mock_client

        # Mock download_file to return bytes
        client.download_file = MagicMock(return_value=b"Hello, World!")

        result = client.download_file_text("file-id")

        assert result == "Hello, World!"
        client.download_file.assert_called_with("file-id")

    def test_file_exists_returns_true_when_found(self, mock_client):
        """Should return True when file exists."""
        client, mock_service = mock_client

        client._folder_cache["daily"] = "daily-folder-id"

        mock_files = mock_service.files.return_value
        mock_list = mock_files.list.return_value
        mock_list.execute.return_value = {
            "files": [{"id": "file-id"}]
        }

        result = client.file_exists("daily", "20251231_143000.txt")

        assert result is True

    def test_file_exists_returns_false_when_not_found(self, mock_client):
        """Should return False when file doesn't exist."""
        client, mock_service = mock_client

        client._folder_cache["daily"] = "daily-folder-id"

        mock_files = mock_service.files.return_value
        mock_list = mock_files.list.return_value
        mock_list.execute.return_value = {"files": []}

        result = client.file_exists("daily", "nonexistent.txt")

        assert result is False


class TestIsGdriveConfigured:
    """Tests for is_gdrive_configured function."""

    def test_returns_true_when_oauth_configured(self, monkeypatch):
        """Should return True when OAuth credentials and folder ID are set."""
        monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "test-client-id")
        monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "test-client-secret")
        monkeypatch.setenv("GOOGLE_DRIVE_FOLDER_ID", "test-folder-id")

        from tasktriage.gdrive import is_gdrive_configured

        assert is_gdrive_configured() is True

    def test_returns_false_when_client_id_not_set(self, monkeypatch):
        """Should return False when OAuth client ID is not set."""
        monkeypatch.delenv("GOOGLE_OAUTH_CLIENT_ID", raising=False)
        monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "test-client-secret")
        monkeypatch.setenv("GOOGLE_DRIVE_FOLDER_ID", "test-folder-id")

        from tasktriage.gdrive import is_gdrive_configured

        assert is_gdrive_configured() is False

    def test_returns_false_when_client_secret_not_set(self, monkeypatch):
        """Should return False when OAuth client secret is not set."""
        monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "test-client-id")
        monkeypatch.delenv("GOOGLE_OAUTH_CLIENT_SECRET", raising=False)
        monkeypatch.setenv("GOOGLE_DRIVE_FOLDER_ID", "test-folder-id")

        from tasktriage.gdrive import is_gdrive_configured

        assert is_gdrive_configured() is False

    def test_returns_false_when_folder_id_not_set(self, monkeypatch):
        """Should return False when folder ID is not set."""
        monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "test-client-id")
        monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "test-client-secret")
        monkeypatch.delenv("GOOGLE_DRIVE_FOLDER_ID", raising=False)

        from tasktriage.gdrive import is_gdrive_configured

        assert is_gdrive_configured() is False


class TestParseFilenameDatetime:
    """Tests for parse_filename_datetime function."""

    def test_parses_txt_filename(self):
        """Should parse datetime from .txt filename."""
        from tasktriage.gdrive import parse_filename_datetime

        result = parse_filename_datetime("20251231_143000.txt")

        assert result == datetime(2025, 12, 31, 14, 30, 0)

    def test_parses_png_filename(self):
        """Should parse datetime from .png filename."""
        from tasktriage.gdrive import parse_filename_datetime

        result = parse_filename_datetime("20251230_090000.png")

        assert result == datetime(2025, 12, 30, 9, 0, 0)

    def test_parses_analysis_filename(self):
        """Should parse datetime from analysis filename."""
        from tasktriage.gdrive import parse_filename_datetime

        result = parse_filename_datetime("29_12_2025.triaged.txt")

        assert result == datetime(2025, 12, 29, 0, 0, 0)

    def test_parses_page_identifier_filename(self):
        """Should parse datetime from filename with page identifier."""
        from tasktriage.gdrive import parse_filename_datetime

        result = parse_filename_datetime("20251225_073454_Page_1.png")

        assert result == datetime(2025, 12, 25, 7, 34, 54)

    def test_parses_multi_digit_page_identifier(self):
        """Should parse datetime from filename with multi-digit page number."""
        from tasktriage.gdrive import parse_filename_datetime

        result = parse_filename_datetime("20251225_073454_Page_15.png")

        assert result == datetime(2025, 12, 25, 7, 34, 54)

    def test_returns_none_for_invalid_format(self):
        """Should return None for invalid filename format."""
        from tasktriage.gdrive import parse_filename_datetime

        result = parse_filename_datetime("invalid_filename.txt")

        assert result is None

    def test_parses_YYYYMMDD_timestamp(self):
        """Should parse YYYYMMDD format (for weekly/monthly analysis files)."""
        from tasktriage.gdrive import parse_filename_datetime

        result = parse_filename_datetime("20251231.txt")

        assert result == datetime(2025, 12, 31, 0, 0)


class TestExtractTimestampFromFilename:
    """Tests for extract_timestamp_from_filename function."""

    def test_extracts_from_simple_filename(self):
        """Should extract timestamp from simple filename."""
        from tasktriage.gdrive import extract_timestamp_from_filename

        result = extract_timestamp_from_filename("20251231_143000.txt")
        assert result == "20251231_143000"

    def test_extracts_from_png_filename(self):
        """Should extract timestamp from PNG filename."""
        from tasktriage.gdrive import extract_timestamp_from_filename

        result = extract_timestamp_from_filename("20251225_073454.png")
        assert result == "20251225_073454"

    def test_extracts_from_page_identifier_filename(self):
        """Should extract timestamp from filename with page identifier."""
        from tasktriage.gdrive import extract_timestamp_from_filename

        result = extract_timestamp_from_filename("20251225_073454_Page_1.png")
        assert result == "20251225_073454"

    def test_extracts_from_multi_digit_page(self):
        """Should extract timestamp from filename with multi-digit page number."""
        from tasktriage.gdrive import extract_timestamp_from_filename

        result = extract_timestamp_from_filename("20251225_073454_Page_12.png")
        assert result == "20251225_073454"

    def test_extracts_from_analysis_filename(self):
        """Should extract timestamp from analysis filename."""
        from tasktriage.gdrive import extract_timestamp_from_filename

        result = extract_timestamp_from_filename("20251225_073454.triaged.txt")
        assert result == "20251225_073454"

    def test_returns_none_for_invalid_filename(self):
        """Should return None for invalid filename."""
        from tasktriage.gdrive import extract_timestamp_from_filename

        result = extract_timestamp_from_filename("invalid_filename.txt")
        assert result is None

    def test_returns_none_for_short_filename(self):
        """Should return None for filename without proper timestamp."""
        from tasktriage.gdrive import extract_timestamp_from_filename

        result = extract_timestamp_from_filename("20251225.txt")
        assert result is None


class TestGetFileExtension:
    """Tests for get_file_extension function."""

    def test_returns_txt_for_text_plain(self):
        """Should return .txt for text/plain MIME type."""
        from tasktriage.gdrive import get_file_extension

        result = get_file_extension("text/plain")
        assert result == ".txt"

    def test_returns_png_for_image_png(self):
        """Should return .png for image/png MIME type."""
        from tasktriage.gdrive import get_file_extension

        result = get_file_extension("image/png")
        assert result == ".png"

    def test_returns_txt_for_unknown_mime_type(self):
        """Should return .txt as default for unknown MIME types."""
        from tasktriage.gdrive import get_file_extension

        result = get_file_extension("application/octet-stream")
        assert result == ".txt"


class TestMimeTypeConstants:
    """Tests for MIME type constants."""

    def test_text_mime_types_contains_text_plain(self):
        """TEXT_MIME_TYPES should include text/plain."""
        from tasktriage.gdrive import TEXT_MIME_TYPES

        assert "text/plain" in TEXT_MIME_TYPES

    def test_image_mime_types_contains_png(self):
        """IMAGE_MIME_TYPES should include image/png."""
        from tasktriage.gdrive import IMAGE_MIME_TYPES

        assert "image/png" in IMAGE_MIME_TYPES

    def test_all_mime_types_is_union(self):
        """ALL_MIME_TYPES should be union of text and image types."""
        from tasktriage.gdrive import TEXT_MIME_TYPES, IMAGE_MIME_TYPES, ALL_MIME_TYPES

        expected = TEXT_MIME_TYPES | IMAGE_MIME_TYPES
        assert ALL_MIME_TYPES == expected
