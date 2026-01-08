"""
Tests for tasktriage.files module.
"""

from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestLoadTaskNotesUsb:
    """Tests for loading task notes from USB/local directory."""

    def test_loads_text_file(self, mock_usb_dir, sample_notes_file):
        """Should load content from a text file."""
        with patch("tasktriage.files.get_all_input_directories", return_value=[mock_usb_dir]), \
             patch("tasktriage.files.get_active_source", return_value="usb"):
            from tasktriage.files import load_task_notes

            content, path, file_date = load_task_notes("daily", "txt")

            assert "Review Q4 budget proposal" in content
            assert path == sample_notes_file
            assert file_date == datetime(2025, 12, 31, 14, 30, 0)

    def test_loads_png_file_with_text_extraction(self, mock_usb_dir, sample_image_file):
        """Should load text from raw_notes.txt for PNG files."""
        # Create the raw_notes.txt file that Sync would create
        raw_notes_path = mock_usb_dir / "20251230_090000.raw_notes.txt"
        raw_notes_path.write_text("Extracted task notes")

        with patch("tasktriage.files.get_all_input_directories", return_value=[mock_usb_dir]), \
             patch("tasktriage.files.get_active_source", return_value="usb"):
            from tasktriage.files import load_task_notes

            content, path, file_date = load_task_notes("daily", "png")

            assert content == "Extracted task notes"
            assert path == sample_image_file

    def test_skips_analysis_files(self, mock_usb_dir, sample_analysis_file):
        """Should skip files that are already analysis files."""
        # Create a notes file at the top level
        notes_path = mock_usb_dir / "20251228_100000.txt"
        notes_path.write_text("Some tasks")

        with patch("tasktriage.files.get_all_input_directories", return_value=[mock_usb_dir]), \
             patch("tasktriage.files.get_active_source", return_value="usb"):
            from tasktriage.files import load_task_notes

            content, path, file_date = load_task_notes("daily", "txt")

            # Should load the notes file, not the analysis file
            assert "Some tasks" in content
            assert ".triaged." not in path.name and "_analysis" not in path.name

    def test_skips_files_with_existing_analysis(self, mock_usb_dir):
        """Should skip notes files that already have an analysis file."""
        daily_dir = mock_usb_dir / "daily"

        # Create a notes file with existing analysis at the top level
        notes_with_analysis = mock_usb_dir / "20251231_143000.txt"
        notes_with_analysis.write_text("Old tasks")
        # Analysis file goes to daily subdirectory (new naming: DD_MM_YYYY.triaged.txt)
        analysis_file = daily_dir / "31_12_2025.triaged.txt"
        analysis_file.write_text("Analysis exists")

        # Create a newer notes file without analysis at the top level
        newer_notes = mock_usb_dir / "20251230_090000.txt"
        newer_notes.write_text("Newer tasks")

        with patch("tasktriage.files.get_all_input_directories", return_value=[mock_usb_dir]), \
             patch("tasktriage.files.get_active_source", return_value="usb"):
            from tasktriage.files import load_task_notes

            content, path, file_date = load_task_notes("daily", "txt")

            # Should load the file without analysis (even though it's older by name)
            assert "Newer tasks" in content

    def test_raises_when_directory_not_found(self, mock_usb_dir):
        """Should raise FileNotFoundError when directory doesn't exist."""
        with patch("tasktriage.files.get_all_input_directories", return_value=[]), \
             patch("tasktriage.files.get_active_source", return_value="usb"):
            from tasktriage.files import load_task_notes

            with pytest.raises(FileNotFoundError, match="No input directories"):
                load_task_notes("daily")

    def test_raises_when_no_unanalyzed_files(self, mock_usb_dir):
        """Should raise FileNotFoundError when all files are analyzed."""
        daily_dir = mock_usb_dir / "daily"
        # Create only an analysis file in daily subdirectory (new naming)
        analysis = daily_dir / "31_12_2025.triaged.txt"
        analysis.write_text("Analysis content")

        with patch("tasktriage.files.get_all_input_directories", return_value=[mock_usb_dir]), \
             patch("tasktriage.files.get_active_source", return_value="usb"):
            from tasktriage.files import load_task_notes

            with pytest.raises(FileNotFoundError, match="No unanalyzed"):
                load_task_notes("daily")


