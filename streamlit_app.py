"""
TaskTriage Streamlit UI

A professional, Canvas-style interface for the TaskTriage GTD-based task analysis tool.
"""

import os
import re
import base64
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

import streamlit as st
import yaml
from dotenv import dotenv_values, set_key

# TaskTriage imports
from tasktriage import (
    analyze_tasks,
    load_all_unanalyzed_task_notes,
    collect_weekly_analyses_for_week,
    collect_monthly_analyses_for_month,
    collect_annual_analyses_for_year,
    save_analysis,
    get_notes_source,
    is_usb_available,
    is_local_input_available,
    is_gdrive_available,
    get_active_source,
    get_primary_input_directory,
    USB_INPUT_DIR,
    LOCAL_INPUT_DIR,
    CONFIG_PATH,
    IMAGE_EXTENSIONS,
    __version__,
)
from tasktriage.files import (
    _find_weeks_needing_analysis,
    _find_months_needing_analysis,
    _find_years_needing_analysis,
    raw_text_exists,
    save_raw_text,
)

# Page configuration
st.set_page_config(
    page_title="TaskTriage",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Custom CSS for professional styling
st.markdown("""
<style>
    /* Main container styling */
    .main .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
        max-width: 100%;
    }

    /* Left panel styling */
    [data-testid="column"]:first-child {
        background-color: #1e1e2e;
        border-radius: 8px;
        padding: 1rem;
    }

    /* Section headers */
    .section-header {
        color: #cdd6f4;
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.5rem;
        padding-bottom: 0.25rem;
        border-bottom: 1px solid #45475a;
    }

    /* File list container */
    .file-list-container {
        background-color: #313244;
        border-radius: 6px;
        padding: 0.5rem;
        max-height: 200px;
        overflow-y: auto;
    }

    /* File item styling */
    .file-item {
        padding: 0.4rem 0.6rem;
        border-radius: 4px;
        cursor: pointer;
        font-size: 0.85rem;
        color: #cdd6f4;
        margin-bottom: 2px;
    }

    .file-item:hover {
        background-color: #45475a;
    }

    .file-item.selected {
        background-color: #89b4fa;
        color: #1e1e2e;
    }

    /* Button styling */
    .stButton > button {
        width: 100%;
        border-radius: 6px;
        font-weight: 500;
    }

    /* Primary triage button */
    .triage-button > button {
        background-color: #89b4fa;
        color: #1e1e2e;
        font-size: 1.1rem;
        padding: 0.75rem;
    }

    .triage-button > button:hover {
        background-color: #b4befe;
    }

    /* Editor panel */
    .editor-panel {
        background-color: #ffffff;
        border-radius: 8px;
        padding: 1rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }

    /* Editor header */
    .editor-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0.75rem;
        padding-bottom: 0.5rem;
        border-bottom: 1px solid #e0e0e0;
    }

    /* Monospace text area */
    .stTextArea textarea {
        font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
        font-size: 0.9rem;
        line-height: 1.5;
    }

    /* Status indicator */
    .status-indicator {
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        margin-right: 0.5rem;
    }

    .status-saved {
        background-color: #a6e3a1;
    }

    .status-unsaved {
        background-color: #f38ba8;
    }

    /* Progress container */
    .progress-container {
        background-color: #313244;
        border-radius: 6px;
        padding: 1rem;
        margin-top: 1rem;
    }

    .progress-item {
        color: #cdd6f4;
        font-size: 0.85rem;
        margin-bottom: 0.25rem;
    }

    /* Markup buttons */
    .markup-buttons {
        display: flex;
        gap: 0.5rem;
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Toast styling */
    .stToast {
        background-color: #313244;
        color: #cdd6f4;
    }
</style>
""", unsafe_allow_html=True)


def get_notes_directory() -> Path | None:
    """Get the primary notes directory path."""
    try:
        source = get_notes_source()
        if source == "usb":
            # Returns the primary input directory (USB_INPUT_DIR or LOCAL_INPUT_DIR)
            return get_primary_input_directory()
        elif source == "gdrive":
            # For Google Drive, we need LOCAL_OUTPUT_DIR or return None
            local_output = os.getenv("LOCAL_OUTPUT_DIR")
            if local_output:
                return Path(local_output)
    except Exception:
        pass
    return None


def parse_filename_datetime(filename: str) -> datetime | None:
    """Parse datetime from filename format YYYYMMDD_HHMMSS."""
    patterns = [
        r"(\d{8}_\d{6})",  # YYYYMMDD_HHMMSS
        r"(\d{8})",  # YYYYMMDD for weekly
        r"(\d{6})",  # YYYYMM for monthly
        r"(\d{4})",  # YYYY for annual
    ]

    for pattern in patterns:
        match = re.search(pattern, filename)
        if match:
            ts = match.group(1)
            try:
                if len(ts) == 15:  # YYYYMMDD_HHMMSS
                    return datetime.strptime(ts, "%Y%m%d_%H%M%S")
                elif len(ts) == 8:  # YYYYMMDD
                    return datetime.strptime(ts, "%Y%m%d")
                elif len(ts) == 6:  # YYYYMM
                    return datetime.strptime(ts, "%Y%m")
                elif len(ts) == 4:  # YYYY
                    return datetime.strptime(ts, "%Y")
            except ValueError:
                continue
    return None


def format_file_datetime(dt: datetime | None, filename: str) -> str:
    """Format datetime for display in file list."""
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
    """List raw note files (.txt and image files) from daily directory."""
    files = []
    daily_dir = notes_dir / "daily"

    if not daily_dir.exists():
        return files

    valid_extensions = {".txt", ".png", ".jpg", ".jpeg", ".gif", ".webp"}

    for f in daily_dir.iterdir():
        if f.is_file() and f.suffix.lower() in valid_extensions:
            # Skip analysis files
            if "_analysis.txt" in f.name:
                continue
            dt = parse_filename_datetime(f.name)
            display_name = format_file_datetime(dt, f.name)
            files.append((f, display_name))

    # Sort by datetime descending (newest first)
    files.sort(key=lambda x: parse_filename_datetime(x[0].name) or datetime.min, reverse=True)
    return files


def list_analysis_files(notes_dir: Path) -> list[tuple[Path, str]]:
    """List all analysis files from all directories."""
    files = []

    analysis_suffixes = [
        ".daily_analysis.txt",
        ".weekly_analysis.txt",
        ".monthly_analysis.txt",
        ".annual_analysis.txt",
    ]

    for subdir in ["daily", "weekly", "monthly", "annual"]:
        dir_path = notes_dir / subdir
        if not dir_path.exists():
            continue

        for f in dir_path.iterdir():
            if f.is_file():
                for suffix in analysis_suffixes:
                    if f.name.endswith(suffix):
                        dt = parse_filename_datetime(f.name)
                        analysis_type = suffix.replace("_analysis.txt", "").replace(".", "")
                        display_name = f"[{analysis_type.upper()}] {format_file_datetime(dt, f.name)}"
                        files.append((f, display_name))
                        break

    # Sort by datetime descending
    files.sort(key=lambda x: parse_filename_datetime(x[0].name) or datetime.min, reverse=True)
    return files


def load_file_content(file_path: Path) -> str:
    """Load content from a file."""
    if file_path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp"}:
        # For images, return a placeholder message
        return f"[Image file: {file_path.name}]\n\nImage preview is shown below the editor."

    try:
        return file_path.read_text(encoding="utf-8")
    except Exception as e:
        return f"Error loading file: {e}"


def save_file_content(file_path: Path, content: str) -> bool:
    """Save content to a file."""
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
    daily_dir = notes_dir / "daily"
    daily_dir.mkdir(parents=True, exist_ok=True)

    # Generate timestamp-based filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    new_file = daily_dir / f"{timestamp}.txt"

    try:
        # Create empty file
        new_file.write_text("", encoding="utf-8")
        return new_file
    except Exception as e:
        st.error(f"Error creating file: {e}")
        return None


def load_env_config() -> dict:
    """Load configuration from .env file."""
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        return dict(dotenv_values(env_path))
    return {}


def save_env_config(config: dict) -> bool:
    """Save configuration to .env file."""
    env_path = Path(__file__).parent / ".env"
    try:
        for key, value in config.items():
            set_key(str(env_path), key, value)
        return True
    except Exception as e:
        st.error(f"Error saving configuration: {e}")
        return False


def load_yaml_config() -> dict:
    """Load model configuration from config.yaml."""
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH) as f:
                return yaml.safe_load(f) or {}
        except Exception:
            pass
    return {"model": "claude-haiku-4-5-20251001", "temperature": 0.7, "max_tokens": 4096}


