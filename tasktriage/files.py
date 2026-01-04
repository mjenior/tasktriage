"""
File I/O operations for TaskTriage.

Handles loading task notes, collecting analyses, and saving output files.
Supports both local USB directory and Google Drive as sources.
"""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from .config import get_active_source, get_all_input_directories, get_primary_input_directory
from .image import extract_text_from_image, IMAGE_EXTENSIONS

# Backward compatibility: USB_DIR references the primary input directory
# This allows existing code to work while we transition to multi-source reading
def _get_usb_dir():
    """Get the primary input directory (for backward compatibility with USB_DIR references)."""
    try:
        return str(get_primary_input_directory())
    except ValueError:
        return None

USB_DIR = _get_usb_dir()

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

def _needs_reanalysis_usb(notes_path: Path, analysis_path: Path) -> bool:
    """Check if a notes file needs re-analysis because it was modified after its analysis.

    This enables edited notes files to be re-analyzed, with the new analysis
    replacing the old one.

    Args:
        notes_path: Path to the notes file (PNG or TXT)
        analysis_path: Path to the existing analysis file

    Returns:
        True if the notes file (or its raw text version) was modified after the analysis
    """
    if not analysis_path.exists():
        return False  # No analysis exists, so not a "re-analysis" case

    analysis_mtime = analysis_path.stat().st_mtime

    # Check if the notes file itself was modified after analysis
    if notes_path.stat().st_mtime > analysis_mtime:
        return True

    # For image files, also check if the corresponding .raw_notes.txt was edited
    if notes_path.suffix.lower() in IMAGE_EXTENSIONS:
        timestamp = _extract_timestamp(notes_path.name)
        if timestamp:
            raw_notes_path = notes_path.parent / f"{timestamp}.raw_notes.txt"
            if raw_notes_path.exists() and raw_notes_path.stat().st_mtime > analysis_mtime:
                return True

    return False


def _load_task_notes_usb(notes_type: str = "daily", file_preference: str = "png") -> tuple[str, Path, datetime]:
    """Load task notes from all configured local input directories.

    Checks all available input directories (USB_INPUT_DIR, LOCAL_INPUT_DIR)
    and returns the first unanalyzed file found.

    Args:
        notes_type: Type of notes to load (e.g., "daily", "weekly")
        file_preference: File type preference ("png" or "txt")

    Returns:
        Tuple of (file contents, path to the notes file, parsed datetime from filename)

    Raises:
        FileNotFoundError: If no unanalyzed notes are found in any directory
    """
    input_dirs = get_all_input_directories()

    if not input_dirs:
        raise FileNotFoundError("No input directories configured or available")

    # Determine which extensions to search based on preference
    if file_preference == "txt":
        search_extensions = TEXT_EXTENSIONS
    else:  # default to "png"
        search_extensions = IMAGE_EXTENSIONS

    # Try each input directory
    for base_dir in input_dirs:
        notes_dir = base_dir / notes_type

        if not notes_dir.exists():
            continue  # Skip this directory if it doesn't exist

        # Find all files matching preference and sort by name (newest first based on timestamp)
        all_files = []
        for ext in search_extensions:
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

            # Include file if: no analysis exists OR file was modified after analysis
            if not analysis_path.exists() or _needs_reanalysis_usb(notes_path, analysis_path):
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
        f"No unanalyzed notes files found in any configured input directory"
    )


def _load_all_unanalyzed_task_notes_usb(notes_type: str = "daily", file_preference: str = "png") -> list[tuple[str, Path, datetime]]:
    """Load all unanalyzed task notes from all configured local input directories.

    Checks all available input directories (USB_INPUT_DIR, LOCAL_INPUT_DIR)
    and collects unique unanalyzed files. Deduplicates by timestamp to avoid
    processing the same logical file from multiple locations.

    Args:
        notes_type: Type of notes to load (default: "daily")
        file_preference: File type preference ("png" or "txt")

    Returns:
        List of tuples of (file contents, path to the notes file, parsed datetime from filename)
    """
    input_dirs = get_all_input_directories()

    if not input_dirs:
        raise FileNotFoundError("No input directories configured or available")

    # Determine which extensions to search based on preference
    if file_preference == "txt":
        search_extensions = TEXT_EXTENSIONS
    else:  # default to "png"
        search_extensions = IMAGE_EXTENSIONS

    unanalyzed_files = []
    seen_timestamps = set()  # Track timestamps to avoid duplicates

    # Check each input directory
    for base_dir in input_dirs:
        notes_dir = base_dir / notes_type

        if not notes_dir.exists():
            continue  # Skip this directory if it doesn't exist

        # Find all files matching preference and sort by name (newest first based on timestamp)
        all_files = []
        for ext in search_extensions:
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

            # Skip if we've already seen this timestamp (deduplication)
            if timestamp in seen_timestamps:
                continue

            # Check if this file already has an associated analysis file
            # Use timestamp only so all pages of a multi-page note share one analysis
            analysis_filename = f"{timestamp}.{notes_type}_analysis.txt"
            analysis_path = notes_dir / analysis_filename

            # Include file if: no analysis exists OR file was modified after analysis
            if not analysis_path.exists() or _needs_reanalysis_usb(notes_path, analysis_path):
                # Parse datetime from the extracted timestamp
                file_date = _parse_filename_datetime(notes_path.name)
                if not file_date:
                    continue

                # Extract text based on file type
                if notes_path.suffix.lower() in IMAGE_EXTENSIONS:
                    file_contents = extract_text_from_image(notes_path)
                else:
                    file_contents = notes_path.read_text()

                unanalyzed_files.append((file_contents, notes_path, file_date))
                seen_timestamps.add(timestamp)  # Mark this timestamp as processed

    if not unanalyzed_files:
        raise FileNotFoundError(
            f"No unanalyzed notes files found in any configured input directory"
        )

    return unanalyzed_files


