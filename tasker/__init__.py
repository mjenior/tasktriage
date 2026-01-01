"""
Tasker - Daily Task Analyzer

Analyzes daily task notes using Claude via LangChain and generates
actionable execution plans based on GTD principles.

Supports reading notes from both local/USB directories and Google Drive.
"""

# Configuration
from .config import (
    fetch_api_key,
    load_model_config,
    USB_DIR,
    CONFIG_PATH,
    DEFAULT_MODEL,
    GOOGLE_CREDENTIALS_PATH,
    GOOGLE_DRIVE_FOLDER_ID,
    NOTES_SOURCE,
    is_usb_available,
    is_gdrive_available,
    get_active_source,
)

# Prompt templates
from .prompts import (
    get_daily_prompt,
    get_weekly_prompt,
    DAILY_SYSTEM_PROMPT,
    DAILY_HUMAN_PROMPT,
    WEEKLY_SYSTEM_PROMPT,
    WEEKLY_HUMAN_PROMPT,
    IMAGE_EXTRACTION_PROMPT,
)

# Image processing
from .image import (
    extract_text_from_image,
    IMAGE_EXTENSIONS,
    MEDIA_TYPE_MAP,
)

# File operations
from .files import (
    load_task_notes,
    collect_weekly_analyses,
    save_analysis,
    get_notes_source,
    TEXT_EXTENSIONS,
    ALL_EXTENSIONS,
)

# Google Drive integration
from .gdrive import (
    GoogleDriveClient,
    is_gdrive_configured,
)

# Core analysis
from .analysis import analyze_tasks

# CLI entry point
from .cli import main

__version__ = "0.1.0"

__all__ = [
    # Main entry point
    "main",
    # Core functions
    "analyze_tasks",
    "load_task_notes",
    "collect_weekly_analyses",
    "save_analysis",
    "extract_text_from_image",
    "get_notes_source",
    # Google Drive
    "GoogleDriveClient",
    "is_gdrive_configured",
    # Configuration
    "fetch_api_key",
    "load_model_config",
    "USB_DIR",
    "CONFIG_PATH",
    "DEFAULT_MODEL",
    "GOOGLE_CREDENTIALS_PATH",
    "GOOGLE_DRIVE_FOLDER_ID",
    "NOTES_SOURCE",
    "is_usb_available",
    "is_gdrive_available",
    "get_active_source",
    # Prompt templates
    "get_daily_prompt",
    "get_weekly_prompt",
    "DAILY_SYSTEM_PROMPT",
    "DAILY_HUMAN_PROMPT",
    "WEEKLY_SYSTEM_PROMPT",
    "WEEKLY_HUMAN_PROMPT",
    "IMAGE_EXTRACTION_PROMPT",
    # Constants
    "IMAGE_EXTENSIONS",
    "MEDIA_TYPE_MAP",
    "TEXT_EXTENSIONS",
    "ALL_EXTENSIONS",
]
