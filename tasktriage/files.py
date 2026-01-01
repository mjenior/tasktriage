"""
File I/O operations for TaskTriage.

Handles loading task notes, collecting analyses, and saving output files.
Supports both local USB directory and Google Drive as sources.
"""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from .config import USB_DIR, get_active_source
from .image import extract_text_from_image, IMAGE_EXTENSIONS

# Supported text file extensions
TEXT_EXTENSIONS = {".txt"}

# All supported input file extensions
ALL_EXTENSIONS = TEXT_EXTENSIONS | IMAGE_EXTENSIONS


def _extract_timestamp(filename: str) -> str | None:
    """Extract timestamp portion from a notes filename.

    Handles filenames with optional page identifiers.

    Supported formats:
        - YYYYMMDD_HHMMSS.ext (e.g., 20251225_073454.txt)
        - YYYYMMDD_HHMMSS_Page_N.ext (e.g., 20251225_073454_Page_1.png)

    Args:
        filename: Filename with timestamp prefix

    Returns:
        Timestamp string (YYYYMMDD_HHMMSS) or None if not found
    """
    stem = Path(filename).stem

    # Handle page identifiers (e.g., 20251225_073454_Page_1)
    if "_Page_" in stem:
        stem = stem.split("_Page_")[0]

    # Validate it looks like a timestamp (15 chars: YYYYMMDD_HHMMSS)
    if len(stem) == 15 and stem[8] == "_":
        return stem

    return None


def _parse_filename_datetime(filename: str) -> datetime | None:
    """Parse datetime from a notes filename.

    Handles filenames with optional page identifiers.

    Supported formats:
        - YYYYMMDD_HHMMSS.ext (e.g., 20251225_073454.txt)
        - YYYYMMDD_HHMMSS_Page_N.ext (e.g., 20251225_073454_Page_1.png)

    Args:
        filename: Filename with timestamp prefix

    Returns:
        Parsed datetime, or None if parsing fails
    """
    timestamp = _extract_timestamp(filename)
    if not timestamp:
        return None

    try:
        return datetime.strptime(timestamp, "%Y%m%d_%H%M%S")
    except ValueError:
        return None


# =============================================================================
# USB/Local Directory Functions
# =============================================================================

def _load_task_notes_usb(notes_type: str = "daily") -> tuple[str, Path, datetime]:
    """Load task notes from USB/local directory.

    Args:
        notes_type: Type of notes to load (e.g., "daily", "weekly")

    Returns:
        Tuple of (file contents, path to the notes file, parsed datetime from filename)
    """
    base_dir = Path(USB_DIR)

    if not base_dir.exists():
        raise FileNotFoundError(
            f"USB directory not found: {USB_DIR}"
        )

    notes_dir = base_dir / notes_type

    if not notes_dir.exists():
        raise FileNotFoundError(f"Notes directory not found: {notes_dir}")

    # Find all supported files and sort by name (newest first based on timestamp)
    all_files = []
    for ext in ALL_EXTENSIONS:
        all_files.extend(notes_dir.glob(f"*{ext}"))
    all_files = sorted(all_files, reverse=True)

    for notes_path in all_files:
        # Skip files that are already analysis files
        if "_analysis" in notes_path.name:
            continue

        # Extract timestamp from filename (handles page identifiers)
        timestamp = _extract_timestamp(notes_path.name)
        if not timestamp:
            continue

        # Check if this file already has an associated analysis file
        # Use timestamp only so all pages of a multi-page note share one analysis
        analysis_filename = f"{timestamp}.{notes_type}_analysis.txt"
        analysis_path = notes_dir / analysis_filename

        if not analysis_path.exists():
            # Parse datetime from the extracted timestamp
            file_date = _parse_filename_datetime(notes_path.name)
            if not file_date:
                continue

            # Extract text based on file type
            if notes_path.suffix.lower() in IMAGE_EXTENSIONS:
                file_contents = extract_text_from_image(notes_path)
            else:
                file_contents = notes_path.read_text()

            return file_contents, notes_path, file_date

    raise FileNotFoundError(
        f"No unanalyzed notes files found in: {notes_dir}"
    )


