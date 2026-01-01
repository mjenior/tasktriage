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
        with patch("tasktriage.files.USB_DIR", str(mock_usb_dir)), \
             patch("tasktriage.files.get_active_source", return_value="usb"):
            from tasktriage.files import load_task_notes

            content, path, file_date = load_task_notes("daily")

            assert "Review Q4 budget proposal" in content
            assert path == sample_notes_file
            assert file_date == datetime(2025, 12, 31, 14, 30, 0)

    def test_loads_png_file_with_text_extraction(self, mock_usb_dir, sample_image_file):
        """Should extract text from PNG file using vision API."""
        with patch("tasktriage.files.USB_DIR", str(mock_usb_dir)), \
             patch("tasktriage.files.get_active_source", return_value="usb"), \
             patch("tasktriage.files.extract_text_from_image") as mock_extract:
            mock_extract.return_value = "Extracted task notes"

            from tasktriage.files import load_task_notes

            content, path, file_date = load_task_notes("daily")

            assert content == "Extracted task notes"
            mock_extract.assert_called_once_with(sample_image_file)

    def test_skips_analysis_files(self, mock_usb_dir, sample_analysis_file):
        """Should skip files that are already analysis files."""
        # Create a notes file
        daily_dir = mock_usb_dir / "daily"
        notes_path = daily_dir / "20251228_100000.txt"
        notes_path.write_text("Some tasks")

        with patch("tasktriage.files.USB_DIR", str(mock_usb_dir)), \
             patch("tasktriage.files.get_active_source", return_value="usb"):
            from tasktriage.files import load_task_notes

            content, path, file_date = load_task_notes("daily")

            # Should load the notes file, not the analysis file
            assert "Some tasks" in content
            assert "daily_analysis" not in path.name

    def test_skips_files_with_existing_analysis(self, mock_usb_dir):
        """Should skip notes files that already have an analysis file."""
        daily_dir = mock_usb_dir / "daily"

        # Create a notes file with existing analysis
        notes_with_analysis = daily_dir / "20251231_143000.txt"
        notes_with_analysis.write_text("Old tasks")
        analysis_file = daily_dir / "20251231_143000.daily_analysis.txt"
        analysis_file.write_text("Analysis exists")

        # Create a newer notes file without analysis
        newer_notes = daily_dir / "20251230_090000.txt"
        newer_notes.write_text("Newer tasks")

        with patch("tasktriage.files.USB_DIR", str(mock_usb_dir)), \
             patch("tasktriage.files.get_active_source", return_value="usb"):
            from tasktriage.files import load_task_notes

            content, path, file_date = load_task_notes("daily")

            # Should load the file without analysis (even though it's older by name)
            assert "Newer tasks" in content

    def test_raises_when_directory_not_found(self, mock_usb_dir):
        """Should raise FileNotFoundError when directory doesn't exist."""
        with patch("tasktriage.files.USB_DIR", "/nonexistent/path"), \
             patch("tasktriage.files.get_active_source", return_value="usb"):
            from tasktriage.files import load_task_notes

            with pytest.raises(FileNotFoundError, match="not found"):
                load_task_notes("daily")

    def test_raises_when_no_unanalyzed_files(self, mock_usb_dir):
        """Should raise FileNotFoundError when all files are analyzed."""
        daily_dir = mock_usb_dir / "daily"
        # Create only an analysis file
        analysis = daily_dir / "20251231_143000.daily_analysis.txt"
        analysis.write_text("Analysis content")

        with patch("tasktriage.files.USB_DIR", str(mock_usb_dir)), \
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

        with patch("tasktriage.files.get_active_source", return_value="gdrive"), \
             patch("tasktriage.gdrive.GoogleDriveClient", return_value=mock_client):
            from tasktriage.files import load_task_notes

            content, path, file_date = load_task_notes("daily")

            assert content == "GDrive task content"
            assert "gdrive:" in str(path)  # Path normalizes gdrive:// to gdrive:/
            assert file_date == datetime(2025, 12, 31, 14, 30, 0)

    def test_extracts_text_from_png_in_gdrive(self, temp_dir):
        """Should extract text from PNG files in Google Drive."""
        mock_client = MagicMock()
        mock_client.list_notes_files.return_value = [
            {"id": "file1", "name": "20251230_090000.png", "mimeType": "image/png"}
        ]
        mock_client.file_exists.return_value = False
        # Return minimal PNG bytes
        mock_client.download_file.return_value = bytes([
            0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,
            0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,
            0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
            0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,
            0xDE, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E,
            0x44, 0xAE, 0x42, 0x60, 0x82
        ])

        with patch("tasktriage.files.get_active_source", return_value="gdrive"), \
             patch("tasktriage.gdrive.GoogleDriveClient", return_value=mock_client), \
             patch("tasktriage.files.extract_text_from_image") as mock_extract:
            mock_extract.return_value = "Extracted from GDrive image"

            from tasktriage.files import load_task_notes

            content, path, file_date = load_task_notes("daily")

            assert content == "Extracted from GDrive image"

    def test_loads_png_with_page_identifier_from_gdrive(self, temp_dir):
        """Should load PNG file with page identifier from Google Drive."""
        mock_client = MagicMock()
        mock_client.list_notes_files.return_value = [
            {"id": "file1", "name": "20251225_073454_Page_1.png", "mimeType": "image/png"}
        ]
        mock_client.file_exists.return_value = False
        mock_client.download_file.return_value = bytes([
            0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,
            0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,
            0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
            0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,
            0xDE, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E,
            0x44, 0xAE, 0x42, 0x60, 0x82
        ])

        with patch("tasktriage.files.get_active_source", return_value="gdrive"), \
             patch("tasktriage.gdrive.GoogleDriveClient", return_value=mock_client), \
             patch("tasktriage.files.extract_text_from_image") as mock_extract:
            mock_extract.return_value = "Extracted from page 1"

            from tasktriage.files import load_task_notes

            content, path, file_date = load_task_notes("daily")

            assert content == "Extracted from page 1"
            assert file_date == datetime(2025, 12, 25, 7, 34, 54)

    def test_skips_gdrive_page_file_with_existing_analysis(self):
        """Should skip GDrive page file when analysis exists for that timestamp."""
        mock_client = MagicMock()
        mock_client.list_notes_files.return_value = [
            {"id": "file1", "name": "20251228_100000_Page_1.png", "mimeType": "image/png"},
            {"id": "file2", "name": "20251227_090000.txt", "mimeType": "text/plain"},
        ]
        # Analysis exists for first file's timestamp (not including page identifier)
        def file_exists_side_effect(subfolder, filename):
            return filename == "20251228_100000.daily_analysis.txt"

        mock_client.file_exists.side_effect = file_exists_side_effect
        mock_client.download_file_text.return_value = "Older notes from text file"

        with patch("tasktriage.files.get_active_source", return_value="gdrive"), \
             patch("tasktriage.gdrive.GoogleDriveClient", return_value=mock_client):
            from tasktriage.files import load_task_notes

            content, path, file_date = load_task_notes("daily")

            # Should load the second file since first file's timestamp has analysis
            assert content == "Older notes from text file"
            assert file_date == datetime(2025, 12, 27, 9, 0, 0)

    def test_checks_analysis_by_timestamp_not_full_filename_gdrive(self):
        """Should check for analysis using timestamp, not full filename with page identifier."""
        mock_client = MagicMock()
        mock_client.list_notes_files.return_value = [
            {"id": "file1", "name": "20251228_100000_Page_1.png", "mimeType": "image/png"},
        ]
        mock_client.file_exists.return_value = False
        mock_client.download_file.return_value = bytes([
            0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,
            0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,
            0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
            0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,
            0xDE, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E,
            0x44, 0xAE, 0x42, 0x60, 0x82
        ])

        with patch("tasktriage.files.get_active_source", return_value="gdrive"), \
             patch("tasktriage.gdrive.GoogleDriveClient", return_value=mock_client), \
             patch("tasktriage.files.extract_text_from_image") as mock_extract:
            mock_extract.return_value = "Extracted text"

            from tasktriage.files import load_task_notes
            load_task_notes("daily")

            # Verify file_exists was called with timestamp-based analysis filename
            mock_client.file_exists.assert_called_with(
                "daily", "20251228_100000.daily_analysis.txt"
            )