class TestLoadTaskNotesGdrive:
    """Tests for loading task notes from Google Drive."""

    def test_loads_text_file_from_gdrive(self):
        """Should load text file content from Google Drive."""
        mock_client = MagicMock()
        mock_client.list_notes_files.return_value = [
            {"id": "file1", "name": "20251231_143000.txt", "mimeType": "text/plain"}
        ]
        mock_client.file_exists.return_value = False
        mock_client.download_file_text.return_value = "GDrive task content"

        # Mock LOCAL_OUTPUT_DIR in config module
        with patch("tasktriage.config.LOCAL_OUTPUT_DIR", None), \
             patch("tasktriage.files.get_active_source", return_value="gdrive"), \
             patch("tasktriage.gdrive.GoogleDriveClient", return_value=mock_client):
            from tasktriage.files import load_task_notes

            content, path, file_date = load_task_notes("daily", "txt")

            assert content == "GDrive task content"
            assert "gdrive:" in str(path)  # Path normalizes gdrive:// to gdrive:/
            assert file_date == datetime(2025, 12, 31, 14, 30, 0)

    def test_extracts_text_from_png_in_gdrive(self, temp_dir):
        """Should load text from raw_notes.txt for PNG files in Google Drive."""
        # Create the raw_notes.txt file that Sync would create
        raw_notes_path = temp_dir / "20251230_090000.raw_notes.txt"
        raw_notes_path.write_text("Extracted from GDrive image")

        mock_client = MagicMock()
        mock_client.list_notes_files.return_value = [
            {"id": "file1", "name": "20251230_090000.png", "mimeType": "image/png"}
        ]
        mock_client.file_exists.return_value = False

        with patch("tasktriage.config.LOCAL_OUTPUT_DIR", str(temp_dir)), \
             patch("tasktriage.files.get_active_source", return_value="gdrive"), \
             patch("tasktriage.gdrive.GoogleDriveClient", return_value=mock_client):
            from tasktriage.files import load_task_notes

            content, path, file_date = load_task_notes("daily", "png")

            assert content == "Extracted from GDrive image"

    def test_loads_png_with_page_identifier_from_gdrive(self, temp_dir):
        """Should load PNG file with page identifier from Google Drive."""
        # Create the raw_notes.txt file that Sync would create (uses base timestamp without page)
        raw_notes_path = temp_dir / "20251225_073454.raw_notes.txt"
        raw_notes_path.write_text("Extracted from page 1")

        mock_client = MagicMock()
        mock_client.list_notes_files.return_value = [
            {"id": "file1", "name": "20251225_073454_Page_1.png", "mimeType": "image/png"}
        ]
        mock_client.file_exists.return_value = False

        with patch("tasktriage.config.LOCAL_OUTPUT_DIR", str(temp_dir)), \
             patch("tasktriage.files.get_active_source", return_value="gdrive"), \
             patch("tasktriage.gdrive.GoogleDriveClient", return_value=mock_client):
            from tasktriage.files import load_task_notes

            content, path, file_date = load_task_notes("daily", "png")

            assert content == "Extracted from page 1"
            assert file_date == datetime(2025, 12, 25, 7, 34, 54)

    def test_skips_gdrive_page_file_with_existing_analysis(self):
        """Should skip GDrive page file when analysis exists for that timestamp."""
        mock_client = MagicMock()
        mock_client.list_notes_files.return_value = [
            {"id": "file1", "name": "20251228_100000_Page_1.png", "mimeType": "image/png"},
            {"id": "file2", "name": "20251227_090000.txt", "mimeType": "text/plain"},
        ]
        # Analysis exists for first file's date (new naming: DD_MM_YYYY.triaged.txt)
        def file_exists_side_effect(subfolder, filename):
            return filename == "28_12_2025.triaged.txt"

        mock_client.file_exists.side_effect = file_exists_side_effect
        mock_client.download_file_text.return_value = "Older notes from text file"

        with patch("tasktriage.files.get_active_source", return_value="gdrive"), \
             patch("tasktriage.gdrive.GoogleDriveClient", return_value=mock_client):
            from tasktriage.files import load_task_notes

            content, path, file_date = load_task_notes("daily", "txt")

            # Should load the second file since first file's timestamp has analysis
            assert content == "Older notes from text file"
            assert file_date == datetime(2025, 12, 27, 9, 0, 0)

    def test_checks_analysis_by_timestamp_not_full_filename_gdrive(self, temp_dir):
        """Should check for analysis using date format, not full filename with page identifier."""
        # Create the raw_notes.txt file that Sync would create
        raw_notes_path = temp_dir / "20251228_100000.raw_notes.txt"
        raw_notes_path.write_text("Extracted text")

        mock_client = MagicMock()
        mock_client.list_notes_files.return_value = [
            {"id": "file1", "name": "20251228_100000_Page_1.png", "mimeType": "image/png"},
        ]
        mock_client.file_exists.return_value = False

        with patch("tasktriage.config.LOCAL_OUTPUT_DIR", str(temp_dir)), \
             patch("tasktriage.files.get_active_source", return_value="gdrive"), \
             patch("tasktriage.gdrive.GoogleDriveClient", return_value=mock_client):
            from tasktriage.files import load_task_notes
            load_task_notes("daily", "png")

            # Verify file_exists was called with date-based analysis filename (DD_MM_YYYY.triaged.txt)
            mock_client.file_exists.assert_called_with(
                "daily", "28_12_2025.triaged.txt"
            )


