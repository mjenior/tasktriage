"""
Configuration management for TaskTriage.

Handles environment variables, API keys, and model configuration.
"""

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

# Load environment variables from .env file (looks in repo root)
load_dotenv(Path(__file__).parent.parent / ".env")

# Input directories for notes (can have multiple sources)
USB_INPUT_DIR = os.getenv("USB_INPUT_DIR")  # USB/mounted device directory
LOCAL_INPUT_DIR = os.getenv("LOCAL_INPUT_DIR")  # Local hard drive directory

# Google Drive configuration
GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH")
GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")

# Local directory to save analysis output (used when GDrive can't upload due to quota)
# If set, analysis files will be saved here instead of uploading to Google Drive
LOCAL_OUTPUT_DIR = os.getenv("LOCAL_OUTPUT_DIR")

# Backward compatibility: support old USB_DIR variable name
if not USB_INPUT_DIR and os.getenv("USB_DIR"):
    USB_INPUT_DIR = os.getenv("USB_DIR")

# Validate that at least one source is configured
if not USB_INPUT_DIR and not LOCAL_INPUT_DIR and not (GOOGLE_CREDENTIALS_PATH and GOOGLE_DRIVE_FOLDER_ID):
    raise ValueError(
        "No notes source configured. Please set at least one of:\n"
        "  - USB_INPUT_DIR for USB/mounted device directory\n"
        "  - LOCAL_INPUT_DIR for local hard drive directory\n"
        "  - GOOGLE_CREDENTIALS_PATH and GOOGLE_DRIVE_FOLDER_ID for Google Drive\n"
        "in your .env file."
    )

# Path to model configuration file (at repository root, parent of package)
CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"

# Default model to use if not specified in config
DEFAULT_MODEL = "claude-haiku-4-5-20241022"

# Notes source preference (can be set via environment)
# Options: "auto", "usb", "gdrive"
# "auto" prefers USB if available, falls back to Google Drive
NOTES_SOURCE = os.getenv("NOTES_SOURCE", "auto").lower()


def fetch_api_key(api_key: str | None = None) -> str:
    """Get Anthropic API key.

    Args:
        api_key: Optional API key to use directly

    Returns:
        The API key string

    Raises:
        ValueError: If no API key is available
    """
    if api_key:
        return api_key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable is not set")
    return api_key


def load_model_config() -> dict:
    """Load model configuration from YAML file.

    Returns:
        Dictionary of configuration parameters
    """
    if not CONFIG_PATH.exists():
        return {}

    with open(CONFIG_PATH) as f:
        config = yaml.safe_load(f)

    return config or {}


def is_usb_available() -> bool:
    """Check if USB input directory is configured and accessible.

    Returns:
        True if USB_INPUT_DIR is set and the directory exists
    """
    if not USB_INPUT_DIR:
        return False
    return Path(USB_INPUT_DIR).exists()


def is_local_input_available() -> bool:
    """Check if local input directory is configured and accessible.

    Returns:
        True if LOCAL_INPUT_DIR is set and the directory exists
    """
    if not LOCAL_INPUT_DIR:
        return False
    return Path(LOCAL_INPUT_DIR).exists()


def get_all_input_directories() -> list[Path]:
    """Get all available input directories.

    Returns:
        List of Path objects for all configured and accessible input directories
    """
    dirs = []

    if is_usb_available():
        dirs.append(Path(USB_INPUT_DIR))

    if is_local_input_available():
        dirs.append(Path(LOCAL_INPUT_DIR))

    return dirs


def is_gdrive_available() -> bool:
    """Check if Google Drive is configured.

    Returns:
        True if Google Drive credentials and folder ID are configured
    """
    if not GOOGLE_CREDENTIALS_PATH or not GOOGLE_DRIVE_FOLDER_ID:
        return False
    return Path(GOOGLE_CREDENTIALS_PATH).exists()


def get_primary_input_directory() -> Path:
    """Get the primary input directory for OUTPUT operations (creating new files).

    Returns:
        Path to the primary input directory

    Raises:
        ValueError: If no local input directory is available
    """
    # Prefer USB, then local input
    if is_usb_available():
        return Path(USB_INPUT_DIR)

    if is_local_input_available():
        return Path(LOCAL_INPUT_DIR)

    raise ValueError(
        "No local input directory available for creating new files. "
        "Please configure USB_INPUT_DIR or LOCAL_INPUT_DIR."
    )


def get_active_source() -> str:
    """Determine primary source for OUTPUT (new file creation).

    Note: For INPUT (reading notes), all configured sources are checked.
    This function is primarily used for determining where to save new files
    created in the UI.

    Returns:
        "usb" or "gdrive" indicating which source to use for output

    Raises:
        ValueError: If no source is available
    """
    if NOTES_SOURCE == "usb":
        if not is_usb_available():
            raise ValueError("USB source requested but USB_INPUT_DIR is not available")
        return "usb"

    if NOTES_SOURCE == "gdrive":
        if not is_gdrive_available():
            raise ValueError("Google Drive source requested but not configured")
        return "gdrive"

    # Auto mode: prefer USB if available, fall back to local input, then Google Drive
    if is_usb_available():
        return "usb"

    if is_local_input_available():
        return "usb"  # Treat local input as USB for output purposes

    if is_gdrive_available():
        return "gdrive"

    raise ValueError(
        "No notes source available. Check that USB_INPUT_DIR or LOCAL_INPUT_DIR exists or "
        "Google Drive credentials are properly configured."
    )
