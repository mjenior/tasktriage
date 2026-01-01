"""
Tests for tasker.config module.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import yaml


class TestFetchApiKey:
    """Tests for fetch_api_key function."""

    def test_returns_provided_api_key(self):
        """Should return the API key when provided directly."""
        from tasker.config import fetch_api_key

        result = fetch_api_key("my-direct-api-key")
        assert result == "my-direct-api-key"

    def test_returns_env_var_when_no_key_provided(self, monkeypatch):
        """Should return ANTHROPIC_API_KEY from environment."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "env-api-key-12345")
        from tasker.config import fetch_api_key

        result = fetch_api_key(None)
        assert result == "env-api-key-12345"

    def test_raises_when_no_key_available(self, monkeypatch):
        """Should raise ValueError when no API key is available."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        from tasker.config import fetch_api_key

        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
            fetch_api_key(None)


class TestLoadModelConfig:
    """Tests for load_model_config function."""

    def test_returns_empty_dict_when_no_config_file(self, temp_dir):
        """Should return empty dict when config.yaml doesn't exist."""
        import tasker.config

        # Save original and patch
        original_path = tasker.config.CONFIG_PATH
        tasker.config.CONFIG_PATH = temp_dir / "nonexistent.yaml"

        try:
            result = tasker.config.load_model_config()
            assert result == {}
        finally:
            tasker.config.CONFIG_PATH = original_path

    def test_loads_config_from_yaml(self, temp_dir):
        """Should load and return configuration from YAML file."""
        import tasker.config

        config_path = temp_dir / "config.yaml"
        config_data = {
            "model": "claude-sonnet-4-20250514",
            "temperature": 0.5,
            "max_tokens": 2048,
        }
        with open(config_path, "w") as f:
            yaml.dump(config_data, f)

        # Save original and patch
        original_path = tasker.config.CONFIG_PATH
        tasker.config.CONFIG_PATH = config_path

        try:
            result = tasker.config.load_model_config()
            assert result["model"] == "claude-sonnet-4-20250514"
            assert result["temperature"] == 0.5
            assert result["max_tokens"] == 2048
        finally:
            tasker.config.CONFIG_PATH = original_path

    def test_returns_empty_dict_for_empty_yaml(self, temp_dir):
        """Should return empty dict for empty YAML file."""
        import tasker.config

        config_path = temp_dir / "config.yaml"
        config_path.write_text("")

        # Save original and patch
        original_path = tasker.config.CONFIG_PATH
        tasker.config.CONFIG_PATH = config_path

        try:
            result = tasker.config.load_model_config()
            assert result == {}
        finally:
            tasker.config.CONFIG_PATH = original_path


class TestIsUsbAvailable:
    """Tests for is_usb_available function."""

    def test_returns_true_when_usb_dir_exists(self, temp_dir, monkeypatch):
        """Should return True when USB_DIR exists."""
        monkeypatch.setenv("USB_DIR", str(temp_dir))

        with patch("tasker.config.USB_DIR", str(temp_dir)):
            from tasker.config import is_usb_available

            import importlib
            import tasker.config
            tasker.config.USB_DIR = str(temp_dir)

            result = tasker.config.is_usb_available()
            assert result is True

    def test_returns_false_when_usb_dir_not_set(self, monkeypatch):
        """Should return False when USB_DIR is not set."""
        with patch("tasker.config.USB_DIR", None):
            from tasker.config import is_usb_available

            import tasker.config
            tasker.config.USB_DIR = None

            result = tasker.config.is_usb_available()
            assert result is False

    def test_returns_false_when_usb_dir_doesnt_exist(self, monkeypatch):
        """Should return False when USB_DIR path doesn't exist."""
        with patch("tasker.config.USB_DIR", "/nonexistent/path"):
            import tasker.config
            tasker.config.USB_DIR = "/nonexistent/path"

            result = tasker.config.is_usb_available()
            assert result is False


