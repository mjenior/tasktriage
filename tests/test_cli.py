"""
Tests for tasker.cli module.
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
        with patch("tasker.cli.load_task_notes") as mock_load, \
             patch("tasker.cli.analyze_tasks") as mock_analyze, \
             patch("tasker.cli.save_analysis") as mock_save, \
             patch("tasker.cli.get_notes_source") as mock_source, \
             patch("tasker.cli.collect_weekly_analyses") as mock_weekly:

            # Default mock returns
            notes_path = temp_dir / "daily" / "20251231_143000.txt"
            mock_load.return_value = ("Task notes content", notes_path, datetime(2025, 12, 31, 14, 30, 0))
            mock_analyze.return_value = "Analysis result"
            mock_save.return_value = temp_dir / "daily" / "20251231_143000.daily_analysis.txt"
            mock_source.return_value = "usb"

            yield {
                "load": mock_load,
                "analyze": mock_analyze,
                "save": mock_save,
                "source": mock_source,
                "weekly": mock_weekly,
                "temp_dir": temp_dir,
            }

    def test_daily_analysis_workflow(self, mock_dependencies, capsys):
        """Should run complete daily analysis workflow."""
        with patch("sys.argv", ["tasker", "--type", "daily"]):
            from tasker.cli import main

            main()

            # Verify workflow
            mock_dependencies["load"].assert_called_once_with("daily")
            mock_dependencies["analyze"].assert_called_once()
            mock_dependencies["save"].assert_called_once()

            # Check output
            captured = capsys.readouterr()
            assert "USB/Local" in captured.out
            assert "Analyzing daily tasks" in captured.out
            assert "Analysis saved" in captured.out

    def test_weekly_analysis_workflow(self, mock_dependencies, capsys):
        """Should run complete weekly analysis workflow."""
        today = datetime.now()
        days_since_sunday = (today.weekday() + 1) % 7
        last_sunday = today - timedelta(days=days_since_sunday)
        last_monday = last_sunday - timedelta(days=6)

        output_path = mock_dependencies["temp_dir"] / "weekly" / "20251223.week.txt"
        mock_dependencies["weekly"].return_value = (
            "Combined weekly content",
            output_path,
            last_monday,
            last_sunday
        )
        mock_dependencies["save"].return_value = output_path

        with patch("sys.argv", ["tasker", "--type", "weekly"]):
            from tasker.cli import main

            main()

            mock_dependencies["weekly"].assert_called_once()
            mock_dependencies["analyze"].assert_called_once()

            captured = capsys.readouterr()
            assert "weekly review" in captured.out.lower()

    def test_shows_notes_source(self, mock_dependencies, capsys):
        """Should display which notes source is being used."""
        with patch("sys.argv", ["tasker", "--type", "daily"]):
            from tasker.cli import main

            main()

            captured = capsys.readouterr()
            assert "Using notes source:" in captured.out

    def test_shows_gdrive_source_label(self, mock_dependencies, capsys):
        """Should show 'Google Drive' when using gdrive source."""
        mock_dependencies["source"].return_value = "gdrive"

        with patch("sys.argv", ["tasker", "--type", "daily"]):
            from tasker.cli import main

            main()

            captured = capsys.readouterr()
            assert "Google Drive" in captured.out

    def test_shows_usb_source_label(self, mock_dependencies, capsys):
        """Should show 'USB/Local' when using usb source."""
        mock_dependencies["source"].return_value = "usb"

        with patch("sys.argv", ["tasker", "--type", "daily"]):
            from tasker.cli import main

            main()

            captured = capsys.readouterr()
            assert "USB/Local" in captured.out

    def test_indicates_image_extraction(self, mock_dependencies, capsys):
        """Should indicate when text was extracted from an image."""
        png_path = mock_dependencies["temp_dir"] / "daily" / "20251230_090000.png"
        mock_dependencies["load"].return_value = (
            "Extracted content",
            png_path,
            datetime(2025, 12, 30, 9, 0, 0)
        )

        with patch("sys.argv", ["tasker", "--type", "daily"]):
            from tasker.cli import main

            main()

            captured = capsys.readouterr()
            assert "Extracted text from image" in captured.out

    def test_formats_date_for_daily_prompt(self, mock_dependencies):
        """Should format date correctly for daily prompt."""
        with patch("sys.argv", ["tasker", "--type", "daily"]):
            from tasker.cli import main

            main()

            call_args = mock_dependencies["analyze"].call_args
            assert call_args[1]["current_date"] == "Wednesday, December 31, 2025"

    def test_formats_dates_for_weekly_prompt(self, mock_dependencies):
        """Should format date range correctly for weekly prompt."""
        today = datetime.now()
        days_since_sunday = (today.weekday() + 1) % 7
        last_sunday = today - timedelta(days=days_since_sunday)
        last_monday = last_sunday - timedelta(days=6)

        output_path = mock_dependencies["temp_dir"] / "weekly" / "20251223.week.txt"
        mock_dependencies["weekly"].return_value = (
            "Combined content",
            output_path,
            last_monday,
            last_sunday
        )

        with patch("sys.argv", ["tasker", "--type", "weekly"]):
            from tasker.cli import main

            main()

            call_args = mock_dependencies["analyze"].call_args
            assert "week_start" in call_args[1]
            assert "week_end" in call_args[1]

    def test_default_type_is_daily(self, mock_dependencies):
        """Should default to daily analysis when no type specified."""
        with patch("sys.argv", ["tasker"]):
            from tasker.cli import main

            main()

            mock_dependencies["load"].assert_called_with("daily")


class TestErrorHandling:
    """Tests for CLI error handling."""

    def test_handles_file_not_found_error(self, capsys):
        """Should handle FileNotFoundError gracefully."""
        with patch("tasker.cli.get_notes_source", return_value="usb"), \
             patch("tasker.cli.load_task_notes") as mock_load, \
             patch("sys.argv", ["tasker", "--type", "daily"]):
            mock_load.side_effect = FileNotFoundError("Notes directory not found")

            from tasker.cli import main

            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1
            captured = capsys.readouterr()
            assert "Error:" in captured.err
            assert "not found" in captured.err

    def test_handles_general_exception(self, capsys):
        """Should handle general exceptions gracefully."""
        with patch("tasker.cli.get_notes_source", return_value="usb"), \
             patch("tasker.cli.load_task_notes") as mock_load, \
             patch("sys.argv", ["tasker", "--type", "daily"]):
            mock_load.side_effect = Exception("Unexpected error")

            from tasker.cli import main

            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1
            captured = capsys.readouterr()
            assert "Error during analysis" in captured.err

    def test_handles_api_error(self, temp_dir, capsys):
        """Should handle API errors gracefully."""
        notes_path = temp_dir / "daily" / "20251231_143000.txt"

        with patch("tasker.cli.get_notes_source", return_value="usb"), \
             patch("tasker.cli.load_task_notes") as mock_load, \
             patch("tasker.cli.analyze_tasks") as mock_analyze, \
             patch("sys.argv", ["tasker", "--type", "daily"]):
            mock_load.return_value = ("Content", notes_path, datetime(2025, 12, 31, 14, 30, 0))
            mock_analyze.side_effect = Exception("API rate limit exceeded")

            from tasker.cli import main

            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1


class TestArgumentParsing:
    """Tests for CLI argument parsing."""

    def test_accepts_daily_type(self):
        """Should accept --type daily argument."""
        with patch("tasker.cli.get_notes_source", return_value="usb"), \
             patch("tasker.cli.load_task_notes") as mock_load, \
             patch("tasker.cli.analyze_tasks", return_value="Result"), \
             patch("tasker.cli.save_analysis", return_value=Path("/tmp/analysis.txt")), \
             patch("sys.argv", ["tasker", "--type", "daily"]):
            mock_load.return_value = ("Content", Path("/tmp/notes.txt"), datetime.now())

            from tasker.cli import main

            main()
            mock_load.assert_called_with("daily")

    def test_accepts_weekly_type(self):
        """Should accept --type weekly argument."""
        with patch("tasker.cli.get_notes_source", return_value="usb"), \
             patch("tasker.cli.collect_weekly_analyses") as mock_weekly, \
             patch("tasker.cli.analyze_tasks", return_value="Result"), \
             patch("tasker.cli.save_analysis", return_value=Path("/tmp/analysis.txt")), \
             patch("sys.argv", ["tasker", "--type", "weekly"]):
            mock_weekly.return_value = (
                "Combined",
                Path("/tmp/weekly.txt"),
                datetime.now() - timedelta(days=7),
                datetime.now()
            )

            from tasker.cli import main

            main()
            mock_weekly.assert_called_once()


class TestImageExtensionConstant:
    """Tests for IMAGE_EXTENSIONS import in CLI."""

    def test_image_extensions_imported(self):
        """Should import IMAGE_EXTENSIONS from image module."""
        from tasker.cli import IMAGE_EXTENSIONS

        assert ".png" in IMAGE_EXTENSIONS
