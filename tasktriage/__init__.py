"""
TaskTriage - Daily Task Analyzer

Analyzes daily task notes using Claude via LangChain and generates
actionable execution plans based on GTD principles.

Supports reading notes from both local/USB directories and Google Drive.
"""

__version__ = "0.2.1"

# Configuration
from .config import (
    fetch_api_key,
    load_model_config,
    EXTERNAL_INPUT_DIR,
    LOCAL_INPUT_DIR,
    CONFIG_PATH,
    DEFAULT_MODEL,
    GOOGLE_OAUTH_CLIENT_ID,
    GOOGLE_OAUTH_CLIENT_SECRET,
    GOOGLE_DRIVE_FOLDER_ID,
    NOTES_SOURCE,
    CONTEXT_FILE_PATH,
    LOCAL_CONTEXT_DIR,
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
    get_context_summary_prompt,
    DAILY_SYSTEM_PROMPT,
    DAILY_HUMAN_PROMPT,
    WEEKLY_SYSTEM_PROMPT,
    WEEKLY_HUMAN_PROMPT,
    MONTHLY_SYSTEM_PROMPT,
    MONTHLY_HUMAN_PROMPT,
    ANNUAL_SYSTEM_PROMPT,
    ANNUAL_HUMAN_PROMPT,
    IMAGE_EXTRACTION_PROMPT,
    CONTEXT_SUMMARY_SYSTEM_PROMPT,
    CONTEXT_SUMMARY_HUMAN_PROMPT,
    METADATA_EXTRACTION_PROMPT,
)

# Image processing
from .image import (
    extract_text_from_image,
    extract_text_from_pdf,
    IMAGE_EXTENSIONS,
    PDF_EXTENSIONS,
    VISUAL_EXTENSIONS,
    MEDIA_TYPE_MAP,
)

# File operations
from .files import (
    load_all_unanalyzed_task_notes,
    collect_weekly_analyses_for_week,
    collect_monthly_analyses_for_month,
    collect_annual_analyses_for_year,
    save_analysis,
    convert_visual_files_in_directory,
    TEXT_EXTENSIONS,
    ALL_EXTENSIONS,
)

# Google Drive integration
from .gdrive import (
    GoogleDriveClient,
    is_gdrive_configured,
)

# Context summarization
from .context import (
    parse_context_file,
    collect_files,
    compile_content,
    needs_resummarization,
    summarize_context,
    summarize_all_contexts,
    select_relevant_contexts,
)

# Core analysis
from .analysis import analyze_tasks

# CLI entry point
from .cli import main

__all__ = [
    # Main entry point
    "main",
    # Core functions
    "analyze_tasks",
    "load_all_unanalyzed_task_notes",
    "collect_weekly_analyses_for_week",
    "collect_monthly_analyses_for_month",
    "collect_annual_analyses_for_year",
    "save_analysis",
    "convert_visual_files_in_directory",
    "extract_text_from_image",
    "extract_text_from_pdf",
    # Google Drive
    "GoogleDriveClient",
    "is_gdrive_configured",
    # Configuration
    "fetch_api_key",
    "load_model_config",
    "EXTERNAL_INPUT_DIR",
    "LOCAL_INPUT_DIR",
    "CONFIG_PATH",
    "DEFAULT_MODEL",
    "GOOGLE_OAUTH_CLIENT_ID",
    "GOOGLE_OAUTH_CLIENT_SECRET",
    "GOOGLE_DRIVE_FOLDER_ID",
    "NOTES_SOURCE",
    "CONTEXT_FILE_PATH",
    "LOCAL_CONTEXT_DIR",
    "is_usb_available",
    "is_local_input_available",
    "is_gdrive_available",
    "get_active_source",
    "get_all_input_directories",
    "get_primary_input_directory",
    # Context summarization
    "parse_context_file",
    "collect_files",
    "compile_content",
    "needs_resummarization",
    "summarize_context",
    "summarize_all_contexts",
    "select_relevant_contexts",
    # Prompt templates
    "get_daily_prompt",
    "get_weekly_prompt",
    "get_monthly_prompt",
    "get_annual_prompt",
    "get_context_summary_prompt",
    "DAILY_SYSTEM_PROMPT",
    "DAILY_HUMAN_PROMPT",
    "WEEKLY_SYSTEM_PROMPT",
    "WEEKLY_HUMAN_PROMPT",
    "MONTHLY_SYSTEM_PROMPT",
    "MONTHLY_HUMAN_PROMPT",
    "ANNUAL_SYSTEM_PROMPT",
    "ANNUAL_HUMAN_PROMPT",
    "IMAGE_EXTRACTION_PROMPT",
    "CONTEXT_SUMMARY_SYSTEM_PROMPT",
    "CONTEXT_SUMMARY_HUMAN_PROMPT",
    "METADATA_EXTRACTION_PROMPT",
    # Constants
    "IMAGE_EXTENSIONS",
    "PDF_EXTENSIONS",
    "VISUAL_EXTENSIONS",
    "MEDIA_TYPE_MAP",
    "TEXT_EXTENSIONS",
    "ALL_EXTENSIONS",
]