class TestIsGdriveAvailable:
    """Tests for is_gdrive_available function."""

    def test_returns_true_when_credentials_exist(self, temp_dir, monkeypatch):
        """Should return True when Google Drive is properly configured."""
        credentials_path = temp_dir / "credentials.json"
        credentials_path.write_text('{"type": "service_account"}')

        with patch("tasker.config.GOOGLE_CREDENTIALS_PATH", str(credentials_path)), \
             patch("tasker.config.GOOGLE_DRIVE_FOLDER_ID", "test-folder-id"):
            import tasker.config
            tasker.config.GOOGLE_CREDENTIALS_PATH = str(credentials_path)
            tasker.config.GOOGLE_DRIVE_FOLDER_ID = "test-folder-id"

            result = tasker.config.is_gdrive_available()
            assert result is True

    def test_returns_false_when_credentials_path_not_set(self):
        """Should return False when GOOGLE_CREDENTIALS_PATH is not set."""
        with patch("tasker.config.GOOGLE_CREDENTIALS_PATH", None), \
             patch("tasker.config.GOOGLE_DRIVE_FOLDER_ID", "test-folder-id"):
            import tasker.config
            tasker.config.GOOGLE_CREDENTIALS_PATH = None
            tasker.config.GOOGLE_DRIVE_FOLDER_ID = "test-folder-id"

            result = tasker.config.is_gdrive_available()
            assert result is False

    def test_returns_false_when_folder_id_not_set(self, temp_dir):
        """Should return False when GOOGLE_DRIVE_FOLDER_ID is not set."""
        credentials_path = temp_dir / "credentials.json"
        credentials_path.write_text('{"type": "service_account"}')

        with patch("tasker.config.GOOGLE_CREDENTIALS_PATH", str(credentials_path)), \
             patch("tasker.config.GOOGLE_DRIVE_FOLDER_ID", None):
            import tasker.config
            tasker.config.GOOGLE_CREDENTIALS_PATH = str(credentials_path)
            tasker.config.GOOGLE_DRIVE_FOLDER_ID = None

            result = tasker.config.is_gdrive_available()
            assert result is False

    def test_returns_false_when_credentials_file_missing(self):
        """Should return False when credentials file doesn't exist."""
        with patch("tasker.config.GOOGLE_CREDENTIALS_PATH", "/nonexistent/creds.json"), \
             patch("tasker.config.GOOGLE_DRIVE_FOLDER_ID", "test-folder-id"):
            import tasker.config
            tasker.config.GOOGLE_CREDENTIALS_PATH = "/nonexistent/creds.json"
            tasker.config.GOOGLE_DRIVE_FOLDER_ID = "test-folder-id"

            result = tasker.config.is_gdrive_available()
            assert result is False


class TestGetActiveSource:
    """Tests for get_active_source function."""

    def test_returns_usb_when_notes_source_is_usb(self, temp_dir):
        """Should return 'usb' when NOTES_SOURCE is 'usb' and USB is available."""
        with patch("tasker.config.NOTES_SOURCE", "usb"), \
             patch("tasker.config.is_usb_available", return_value=True):
            import tasker.config
            tasker.config.NOTES_SOURCE = "usb"

            result = tasker.config.get_active_source()
            assert result == "usb"

    def test_returns_gdrive_when_notes_source_is_gdrive(self, temp_dir):
        """Should return 'gdrive' when NOTES_SOURCE is 'gdrive' and GDrive is available."""
        credentials_path = temp_dir / "credentials.json"
        credentials_path.write_text('{"type": "service_account"}')

        with patch("tasker.config.NOTES_SOURCE", "gdrive"), \
             patch("tasker.config.is_gdrive_available", return_value=True):
            import tasker.config
            tasker.config.NOTES_SOURCE = "gdrive"

            result = tasker.config.get_active_source()
            assert result == "gdrive"

    def test_raises_when_usb_requested_but_unavailable(self):
        """Should raise ValueError when USB is requested but not available."""
        with patch("tasker.config.NOTES_SOURCE", "usb"), \
             patch("tasker.config.is_usb_available", return_value=False):
            import tasker.config
            tasker.config.NOTES_SOURCE = "usb"

            with pytest.raises(ValueError, match="USB source requested"):
                tasker.config.get_active_source()

    def test_raises_when_gdrive_requested_but_unavailable(self):
        """Should raise ValueError when GDrive is requested but not available."""
        with patch("tasker.config.NOTES_SOURCE", "gdrive"), \
             patch("tasker.config.is_gdrive_available", return_value=False):
            import tasker.config
            tasker.config.NOTES_SOURCE = "gdrive"

            with pytest.raises(ValueError, match="Google Drive source requested"):
                tasker.config.get_active_source()

    def test_auto_prefers_usb_when_both_available(self, temp_dir):
        """Should prefer USB over GDrive in auto mode when both are available."""
        with patch("tasker.config.NOTES_SOURCE", "auto"), \
             patch("tasker.config.is_usb_available", return_value=True), \
             patch("tasker.config.is_gdrive_available", return_value=True):
            import tasker.config
            tasker.config.NOTES_SOURCE = "auto"

            result = tasker.config.get_active_source()
            assert result == "usb"

    def test_auto_falls_back_to_gdrive(self, temp_dir):
        """Should fall back to GDrive in auto mode when USB is unavailable."""
        with patch("tasker.config.NOTES_SOURCE", "auto"), \
             patch("tasker.config.is_usb_available", return_value=False), \
             patch("tasker.config.is_gdrive_available", return_value=True):
            import tasker.config
            tasker.config.NOTES_SOURCE = "auto"

            result = tasker.config.get_active_source()
            assert result == "gdrive"

    def test_auto_raises_when_no_source_available(self):
        """Should raise ValueError when no source is available in auto mode."""
        with patch("tasker.config.NOTES_SOURCE", "auto"), \
             patch("tasker.config.is_usb_available", return_value=False), \
             patch("tasker.config.is_gdrive_available", return_value=False):
            import tasker.config
            tasker.config.NOTES_SOURCE = "auto"

            with pytest.raises(ValueError, match="No notes source available"):
                tasker.config.get_active_source()
