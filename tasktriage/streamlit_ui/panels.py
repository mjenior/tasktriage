"""
Main panel rendering for the Streamlit UI.

Contains all the rendering logic for the left control panel and right editor panel.
"""

import os
import time
from datetime import datetime, timedelta
from pathlib import Path

import streamlit as st

from tasktriage import (
    is_usb_available,
    is_local_input_available,
    is_gdrive_available,
    EXTERNAL_INPUT_DIR,
    LOCAL_INPUT_DIR,
)
from .file_ops import (
    list_raw_notes,
    list_analysis_files,
    filter_analysis_files,
    load_file_content,
    save_file_content,
    create_new_notes_file,
    select_file,
)
from tasktriage.gdrive import parse_filename_datetime
from .components import render_image_preview, render_quick_markup_tools, render_progress_display
from .config_ui import render_config_panel
from .oauth_ui import render_oauth_section
from .logic import run_triage_pipeline, sync_files_across_directories


# Help text constant
HELP_TEXT = """TaskTriage uses Claude AI to turn your handwritten task notes into realistic, actionable execution plans based on GTD principles. Think of it as a reality check for your optimistic planning habits.

**Recommended Workflow: Sync → Edit → Analyze**

**Left Panel (Controls)**
- **Analyze Button** - Generates daily analyses for synced files. Weekly/monthly/annual analyses auto-trigger when conditions are met
- **Sync Button** (run first!) - Copies raw notes from input directories, converts images/PDFs to editable `.raw_notes.txt` files, and syncs everything across all configured directories
- **Configuration** - Edit `.env` and `config.yaml` settings directly in the browser
- **Raw Notes List** - Browse `.txt` and image files from your notes directory
- **Analysis Files List** - Browse generated analysis files across daily/weekly/monthly/annual

**Right Panel (Editor)**
- Full-height text editor for viewing and editing files
- Image preview for handwritten note images
- Save/Revert buttons with unsaved changes indicator
- **Quick Markup Tools** - Add task markers (✓ completed, ✗ removed, * urgent, ↳ subtask)

**Note**: Image/PDF files must be synced first to create `.raw_notes.txt` files before they can be analyzed.
"""


def render_actions_section(notes_dir: Path | None) -> None:
    """Render Sync and Analyze buttons with progress.

    Args:
        notes_dir: Notes directory path
    """
    st.markdown('<p class="section-header">Actions</p>', unsafe_allow_html=True)

    # Define sync_disabled and triage_disabled
    sync_disabled = st.session_state.sync_disabled or notes_dir is None
    triage_disabled = st.session_state.triage_disabled or notes_dir is None

    # Sync Button
    if st.button("🔄 Sync", type="secondary", disabled=sync_disabled,
        use_container_width=True, key="btn_sync",
        help="Copy raw notes from inputs, convert images/PDFs to text, and sync all files across directories"):

        st.session_state.sync_disabled = True

        # Get the output directory (where files are generated)
        local_output = os.getenv("LOCAL_OUTPUT_DIR")
        if not local_output:
            st.error("LOCAL_OUTPUT_DIR not configured. Cannot sync files.")
        else:
            output_dir = Path(local_output)

            # Create a progress area
            progress_placeholder = st.empty()
            status_placeholder = st.empty()

            def progress_callback(msg: str, seconds: int = 5):
                with st.empty():
                    status_placeholder.info(msg)
                    time.sleep(seconds)
                    st.empty()

            # Run sync
            with progress_placeholder.container():
                st.info("🔄 Syncing files across all configured directories...")

            stats = sync_files_across_directories(output_dir, progress_callback)

            # Show results
            progress_placeholder.empty()

            if stats["total"] == 0 and stats["converted"] == 0 and stats["contexts_updated"] == 0:
                st.warning("No files to sync or convert, no context updates needed")
            else:
                # Build success message
                parts = []
                if stats["synced"] > 0:
                    parts.append(f"synced {stats['synced']} files")
                if stats["converted"] > 0:
                    parts.append(f"converted {stats['converted']} visual files")
                if stats["contexts_updated"] > 0:
                    parts.append(f"updated {stats['contexts_updated']}/{stats['contexts_total']} contexts")
                elif stats["contexts_total"] > 0:
                    parts.append(f"all {stats['contexts_total']} contexts up-to-date")

                if parts:
                    msg = "✅ Sync complete! " + ", ".join(parts)
                    st.success(msg)
                else:
                    st.info("No new files to sync or convert, all contexts up-to-date")

                if stats["errors"]:
                    with st.expander(f"⚠️ {len(stats['errors'])} Errors"):
                        for error in stats["errors"]:
                            st.error(error)

            st.session_state.sync_disabled = False

    # Analyze button
    if st.button("🔍 Analyze", type="primary", disabled=triage_disabled,
        use_container_width=True, key="btn_triage",
        help="Analyze synced files. Weekly/monthly/annual auto-trigger."):
        st.session_state.triage_running = True
        st.session_state.triage_progress = []
        st.rerun()