def save_yaml_config(config: dict) -> bool:
    """Save model configuration to config.yaml."""
    try:
        with open(CONFIG_PATH, "w") as f:
            yaml.dump(config, f, default_flow_style=False)
        return True
    except Exception as e:
        st.error(f"Error saving config.yaml: {e}")
        return False


def analyze_single_file(task_notes: str, notes_path: Path, file_date: datetime, notes_type: str) -> tuple:
    """Analyze a single task notes file.

    For PNG files, also saves the raw extracted text to a .raw_notes.txt file
    in parallel with the analysis. This preserves the original text with any
    completion markers (✓, ✗, ☆) for display in the UI text editor.
    """
    try:
        # If this is a PNG file, save the raw extracted text (if not already saved)
        # This runs in parallel with the analysis - text is already extracted
        raw_text_path = None
        if notes_path.suffix.lower() in IMAGE_EXTENSIONS:
            if not raw_text_exists(notes_path):
                raw_text_path = save_raw_text(task_notes, notes_path)

        # Run the analysis
        prompt_vars = {
            "current_date": file_date.strftime("%A, %B %d, %Y"),
        }
        result = analyze_tasks(notes_type, task_notes, **prompt_vars)
        output_path = save_analysis(result, notes_path, notes_type)
        return (notes_path, output_path, True, None, raw_text_path)
    except Exception as e:
        return (notes_path, None, False, str(e), None)