def _collect_weekly_analyses_usb_for_week(week_start: datetime, week_end: datetime) -> tuple[str, Path, datetime, datetime]:
    """Collect weekly analyses from all configured local input directories for a specific work week.

    Collects daily analyses from all input directories and saves the weekly analysis
    to the primary input directory.

    Args:
        week_start: Start of work week (Monday)
        week_end: End of work week (Friday)

    Returns:
        Tuple of (combined analysis text, output path, week start, week end)
    """
    from .config import get_primary_input_directory

    input_dirs = get_all_input_directories()

    if not input_dirs:
        raise FileNotFoundError("No input directories configured or available")

    # Collect daily analyses from all input directories
    collected_analyses = []
    seen_timestamps = set()  # Deduplicate by timestamp

    for base_dir in input_dirs:
        daily_dir = base_dir / "daily"

        if not daily_dir.exists():
            continue

        # Find all daily_analysis files from the specified week
        analysis_files = sorted(daily_dir.glob("*.daily_analysis.txt"))

        for analysis_path in analysis_files:
            try:
                date_str = analysis_path.stem.split(".")[0]
                file_date = datetime.strptime(date_str, "%Y%m%d_%H%M%S")
            except ValueError:
                continue

            # Skip if we've already seen this timestamp
            if date_str in seen_timestamps:
                continue

            if week_start <= file_date <= week_end:
                content = analysis_path.read_text()
                date_label = file_date.strftime("%A, %B %d, %Y")
                collected_analyses.append(f"## {date_label}\n\n{content}")
                seen_timestamps.add(date_str)

    if not collected_analyses:
        raise FileNotFoundError(
            f"No daily analysis files found for the week of "
            f"{week_start.strftime('%Y-%m-%d')} to {week_end.strftime('%Y-%m-%d')}"
        )

    # Sort by date (analyses are labeled with dates)
    collected_analyses.sort()

    combined_text = "\n\n---\n\n".join(collected_analyses)

    # Save to primary input directory
    primary_dir = get_primary_input_directory()
    weekly_dir = primary_dir / "weekly"
    weekly_dir.mkdir(exist_ok=True)

    week_label = week_start.strftime("%Y%m%d")
    output_path = weekly_dir / f"{week_label}.week.txt"

    return combined_text, output_path, week_start, week_end


def _collect_weekly_analyses_usb() -> tuple[str, Path, datetime, datetime]:
    """Collect weekly analyses from USB/local directory for previous work week.

    Returns:
        Tuple of (combined analysis text, output path, week start, week end)
    """
    # Calculate previous work week's date range (Monday to Friday)
    today = datetime.now()

    # Get current week's Monday
    days_since_monday = today.weekday()
    current_monday = today - timedelta(days=days_since_monday)

    # Previous week's Monday and Friday
    last_monday = current_monday - timedelta(days=7)
    last_friday = last_monday + timedelta(days=4)

    week_start = last_monday.replace(hour=0, minute=0, second=0, microsecond=0)
    week_end = last_friday.replace(hour=23, minute=59, second=59, microsecond=999999)

    return _collect_weekly_analyses_usb_for_week(week_start, week_end)


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


def _raw_text_exists_usb(input_path: Path) -> bool:
    """Check if a raw text file already exists for the given input file.

    Args:
        input_path: Path to the original notes file (PNG)

    Returns:
        True if raw text file exists, False otherwise
    """
    timestamp = _extract_timestamp(input_path.name)
    if timestamp:
        raw_filename = f"{timestamp}.raw_notes.txt"
    else:
        raw_filename = f"{input_path.stem}.raw_notes.txt"
    raw_path = input_path.parent / raw_filename
    return raw_path.exists()


def _save_raw_text_usb(raw_text: str, input_path: Path) -> Path:
    """Save raw extracted text to USB/local directory.

    Args:
        raw_text: The raw extracted text content
        input_path: Path to the original notes file (PNG)

    Returns:
        Path to the saved raw text file
    """
    # Extract timestamp from filename (handles page identifiers)
    timestamp = _extract_timestamp(input_path.name)
    if timestamp:
        output_filename = f"{timestamp}.raw_notes.txt"
    else:
        # Fallback to full stem if timestamp extraction fails
        output_filename = f"{input_path.stem}.raw_notes.txt"
    output_path = input_path.parent / output_filename

    output_path.write_text(raw_text)
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


