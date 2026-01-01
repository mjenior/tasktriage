"""
Shared pytest fixtures for Tasker tests.
"""

import os
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_usb_dir(temp_dir):
    """Create a mock USB directory structure with daily and weekly folders."""
    daily_dir = temp_dir / "daily"
    weekly_dir = temp_dir / "weekly"
    daily_dir.mkdir()
    weekly_dir.mkdir()
    return temp_dir


@pytest.fixture
def sample_notes_file(mock_usb_dir):
    """Create a sample notes text file."""
    daily_dir = mock_usb_dir / "daily"
    notes_path = daily_dir / "20251231_143000.txt"
    notes_content = """Work
    Review Q4 budget proposal
    Fix login bug *
    Respond to client emails ✓

Home
    Grocery shopping
    Clean garage X
"""
    notes_path.write_text(notes_content)
    return notes_path


@pytest.fixture
def sample_image_file(mock_usb_dir):
    """Create a sample PNG file (minimal valid PNG)."""
    daily_dir = mock_usb_dir / "daily"
    image_path = daily_dir / "20251230_090000.png"
    # Minimal valid 1x1 PNG file
    png_data = bytes([
        0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG signature
        0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,  # IHDR chunk
        0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
        0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,
        0xDE, 0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41,  # IDAT chunk
        0x54, 0x08, 0xD7, 0x63, 0xF8, 0xFF, 0xFF, 0x3F,
        0x00, 0x05, 0xFE, 0x02, 0xFE, 0xDC, 0xCC, 0x59,
        0xE7, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E,  # IEND chunk
        0x44, 0xAE, 0x42, 0x60, 0x82
    ])
    image_path.write_bytes(png_data)
    return image_path


@pytest.fixture
def sample_analysis_file(mock_usb_dir):
    """Create a sample daily analysis file."""
    daily_dir = mock_usb_dir / "daily"
    analysis_path = daily_dir / "20251229_080000.daily_analysis.txt"
    analysis_content = """Daily Task Analysis
========================================

# Daily Execution Order

1. **Review Q4 budget proposal** [Energy: High] [Est: 45min]
   - Open budget spreadsheet
   - Identify discrepancies
   - Draft summary

## Deferred Tasks
- None

## Critical Assessment
Tasks were well-defined and achievable.
"""
    analysis_path.write_text(analysis_content)
    return analysis_path


@pytest.fixture
def mock_env_vars(temp_dir, monkeypatch):
    """Set up mock environment variables for testing."""
    monkeypatch.setenv("USB_DIR", str(temp_dir))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-api-key-12345")
    return {
        "USB_DIR": str(temp_dir),
        "ANTHROPIC_API_KEY": "test-api-key-12345",
    }


@pytest.fixture
def mock_gdrive_env_vars(temp_dir, monkeypatch):
    """Set up mock Google Drive environment variables."""
    credentials_path = temp_dir / "credentials.json"
    credentials_path.write_text('{"type": "service_account"}')

    monkeypatch.setenv("GOOGLE_CREDENTIALS_PATH", str(credentials_path))
    monkeypatch.setenv("GOOGLE_DRIVE_FOLDER_ID", "test-folder-id-12345")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-api-key-12345")

    return {
        "GOOGLE_CREDENTIALS_PATH": str(credentials_path),
        "GOOGLE_DRIVE_FOLDER_ID": "test-folder-id-12345",
    }


@pytest.fixture
def mock_llm_response():
    """Create a mock LLM response."""
    mock_response = MagicMock()
    mock_response.content = """# Daily Execution Order

1. **Review Q4 budget proposal** [Energy: High] [Est: 45min]
   - Open budget spreadsheet
   - Identify discrepancies

## Critical Assessment
Good task list.
"""
    return mock_response


@pytest.fixture
def mock_chat_anthropic(mock_llm_response):
    """Create a mock ChatAnthropic instance."""
    with patch("tasker.analysis.ChatAnthropic") as mock_class:
        mock_instance = MagicMock()
        mock_instance.invoke.return_value = mock_llm_response
        # Make chain work with | operator
        mock_instance.__or__ = lambda self, other: mock_instance
        mock_class.return_value = mock_instance
        yield mock_class


@pytest.fixture
def sample_datetime():
    """Return a sample datetime for testing."""
    return datetime(2025, 12, 31, 14, 30, 0)