def run_triage_pipeline(progress_callback) -> dict:
    """Run the full triage analysis pipeline."""
    results = {
        "daily": {"successful": 0, "failed": 0, "errors": []},
        "weekly": {"successful": 0, "failed": 0, "errors": []},
        "monthly": {"successful": 0, "failed": 0, "errors": []},
        "annual": {"successful": 0, "failed": 0, "errors": []},
    }

    # Level 1: Daily analyses
    progress_callback("Loading unanalyzed daily files...")
    try:
        unanalyzed_files = load_all_unanalyzed_task_notes("daily", "png")
    except Exception as e:
        progress_callback(f"Error loading files: {e}")
        return results

    total_files = len(unanalyzed_files)
    progress_callback(f"Found {total_files} unanalyzed file(s)")

    if total_files > 0:
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_file = {
                executor.submit(
                    analyze_single_file, task_notes, notes_path, file_date, "daily"
                ): notes_path
                for task_notes, notes_path, file_date in unanalyzed_files
            }

            completed = 0
            for future in as_completed(future_to_file):
                notes_path, output_path, success, error_msg, raw_text_path = future.result()
                completed += 1

                if success:
                    results["daily"]["successful"] += 1
                    msg = f"Processing daily notes... ({completed}/{total_files}) - {notes_path.name}"
                    if raw_text_path:
                        msg += " (+ raw text)"
                    progress_callback(msg)
                else:
                    results["daily"]["failed"] += 1
                    results["daily"]["errors"].append(f"{notes_path.name}: {error_msg}")
                    progress_callback(f"Failed: {notes_path.name}")

    progress_callback(f"Daily Summary: {results['daily']['successful']} successful, {results['daily']['failed']} failed")

    # Level 2: Weekly analyses
    progress_callback("Checking for weekly analyses...")
    try:
        weeks_to_analyze = _find_weeks_needing_analysis()
    except Exception:
        weeks_to_analyze = []

    for week_start, week_end in weeks_to_analyze:
        week_label = week_start.strftime("%B %d") + " - " + week_end.strftime("%B %d, %Y")
        progress_callback(f"Analyzing week: {week_label}")

        try:
            task_notes, notes_path, ws, we = collect_weekly_analyses_for_week(week_start, week_end)
            prompt_vars = {
                "week_start": ws.strftime("%A, %B %d, %Y"),
                "week_end": we.strftime("%A, %B %d, %Y"),
            }
            result = analyze_tasks("weekly", task_notes, **prompt_vars)
            save_analysis(result, notes_path, "weekly")
            results["weekly"]["successful"] += 1
        except Exception as e:
            results["weekly"]["failed"] += 1
            results["weekly"]["errors"].append(f"{week_label}: {str(e)}")

    if weeks_to_analyze:
        progress_callback(f"Weekly Summary: {results['weekly']['successful']} successful, {results['weekly']['failed']} failed")

    # Level 3: Monthly analyses
    progress_callback("Checking for monthly analyses...")
    try:
        months_to_analyze = _find_months_needing_analysis()
    except Exception:
        months_to_analyze = []

    for month_start, month_end in months_to_analyze:
        month_label = month_start.strftime("%B %Y")
        progress_callback(f"Analyzing month: {month_label}")

        try:
            task_notes, notes_path, ms, me = collect_monthly_analyses_for_month(month_start, month_end)
            prompt_vars = {
                "month_start": ms.strftime("%B %d, %Y"),
                "month_end": me.strftime("%B %d, %Y"),
            }
            result = analyze_tasks("monthly", task_notes, **prompt_vars)
            save_analysis(result, notes_path, "monthly")
            results["monthly"]["successful"] += 1
        except Exception as e:
            results["monthly"]["failed"] += 1
            results["monthly"]["errors"].append(f"{month_label}: {str(e)}")

    if months_to_analyze:
        progress_callback(f"Monthly Summary: {results['monthly']['successful']} successful, {results['monthly']['failed']} failed")

    # Level 4: Annual analyses
    progress_callback("Checking for annual analyses...")
    try:
        years_to_analyze = _find_years_needing_analysis()
    except Exception:
        years_to_analyze = []

    for year in years_to_analyze:
        progress_callback(f"Analyzing year: {year}")

        try:
            task_notes, notes_path, yr = collect_annual_analyses_for_year(year)
            prompt_vars = {"year": str(year)}
            result = analyze_tasks("annual", task_notes, **prompt_vars)
            save_analysis(result, notes_path, "annual")
            results["annual"]["successful"] += 1
        except Exception as e:
            results["annual"]["failed"] += 1
            results["annual"]["errors"].append(f"{year}: {str(e)}")

    if years_to_analyze:
        progress_callback(f"Annual Summary: {results['annual']['successful']} successful, {results['annual']['failed']} failed")

    progress_callback("Triage complete!")
    return results