def _needs_reanalysis_gdrive(notes_type: str, timestamp: str, file_info: dict) -> bool:
    """Check if a Google Drive notes file needs re-analysis.

    For Google Drive sources with LOCAL_OUTPUT_DIR, checks if the local raw_notes.txt
    file was modified after the analysis file was created.

    Args:
        notes_type: Type of notes ("daily" or "weekly")
        timestamp: The extracted timestamp from the filename
        file_info: Google Drive file info dict with 'modifiedTime'

    Returns:
        True if re-analysis is needed
    """
    from .config import LOCAL_OUTPUT_DIR

    if not LOCAL_OUTPUT_DIR:
        return False  # Can't check modification times without local files

    analysis_path = Path(LOCAL_OUTPUT_DIR) / notes_type / f"{timestamp}.{notes_type}_analysis.txt"
    if not analysis_path.exists():
        return False  # No analysis exists, not a "re-analysis" case

    analysis_mtime = analysis_path.stat().st_mtime

    # Check if the local raw_notes.txt was edited after the analysis
    raw_notes_path = Path(LOCAL_OUTPUT_DIR) / notes_type / f"{timestamp}.raw_notes.txt"
    if raw_notes_path.exists() and raw_notes_path.stat().st_mtime > analysis_mtime:
        return True

    return False


def _load_task_notes_gdrive(notes_type: str = "daily", file_preference: str = "png") -> tuple[str, Path, datetime]:
    """Load task notes from Google Drive.

    Args:
        notes_type: Type of notes to load (e.g., "daily", "weekly")
        file_preference: File type preference ("png" or "txt")

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

        # Filter by file type preference
        file_ext = Path(filename).suffix.lower()
        if file_preference == "txt":
            if file_ext not in TEXT_EXTENSIONS:
                continue
        else:  # default to "png"
            if file_ext not in IMAGE_EXTENSIONS:
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
        # Skip if analysis exists AND no re-analysis is needed
        if _analysis_exists_locally(notes_type, analysis_filename):
            if timestamp and _needs_reanalysis_gdrive(notes_type, timestamp, file_info):
                pass  # Include for re-analysis
            else:
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


def _load_all_unanalyzed_task_notes_gdrive(notes_type: str = "daily", file_preference: str = "png") -> list[tuple[str, Path, datetime]]:
    """Load all unanalyzed task notes from Google Drive.

    Args:
        notes_type: Type of notes to load (e.g., "daily", "weekly")
        file_preference: File type preference ("png" or "txt")

    Returns:
        List of tuples of (file contents, virtual path, parsed datetime from filename)
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

    unanalyzed_files = []

    for file_info in files:
        filename = file_info["name"]
        file_id = file_info["id"]
        mime_type = file_info["mimeType"]

        # Skip analysis files
        if "_analysis" in filename:
            continue

        # Filter by file type preference
        file_ext = Path(filename).suffix.lower()
        if file_preference == "txt":
            if file_ext not in TEXT_EXTENSIONS:
                continue
        else:  # default to "png"
            if file_ext not in IMAGE_EXTENSIONS:
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
        # Skip if analysis exists AND no re-analysis is needed
        if _analysis_exists_locally(notes_type, analysis_filename):
            if timestamp and _needs_reanalysis_gdrive(notes_type, timestamp, file_info):
                pass  # Include for re-analysis
            else:
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

        unanalyzed_files.append((file_contents, virtual_path, file_date))

    if not unanalyzed_files:
        raise FileNotFoundError(
            f"No unanalyzed notes files found in Google Drive folder: {notes_type}/"
        )

    return unanalyzed_files


def _collect_weekly_analyses_gdrive_for_week(week_start: datetime, week_end: datetime) -> tuple[str, Path, datetime, datetime]:
    """Collect weekly analyses from Google Drive for a specific work week.

    Args:
        week_start: Start of work week (Monday)
        week_end: End of work week (Friday)

    Returns:
        Tuple of (combined analysis text, virtual output path, week start, week end)
    """
    from .gdrive import GoogleDriveClient, parse_filename_datetime

    client = GoogleDriveClient()

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


def _collect_weekly_analyses_gdrive() -> tuple[str, Path, datetime, datetime]:
    """Collect weekly analyses from Google Drive for previous work week.

    Returns:
        Tuple of (combined analysis text, virtual output path, week start, week end)
    """
    # Calculate previous work week's date range (Monday to Friday)
    today = datetime.now()

    # Get current week's Monday
    days_since_monday = today.weekday()
    current_monday = today - timedelta(days=days_since_monday)

    # Previous week's Monday and Friday
    last_monday = current_monday - timedelta(days=7)
    last_friday = last_monday + timedelta(days=4)

    week_start = last_monday.replace(hour=0, minute=0, second=0, microsecond=0)
    week_end = last_friday.replace(hour=23, minute=59, second=59, microsecond=999999)

    return _collect_weekly_analyses_gdrive_for_week(week_start, week_end)


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


def _raw_text_exists_gdrive(input_path: Path) -> bool:
    """Check if a raw text file already exists for the given Google Drive input file.

    Args:
        input_path: Virtual path from load functions (gdrive://...)

    Returns:
        True if raw text file exists, False otherwise
    """
    from .config import LOCAL_OUTPUT_DIR
    from .gdrive import extract_timestamp_from_filename

    filename = input_path.name
    timestamp = extract_timestamp_from_filename(filename)
    if timestamp:
        raw_filename = f"{timestamp}.raw_notes.txt"
    else:
        stem = Path(filename).stem
        if "." in stem:
            stem = stem.split(".")[0]
        raw_filename = f"{stem}.raw_notes.txt"

    # Check local output directory first (when LOCAL_OUTPUT_DIR is set)
    if LOCAL_OUTPUT_DIR:
        raw_path = Path(LOCAL_OUTPUT_DIR) / "daily" / raw_filename
        if raw_path.exists():
            return True

    # Fall back to checking Google Drive
    if not LOCAL_OUTPUT_DIR:
        from .gdrive import GoogleDriveClient
        client = GoogleDriveClient()
        return client.file_exists("daily", raw_filename)

    return False


