"""
Tests for tasker.gdrive module.
"""

import io
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest


class TestGoogleDriveClientInit:
    """Tests for GoogleDriveClient initialization."""

    def test_init_with_env_vars(self, temp_dir, monkeypatch):
        """Should initialize using environment variables."""
        credentials_path = temp_dir / "credentials.json"
        credentials_path.write_text('{"type": "service_account"}')

        monkeypatch.setenv("GOOGLE_CREDENTIALS_PATH", str(credentials_path))
        monkeypatch.setenv("GOOGLE_DRIVE_FOLDER_ID", "test-folder-id")

        from tasker.gdrive import GoogleDriveClient

        client = GoogleDriveClient()
        assert client.credentials_path == str(credentials_path)
        assert client.folder_id == "test-folder-id"

    def test_init_with_explicit_params(self, temp_dir):
        """Should initialize with explicitly provided parameters."""
        credentials_path = temp_dir / "credentials.json"
        credentials_path.write_text('{"type": "service_account"}')

        from tasker.gdrive import GoogleDriveClient

        client = GoogleDriveClient(
            credentials_path=str(credentials_path),
            folder_id="explicit-folder-id"
        )
        assert client.credentials_path == str(credentials_path)
        assert client.folder_id == "explicit-folder-id"

    def test_raises_when_credentials_path_not_set(self, monkeypatch):
        """Should raise ValueError when credentials path is not set."""
        monkeypatch.delenv("GOOGLE_CREDENTIALS_PATH", raising=False)
        monkeypatch.setenv("GOOGLE_DRIVE_FOLDER_ID", "test-folder-id")

        from tasker.gdrive import GoogleDriveClient

        with pytest.raises(ValueError, match="credentials path not set"):
            GoogleDriveClient()

    def test_raises_when_folder_id_not_set(self, temp_dir, monkeypatch):
        """Should raise ValueError when folder ID is not set."""
        credentials_path = temp_dir / "credentials.json"
        credentials_path.write_text('{"type": "service_account"}')

        monkeypatch.setenv("GOOGLE_CREDENTIALS_PATH", str(credentials_path))
        monkeypatch.delenv("GOOGLE_DRIVE_FOLDER_ID", raising=False)

        from tasker.gdrive import GoogleDriveClient

        with pytest.raises(ValueError, match="folder ID not set"):
            GoogleDriveClient()

    def test_raises_when_credentials_file_not_found(self, monkeypatch):
        """Should raise FileNotFoundError when credentials file doesn't exist."""
        monkeypatch.setenv("GOOGLE_CREDENTIALS_PATH", "/nonexistent/credentials.json")
        monkeypatch.setenv("GOOGLE_DRIVE_FOLDER_ID", "test-folder-id")

        from tasker.gdrive import GoogleDriveClient

        with pytest.raises(FileNotFoundError, match="credentials file not found"):
            GoogleDriveClient()


class TestGoogleDriveClientService:
    """Tests for GoogleDriveClient service property."""

    @pytest.fixture
    def mock_credentials(self, temp_dir, monkeypatch):
        """Set up mock credentials."""
        credentials_path = temp_dir / "credentials.json"
        credentials_path.write_text('{"type": "service_account"}')
        monkeypatch.setenv("GOOGLE_CREDENTIALS_PATH", str(credentials_path))
        monkeypatch.setenv("GOOGLE_DRIVE_FOLDER_ID", "test-folder-id")
        return credentials_path

    def test_service_lazily_initialized(self, mock_credentials):
        """Service should be lazily initialized on first access."""
        with patch("tasker.gdrive.service_account.Credentials.from_service_account_file") as mock_creds, \
             patch("tasker.gdrive.build") as mock_build:
            mock_creds.return_value = MagicMock()
            mock_build.return_value = MagicMock()

            from tasker.gdrive import GoogleDriveClient

            client = GoogleDriveClient()
            assert client._service is None

            # Access service property
            _ = client.service

            mock_creds.assert_called_once()
            mock_build.assert_called_once()

    def test_service_cached_after_first_access(self, mock_credentials):
        """Service should be cached after first initialization."""
        with patch("tasker.gdrive.service_account.Credentials.from_service_account_file") as mock_creds, \
             patch("tasker.gdrive.build") as mock_build:
            mock_creds.return_value = MagicMock()
            mock_service = MagicMock()
            mock_build.return_value = mock_service

            from tasker.gdrive import GoogleDriveClient

            client = GoogleDriveClient()

            # Access service multiple times
            service1 = client.service
            service2 = client.service

            assert service1 is service2
            assert mock_build.call_count == 1