class TestCollectWeeklyAnalysesUsb:
    """Tests for collecting weekly analyses from USB."""

    def test_collects_analyses_from_previous_week(self, mock_usb_dir):
        """Should collect all daily analyses from the previous week."""
        daily_dir = mock_usb_dir / "daily"

        # Calculate dates for last week
        today = datetime.now()
        days_since_sunday = (today.weekday() + 1) % 7
        last_sunday = today - timedelta(days=days_since_sunday)
        last_monday = last_sunday - timedelta(days=6)

        # Create analysis files for last week
        for i, day in enumerate([last_monday, last_monday + timedelta(days=2)]):
            timestamp = day.strftime("%Y%m%d_080000")
            analysis_path = daily_dir / f"{timestamp}.daily_analysis.txt"
            analysis_path.write_text(f"Analysis for day {i + 1}")

        with patch("tasktriage.files.USB_DIR", str(mock_usb_dir)), \
             patch("tasktriage.files.get_active_source", return_value="usb"):
            from tasktriage.files import collect_weekly_analyses

            combined, output_path, week_start, week_end = collect_weekly_analyses()

            assert "Analysis for day 1" in combined
            assert "Analysis for day 2" in combined
            assert "weekly" in str(output_path)

    def test_creates_weekly_directory_if_missing(self, mock_usb_dir):
        """Should create weekly directory if it doesn't exist."""
        # Remove weekly directory
        weekly_dir = mock_usb_dir / "weekly"
        weekly_dir.rmdir()

        daily_dir = mock_usb_dir / "daily"

        # Create at least one analysis file
        today = datetime.now()
        days_since_sunday = (today.weekday() + 1) % 7
        last_sunday = today - timedelta(days=days_since_sunday)
        last_monday = last_sunday - timedelta(days=6)
        timestamp = last_monday.strftime("%Y%m%d_080000")
        (daily_dir / f"{timestamp}.daily_analysis.txt").write_text("Analysis")

        with patch("tasktriage.files.USB_DIR", str(mock_usb_dir)), \
             patch("tasktriage.files.get_active_source", return_value="usb"):
            from tasktriage.files import collect_weekly_analyses

            collect_weekly_analyses()

            assert weekly_dir.exists()

    def test_raises_when_no_analyses_found(self, mock_usb_dir):
        """Should raise FileNotFoundError when no analyses found for the week."""
        with patch("tasktriage.files.USB_DIR", str(mock_usb_dir)), \
             patch("tasktriage.files.get_active_source", return_value="usb"):
            from tasktriage.files import collect_weekly_analyses

            with pytest.raises(FileNotFoundError, match="No daily analysis files"):
                collect_weekly_analyses()