def _save_raw_text_gdrive(raw_text: str, input_path: Path) -> Path:
    """Save raw extracted text when source is Google Drive.

    If LOCAL_OUTPUT_DIR is configured, saves locally to that directory.
    Otherwise attempts to upload to Google Drive.

    Args:
        raw_text: The raw extracted text content
        input_path: Virtual path from load functions (gdrive://...)

    Returns:
        Path to the saved raw text file (local or virtual gdrive path)
    """
    from .config import LOCAL_OUTPUT_DIR
    from .gdrive import extract_timestamp_from_filename

    filename = input_path.name
    timestamp = extract_timestamp_from_filename(filename)
    if timestamp:
        output_filename = f"{timestamp}.raw_notes.txt"
    else:
        stem = Path(filename).stem
        if "." in stem:
            stem = stem.split(".")[0]
        output_filename = f"{stem}.raw_notes.txt"

    # If local output directory is configured, save there
    if LOCAL_OUTPUT_DIR:
        output_dir = Path(LOCAL_OUTPUT_DIR) / "daily"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / output_filename
        output_path.write_text(raw_text)
        return output_path

    # Otherwise, attempt to upload to Google Drive
    from .gdrive import GoogleDriveClient
    client = GoogleDriveClient()
    client.upload_file("daily", output_filename, raw_text)

    return Path(f"gdrive://daily/{output_filename}")


# =============================================================================
# Public API (automatically selects source based on configuration)
# =============================================================================

def load_task_notes(notes_type: str = "daily", file_preference: str = "png") -> tuple[str, Path, datetime]:
    """Load the most recent task notes file that hasn't been analyzed yet.

    Automatically selects between USB and Google Drive based on configuration.

    Supports both .txt files (read directly) and image files (.png, .jpg, .jpeg,
    .gif, .webp) which are processed through Claude's vision API to extract text.

    Args:
        notes_type: Type of notes to load (e.g., "daily", "weekly")
        file_preference: File type preference - "png" or "txt" (default: "png")

    Returns:
        Tuple of (file contents, path to the notes file, parsed datetime from filename)

    Raises:
        FileNotFoundError: If the notes directory doesn't exist or no unanalyzed files found
    """
    source = get_active_source()

    if source == "gdrive":
        return _load_task_notes_gdrive(notes_type, file_preference)
    else:
        return _load_task_notes_usb(notes_type, file_preference)


def load_all_unanalyzed_task_notes(notes_type: str = "daily", file_preference: str = "png") -> list[tuple[str, Path, datetime]]:
    """Load all unanalyzed task notes files.

    Automatically selects between USB and Google Drive based on configuration.

    Supports both .txt files (read directly) and image files (.png, .jpg, .jpeg,
    .gif, .webp) which are processed through Claude's vision API to extract text.

    Args:
        notes_type: Type of notes to load (e.g., "daily", "weekly")
        file_preference: File type preference - "png" or "txt" (default: "png")

    Returns:
        List of tuples of (file contents, path to the notes file, parsed datetime from filename)

    Raises:
        FileNotFoundError: If the notes directory doesn't exist or no unanalyzed files found
    """
    source = get_active_source()

    if source == "gdrive":
        return _load_all_unanalyzed_task_notes_gdrive(notes_type, file_preference)
    else:
        return _load_all_unanalyzed_task_notes_usb(notes_type, file_preference)


def _get_week_boundaries(date: datetime) -> tuple[datetime, datetime]:
    """Get the Monday-Friday boundaries for the work week containing the given date.

    Args:
        date: Any date within the target week

    Returns:
        Tuple of (monday_start, friday_end) as datetime objects
    """
    # Calculate Monday (weekday() returns 0=Monday, 6=Sunday)
    days_since_monday = date.weekday()
    monday = date - timedelta(days=days_since_monday)
    monday = monday.replace(hour=0, minute=0, second=0, microsecond=0)

    # Calculate Friday (4 days after Monday)
    friday = monday + timedelta(days=4)
    friday = friday.replace(hour=23, minute=59, second=59, microsecond=999999)

    return monday, friday


def _weekly_analysis_exists(week_start: datetime) -> bool:
    """Check if a weekly analysis already exists for the given week.

    Args:
        week_start: Monday date of the week to check

    Returns:
        True if weekly analysis exists, False otherwise
    """
    source = get_active_source()
    week_label = week_start.strftime("%Y%m%d")

    if source == "gdrive":
        from .gdrive import GoogleDriveClient
        from .config import LOCAL_OUTPUT_DIR

        # Check local output directory first
        if LOCAL_OUTPUT_DIR:
            analysis_path = Path(LOCAL_OUTPUT_DIR) / "weekly" / f"{week_label}.weekly_analysis.txt"
            if analysis_path.exists():
                return True

        # Check Google Drive
        client = GoogleDriveClient()
        return client.file_exists("weekly", f"{week_label}.weekly_analysis.txt")
    else:
        # Check USB/local directory
        weekly_dir = Path(USB_DIR) / "weekly"
        if not weekly_dir.exists():
            return False
        analysis_path = weekly_dir / f"{week_label}.weekly_analysis.txt"
        return analysis_path.exists()