class TestGoogleDriveClientOperations:
    """Tests for GoogleDriveClient file operations."""

    @pytest.fixture
    def mock_client(self, temp_dir, monkeypatch):
        """Create a mock GoogleDriveClient with mocked service."""
        credentials_path = temp_dir / "credentials.json"
        credentials_path.write_text('{"type": "service_account"}')
        monkeypatch.setenv("GOOGLE_CREDENTIALS_PATH", str(credentials_path))
        monkeypatch.setenv("GOOGLE_DRIVE_FOLDER_ID", "root-folder-id")

        with patch("tasker.gdrive.service_account.Credentials.from_service_account_file"), \
             patch("tasker.gdrive.build") as mock_build:
            mock_service = MagicMock()
            mock_build.return_value = mock_service

            from tasker.gdrive import GoogleDriveClient

            client = GoogleDriveClient()
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
        with patch("tasker.gdrive.MediaIoBaseDownload") as mock_downloader_class:
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

    def test_returns_true_when_configured(self, temp_dir, monkeypatch):
        """Should return True when both credentials and folder ID are set."""
        credentials_path = temp_dir / "credentials.json"
        credentials_path.write_text('{"type": "service_account"}')

        monkeypatch.setenv("GOOGLE_CREDENTIALS_PATH", str(credentials_path))
        monkeypatch.setenv("GOOGLE_DRIVE_FOLDER_ID", "test-folder-id")

        from tasker.gdrive import is_gdrive_configured

        assert is_gdrive_configured() is True

    def test_returns_false_when_credentials_not_set(self, monkeypatch):
        """Should return False when credentials path is not set."""
        monkeypatch.delenv("GOOGLE_CREDENTIALS_PATH", raising=False)
        monkeypatch.setenv("GOOGLE_DRIVE_FOLDER_ID", "test-folder-id")

        from tasker.gdrive import is_gdrive_configured

        assert is_gdrive_configured() is False

    def test_returns_false_when_folder_id_not_set(self, temp_dir, monkeypatch):
        """Should return False when folder ID is not set."""
        credentials_path = temp_dir / "credentials.json"
        credentials_path.write_text('{"type": "service_account"}')

        monkeypatch.setenv("GOOGLE_CREDENTIALS_PATH", str(credentials_path))
        monkeypatch.delenv("GOOGLE_DRIVE_FOLDER_ID", raising=False)

        from tasker.gdrive import is_gdrive_configured

        assert is_gdrive_configured() is False

    def test_returns_false_when_credentials_file_missing(self, monkeypatch):
        """Should return False when credentials file doesn't exist."""
        monkeypatch.setenv("GOOGLE_CREDENTIALS_PATH", "/nonexistent/credentials.json")
        monkeypatch.setenv("GOOGLE_DRIVE_FOLDER_ID", "test-folder-id")

        from tasker.gdrive import is_gdrive_configured

        assert is_gdrive_configured() is False


class TestParseFilenameDatetime:
    """Tests for parse_filename_datetime function."""

    def test_parses_txt_filename(self):
        """Should parse datetime from .txt filename."""
        from tasker.gdrive import parse_filename_datetime

        result = parse_filename_datetime("20251231_143000.txt")

        assert result == datetime(2025, 12, 31, 14, 30, 0)

    def test_parses_png_filename(self):
        """Should parse datetime from .png filename."""
        from tasker.gdrive import parse_filename_datetime

        result = parse_filename_datetime("20251230_090000.png")

        assert result == datetime(2025, 12, 30, 9, 0, 0)

    def test_parses_analysis_filename(self):
        """Should parse datetime from analysis filename."""
        from tasker.gdrive import parse_filename_datetime

        result = parse_filename_datetime("20251229_080000.daily_analysis.txt")

        assert result == datetime(2025, 12, 29, 8, 0, 0)

    def test_parses_page_identifier_filename(self):
        """Should parse datetime from filename with page identifier."""
        from tasker.gdrive import parse_filename_datetime

        result = parse_filename_datetime("20251225_073454_Page_1.png")

        assert result == datetime(2025, 12, 25, 7, 34, 54)

    def test_parses_multi_digit_page_identifier(self):
        """Should parse datetime from filename with multi-digit page number."""
        from tasker.gdrive import parse_filename_datetime

        result = parse_filename_datetime("20251225_073454_Page_15.png")

        assert result == datetime(2025, 12, 25, 7, 34, 54)

    def test_returns_none_for_invalid_format(self):
        """Should return None for invalid filename format."""
        from tasker.gdrive import parse_filename_datetime

        result = parse_filename_datetime("invalid_filename.txt")

        assert result is None

    def test_returns_none_for_partial_timestamp(self):
        """Should return None for partial timestamp."""
        from tasker.gdrive import parse_filename_datetime

        result = parse_filename_datetime("20251231.txt")

        assert result is None