def _collect_weekly_analyses_usb() -> tuple[str, Path, datetime, datetime]:
    """Collect weekly analyses from USB/local directory.

    Returns:
        Tuple of (combined analysis text, output path, week start, week end)
    """
    base_dir = Path(USB_DIR)

    if not base_dir.exists():
        raise FileNotFoundError(
            f"USB directory not found: {USB_DIR}"
        )

    daily_dir = base_dir / "daily"
    weekly_dir = base_dir / "weekly"

    if not daily_dir.exists():
        raise FileNotFoundError(f"daily notes directory not found: {daily_dir}")

    weekly_dir.mkdir(exist_ok=True)

    # Calculate previous week's date range (Monday to Sunday)
    today = datetime.now()
    days_since_sunday = (today.weekday() + 1) % 7
    last_sunday = today - timedelta(days=days_since_sunday)
    last_monday = last_sunday - timedelta(days=6)

    week_start = last_monday.replace(hour=0, minute=0, second=0, microsecond=0)
    week_end = last_sunday.replace(hour=23, minute=59, second=59, microsecond=999999)

    # Find all daily_analysis files from the previous week
    analysis_files = sorted(daily_dir.glob("*.daily_analysis.txt"))

    collected_analyses = []
    for analysis_path in analysis_files:
        try:
            date_str = analysis_path.stem.split(".")[0]
            file_date = datetime.strptime(date_str, "%Y%m%d_%H%M%S")
        except ValueError:
            continue

        if week_start <= file_date <= week_end:
            content = analysis_path.read_text()
            date_label = file_date.strftime("%A, %B %d, %Y")
            collected_analyses.append(f"## {date_label}\n\n{content}")

    if not collected_analyses:
        raise FileNotFoundError(
            f"No daily analysis files found for the week of "
            f"{week_start.strftime('%Y-%m-%d')} to {week_end.strftime('%Y-%m-%d')}"
        )

    combined_text = "\n\n---\n\n".join(collected_analyses)
    week_label = week_start.strftime("%Y%m%d")
    output_path = weekly_dir / f"{week_label}.week.txt"

    return combined_text, output_path, week_start, week_end


def _save_analysis_usb(analysis: str, input_path: Path, notes_type: str = "daily") -> Path:
    """Save analysis to USB/local directory.

    Args:
        analysis: The analysis content
        input_path: Path to the original notes file
        notes_type: Type of analysis

    Returns:
        Path to the saved analysis file
    """
    # Extract timestamp from filename (handles page identifiers)
    timestamp = _extract_timestamp(input_path.name)
    if timestamp:
        output_filename = f"{timestamp}.{notes_type}_analysis.txt"
    else:
        # Fallback to full stem if timestamp extraction fails
        output_filename = f"{input_path.stem}.{notes_type}_analysis.txt"
    output_path = input_path.parent / output_filename

    header = f"{notes_type.capitalize()} Task Analysis"
    formatted_output = f"{header}\n{'=' * 40}\n\n{analysis}\n"

    output_path.write_text(formatted_output)
    return output_path


# =============================================================================
# Google Drive Functions
# =============================================================================

def _analysis_exists_locally(notes_type: str, analysis_filename: str) -> bool:
    """Check if an analysis file exists in the local output directory.

    Args:
        notes_type: Type of notes ("daily" or "weekly")
        analysis_filename: Name of the analysis file to check

    Returns:
        True if the analysis file exists locally
    """
    from .config import LOCAL_OUTPUT_DIR

    if not LOCAL_OUTPUT_DIR:
        return False

    analysis_path = Path(LOCAL_OUTPUT_DIR) / notes_type / analysis_filename
    return analysis_path.exists()