def render_raw_notes_section(notes_dir: Path) -> None:
    """Render raw notes file selector.

    Args:
        notes_dir: Notes directory path
    """
    st.markdown('<p class="section-header">Raw Notes</p>', unsafe_allow_html=True)

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

        # Add slider to filter by maximum age of files
        max_age_days = st.slider(
            "Maximum age (days)",
            min_value=0,
            max_value=365,
            value=365,
            step=1,
            help="Show only files from the last N days. Set to 365 to show all files from previous year."
        )

        # Filter files by age if slider is not at maximum
        if max_age_days < 365 and raw_notes:
            cutoff_date = datetime.now() - timedelta(days=max_age_days)
            filtered_notes = []
            for file_path, display_name in raw_notes:
                file_date = parse_filename_datetime(file_path.name)
                if file_date and file_date >= cutoff_date:
                    filtered_notes.append((file_path, display_name))
            raw_notes = filtered_notes

        btn_col1, btn_col2, btn_col3 = st.columns(3)
        with btn_col1:
            if st.button("🔄 Refresh", use_container_width=True, key="btn_refresh_raw"):
                st.rerun()
        with btn_col2:
            if st.button("📂 Open", use_container_width=True, key="btn_render_raw"):
                select_file(selected_raw)
                st.rerun()
        with btn_col3:
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


def render_analysis_files_section(notes_dir: Path) -> None:
    """Render analysis files selector.

    Args:
        notes_dir: Notes directory path
    """
    st.markdown('<p class="section-header">Analysis Files</p>', unsafe_allow_html=True)

    analysis_files = list_analysis_files(notes_dir)
    
    # Apply filters
    filtered_files = filter_analysis_files(
        analysis_files,
        include_notes=st.session_state.filter_daily,
        include_weekly=st.session_state.filter_weekly,
        include_monthly=st.session_state.filter_monthly,
        include_annual=st.session_state.filter_annual,
    )
    
    if filtered_files:
        # Set default selection if not set
        if st.session_state.analysis_files_selection is None and filtered_files:
            st.session_state.analysis_files_selection = filtered_files[0][0]

        selected_analysis = st.selectbox(
            "Select an analysis file",
            options=[f[0] for f in filtered_files],
            format_func=lambda x: next((f[1] for f in filtered_files if f[0] == x), x.name),
            key="analysis_files_select",
            label_visibility="collapsed",
            index=[f[0] for f in filtered_files].index(st.session_state.analysis_files_selection) if st.session_state.analysis_files_selection in [f[0] for f in filtered_files] else 0
        )
        st.session_state.analysis_files_selection = selected_analysis

        if st.button("📂 Open", use_container_width=True, key="btn_render_analysis"):
            select_file(selected_analysis)
            st.rerun()
        
        # Filter controls for analysis files
        filter_col1, filter_col2 = st.columns(2)
        with filter_col1:
            st.session_state.filter_daily = st.checkbox(
                "Notes (Daily)",
                value=st.session_state.filter_daily,
                key="checkbox_filter_daily"
            )
            st.session_state.filter_monthly = st.checkbox(
                "Monthly",
                value=st.session_state.filter_monthly,
                key="checkbox_filter_monthly"
            )
        with filter_col2:
            st.session_state.filter_weekly = st.checkbox(
                "Weekly",
                value=st.session_state.filter_weekly,
                key="checkbox_filter_weekly"
            )
            st.session_state.filter_annual = st.checkbox(
                "Annual",
                value=st.session_state.filter_annual,
                key="checkbox_filter_annual"
            )
        
        if st.button("🔄 Refresh", use_container_width=True, key="btn_filter_refresh"):
            st.rerun()

    else:
        st.info("No analysis files found")