def _find_weeks_needing_analysis() -> list[tuple[datetime, datetime]]:
    """Find all work weeks that should have weekly analyses but don't.

    A work week (Monday-Friday) needs analysis if:
    1. It has 5+ Monday-Friday daily analyses, OR
    2. The work week has ended (Friday has passed) AND it has at least 1 daily analysis

    Returns:
        List of tuples of (monday_start, friday_end) for weeks needing analysis
    """
    source = get_active_source()

    # Collect all daily analysis files and their dates
    analysis_dates = []

    if source == "gdrive":
        from .gdrive import GoogleDriveClient, parse_filename_datetime
        client = GoogleDriveClient()
        files = client.list_notes_files("daily")

        for file_info in files:
            filename = file_info["name"]
            if ".daily_analysis.txt" in filename:
                file_date = parse_filename_datetime(filename)
                if file_date:
                    analysis_dates.append(file_date)
    else:
        daily_dir = Path(USB_DIR) / "daily"
        if daily_dir.exists():
            for analysis_file in daily_dir.glob("*.daily_analysis.txt"):
                file_date = _parse_filename_datetime(analysis_file.name)
                if file_date:
                    analysis_dates.append(file_date)

    if not analysis_dates:
        return []

    # Group analyses by week
    weeks_map = {}  # week_start -> list of dates
    for file_date in analysis_dates:
        week_start, week_end = _get_week_boundaries(file_date)
        week_key = week_start.strftime("%Y%m%d")

        if week_key not in weeks_map:
            weeks_map[week_key] = {
                "start": week_start,
                "end": week_end,
                "dates": []
            }
        weeks_map[week_key]["dates"].append(file_date)

    # Determine which weeks need analysis
    weeks_needing_analysis = []
    today = datetime.now()

    for week_key, week_data in weeks_map.items():
        week_start = week_data["start"]
        week_end = week_data["end"]
        dates = week_data["dates"]

        # Skip if weekly analysis already exists
        if _weekly_analysis_exists(week_start):
            continue

        # Count weekday analyses (Monday=0 through Friday=4)
        weekday_count = sum(1 for d in dates if d.weekday() < 5)

        # Condition 1: Has 5+ weekday analyses
        if weekday_count >= 5:
            weeks_needing_analysis.append((week_start, week_end))
            continue

        # Condition 2: Week has passed and has at least 1 analysis
        if today > week_end and len(dates) > 0:
            weeks_needing_analysis.append((week_start, week_end))

    return weeks_needing_analysis


def collect_weekly_analyses_for_week(week_start: datetime, week_end: datetime) -> tuple[str, Path, datetime, datetime]:
    """Collect all daily analysis files for a specific work week.

    Automatically selects between USB and Google Drive based on configuration.

    Args:
        week_start: Start of work week (Monday)
        week_end: End of work week (Friday)

    Returns:
        Tuple of (combined analysis text, output path for weekly analysis,
                  week start datetime, week end datetime)

    Raises:
        FileNotFoundError: If directories don't exist or no analyses found for the week
    """
    source = get_active_source()

    if source == "gdrive":
        return _collect_weekly_analyses_gdrive_for_week(week_start, week_end)
    else:
        return _collect_weekly_analyses_usb_for_week(week_start, week_end)


def collect_weekly_analyses() -> tuple[str, Path, datetime, datetime]:
    """Collect all daily analysis files from the previous work week (Monday-Friday).

    Automatically selects between USB and Google Drive based on configuration.

    Returns:
        Tuple of (combined analysis text, output path for weekly analysis,
                  week start datetime (Monday), week end datetime (Friday))

    Raises:
        FileNotFoundError: If directories don't exist or no analyses found for the week
    """
    source = get_active_source()

    if source == "gdrive":
        return _collect_weekly_analyses_gdrive()
    else:
        return _collect_weekly_analyses_usb()


# =============================================================================
# Monthly Analysis Collection Functions
# =============================================================================

def _get_month_boundaries(date: datetime) -> tuple[datetime, datetime]:
    """Get the first and last day of the month containing the given date.

    Args:
        date: Any date within the month

    Returns:
        Tuple of (month_start, month_end) as datetime objects
    """
    # First day of month
    month_start = date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Last day of month - go to first day of next month, then back one day
    if month_start.month == 12:
        next_month = month_start.replace(year=month_start.year + 1, month=1)
    else:
        next_month = month_start.replace(month=month_start.month + 1)

    month_end = next_month - timedelta(days=1)
    month_end = month_end.replace(hour=23, minute=59, second=59, microsecond=999999)

    return month_start, month_end