def render_image_preview(file_path: Path):
    """Render an image preview if the selected file is an image."""
    if file_path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp"}:
        try:
            with open(file_path, "rb") as f:
                image_data = f.read()
            st.image(image_data, caption=file_path.name, use_container_width=True)
        except Exception as e:
            st.error(f"Error loading image: {e}")


# Initialize session state
if "selected_file" not in st.session_state:
    st.session_state.selected_file = None
if "file_content" not in st.session_state:
    st.session_state.file_content = ""
if "original_content" not in st.session_state:
    st.session_state.original_content = ""
if "triage_progress" not in st.session_state:
    st.session_state.triage_progress = []
if "triage_running" not in st.session_state:
    st.session_state.triage_running = False
if "show_config" not in st.session_state:
    st.session_state.show_config = False
if "raw_notes_selection" not in st.session_state:
    st.session_state.raw_notes_selection = None
if "analysis_files_selection" not in st.session_state:
    st.session_state.analysis_files_selection = None


def select_file(file_path: Path):
    """Handle file selection."""
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


HELP_TEXT = """TaskTriage uses Claude AI to turn your handwritten task notes into realistic, actionable execution plans based on GTD principles. Think of it as a reality check for your optimistic planning habits.

**Left Panel (Controls)**
- **Analyze Button** - Run the full analysis pipeline with real-time progress updates
- **Configuration** - Edit `.env` and `config.yaml` settings directly in the browser (API keys, notes source, model parameters)
- **Raw Notes List** - Browse `.txt` and image files from your `daily/` directory, sorted by date
- **Analysis Files List** - Browse all generated analysis files across daily/weekly/monthly/annual

**Right Panel (Editor)**
- Full-height text editor for viewing and editing selected files
- Image preview for handwritten note images
- Save/Revert buttons with unsaved changes indicator
- Notes source status display
- **Quick Markup Tools** - Add task markers to clipboard (✓ completed, ✗ removed, ☆ urgent). These are automatically interpretted at the right side of each line.
"""