class TestSaveAnalysis:
    """Tests for saving analysis files."""

    def test_saves_analysis_to_usb(self, mock_usb_dir, sample_notes_file):
        """Should save analysis file next to the input file."""
        from tasktriage.files import save_analysis

        analysis_content = "# Daily Execution Order\n\n1. Task one"

        with patch("tasktriage.files.USB_DIR", str(mock_usb_dir)):
            output_path = save_analysis(analysis_content, sample_notes_file, "daily")

            assert output_path.exists()
            assert "daily_analysis" in output_path.name
            content = output_path.read_text()
            assert "Daily Task Analysis" in content
            assert "Task one" in content

    def test_saves_analysis_to_gdrive(self, mock_usb_dir):
        """Should upload analysis to Google Drive for gdrive:// paths."""
        mock_client = MagicMock()

        with patch("tasktriage.gdrive.GoogleDriveClient", return_value=mock_client):
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

        with patch("tasktriage.gdrive.GoogleDriveClient", return_value=mock_client):
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
        """Should save analysis using timestamp only, not page identifier, for USB."""
        daily_dir = mock_usb_dir / "daily"
        page_file = daily_dir / "20251228_100000_Page_1.png"
        page_file.write_bytes(b"fake png data")

        from tasktriage.files import save_analysis

        with patch("tasktriage.files.USB_DIR", str(mock_usb_dir)):
            output_path = save_analysis("Analysis content", page_file, "daily")

            # Should use timestamp without page identifier
            assert output_path.name == "20251228_100000.daily_analysis.txt"
            assert "_Page_" not in output_path.name

    def test_saves_analysis_with_page_identifier_gdrive(self):
        """Should save analysis using timestamp only, not page identifier, for GDrive."""
        mock_client = MagicMock()

        with patch("tasktriage.gdrive.GoogleDriveClient", return_value=mock_client):
            from tasktriage.files import _save_analysis_gdrive

            virtual_path = Path("gdrive://daily/20251228_100000_Page_1.png")
            analysis_content = "Analysis content"

            output_path = _save_analysis_gdrive(analysis_content, virtual_path, "daily")

            # Verify upload was called with timestamp-based filename
            call_args = mock_client.upload_file.call_args
            uploaded_filename = call_args[0][1]  # Second positional arg is filename
            assert uploaded_filename == "20251228_100000.daily_analysis.txt"
            assert "_Page_" not in uploaded_filename

    def test_formats_output_with_header(self, mock_usb_dir, sample_notes_file):
        """Should format output with proper header."""
        from tasktriage.files import save_analysis

        with patch("tasktriage.files.USB_DIR", str(mock_usb_dir)):
            output_path = save_analysis("Content", sample_notes_file, "daily")

            content = output_path.read_text()
            assert "Daily Task Analysis" in content
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


