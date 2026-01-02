"""
Tests for tasktriage.cli module.
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch, call
from io import StringIO

import pytest


class TestMainFunction:
    """Tests for the main CLI entry point."""

    @pytest.fixture
    def mock_dependencies(self, temp_dir):
        """Set up mock dependencies for CLI tests."""
        with patch("tasktriage.cli.load_all_unanalyzed_task_notes") as mock_load_all, \
             patch("tasktriage.cli.analyze_tasks") as mock_analyze, \
             patch("tasktriage.cli.save_analysis") as mock_save, \
             patch("tasktriage.cli.get_notes_source") as mock_source, \
             patch("tasktriage.cli.collect_weekly_analyses") as mock_weekly:

            # Default mock returns - list of files for batch processing
            notes_path = temp_dir / "daily" / "20251231_143000.txt"
            mock_load_all.return_value = [
                ("Task notes content", notes_path, datetime(2025, 12, 31, 14, 30, 0))
            ]
            mock_analyze.return_value = "Analysis result"
            mock_save.return_value = temp_dir / "daily" / "20251231_143000.daily_analysis.txt"
            mock_source.return_value = "usb"

            yield {
                "load_all": mock_load_all,
                "analyze": mock_analyze,
                "save": mock_save,
                "source": mock_source,
                "weekly": mock_weekly,
                "temp_dir": temp_dir,
            }

    def test_daily_analysis_workflow(self, mock_dependencies, capsys):
        """Should run complete daily analysis workflow for all unanalyzed files."""
        with patch("sys.argv", ["tasker"]):
            from tasktriage.cli import main

            main()

            # Verify workflow (now loads all unanalyzed files)
            mock_dependencies["load_all"].assert_called_once_with("daily", "png")
            mock_dependencies["analyze"].assert_called_once()
            mock_dependencies["save"].assert_called_once()

            # Check output
            captured = capsys.readouterr()
            assert "USB/Local" in captured.out
            assert "Found 1 unanalyzed file(s)" in captured.out
            assert "✓ Analyzed:" in captured.out
            assert "Daily Summary: 1 successful, 0 failed" in captured.out

    def test_auto_weekly_analysis(self, mock_dependencies, capsys):
        """Should auto-trigger weekly analysis when conditions are met."""
        # Mock _find_weeks_needing_analysis to return a week that needs analysis
        from datetime import datetime
        week_start = datetime(2025, 12, 16, 0, 0, 0)
        week_end = datetime(2025, 12, 20, 23, 59, 59)

        output_path = mock_dependencies["temp_dir"] / "weekly" / "20251216.weekly_analysis.txt"

        with patch("sys.argv", ["tasker"]), \
             patch("tasktriage.files._find_weeks_needing_analysis") as mock_find_weeks, \
             patch("tasktriage.cli.collect_weekly_analyses_for_week") as mock_collect:

            mock_find_weeks.return_value = [(week_start, week_end)]
            mock_collect.return_value = (
                "Combined weekly content",
                output_path,
                week_start,
                week_end
            )

            from tasktriage.cli import main
            main()

            # Check that weekly analysis was auto-triggered
            mock_find_weeks.assert_called_once()
            mock_collect.assert_called_once_with(week_start, week_end)

            captured = capsys.readouterr()
            assert "Auto-triggering weekly analyses" in captured.out
            assert "(based on completed daily analyses)" in captured.out

    def test_shows_notes_source(self, mock_dependencies, capsys):
        """Should display which notes source is being used."""
        with patch("sys.argv", ["tasker"]):
            from tasktriage.cli import main

            main()

            captured = capsys.readouterr()
            assert "Using notes source:" in captured.out

    def test_shows_gdrive_source_label(self, mock_dependencies, capsys):
        """Should show 'Google Drive' when using gdrive source."""
        mock_dependencies["source"].return_value = "gdrive"

        with patch("sys.argv", ["tasker"]):
            from tasktriage.cli import main

            main()

            captured = capsys.readouterr()
            assert "Google Drive" in captured.out

    def test_shows_usb_source_label(self, mock_dependencies, capsys):
        """Should show 'USB/Local' when using usb source."""
        mock_dependencies["source"].return_value = "usb"

        with patch("sys.argv", ["tasker"]):
            from tasktriage.cli import main

            main()

            captured = capsys.readouterr()
            assert "USB/Local" in captured.out

    def test_indicates_image_extraction(self, mock_dependencies, capsys):
        """Should indicate when text was extracted from an image."""
        png_path = mock_dependencies["temp_dir"] / "daily" / "20251230_090000.png"
        mock_dependencies["load_all"].return_value = [
            ("Extracted content", png_path, datetime(2025, 12, 30, 9, 0, 0))
        ]

        with patch("sys.argv", ["tasker"]):
            from tasktriage.cli import main

            main()

            captured = capsys.readouterr()
            assert "(image)" in captured.out

    def test_formats_date_for_daily_prompt(self, mock_dependencies):
        """Should format date correctly for daily prompt."""
        with patch("sys.argv", ["tasker"]):
            from tasktriage.cli import main

            main()

            call_args = mock_dependencies["analyze"].call_args
            assert call_args[1]["current_date"] == "Wednesday, December 31, 2025"

    def test_default_type_is_daily(self, mock_dependencies):
        """Should default to daily analysis when no type specified."""
        with patch("sys.argv", ["tasker"]):
            from tasktriage.cli import main

            main()

            mock_dependencies["load_all"].assert_called_with("daily", "png")


class TestErrorHandling:
    """Tests for CLI error handling."""

    def test_handles_file_not_found_error(self, capsys):
        """Should handle FileNotFoundError gracefully."""
        with patch("tasktriage.cli.get_notes_source", return_value="usb"), \
             patch("tasktriage.cli.load_all_unanalyzed_task_notes") as mock_load_all, \
             patch("sys.argv", ["tasker"]):
            mock_load_all.side_effect = FileNotFoundError("Notes directory not found")

            from tasktriage.cli import main

            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1
            captured = capsys.readouterr()
            assert "Error:" in captured.err
            assert "not found" in captured.err

    def test_handles_general_exception(self, capsys):
        """Should handle general exceptions gracefully."""
        with patch("tasktriage.cli.get_notes_source", return_value="usb"), \
             patch("tasktriage.cli.load_all_unanalyzed_task_notes") as mock_load_all, \
             patch("sys.argv", ["tasker"]):
            mock_load_all.side_effect = Exception("Unexpected error")

            from tasktriage.cli import main

            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1
            captured = capsys.readouterr()
            assert "Error during analysis" in captured.err

    def test_handles_api_error(self, temp_dir, capsys):
        """Should handle API errors gracefully."""
        notes_path = temp_dir / "daily" / "20251231_143000.txt"

        with patch("tasktriage.cli.get_notes_source", return_value="usb"), \
             patch("tasktriage.cli.load_all_unanalyzed_task_notes") as mock_load_all, \
             patch("tasktriage.cli.analyze_tasks") as mock_analyze, \
             patch("sys.argv", ["tasker"]):
            mock_load_all.return_value = [("Content", notes_path, datetime(2025, 12, 31, 14, 30, 0))]
            mock_analyze.side_effect = Exception("API rate limit exceeded")

            from tasktriage.cli import main

            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1


class TestArgumentParsing:
    """Tests for CLI argument parsing."""

    def test_accepts_files_argument(self):
        """Should accept --files argument for file type preference."""
        with patch("tasktriage.cli.get_notes_source", return_value="usb"), \
             patch("tasktriage.cli.load_all_unanalyzed_task_notes") as mock_load_all, \
             patch("tasktriage.cli.analyze_tasks", return_value="Result"), \
             patch("tasktriage.cli.save_analysis", return_value=Path("/tmp/analysis.txt")), \
             patch("sys.argv", ["tasker", "--files", "txt"]):
            mock_load_all.return_value = [("Content", Path("/tmp/notes.txt"), datetime.now())]

            from tasktriage.cli import main

            main()
            mock_load_all.assert_called_with("daily", "txt")

    def test_defaults_to_png_files(self):
        """Should default to png file type when no --files argument provided."""
        with patch("tasktriage.cli.get_notes_source", return_value="usb"), \
             patch("tasktriage.cli.load_all_unanalyzed_task_notes") as mock_load_all, \
             patch("tasktriage.cli.analyze_tasks", return_value="Result"), \
             patch("tasktriage.cli.save_analysis", return_value=Path("/tmp/analysis.txt")), \
             patch("sys.argv", ["tasker"]):
            mock_load_all.return_value = [("Content", Path("/tmp/notes.png"), datetime.now())]

            from tasktriage.cli import main

            main()
            mock_load_all.assert_called_with("daily", "png")


class TestImageExtensionConstant:
    """Tests for IMAGE_EXTENSIONS import in CLI."""

    def test_image_extensions_imported(self):
        """Should import IMAGE_EXTENSIONS from image module."""
        from tasktriage.cli import IMAGE_EXTENSIONS

        assert ".png" in IMAGE_EXTENSIONS


class TestExampleFilesIntegration:
    """Tests demonstrating use of example files from tests/examples directory."""

    def test_example_text_file_content_readable(self, example_text_file):
        """Example text file should be readable."""
        content = example_text_file.read_text()
        assert len(content) > 0
        # Example file contains task categories
        assert "agents team" in content.lower() or "admin" in content.lower()

    def test_example_image_file_is_valid_png(self, example_image_file):
        """Example image file should be a valid PNG."""
        data = example_image_file.read_bytes()
        # Check PNG signature
        assert data[:8] == b'\x89PNG\r\n\x1a\n'

    def test_cli_can_process_example_file_format(self, example_text_file):
        """CLI should be able to process files with example file naming format."""
        from tasktriage.files import _parse_filename_datetime

        # Verify the example file uses the correct naming format
        file_date = _parse_filename_datetime(example_text_file.name)
        assert file_date is not None
        assert file_date.year == 2025
        assert file_date.month == 12
        assert file_date.day == 25