def _collect_monthly_analyses_usb_for_month(month_start: datetime, month_end: datetime) -> tuple[str, Path, datetime, datetime]:
    """Collect monthly analyses from USB/local directory for a specific month.

    Args:
        month_start: Start of month (first day)
        month_end: End of month (last day)

    Returns:
        Tuple of (combined analysis text, output path, month start, month end)
    """
    base_dir = Path(USB_DIR)

    if not base_dir.exists():
        raise FileNotFoundError(
            f"USB directory not found: {USB_DIR}"
        )

    weekly_dir = base_dir / "weekly"
    monthly_dir = base_dir / "monthly"

    if not weekly_dir.exists():
        raise FileNotFoundError(f"weekly directory not found: {weekly_dir}")

    monthly_dir.mkdir(exist_ok=True)

    # Find all weekly_analysis files from the specified month
    analysis_files = sorted(weekly_dir.glob("*.weekly_analysis.txt"))

    collected_analyses = []
    for analysis_path in analysis_files:
        try:
            date_str = analysis_path.stem.split(".")[0]
            file_date = datetime.strptime(date_str, "%Y%m%d")
        except ValueError:
            continue

        if month_start <= file_date <= month_end:
            content = analysis_path.read_text()
            # Calculate week boundaries for better labeling
            week_start, week_end = _get_week_boundaries(file_date)
            week_label = f"{week_start.strftime('%B %d')} - {week_end.strftime('%B %d, %Y')}"
            collected_analyses.append(f"## Week of {week_label}\n\n{content}")

    if not collected_analyses:
        raise FileNotFoundError(
            f"No weekly analysis files found for the month of "
            f"{month_start.strftime('%B %Y')}"
        )

    combined_text = "\n\n---\n\n".join(collected_analyses)
    month_label = month_start.strftime("%Y%m")
    output_path = monthly_dir / f"{month_label}.month.txt"

    return combined_text, output_path, month_start, month_end


def _collect_monthly_analyses_gdrive_for_month(month_start: datetime, month_end: datetime) -> tuple[str, Path, datetime, datetime]:
    """Collect monthly analyses from Google Drive for a specific month.

    Args:
        month_start: Start of month (first day)
        month_end: End of month (last day)

    Returns:
        Tuple of (combined analysis text, virtual path, month start, month end)
    """
    from .config import LOCAL_OUTPUT_DIR
    from .gdrive import GoogleDriveClient, parse_filename_datetime

    client = GoogleDriveClient()
    files = client.list_notes_files("weekly")

    collected_analyses = []
    for file_info in files:
        filename = file_info["name"]
        file_id = file_info["id"]

        if ".weekly_analysis.txt" not in filename:
            continue

        file_date = parse_filename_datetime(filename)
        if not file_date:
            continue

        if month_start <= file_date <= month_end:
            content = client.download_file_text(file_id)
            # Calculate week boundaries for better labeling
            week_start, week_end = _get_week_boundaries(file_date)
            week_label = f"{week_start.strftime('%B %d')} - {week_end.strftime('%B %d, %Y')}"
            collected_analyses.append(f"## Week of {week_label}\n\n{content}")

    if not collected_analyses:
        raise FileNotFoundError(
            f"No weekly analysis files found for the month of "
            f"{month_start.strftime('%B %Y')}"
        )

    combined_text = "\n\n---\n\n".join(collected_analyses)
    month_label = month_start.strftime("%Y%m")

    # Use local output directory if configured
    if LOCAL_OUTPUT_DIR:
        monthly_dir = Path(LOCAL_OUTPUT_DIR) / "monthly"
        monthly_dir.mkdir(parents=True, exist_ok=True)
        output_path = monthly_dir / f"{month_label}.monthly_analysis.txt"
    else:
        # Virtual path for compatibility
        output_path = Path(f"gdrive://monthly/{month_label}.monthly_analysis.txt")

    return combined_text, output_path, month_start, month_end


def _monthly_analysis_exists(month_start: datetime) -> bool:
    """Check if a monthly analysis already exists for the given month.

    Args:
        month_start: First day of the month to check

    Returns:
        True if monthly analysis exists, False otherwise
    """
    source = get_active_source()
    month_label = month_start.strftime("%Y%m")

    if source == "gdrive":
        from .gdrive import GoogleDriveClient
        from .config import LOCAL_OUTPUT_DIR

        # Check local output directory first
        if LOCAL_OUTPUT_DIR:
            analysis_path = Path(LOCAL_OUTPUT_DIR) / "monthly" / f"{month_label}.monthly_analysis.txt"
            if analysis_path.exists():
                return True

        # Check Google Drive
        client = GoogleDriveClient()
        return client.file_exists("monthly", f"{month_label}.monthly_analysis.txt")
    else:
        # Check USB/local directory
        monthly_dir = Path(USB_DIR) / "monthly"
        if not monthly_dir.exists():
            return False
        analysis_path = monthly_dir / f"{month_label}.monthly_analysis.txt"
        return analysis_path.exists()