class TestExtractTimestampFromFilename:
    """Tests for extract_timestamp_from_filename function."""

    def test_extracts_from_simple_filename(self):
        """Should extract timestamp from simple filename."""
        from tasker.gdrive import extract_timestamp_from_filename

        result = extract_timestamp_from_filename("20251231_143000.txt")
        assert result == "20251231_143000"

    def test_extracts_from_png_filename(self):
        """Should extract timestamp from PNG filename."""
        from tasker.gdrive import extract_timestamp_from_filename

        result = extract_timestamp_from_filename("20251225_073454.png")
        assert result == "20251225_073454"

    def test_extracts_from_page_identifier_filename(self):
        """Should extract timestamp from filename with page identifier."""
        from tasker.gdrive import extract_timestamp_from_filename

        result = extract_timestamp_from_filename("20251225_073454_Page_1.png")
        assert result == "20251225_073454"

    def test_extracts_from_multi_digit_page(self):
        """Should extract timestamp from filename with multi-digit page number."""
        from tasker.gdrive import extract_timestamp_from_filename

        result = extract_timestamp_from_filename("20251225_073454_Page_12.png")
        assert result == "20251225_073454"

    def test_extracts_from_analysis_filename(self):
        """Should extract timestamp from analysis filename."""
        from tasker.gdrive import extract_timestamp_from_filename

        result = extract_timestamp_from_filename("20251225_073454.daily_analysis.txt")
        assert result == "20251225_073454"

    def test_returns_none_for_invalid_filename(self):
        """Should return None for invalid filename."""
        from tasker.gdrive import extract_timestamp_from_filename

        result = extract_timestamp_from_filename("invalid_filename.txt")
        assert result is None

    def test_returns_none_for_short_filename(self):
        """Should return None for filename without proper timestamp."""
        from tasker.gdrive import extract_timestamp_from_filename

        result = extract_timestamp_from_filename("20251225.txt")
        assert result is None


class TestGetFileExtension:
    """Tests for get_file_extension function."""

    def test_returns_txt_for_text_plain(self):
        """Should return .txt for text/plain MIME type."""
        from tasker.gdrive import get_file_extension

        result = get_file_extension("text/plain")
        assert result == ".txt"

    def test_returns_png_for_image_png(self):
        """Should return .png for image/png MIME type."""
        from tasker.gdrive import get_file_extension

        result = get_file_extension("image/png")
        assert result == ".png"

    def test_returns_txt_for_unknown_mime_type(self):
        """Should return .txt as default for unknown MIME types."""
        from tasker.gdrive import get_file_extension

        result = get_file_extension("application/octet-stream")
        assert result == ".txt"


class TestMimeTypeConstants:
    """Tests for MIME type constants."""

    def test_text_mime_types_contains_text_plain(self):
        """TEXT_MIME_TYPES should include text/plain."""
        from tasker.gdrive import TEXT_MIME_TYPES

        assert "text/plain" in TEXT_MIME_TYPES

    def test_image_mime_types_contains_png(self):
        """IMAGE_MIME_TYPES should include image/png."""
        from tasker.gdrive import IMAGE_MIME_TYPES

        assert "image/png" in IMAGE_MIME_TYPES

    def test_all_mime_types_is_union(self):
        """ALL_MIME_TYPES should be union of text and image types."""
        from tasker.gdrive import TEXT_MIME_TYPES, IMAGE_MIME_TYPES, ALL_MIME_TYPES

        expected = TEXT_MIME_TYPES | IMAGE_MIME_TYPES
        assert ALL_MIME_TYPES == expected
