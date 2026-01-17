"""
UI-specific file operations.

Handles file listing, loading, saving, and formatting for the Streamlit UI.
"""

import os
from pathlib import Path
from datetime import datetime

import streamlit as st

from tasktriage.config import get_active_source, get_primary_input_directory
from tasktriage.gdrive import parse_filename_datetime


def get_notes_directory() -> Path | None:
    """Get the primary notes directory path.

    Returns:
        Path to the notes directory, or None if not configured
    """
    try:
        source = get_active_source()
        if source == "usb":
            # Returns the primary input directory (EXTERNAL_INPUT_DIR or LOCAL_INPUT_DIR)
            return get_primary_input_directory()
        elif source == "gdrive":
            # For Google Drive, we need LOCAL_OUTPUT_DIR or return None
            local_output = os.getenv("LOCAL_OUTPUT_DIR")
            if local_output:
                return Path(local_output)
    except Exception:
        pass
    return None


def format_file_datetime(dt: datetime | None, filename: str) -> str:
    """Format datetime for display in file list.

    Args:
        dt: Datetime object to format
        filename: Original filename

    Returns:
        Formatted string for display
    """
    if dt is None:
        return filename

    if "_" in filename and len(filename) >= 15:
        # Full datetime format
        return dt.strftime("%Y-%m-%d %H:%M")
    elif "weekly" in filename:
        return f"Week of {dt.strftime('%b %d, %Y')}"
    elif "monthly" in filename:
        return dt.strftime("%B %Y")
    elif "annual" in filename:
        return dt.strftime("%Y")
    else:
        return dt.strftime("%Y-%m-%d")