def _load_task_notes_gdrive(notes_type: str = "daily") -> tuple[str, Path, datetime]:
    """Load task notes from Google Drive.

    Args:
        notes_type: Type of notes to load (e.g., "daily", "weekly")

    Returns:
        Tuple of (file contents, virtual path, parsed datetime from filename)
    """
    from .config import LOCAL_OUTPUT_DIR
    from .gdrive import (
        GoogleDriveClient,
        IMAGE_MIME_TYPES,
        parse_filename_datetime,
        get_file_extension,
        extract_timestamp_from_filename,
    )

    client = GoogleDriveClient()
    files = client.list_notes_files(notes_type)

    for file_info in files:
        filename = file_info["name"]
        file_id = file_info["id"]
        mime_type = file_info["mimeType"]

        # Skip analysis files
        if "_analysis" in filename:
            continue

        # Parse datetime from filename
        file_date = parse_filename_datetime(filename)
        if not file_date:
            continue

        # Check if analysis already exists
        # Use timestamp only so all pages of a multi-page note share one analysis
        timestamp = extract_timestamp_from_filename(filename)
        if timestamp:
            analysis_filename = f"{timestamp}.{notes_type}_analysis.txt"
        else:
            stem = Path(filename).stem
            if "." in stem:
                stem = stem.split(".")[0]
            analysis_filename = f"{stem}.{notes_type}_analysis.txt"

        # Check local output directory first (when LOCAL_OUTPUT_DIR is set)
        if _analysis_exists_locally(notes_type, analysis_filename):
            continue

        # Fall back to checking Google Drive (for setups without local output)
        if not LOCAL_OUTPUT_DIR and client.file_exists(notes_type, analysis_filename):
            continue

        # Download and process the file
        if mime_type in IMAGE_MIME_TYPES:
            # Download image to temp file and extract text
            image_data = client.download_file(file_id)
            ext = get_file_extension(mime_type)

            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
                tmp.write(image_data)
                tmp_path = Path(tmp.name)

            try:
                file_contents = extract_text_from_image(tmp_path)
            finally:
                tmp_path.unlink()
        else:
            # Download text file directly
            file_contents = client.download_file_text(file_id)

        # Create a virtual path for compatibility with save functions
        virtual_path = Path(f"gdrive://{notes_type}/{filename}")

        return file_contents, virtual_path, file_date

    raise FileNotFoundError(
        f"No unanalyzed notes files found in Google Drive folder: {notes_type}/"
    )


def _collect_weekly_analyses_gdrive() -> tuple[str, Path, datetime, datetime]:
    """Collect weekly analyses from Google Drive.

    Returns:
        Tuple of (combined analysis text, virtual output path, week start, week end)
    """
    from .gdrive import GoogleDriveClient, parse_filename_datetime

    client = GoogleDriveClient()

    # Calculate previous week's date range (Monday to Sunday)
    today = datetime.now()
    days_since_sunday = (today.weekday() + 1) % 7
    last_sunday = today - timedelta(days=days_since_sunday)
    last_monday = last_sunday - timedelta(days=6)

    week_start = last_monday.replace(hour=0, minute=0, second=0, microsecond=0)
    week_end = last_sunday.replace(hour=23, minute=59, second=59, microsecond=999999)

    # List all files in daily folder
    try:
        files = client.list_notes_files("daily")
    except FileNotFoundError:
        raise FileNotFoundError("daily folder not found in Google Drive")

    collected_analyses = []
    for file_info in sorted(files, key=lambda x: x["name"]):
        filename = file_info["name"]

        # Only process analysis files
        if ".daily_analysis.txt" not in filename:
            continue

        file_date = parse_filename_datetime(filename)
        if not file_date:
            continue

        if week_start <= file_date <= week_end:
            content = client.download_file_text(file_info["id"])
            date_label = file_date.strftime("%A, %B %d, %Y")
            collected_analyses.append(f"## {date_label}\n\n{content}")

    if not collected_analyses:
        raise FileNotFoundError(
            f"No daily analysis files found for the week of "
            f"{week_start.strftime('%Y-%m-%d')} to {week_end.strftime('%Y-%m-%d')}"
        )

    combined_text = "\n\n---\n\n".join(collected_analyses)
    week_label = week_start.strftime("%Y%m%d")
    virtual_path = Path(f"gdrive://weekly/{week_label}.week.txt")

    return combined_text, virtual_path, week_start, week_end


