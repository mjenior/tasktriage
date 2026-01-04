"""
TaskTriage - Daily Task Analyzer

Analyzes daily task notes using Claude via LangChain and generates
actionable execution plans based on GTD principles.

Supports reading notes from both local/USB directories and Google Drive.
"""

# Configuration
from .config import (
    fetch_api_key,
    load_model_config,
    USB_INPUT_DIR,
    LOCAL_INPUT_DIR,
    CONFIG_PATH,
    DEFAULT_MODEL,
    GOOGLE_CREDENTIALS_PATH,
    GOOGLE_DRIVE_FOLDER_ID,
    NOTES_SOURCE,
    is_usb_available,
    is_local_input_available,
    is_gdrive_available,
    get_active_source,
    get_all_input_directories,
    get_primary_input_directory,
)

# Prompt templates
from .prompts import (
    get_daily_prompt,
    get_weekly_prompt,
    get_monthly_prompt,
    get_annual_prompt,
    DAILY_SYSTEM_PROMPT,
    DAILY_HUMAN_PROMPT,
    WEEKLY_SYSTEM_PROMPT,
    WEEKLY_HUMAN_PROMPT,
    MONTHLY_SYSTEM_PROMPT,
    MONTHLY_HUMAN_PROMPT,
    ANNUAL_SYSTEM_PROMPT,
    ANNUAL_HUMAN_PROMPT,
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
    load_all_unanalyzed_task_notes,
    collect_weekly_analyses,
    collect_weekly_analyses_for_week,
    collect_monthly_analyses_for_month,
    collect_annual_analyses_for_year,
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

__version__ = "0.1.1"

__all__ = [
    # Main entry point
    "main",
    # Core functions
    "analyze_tasks",
    "load_task_notes",
    "load_all_unanalyzed_task_notes",
    "collect_weekly_analyses",
    "collect_weekly_analyses_for_week",
    "collect_monthly_analyses_for_month",
    "collect_annual_analyses_for_year",
    "save_analysis",
    "extract_text_from_image",
    "get_notes_source",
    # Google Drive
    "GoogleDriveClient",
    "is_gdrive_configured",
    # Configuration
    "fetch_api_key",
    "load_model_config",
    "USB_INPUT_DIR",
    "LOCAL_INPUT_DIR",
    "CONFIG_PATH",
    "DEFAULT_MODEL",
    "GOOGLE_CREDENTIALS_PATH",
    "GOOGLE_DRIVE_FOLDER_ID",
    "NOTES_SOURCE",
    "is_usb_available",
    "is_local_input_available",
    "is_gdrive_available",
    "get_active_source",
    "get_all_input_directories",
    "get_primary_input_directory",
    # Prompt templates
    "get_daily_prompt",
    "get_weekly_prompt",
    "get_monthly_prompt",
    "get_annual_prompt",
    "DAILY_SYSTEM_PROMPT",
    "DAILY_HUMAN_PROMPT",
    "WEEKLY_SYSTEM_PROMPT",
    "WEEKLY_HUMAN_PROMPT",
    "MONTHLY_SYSTEM_PROMPT",
    "MONTHLY_HUMAN_PROMPT",
    "ANNUAL_SYSTEM_PROMPT",
    "ANNUAL_HUMAN_PROMPT",
    "IMAGE_EXTRACTION_PROMPT",
    # Constants
    "IMAGE_EXTENSIONS",
    "MEDIA_TYPE_MAP",
    "TEXT_EXTENSIONS",
    "ALL_EXTENSIONS",
]