def list_raw_notes(notes_dir: Path) -> list[tuple[Path, str]]:
    """List raw note files (.txt and image files) from top level.

    Args:
        notes_dir: Directory to search for notes

    Returns:
        List of tuples (file_path, display_name) sorted by date descending
    """
    files = []

    if not notes_dir.exists():
        return files

    valid_extensions = {".txt", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf"}

    for f in notes_dir.iterdir():
        # Skip subdirectories (analysis output)
        if f.is_dir():
            continue
        if f.is_file() and f.suffix.lower() in valid_extensions:
            # Skip analysis files and raw notes files
            if ".triaged.txt" in f.name or ".raw_notes.txt" in f.name:
                continue
            dt = parse_filename_datetime(f.name)
            display_name = format_file_datetime(dt, f.name)
            files.append((f, display_name))

    # Sort by datetime descending (newest first)
    files.sort(key=lambda x: parse_filename_datetime(x[0].name) or datetime.min, reverse=True)
    return files


def list_analysis_files(notes_dir: Path) -> list[tuple[Path, str]]:
    """List all analysis files from all directories.

    Args:
        notes_dir: Base directory containing analysis subdirectories

    Returns:
        List of tuples (file_path, display_name) sorted by date descending
    """
    files = []

    analysis_suffixes = [
        ".triaged.txt",  # All analyses now use "triaged" naming
    ]

    for subdir in ["daily", "weekly", "monthly", "annual"]:
        dir_path = notes_dir / subdir
        if not dir_path.exists():
            continue

        for f in dir_path.iterdir():
            if f.is_file():
                for suffix in analysis_suffixes:
                    if f.name.endswith(suffix):
                        # Parse date format based on parent directory (analysis type)
                        date_str = f.stem.split(".")[0]
                        try:
                            if subdir == "weekly":
                                # weekX_MM_YYYY format for weekly (e.g., week1_12_2025)
                                # Just parse month/year for sorting, ignore week number
                                parts = date_str.split("_")
                                if len(parts) == 3 and parts[0].startswith("week"):
                                    dt = datetime.strptime(f"{parts[1]}_{parts[2]}", "%m_%Y")
                                else:
                                    dt = parse_filename_datetime(f.name)
                            elif subdir == "monthly":
                                # MM_YYYY format for monthly
                                dt = datetime.strptime(date_str, "%m_%Y")
                            elif subdir == "annual":
                                # YYYY format for annual
                                dt = datetime.strptime(date_str, "%Y")
                            else:
                                # DD_MM_YYYY format for daily
                                dt = datetime.strptime(date_str, "%d_%m_%Y")
                        except ValueError:
                            # Fallback to original parser
                            dt = parse_filename_datetime(f.name)

                        # Determine analysis type from parent directory
                        analysis_type = dir_path.name.upper()  # daily, weekly, monthly, annual
                        display_name = f"[{analysis_type}] {format_file_datetime(dt, f.name)}"
                        files.append((f, display_name))
                        break

    # Sort by datetime descending
    def get_sort_date(item):
        f = item[0]
        parent_dir = f.parent.name
        # Parse date format based on parent directory for triaged files
        if ".triaged.txt" in f.name:
            try:
                date_str = f.stem.split(".")[0]
                if parent_dir == "weekly":
                    # weekX_MM_YYYY format - parse month/year for sorting
                    parts = date_str.split("_")
                    if len(parts) == 3 and parts[0].startswith("week"):
                        return datetime.strptime(f"{parts[1]}_{parts[2]}", "%m_%Y")
                elif parent_dir == "monthly":
                    return datetime.strptime(date_str, "%m_%Y")
                elif parent_dir == "annual":
                    return datetime.strptime(date_str, "%Y")
                else:  # daily
                    return datetime.strptime(date_str, "%d_%m_%Y")
            except ValueError:
                pass
        return parse_filename_datetime(f.name) or datetime.min

    files.sort(key=get_sort_date, reverse=True)
    return files


def load_file_content(file_path: Path) -> str:
    """Load content from a file.

    Args:
        file_path: Path to the file to load

    Returns:
        File content as string (or placeholder for visual files)
    """
    if file_path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf"}:
        # For visual files (images and PDFs), return a placeholder message
        if file_path.suffix.lower() == ".pdf":
            return f"[PDF file: {file_path.name}]\n\nPDF content is processed and displayed below."
        else:
            return f"[Image file: {file_path.name}]\n\nImage preview is shown below the editor."

    try:
        return file_path.read_text(encoding="utf-8")
    except Exception as e:
        return f"Error loading file: {e}"


def save_file_content(file_path: Path, content: str) -> bool:
    """Save content to a file.

    Args:
        file_path: Path to the file to save
        content: Content to write

    Returns:
        True if successful, False otherwise
    """
    try:
        file_path.write_text(content, encoding="utf-8")
        return True
    except Exception as e:
        st.error(f"Error saving file: {e}")
        return False


def create_new_notes_file(notes_dir: Path) -> Path | None:
    """Create a new empty notes file with timestamp-based name.

    Args:
        notes_dir: The base notes directory

    Returns:
        Path to the created file, or None if creation failed
    """
    # Create notes directory if it doesn't exist
    notes_dir.mkdir(parents=True, exist_ok=True)

    # Generate timestamp-based filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    new_file = notes_dir / f"{timestamp}.txt"

    try:
        # Create empty file
        new_file.write_text("", encoding="utf-8")
        return new_file
    except Exception as e:
        st.error(f"Error creating file: {e}")
        return None


def select_file(file_path: Path) -> None:
    """Handle file selection.

    Updates session state to load the selected file into the editor.

    Args:
        file_path: Path to the file to select
    """
    # Only reset editor content if we're switching to a DIFFERENT file
    # This prevents losing unsaved changes when the app reruns
    is_new_file = st.session_state.selected_file != file_path

    st.session_state.selected_file = file_path
    content = load_file_content(file_path)
    st.session_state.file_content = content
    st.session_state.original_content = content

    # Only reset the editor content when actually switching files
    if is_new_file:
        st.session_state.content_editor = content