def _find_months_needing_analysis() -> list[tuple[datetime, datetime]]:
    """Find all months that should have monthly analyses but don't.

    A month needs analysis if:
    1. It has 4+ weekly analyses (one for each week), OR
    2. The calendar month has ended AND it has at least 1 weekly analysis

    Returns:
        List of tuples of (month_start, month_end) for months needing analysis
    """
    source = get_active_source()

    # Collect all weekly analysis files and their dates
    analysis_dates = []

    if source == "gdrive":
        from .gdrive import GoogleDriveClient, parse_filename_datetime
        client = GoogleDriveClient()
        files = client.list_notes_files("weekly")

        for file_info in files:
            filename = file_info["name"]
            if ".weekly_analysis.txt" in filename:
                file_date = parse_filename_datetime(filename)
                if file_date:
                    analysis_dates.append(file_date)
    else:
        weekly_dir = Path(USB_DIR) / "weekly"
        if weekly_dir.exists():
            for analysis_file in weekly_dir.glob("*.weekly_analysis.txt"):
                file_date = _parse_filename_datetime(analysis_file.name)
                if file_date:
                    analysis_dates.append(file_date)

    if not analysis_dates:
        return []

    # Group analyses by month
    months_map = {}  # month_key -> month_data
    for file_date in analysis_dates:
        month_start, month_end = _get_month_boundaries(file_date)
        month_key = month_start.strftime("%Y%m")

        if month_key not in months_map:
            months_map[month_key] = {
                "start": month_start,
                "end": month_end,
                "dates": []
            }
        months_map[month_key]["dates"].append(file_date)

    # Determine which months need analysis
    months_needing_analysis = []
    today = datetime.now()

    for month_key, month_data in months_map.items():
        month_start = month_data["start"]
        month_end = month_data["end"]
        dates = month_data["dates"]

        # Skip if monthly analysis already exists
        if _monthly_analysis_exists(month_start):
            continue

        # Condition 1: Has 4+ weekly analyses
        if len(dates) >= 4:
            months_needing_analysis.append((month_start, month_end))
            continue

        # Condition 2: Month has ended and has at least 1 analysis
        if today > month_end and len(dates) > 0:
            months_needing_analysis.append((month_start, month_end))

    return months_needing_analysis


def collect_monthly_analyses_for_month(month_start: datetime, month_end: datetime) -> tuple[str, Path, datetime, datetime]:
    """Collect all weekly analysis files for a specific month.

    Automatically selects between USB and Google Drive based on configuration.

    Args:
        month_start: Start of month (first day)
        month_end: End of month (last day)

    Returns:
        Tuple of (combined analysis text, output path for monthly analysis,
                  month start datetime, month end datetime)

    Raises:
        FileNotFoundError: If directories don't exist or no analyses found for the month
    """
    source = get_active_source()

    if source == "gdrive":
        return _collect_monthly_analyses_gdrive_for_month(month_start, month_end)
    else:
        return _collect_monthly_analyses_usb_for_month(month_start, month_end)


# =============================================================================
# Annual Analysis Collection Functions
# =============================================================================

def _collect_annual_analyses_usb_for_year(year: int) -> tuple[str, Path, int]:
    """Collect all monthly analyses from USB/local directory for a specific year.

    Args:
        year: The calendar year to collect (e.g., 2025)

    Returns:
        Tuple of (combined analysis text, output path, year)
    """
    base_dir = Path(USB_DIR)

    if not base_dir.exists():
        raise FileNotFoundError(f"USB directory not found: {USB_DIR}")

    monthly_dir = base_dir / "monthly"
    annual_dir = base_dir / "annual"

    if not monthly_dir.exists():
        raise FileNotFoundError(f"monthly directory not found: {monthly_dir}")

    annual_dir.mkdir(exist_ok=True)

    # Find all monthly_analysis files from the specified year
    analysis_files = sorted(monthly_dir.glob("*.monthly_analysis.txt"))

    collected_analyses = []
    for analysis_path in analysis_files:
        try:
            date_str = analysis_path.stem.split(".")[0]
            file_year = int(date_str[:4])
            file_month = int(date_str[4:6])
        except (ValueError, IndexError):
            continue

        if file_year == year:
            content = analysis_path.read_text()
            # Format month name for better labeling
            month_date = datetime(year, file_month, 1)
            month_label = month_date.strftime("%B")
            collected_analyses.append(f"## {month_label} {year}\n\n{content}")

    if not collected_analyses:
        raise FileNotFoundError(f"No monthly analysis files found for year {year}")

    combined_text = "\n\n---\n\n".join(collected_analyses)
    output_path = annual_dir / f"{year}.annual.txt"

    return combined_text, output_path, year


def _collect_annual_analyses_gdrive_for_year(year: int) -> tuple[str, Path, int]:
    """Collect all monthly analyses from Google Drive for a specific year.

    Args:
        year: The calendar year to collect (e.g., 2025)

    Returns:
        Tuple of (combined analysis text, virtual path, year)
    """
    from .config import LOCAL_OUTPUT_DIR
    from .gdrive import GoogleDriveClient, parse_filename_datetime

    client = GoogleDriveClient()
    files = client.list_notes_files("monthly")

    collected_analyses = []
    for file_info in files:
        filename = file_info["name"]
        file_id = file_info["id"]

        if ".monthly_analysis.txt" not in filename:
            continue

        file_date = parse_filename_datetime(filename)
        if not file_date or file_date.year != year:
            continue

        content = client.download_file_text(file_id)
        month_label = file_date.strftime("%B")
        collected_analyses.append(f"## {month_label} {year}\n\n{content}")

    if not collected_analyses:
        raise FileNotFoundError(f"No monthly analysis files found for year {year}")

    combined_text = "\n\n---\n\n".join(collected_analyses)

    # Use local output directory if configured
    if LOCAL_OUTPUT_DIR:
        annual_dir = Path(LOCAL_OUTPUT_DIR) / "annual"
        annual_dir.mkdir(parents=True, exist_ok=True)
        output_path = annual_dir / f"{year}.annual_analysis.txt"
    else:
        # Virtual path for compatibility
        output_path = Path(f"gdrive://annual/{year}.annual_analysis.txt")

    return combined_text, output_path, year