class TestSaveAnalysis:
    """Tests for saving analysis files."""

    def test_saves_analysis_to_usb(self, mock_usb_dir, sample_notes_file):
        """Should save analysis file next to the input file."""
        from tasktriage.files import save_analysis

        analysis_content = "# Daily Execution Order\n\n1. Task one"

        with patch("tasktriage.files.get_primary_input_directory", return_value=mock_usb_dir):
            output_path = save_analysis(analysis_content, sample_notes_file, "daily")

            assert output_path.exists()
            assert ".triaged." in output_path.name
            content = output_path.read_text()
            assert "Triaged Tasks" in content
            assert "Task one" in content

    def test_saves_analysis_to_gdrive(self, mock_usb_dir):
        """Should upload analysis to Google Drive for gdrive:// paths."""
        mock_client = MagicMock()

        # Mock LOCAL_OUTPUT_DIR in config module, not files module
        with patch("tasktriage.config.LOCAL_OUTPUT_DIR", None), \
             patch("tasktriage.gdrive.GoogleDriveClient", return_value=mock_client):
            from tasktriage.files import _save_analysis_gdrive

            # Test the gdrive function directly since Path normalizes gdrive://
            virtual_path = Path("gdrive://daily/20251231_143000.txt")
            analysis_content = "Analysis content"

            output_path = _save_analysis_gdrive(analysis_content, virtual_path, "daily")

            mock_client.upload_file.assert_called_once()
            assert "gdrive:" in str(output_path)

    def test_save_analysis_routes_to_gdrive_with_normalized_path(self):
        """Should route to gdrive save when path is normalized (gdrive:/ not gdrive://)."""
        mock_client = MagicMock()

        # Mock LOCAL_OUTPUT_DIR in config module, not files module
        with patch("tasktriage.config.LOCAL_OUTPUT_DIR", None), \
             patch("tasktriage.gdrive.GoogleDriveClient", return_value=mock_client):
            from tasktriage.files import save_analysis

            # Path normalizes gdrive:// to gdrive:/ - this should still route to gdrive
            virtual_path = Path("gdrive://daily/20251231_143000.txt")
            # Verify the path was normalized
            assert str(virtual_path).startswith("gdrive:/")
            assert not str(virtual_path).startswith("gdrive://")

            output_path = save_analysis("Analysis content", virtual_path, "daily")

            # Should have called gdrive upload, not tried to write locally
            mock_client.upload_file.assert_called_once()
            assert "gdrive:" in str(output_path)

    def test_saves_analysis_with_page_identifier_usb(self, mock_usb_dir):
        """Should save analysis using date only (DD_MM_YYYY), not page identifier, for USB."""
        daily_dir = mock_usb_dir / "daily"
        page_file = daily_dir / "20251228_100000_Page_1.png"
        page_file.write_bytes(b"fake png data")

        from tasktriage.files import save_analysis

        output_path = save_analysis("Analysis content", page_file, "daily")

        # Should use date format DD_MM_YYYY without page identifier
        assert output_path.name == "28_12_2025.triaged.txt"
        assert "_Page_" not in output_path.name

    def test_saves_analysis_with_page_identifier_gdrive(self):
        """Should save analysis using date only (DD_MM_YYYY), not page identifier, for GDrive."""
        mock_client = MagicMock()

        # Mock LOCAL_OUTPUT_DIR in config module, not files module
        with patch("tasktriage.config.LOCAL_OUTPUT_DIR", None), \
             patch("tasktriage.gdrive.GoogleDriveClient", return_value=mock_client):
            from tasktriage.files import _save_analysis_gdrive

            virtual_path = Path("gdrive://daily/20251228_100000_Page_1.png")
            analysis_content = "Analysis content"

            output_path = _save_analysis_gdrive(analysis_content, virtual_path, "daily")

            # Verify upload was called with date-based filename (DD_MM_YYYY.triaged.txt)
            call_args = mock_client.upload_file.call_args
            uploaded_filename = call_args[0][1]  # Second positional arg is filename
            assert uploaded_filename == "28_12_2025.triaged.txt"
            assert "_Page_" not in uploaded_filename

    def test_formats_output_with_header(self, mock_usb_dir, sample_notes_file):
        """Should format output with proper header."""
        from tasktriage.files import save_analysis

        with patch("tasktriage.files.USB_DIR", str(mock_usb_dir)):
            output_path = save_analysis("Content", sample_notes_file, "daily")

            content = output_path.read_text()
            assert "Triaged Tasks" in content
            assert "=" * 40 in content

    def test_always_saves_as_txt(self, mock_usb_dir):
        """Should always save as .txt regardless of input format."""
        daily_dir = mock_usb_dir / "daily"
        png_input = daily_dir / "20251230_090000.png"
        png_input.write_bytes(b"fake png data")

        from tasktriage.files import save_analysis

        with patch("tasktriage.files.USB_DIR", str(mock_usb_dir)):
            output_path = save_analysis("Analysis", png_input, "daily")

            assert output_path.suffix == ".txt"