def _save_analysis_gdrive(analysis: str, input_path: Path, notes_type: str = "daily") -> Path:
    """Save analysis when source is Google Drive.

    If LOCAL_OUTPUT_DIR is configured, saves locally to that directory.
    Otherwise attempts to upload to Google Drive (requires proper quota/permissions).

    Args:
        analysis: The analysis content
        input_path: Virtual path from load functions (gdrive://...)
        notes_type: Type of analysis

    Returns:
        Path to the saved analysis file (local or virtual gdrive path)
    """
    from .config import LOCAL_OUTPUT_DIR
    from .gdrive import extract_timestamp_from_filename

    # Extract filename from virtual path
    filename = input_path.name

    # Extract timestamp (handles page identifiers)
    timestamp = extract_timestamp_from_filename(filename)
    if timestamp:
        stem = timestamp
    else:
        # Fallback: extract stem and handle special cases
        stem = Path(filename).stem
        if "." in stem and "_analysis" not in stem:
            stem = stem.split(".")[0]

    output_filename = f"{stem}.{notes_type}_analysis.txt"

    header = f"{notes_type.capitalize()} Task Analysis"
    formatted_output = f"{header}\n{'=' * 40}\n\n{analysis}\n"

    # Determine target folder from path
    if "weekly" in str(input_path):
        subfolder = "weekly"
    else:
        subfolder = "daily"

    # If local output directory is configured, save there instead of GDrive
    # (Service accounts don't have storage quota for uploads)
    if LOCAL_OUTPUT_DIR:
        output_dir = Path(LOCAL_OUTPUT_DIR) / subfolder
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / output_filename
        output_path.write_text(formatted_output)
        return output_path

    # Otherwise, attempt to upload to Google Drive
    from .gdrive import GoogleDriveClient
    client = GoogleDriveClient()
    client.upload_file(subfolder, output_filename, formatted_output)

    return Path(f"gdrive://{subfolder}/{output_filename}")


# =============================================================================
# Public API (automatically selects source based on configuration)
# =============================================================================

def load_task_notes(notes_type: str = "daily") -> tuple[str, Path, datetime]:
    """Load the most recent task notes file that hasn't been analyzed yet.

    Automatically selects between USB and Google Drive based on configuration.

    Supports both .txt files (read directly) and image files (.png, .jpg, .jpeg,
    .gif, .webp) which are processed through Claude's vision API to extract text.

    Args:
        notes_type: Type of notes to load (e.g., "daily", "weekly")

    Returns:
        Tuple of (file contents, path to the notes file, parsed datetime from filename)

    Raises:
        FileNotFoundError: If the notes directory doesn't exist or no unanalyzed files found
    """
    source = get_active_source()

    if source == "gdrive":
        return _load_task_notes_gdrive(notes_type)
    else:
        return _load_task_notes_usb(notes_type)


def collect_weekly_analyses() -> tuple[str, Path, datetime, datetime]:
    """Collect all daily analysis files from the previous week.

    Automatically selects between USB and Google Drive based on configuration.

    Returns:
        Tuple of (combined analysis text, output path for weekly analysis,
                  week start datetime, week end datetime)

    Raises:
        FileNotFoundError: If directories don't exist or no analyses found for the week
    """
    source = get_active_source()

    if source == "gdrive":
        return _collect_weekly_analyses_gdrive()
    else:
        return _collect_weekly_analyses_usb()


def save_analysis(analysis: str, input_path: Path, notes_type: str = "daily") -> Path:
    """Save the analysis output to a file.

    Automatically selects between USB and Google Drive based on the input path.
    If input_path starts with "gdrive:", saves to Google Drive; otherwise saves locally.

    Args:
        analysis: The analysis content from analyze_tasks
        input_path: Path to the original notes file
        notes_type: Type of analysis (e.g., "daily", "weekly")

    Returns:
        Path to the saved analysis file
    """
    # Check if this is a Google Drive path
    # Note: Path normalizes "gdrive://" to "gdrive:/" so we check for "gdrive:"
    path_str = str(input_path)
    if path_str.startswith("gdrive:"):
        return _save_analysis_gdrive(analysis, input_path, notes_type)
    else:
        return _save_analysis_usb(analysis, input_path, notes_type)


def get_notes_source() -> str:
    """Get the currently active notes source.

    Returns:
        "usb" or "gdrive" indicating which source is being used
    """
    return get_active_source()