def _annual_analysis_exists(year: int) -> bool:
    """Check if an annual analysis already exists for the given year.

    Args:
        year: The calendar year to check

    Returns:
        True if annual analysis exists, False otherwise
    """
    source = get_active_source()

    if source == "gdrive":
        from .gdrive import GoogleDriveClient
        from .config import LOCAL_OUTPUT_DIR

        # Check local output directory first
        if LOCAL_OUTPUT_DIR:
            analysis_path = Path(LOCAL_OUTPUT_DIR) / "annual" / f"{year}.annual_analysis.txt"
            if analysis_path.exists():
                return True

        # Check Google Drive
        client = GoogleDriveClient()
        return client.file_exists("annual", f"{year}.annual_analysis.txt")
    else:
        # Check USB/local directory
        annual_dir = Path(USB_DIR) / "annual"
        if not annual_dir.exists():
            return False
        analysis_path = annual_dir / f"{year}.annual_analysis.txt"
        return analysis_path.exists()


def _find_years_needing_analysis() -> list[int]:
    """Find all years that should have annual analyses but don't.

    A year needs analysis if:
    1. It has 12 monthly analyses, OR
    2. The calendar year has ended AND it has at least 1 monthly analysis

    Returns:
        List of years (as integers) needing analysis
    """
    source = get_active_source()

    # Collect all monthly analysis files and their years
    analysis_years = {}  # year -> count

    try:
        if source == "gdrive":
            from .gdrive import GoogleDriveClient, parse_filename_datetime
            client = GoogleDriveClient()
            files = client.list_notes_files("monthly")

            for file_info in files:
                filename = file_info["name"]
                if ".monthly_analysis.txt" in filename:
                    file_date = parse_filename_datetime(filename)
                    if file_date:
                        year = file_date.year
                        analysis_years[year] = analysis_years.get(year, 0) + 1
        else:
            monthly_dir = Path(USB_DIR) / "monthly"
            if monthly_dir.exists():
                for analysis_file in monthly_dir.glob("*.monthly_analysis.txt"):
                    try:
                        date_str = analysis_file.stem.split(".")[0]
                        year = int(date_str[:4])
                        analysis_years[year] = analysis_years.get(year, 0) + 1
                    except (ValueError, IndexError):
                        continue
    except FileNotFoundError:
        # If monthly directory/folder doesn't exist yet, no annual analyses needed
        return []

    if not analysis_years:
        return []

    # Determine which years need analysis
    years_needing_analysis = []
    today = datetime.now()

    for year, count in analysis_years.items():
        # Skip if annual analysis already exists
        if _annual_analysis_exists(year):
            continue

        # Condition 1: Has 12 monthly analyses
        if count >= 12:
            years_needing_analysis.append(year)
            continue

        # Condition 2: Year has ended and has at least 1 analysis
        year_end = datetime(year, 12, 31, 23, 59, 59)
        if today > year_end and count > 0:
            years_needing_analysis.append(year)

    return sorted(years_needing_analysis)


def collect_annual_analyses_for_year(year: int) -> tuple[str, Path, int]:
    """Collect all monthly analysis files for a specific year.

    Automatically selects between USB and Google Drive based on configuration.

    Args:
        year: The calendar year to collect (e.g., 2025)

    Returns:
        Tuple of (combined analysis text, output path for annual analysis, year)

    Raises:
        FileNotFoundError: If directories don't exist or no analyses found for the year
    """
    source = get_active_source()

    if source == "gdrive":
        return _collect_annual_analyses_gdrive_for_year(year)
    else:
        return _collect_annual_analyses_usb_for_year(year)


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


def raw_text_exists(input_path: Path) -> bool:
    """Check if a raw text file already exists for the given input file.

    Automatically selects between USB and Google Drive based on the input path.

    Args:
        input_path: Path to the original notes file (PNG)

    Returns:
        True if raw text file exists, False otherwise
    """
    path_str = str(input_path)
    if path_str.startswith("gdrive:"):
        return _raw_text_exists_gdrive(input_path)
    else:
        return _raw_text_exists_usb(input_path)


def save_raw_text(raw_text: str, input_path: Path) -> Path:
    """Save the raw extracted text to a file.

    Automatically selects between USB and Google Drive based on the input path.
    If input_path starts with "gdrive:", saves to Google Drive; otherwise saves locally.

    The raw text is saved as-is without any modifications or headers,
    preserving any completion markers (✓, ✗, ☆) present in the original notes.

    Args:
        raw_text: The raw extracted text content
        input_path: Path to the original notes file (PNG)

    Returns:
        Path to the saved raw text file
    """
    path_str = str(input_path)
    if path_str.startswith("gdrive:"):
        return _save_raw_text_gdrive(raw_text, input_path)
    else:
        return _save_raw_text_usb(raw_text, input_path)


def get_notes_source() -> str:
    """Get the currently active notes source.

    Returns:
        "usb" or "gdrive" indicating which source is being used
    """
    return get_active_source()