class TestFileExtensionConstants:
    """Tests for file extension constants."""

    def test_text_extensions_contains_txt(self):
        """TEXT_EXTENSIONS should include .txt."""
        from tasktriage.files import TEXT_EXTENSIONS

        assert ".txt" in TEXT_EXTENSIONS

    def test_all_extensions_includes_both(self):
        """ALL_EXTENSIONS should include both text and image extensions."""
        from tasktriage.files import ALL_EXTENSIONS, TEXT_EXTENSIONS
        from tasktriage.image import IMAGE_EXTENSIONS

        assert TEXT_EXTENSIONS.issubset(ALL_EXTENSIONS)
        assert IMAGE_EXTENSIONS.issubset(ALL_EXTENSIONS)


class TestExtractTimestamp:
    """Tests for _extract_timestamp helper function."""

    def test_extracts_from_simple_filename(self):
        """Should extract timestamp from simple filename."""
        from tasktriage.files import _extract_timestamp

        result = _extract_timestamp("20251225_073454.txt")
        assert result == "20251225_073454"

    def test_extracts_from_png_filename(self):
        """Should extract timestamp from PNG filename."""
        from tasktriage.files import _extract_timestamp

        result = _extract_timestamp("20251225_073454.png")
        assert result == "20251225_073454"

    def test_extracts_from_page_identifier_filename(self):
        """Should extract timestamp from filename with page identifier."""
        from tasktriage.files import _extract_timestamp

        result = _extract_timestamp("20251225_073454_Page_1.png")
        assert result == "20251225_073454"

    def test_extracts_from_multi_digit_page(self):
        """Should extract timestamp from filename with multi-digit page number."""
        from tasktriage.files import _extract_timestamp

        result = _extract_timestamp("20251225_073454_Page_12.png")
        assert result == "20251225_073454"

    def test_returns_none_for_invalid_filename(self):
        """Should return None for invalid filename."""
        from tasktriage.files import _extract_timestamp

        result = _extract_timestamp("invalid_filename.txt")
        assert result is None

    def test_returns_none_for_analysis_filename(self):
        """Should return None for analysis filename without proper timestamp."""
        from tasktriage.files import _extract_timestamp

        # Analysis filenames have the format timestamp.daily_analysis.txt
        # The stem is "timestamp.daily_analysis" which should still extract properly
        result = _extract_timestamp("20251225_073454.daily_analysis.txt")
        # The stem is "20251225_073454.daily_analysis" which has a dot
        # After splitting, we'd check "20251225_073454.daily_analysis"
        # But our function only looks at stem, not handling dots in stem
        # Since stem="20251225_073454.daily_analysis" is not 15 chars, returns None
        assert result is None


class TestExampleFiles:
    """Tests using example files from tests/examples directory."""

    def test_example_text_file_exists(self, example_text_file):
        """Example text file should exist."""
        assert example_text_file.exists()
        assert example_text_file.suffix == ".txt"

    def test_example_image_file_exists(self, example_image_file):
        """Example image file should exist."""
        assert example_image_file.exists()
        assert example_image_file.suffix == ".png"

    def test_example_text_file_parses_correctly(self, example_text_file):
        """Example text file should parse with correct datetime."""
        from tasktriage.gdrive import parse_filename_datetime

        result = parse_filename_datetime(example_text_file.name)
        assert result == datetime(2025, 12, 25, 7, 43, 53)

    def test_example_image_file_parses_correctly(self, example_image_file):
        """Example image file with page identifier should parse correctly."""
        from tasktriage.gdrive import parse_filename_datetime

        result = parse_filename_datetime(example_image_file.name)
        assert result == datetime(2025, 12, 25, 7, 43, 53)

    def test_example_files_have_matching_timestamps(self, example_text_file, example_image_file):
        """Example text and image files should have matching timestamps."""
        from tasktriage.files import _extract_timestamp

        text_timestamp = _extract_timestamp(example_text_file.name)
        image_timestamp = _extract_timestamp(example_image_file.name)

        assert text_timestamp == image_timestamp
        assert text_timestamp == "20251225_074353"


