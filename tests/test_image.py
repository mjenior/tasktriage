"""
Tests for tasker.image module.
"""

import base64
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestImageExtensions:
    """Tests for image extension constants."""

    def test_image_extensions_contains_png(self):
        """Should include .png extension."""
        from tasker.image import IMAGE_EXTENSIONS

        assert ".png" in IMAGE_EXTENSIONS

    def test_image_extensions_is_set(self):
        """IMAGE_EXTENSIONS should be a set for efficient lookups."""
        from tasker.image import IMAGE_EXTENSIONS

        assert isinstance(IMAGE_EXTENSIONS, set)


class TestMediaTypeMap:
    """Tests for MIME type mapping."""

    def test_media_type_map_contains_png(self):
        """Should map .png to image/png."""
        from tasker.image import MEDIA_TYPE_MAP

        assert ".png" in MEDIA_TYPE_MAP
        assert MEDIA_TYPE_MAP[".png"] == "image/png"


class TestExtractTextFromImage:
    """Tests for extract_text_from_image function."""

    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM that returns extracted text."""
        with patch("tasker.image.ChatAnthropic") as mock_class:
            mock_instance = MagicMock()
            mock_response = MagicMock()
            mock_response.content = """Work
    Review budget proposal
    Fix login bug *

Home
    Grocery shopping
"""
            mock_instance.invoke.return_value = mock_response
            mock_class.return_value = mock_instance
            yield mock_class, mock_instance

    @pytest.fixture
    def png_file(self, temp_dir):
        """Create a minimal valid PNG file."""
        png_path = temp_dir / "test_notes.png"
        # Minimal valid 1x1 PNG
        png_data = bytes([
            0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,
            0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,
            0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
            0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,
            0xDE, 0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41,
            0x54, 0x08, 0xD7, 0x63, 0xF8, 0xFF, 0xFF, 0x3F,
            0x00, 0x05, 0xFE, 0x02, 0xFE, 0xDC, 0xCC, 0x59,
            0xE7, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E,
            0x44, 0xAE, 0x42, 0x60, 0x82
        ])
        png_path.write_bytes(png_data)
        return png_path

    def test_extracts_text_from_png(self, mock_llm, png_file):
        """Should extract text from a PNG image using Claude's vision API."""
        mock_class, mock_instance = mock_llm

        with patch("tasker.image.fetch_api_key", return_value="test-key"), \
             patch("tasker.image.load_model_config", return_value={}):
            from tasker.image import extract_text_from_image

            result = extract_text_from_image(png_file)

            assert "Work" in result
            assert "Review budget proposal" in result
            mock_instance.invoke.assert_called_once()

    def test_uses_provided_api_key(self, mock_llm, png_file):
        """Should use the provided API key."""
        mock_class, mock_instance = mock_llm

        with patch("tasker.image.fetch_api_key") as mock_fetch, \
             patch("tasker.image.load_model_config", return_value={}):
            mock_fetch.return_value = "custom-api-key"
            from tasker.image import extract_text_from_image

            extract_text_from_image(png_file, api_key="custom-api-key")

            mock_fetch.assert_called_with("custom-api-key")

    def test_uses_default_model_when_not_configured(self, mock_llm, png_file):
        """Should use default model when not specified in config."""
        mock_class, mock_instance = mock_llm

        with patch("tasker.image.fetch_api_key", return_value="test-key"), \
             patch("tasker.image.load_model_config", return_value={}):
            from tasker.image import extract_text_from_image, DEFAULT_MODEL

            extract_text_from_image(png_file)

            # Verify ChatAnthropic was called with default model
            mock_class.assert_called_once()
            call_kwargs = mock_class.call_args[1]
            assert call_kwargs["model"] == DEFAULT_MODEL

    def test_uses_model_from_config(self, mock_llm, png_file):
        """Should use model specified in config."""
        mock_class, mock_instance = mock_llm
        config = {"model": "claude-sonnet-4-20250514", "temperature": 0.5}

        with patch("tasker.image.fetch_api_key", return_value="test-key"), \
             patch("tasker.image.load_model_config", return_value=config.copy()):
            from tasker.image import extract_text_from_image

            extract_text_from_image(png_file)

            mock_class.assert_called_once()
            call_kwargs = mock_class.call_args[1]
            assert call_kwargs["model"] == "claude-sonnet-4-20250514"

    def test_encodes_image_as_base64(self, mock_llm, png_file):
        """Should encode image content as base64."""
        mock_class, mock_instance = mock_llm

        with patch("tasker.image.fetch_api_key", return_value="test-key"), \
             patch("tasker.image.load_model_config", return_value={}):
            from tasker.image import extract_text_from_image

            extract_text_from_image(png_file)

            # Check that invoke was called with image data
            call_args = mock_instance.invoke.call_args[0][0]
            assert len(call_args) == 1  # One message
            message = call_args[0]
            assert len(message.content) == 2  # Text and image

            # Verify image URL format
            image_content = message.content[1]
            assert image_content["type"] == "image_url"
            assert "data:image/png;base64," in image_content["image_url"]["url"]

    def test_includes_extraction_prompt(self, mock_llm, png_file):
        """Should include the image extraction prompt in the message."""
        mock_class, mock_instance = mock_llm

        with patch("tasker.image.fetch_api_key", return_value="test-key"), \
             patch("tasker.image.load_model_config", return_value={}):
            from tasker.image import extract_text_from_image, IMAGE_EXTRACTION_PROMPT
            from tasker.prompts import IMAGE_EXTRACTION_PROMPT

            extract_text_from_image(png_file)

            call_args = mock_instance.invoke.call_args[0][0]
            message = call_args[0]
            text_content = message.content[0]
            assert text_content["type"] == "text"
            assert text_content["text"] == IMAGE_EXTRACTION_PROMPT

    def test_returns_response_content(self, mock_llm, png_file):
        """Should return the content from the LLM response."""
        mock_class, mock_instance = mock_llm

        with patch("tasker.image.fetch_api_key", return_value="test-key"), \
             patch("tasker.image.load_model_config", return_value={}):
            from tasker.image import extract_text_from_image

            result = extract_text_from_image(png_file)

            # Result should match the mock response content
            assert "Work" in result
            assert "Home" in result