class TestGetNotesSource:
    """Tests for get_notes_source function."""

    def test_returns_usb_when_usb_active(self):
        """Should return 'usb' when USB source is active."""
        with patch("tasktriage.files.get_active_source", return_value="usb"):
            from tasktriage.files import get_notes_source

            result = get_notes_source()
            assert result == "usb"

    def test_returns_gdrive_when_gdrive_active(self):
        """Should return 'gdrive' when Google Drive source is active."""
        with patch("tasktriage.files.get_active_source", return_value="gdrive"):
            from tasktriage.files import get_notes_source

            result = get_notes_source()
            assert result == "gdrive"


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


class TestParseFilenameDateTime:
    """Tests for _parse_filename_datetime helper function."""

    def test_parses_simple_filename(self):
        """Should parse datetime from simple filename."""
        from tasktriage.files import _parse_filename_datetime

        result = _parse_filename_datetime("20251225_073454.txt")
        assert result == datetime(2025, 12, 25, 7, 34, 54)

    def test_parses_png_filename(self):
        """Should parse datetime from PNG filename."""
        from tasktriage.files import _parse_filename_datetime

        result = _parse_filename_datetime("20251231_143000.png")
        assert result == datetime(2025, 12, 31, 14, 30, 0)

    def test_parses_page_identifier_filename(self):
        """Should parse datetime from filename with page identifier."""
        from tasktriage.files import _parse_filename_datetime

        result = _parse_filename_datetime("20251225_073454_Page_1.png")
        assert result == datetime(2025, 12, 25, 7, 34, 54)

    def test_parses_multi_digit_page(self):
        """Should parse datetime from filename with multi-digit page number."""
        from tasktriage.files import _parse_filename_datetime

        result = _parse_filename_datetime("20251225_073454_Page_15.png")
        assert result == datetime(2025, 12, 25, 7, 34, 54)

    def test_returns_none_for_invalid_filename(self):
        """Should return None for invalid filename."""
        from tasktriage.files import _parse_filename_datetime

        result = _parse_filename_datetime("not_a_timestamp.txt")
        assert result is None

    def test_returns_none_for_invalid_date(self):
        """Should return None for invalid date values."""
        from tasktriage.files import _parse_filename_datetime

        # Month 13 is invalid
        result = _parse_filename_datetime("20251325_073454.txt")
        assert result is None


class TestLoadTaskNotesWithPageIdentifiers:
    """Tests for loading task notes with page identifier filenames."""

    def test_loads_page_identifier_file(self, mock_usb_dir):
        """Should load PNG file with page identifier in filename."""
        daily_dir = mock_usb_dir / "daily"
        page_file = daily_dir / "20251228_100000_Page_1.png"
        page_file.write_bytes(b"fake png data")

        with patch("tasktriage.files.USB_DIR", str(mock_usb_dir)), \
             patch("tasktriage.files.get_active_source", return_value="usb"), \
             patch("tasktriage.files.extract_text_from_image") as mock_extract:
            mock_extract.return_value = "Extracted text from page"

            from tasktriage.files import load_task_notes

            content, path, file_date = load_task_notes("daily")

            assert content == "Extracted text from page"
            assert file_date == datetime(2025, 12, 28, 10, 0, 0)

    def test_skips_page_file_with_existing_timestamp_analysis(self, mock_usb_dir):
        """Should skip page file when analysis exists for that timestamp."""
        daily_dir = mock_usb_dir / "daily"

        # Create page file
        page_file = daily_dir / "20251228_100000_Page_1.png"
        page_file.write_bytes(b"fake png data")

        # Create analysis file using timestamp (not including page identifier)
        analysis_file = daily_dir / "20251228_100000.daily_analysis.txt"
        analysis_file.write_text("Existing analysis")

        # Create an older file without analysis
        older_file = daily_dir / "20251227_090000.txt"
        older_file.write_text("Older notes")

        with patch("tasktriage.files.USB_DIR", str(mock_usb_dir)), \
             patch("tasktriage.files.get_active_source", return_value="usb"):
            from tasktriage.files import load_task_notes

            content, path, file_date = load_task_notes("daily")

            # Should load the older file since the page file's timestamp has analysis
            assert "Older notes" in content
            assert file_date == datetime(2025, 12, 27, 9, 0, 0)