class TestParseFilenameDateTime:
    """Tests for _parse_filename_datetime helper function."""

    def test_parses_simple_filename(self):
        """Should parse datetime from simple filename."""
        from tasktriage.gdrive import parse_filename_datetime

        result = parse_filename_datetime("20251225_073454.txt")
        assert result == datetime(2025, 12, 25, 7, 34, 54)

    def test_parses_png_filename(self):
        """Should parse datetime from PNG filename."""
        from tasktriage.gdrive import parse_filename_datetime

        result = parse_filename_datetime("20251231_143000.png")
        assert result == datetime(2025, 12, 31, 14, 30, 0)

    def test_parses_page_identifier_filename(self):
        """Should parse datetime from filename with page identifier."""
        from tasktriage.gdrive import parse_filename_datetime

        result = parse_filename_datetime("20251225_073454_Page_1.png")
        assert result == datetime(2025, 12, 25, 7, 34, 54)

    def test_parses_multi_digit_page(self):
        """Should parse datetime from filename with multi-digit page number."""
        from tasktriage.gdrive import parse_filename_datetime

        result = parse_filename_datetime("20251225_073454_Page_15.png")
        assert result == datetime(2025, 12, 25, 7, 34, 54)

    def test_returns_none_for_invalid_filename(self):
        """Should return None for invalid filename."""
        from tasktriage.gdrive import parse_filename_datetime

        result = parse_filename_datetime("not_a_timestamp.txt")
        assert result is None

    def test_returns_none_for_invalid_date(self):
        """Should return None for invalid date values."""
        from tasktriage.gdrive import parse_filename_datetime

        # Month 13 is invalid
        result = parse_filename_datetime("20251325_073454.txt")
        assert result is None


class TestLoadTaskNotesWithPageIdentifiers:
    """Tests for loading task notes with page identifier filenames."""

    def test_loads_page_identifier_file(self, mock_usb_dir):
        """Should load PNG file with page identifier in filename."""
        page_file = mock_usb_dir / "20251228_100000_Page_1.png"
        page_file.write_bytes(b"fake png data")

        # Create the raw_notes.txt file that Sync would create (uses base timestamp without page)
        raw_notes_path = mock_usb_dir / "20251228_100000.raw_notes.txt"
        raw_notes_path.write_text("Extracted text from page")

        with patch("tasktriage.files.get_all_input_directories", return_value=[mock_usb_dir]), \
             patch("tasktriage.files.get_active_source", return_value="usb"):
            from tasktriage.files import load_task_notes

            content, path, file_date = load_task_notes("daily", "png")

            assert content == "Extracted text from page"
            assert file_date == datetime(2025, 12, 28, 10, 0, 0)

    def test_skips_page_file_with_existing_timestamp_analysis(self, mock_usb_dir):
        """Should skip page file when analysis exists for that date."""
        daily_dir = mock_usb_dir / "daily"

        # Create page file at top level
        page_file = mock_usb_dir / "20251228_100000_Page_1.png"
        page_file.write_bytes(b"fake png data")

        # Create raw_notes.txt for the page file
        raw_notes_path = mock_usb_dir / "20251228_100000.raw_notes.txt"
        raw_notes_path.write_text("Page content")

        # Create analysis file using date format (in daily subdirectory)
        analysis_file = daily_dir / "28_12_2025.triaged.txt"
        analysis_file.write_text("Existing analysis")

        # Create an older file without analysis at top level
        older_file = mock_usb_dir / "20251227_090000.txt"
        older_file.write_text("Older notes")

        with patch("tasktriage.files.get_all_input_directories", return_value=[mock_usb_dir]), \
             patch("tasktriage.files.get_active_source", return_value="usb"):
            from tasktriage.files import load_task_notes

            content, path, file_date = load_task_notes("daily", "txt")

            # Should load the older file since the page file's date has analysis
            assert "Older notes" in content
            assert file_date == datetime(2025, 12, 27, 9, 0, 0)