def render_triage_progress() -> None:
    """Render triage progress section."""
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
                        
                        # Show error details if there are any failures
                        all_errors = []
                        for level, result in results.items():
                            if result["errors"]:
                                all_errors.extend(result["errors"])
                        
                        if all_errors:
                            with st.expander(f"⚠️ {len(all_errors)} Error(s) - Details"):
                                for error in all_errors:
                                    st.error(error)

                    st.rerun()


def render_left_panel(notes_dir: Path | None) -> None:
    """Render the complete left control panel.

    Args:
        notes_dir: Notes directory path
    """
    # Actions section
    render_actions_section(notes_dir)

    # Configuration expander
    with st.expander("Configuration", expanded=False):
        render_config_panel(render_oauth_section)

    st.markdown("---")

    # File Selection - Raw Notes
    if notes_dir:
        render_raw_notes_section(notes_dir)
    else:
        st.info("Configure notes directory to see files")

    # File Selection - Analysis Files
    if notes_dir:
        render_analysis_files_section(notes_dir)
    else:
        st.info("Configure notes directory to see files")

    # Triage Progress
    render_triage_progress()


def render_editor_for_text_file(file_path: Path) -> None:
    """Render text editor with save/revert controls.

    Args:
        file_path: Path to the text file
    """
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
    render_quick_markup_tools()

    # Text editor - uses content_editor session state key
    # Don't pass 'value' when using 'key' - Streamlit manages it automatically
    st.text_area(
        "File content",
        height=600,
        key="content_editor",
        label_visibility="collapsed"
    )


def render_visual_file_preview(file_path: Path) -> None:
    """Render preview for image/PDF files.

    Args:
        file_path: Path to the image or PDF file
    """
    if file_path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp"}:
        # Image files - show header without edit controls
        st.markdown(f"### 📄 {file_path.name}")
        st.caption("Image file (read-only)")
        st.markdown("---")
        st.info("Run Sync to convert this image to an editable .raw_notes.txt file, then Analyze to generate the analysis.")
        # Show image preview
        render_image_preview(file_path)
    elif file_path.suffix.lower() == ".pdf":
        # PDF files - show header without edit controls
        st.markdown(f"### 📄 {file_path.name}")
        st.caption("PDF file (read-only)")
        st.markdown("---")
        st.info("Run Sync to convert this PDF to an editable .raw_notes.txt file, then Analyze to generate the analysis.")


def render_empty_state() -> None:
    """Render empty state with source status."""
    st.markdown("### Select a file to edit")
    st.info("Choose a file from the Raw Notes or Analysis Files list on the left to view and edit its content. For new image/PDF files, run Sync first to convert them to editable text.")

    # Show notes source status
    st.markdown("---")
    st.markdown("#### Notes Source Status")

    try:
        if is_local_input_available():
            st.success(f"✓ Local Input: {LOCAL_INPUT_DIR}")
        else:
            st.warning("✗ Local Input not found")
    except Exception:
        st.warning("Local Input not configured")

    try:
        if is_usb_available():
            st.success(f"✓ USB Input: {EXTERNAL_INPUT_DIR}")
        else:
            st.warning("✗ USB Input not found")
    except Exception:
        st.info("USB Input not configured")

    try:
        if is_gdrive_available():
            st.success("✓ Google Drive configured")
        else:
            st.warning("✗ Google Drive not configured")
    except Exception:
        st.warning("Google Drive not configured")


def render_right_panel(notes_dir: Path | None) -> None:
    """Render the complete right editor panel.

    Args:
        notes_dir: Notes directory path
    """
    if st.session_state.selected_file:
        file_path = st.session_state.selected_file

        # Check if it's an image or PDF file
        if file_path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf"}:
            render_visual_file_preview(file_path)
        else:
            # Text files - show editor with controls
            render_editor_for_text_file(file_path)
    else:
        # No file selected
        render_empty_state()