def main():
    """Main application entry point."""
    # Header
    st.markdown(f"# 📋 TaskTriage v{__version__}", help=HELP_TEXT)

    # Get notes directory
    notes_dir = get_notes_directory()

    if notes_dir is None or not notes_dir.exists():
        st.warning("No notes directory configured. Please set up your configuration.")
        notes_dir = None

    # Two-panel layout
    left_col, right_col = st.columns([3, 7], gap="medium")

    # LEFT PANEL - Controls and file selection
    with left_col:
        # Triage Button
        st.markdown('<p class="section-header">Actions</p>', unsafe_allow_html=True)

        triage_disabled = st.session_state.triage_running or notes_dir is None
        if st.button("🔍 Analyze", type="primary", disabled=triage_disabled, use_container_width=True, key="btn_triage"):
            st.session_state.triage_running = True
            st.session_state.triage_progress = []
            st.rerun()

        with st.expander("Configuration", expanded=False):
            env_config = load_env_config()
            yaml_config = load_yaml_config()

            st.markdown("**Environment Variables**")

            api_key = st.text_input(
                "ANTHROPIC_API_KEY",
                value=env_config.get("ANTHROPIC_API_KEY", ""),
                type="password"
            )

            notes_source = st.selectbox(
                "NOTES_SOURCE",
                options=["auto", "usb", "gdrive"],
                index=["auto", "usb", "gdrive"].index(env_config.get("NOTES_SOURCE", "auto"))
            )

            st.markdown("**Input Directories**")

            usb_input_dir = st.text_input(
                "USB_INPUT_DIR",
                value=env_config.get("USB_INPUT_DIR", env_config.get("USB_DIR", "")),  # Backward compat
                help="Path to USB/mounted device notes directory"
            )

            local_input_dir = st.text_input(
                "LOCAL_INPUT_DIR",
                value=env_config.get("LOCAL_INPUT_DIR", ""),
                help="Path to local hard drive notes directory (optional)"
            )

            st.markdown("**Google Drive**")

            gdrive_folder = st.text_input(
                "GOOGLE_DRIVE_FOLDER_ID",
                value=env_config.get("GOOGLE_DRIVE_FOLDER_ID", "")
            )

            local_output = st.text_input(
                "LOCAL_OUTPUT_DIR",
                value=env_config.get("LOCAL_OUTPUT_DIR", ""),
                help="Local directory for saving analysis output"
            )

            st.markdown("**Model Configuration**")

            model = st.text_input(
                "Model",
                value=yaml_config.get("model", "claude-haiku-4-5-20251001")
            )

            temperature = st.slider(
                "Temperature",
                min_value=0.0,
                max_value=1.0,
                value=float(yaml_config.get("temperature", 0.7)),
                step=0.1
            )

            max_tokens = st.number_input(
                "Max Tokens",
                min_value=256,
                max_value=16384,
                value=int(yaml_config.get("max_tokens", 4096)),
                step=256
            )

            col1, col2 = st.columns(2)
            with col1:
                if st.button("Save", type="primary", key="btn_save_config"):
                    # Save env config
                    new_env = {
                        "ANTHROPIC_API_KEY": api_key,
                        "NOTES_SOURCE": notes_source,
                        "USB_INPUT_DIR": usb_input_dir,
                        "LOCAL_INPUT_DIR": local_input_dir,
                        "GOOGLE_DRIVE_FOLDER_ID": gdrive_folder,
                        "LOCAL_OUTPUT_DIR": local_output,
                    }
                    save_env_config(new_env)

                    # Save yaml config
                    new_yaml = {
                        "model": model,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    }
                    save_yaml_config(new_yaml)

                    st.success("Configuration saved!")
                    st.rerun()

            with col2:
                if st.button("Cancel", key="btn_cancel_config"):
                    st.session_state.show_config = False
                    st.rerun()

        st.markdown("---")

        # File Selection - Raw Notes
        st.markdown('<p class="section-header">Raw Notes</p>', unsafe_allow_html=True)

        if notes_dir:
            raw_notes = list_raw_notes(notes_dir)
            if raw_notes:
                # Set default selection if not set
                if st.session_state.raw_notes_selection is None and raw_notes:
                    st.session_state.raw_notes_selection = raw_notes[0][0]

                selected_raw = st.selectbox(
                    "Select a raw note file",
                    options=[f[0] for f in raw_notes],
                    format_func=lambda x: next((f[1] for f in raw_notes if f[0] == x), x.name),
                    key="raw_notes_select",
                    label_visibility="collapsed",
                    index=[f[0] for f in raw_notes].index(st.session_state.raw_notes_selection) if st.session_state.raw_notes_selection in [f[0] for f in raw_notes] else 0
                )
                st.session_state.raw_notes_selection = selected_raw

                btn_col1, btn_col2 = st.columns(2)
                with btn_col1:
                    if st.button("📂 Open", use_container_width=True, key="btn_render_raw"):
                        select_file(selected_raw)
                        st.rerun()
                with btn_col2:
                    if st.button("📝 New", use_container_width=True, key="btn_new_raw"):
                        new_file = create_new_notes_file(notes_dir)
                        if new_file:
                            st.session_state.raw_notes_selection = new_file
                            select_file(new_file)
                            st.rerun()
            else:
                st.info("No raw notes found in daily/ directory")
                if st.button("📝 New", use_container_width=True, key="btn_new_raw_empty"):
                    new_file = create_new_notes_file(notes_dir)
                    if new_file:
                        st.session_state.raw_notes_selection = new_file
                        select_file(new_file)
                        st.rerun()
        else:
            st.info("Configure notes directory to see files")

        # File Selection - Analysis Files
        st.markdown('<p class="section-header">Analysis Files</p>', unsafe_allow_html=True)

        if notes_dir:
            analysis_files = list_analysis_files(notes_dir)
            if analysis_files:
                # Set default selection if not set
                if st.session_state.analysis_files_selection is None and analysis_files:
                    st.session_state.analysis_files_selection = analysis_files[0][0]

                selected_analysis = st.selectbox(
                    "Select an analysis file",
                    options=[f[0] for f in analysis_files],
                    format_func=lambda x: next((f[1] for f in analysis_files if f[0] == x), x.name),
                    key="analysis_files_select",
                    label_visibility="collapsed",
                    index=[f[0] for f in analysis_files].index(st.session_state.analysis_files_selection) if st.session_state.analysis_files_selection in [f[0] for f in analysis_files] else 0
                )
                st.session_state.analysis_files_selection = selected_analysis

                if st.button("📂 Open", use_container_width=True, key="btn_render_analysis"):
                    select_file(selected_analysis)
                    st.rerun()
            else:
                st.info("No analysis files found")
        else:
            st.info("Configure notes directory to see files")

        #--------------------------------------------------------------------#

        # Triage Progress
        if st.session_state.triage_running or st.session_state.triage_progress:
            st.markdown("---")
            st.markdown('<p class="section-header">Triage Progress</p>', unsafe_allow_html=True)

            progress_container = st.container()
            with progress_container:
                for msg in st.session_state.triage_progress:
                    st.text(msg)

                if st.session_state.triage_running:
                    with st.spinner("Running triage..."):
                        def progress_callback(msg: str):
                            st.session_state.triage_progress.append(msg)

                        results = run_triage_pipeline(progress_callback)

                        st.session_state.triage_running = False

                        # Summary
                        total_success = sum(r["successful"] for r in results.values())
                        total_failed = sum(r["failed"] for r in results.values())

                        if total_failed == 0:
                            st.success(f"Triage complete! {total_success} analyses successful.")
                        else:
                            st.warning(f"Triage complete. {total_success} successful, {total_failed} failed.")

                        st.rerun()

    # RIGHT PANEL - Content Editor
    with right_col:
        if st.session_state.selected_file:
            file_path = st.session_state.selected_file

            # Check if it's an image file
            if file_path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp"}:
                # Image files - show header without edit controls
                st.markdown(f"### 📄 {file_path.name}")
                st.caption("Image file (read-only)")
                st.markdown("---")
                # Show image preview
                render_image_preview(file_path)
            else:
                # Text files - show editor with controls
                # Initialize content_editor in session state if needed
                if "content_editor" not in st.session_state:
                    st.session_state.content_editor = st.session_state.file_content

                # Check for changes using the editor's session state
                current_content = st.session_state.get("content_editor", st.session_state.file_content)
                has_changes = current_content != st.session_state.original_content
                status_text = "Unsaved changes" if has_changes else "Saved"

                # Editor header with save/revert buttons
                header_col1, header_col2, header_col3 = st.columns([5, 1.5, 1.5])

                with header_col1:
                    st.markdown(f"### 📄 {file_path.name}")
                    st.caption(f"Status: {status_text}")

                with header_col2:
                    if st.button("💾 Save", type="primary", disabled=not has_changes, key="btn_save_file", use_container_width=True):
                        content_to_save = st.session_state.content_editor
                        if save_file_content(file_path, content_to_save):
                            st.session_state.file_content = content_to_save
                            st.session_state.original_content = content_to_save
                            st.success("Saved!")
                            st.rerun()

                with header_col3:
                    if st.button("↩️ Revert", disabled=not has_changes, key="btn_revert_file", use_container_width=True):
                        st.session_state.content_editor = st.session_state.original_content
                        st.session_state.file_content = st.session_state.original_content
                        st.rerun()

                # Quick Markup Tools
                st.markdown('<p class="section-header">Quick Markup</p>', unsafe_allow_html=True)
                st.caption("Copyable task markers (✓ Completed, ✗ Removed, ☆ Urgent)")

                # Show markup text
                col1, col2, col3 = st.columns(3, width=200)

                with col1:
                    st.code(" ✓", language=None)

                with col2:
                    st.code(" ✗", language=None)

                with col3:
                    st.code(" ☆", language=None)

                # Text editor - uses content_editor session state key
                # Don't pass 'value' when using 'key' - Streamlit manages it automatically
                st.text_area(
                    "File content",
                    height=600,
                    key="content_editor",
                    label_visibility="collapsed"
                )
                    
        else:
            # No file selected
            st.markdown("### Select a file to edit")
            st.info("Choose a file from the Raw Notes or Analysis Files list on the left to view and edit its content.")

            # Show notes source status
            st.markdown("---")
            st.markdown("#### Notes Source Status")

            try:
                if is_usb_available():
                    st.success(f"✓ USB Input: {USB_INPUT_DIR}")
                else:
                    st.warning("✗ USB Input not configured")
            except Exception:
                st.warning("✗ USB Input not configured")

            try:
                if is_local_input_available():
                    st.success(f"✓ Local Input: {LOCAL_INPUT_DIR}")
                else:
                    st.info("Local Input not configured (optional)")
            except Exception:
                st.info("Local Input not configured (optional)")

            try:
                if is_gdrive_available():
                    st.success("✓ Google Drive configured")
                else:
                    st.warning("✗ Google Drive not configured")
            except Exception:
                st.warning("✗ Google Drive not configured")

            try:
                active = get_active_source()
                st.info(f"Active source: {active}")
            except Exception:
                st.error("No active notes source available")


if __name__ == "__main__":
    main()
