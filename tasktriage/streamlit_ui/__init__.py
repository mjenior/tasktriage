"""
Streamlit UI package for TaskTriage.

Provides a clean, modular UI structure with separation of concerns:
- Styling (styles.py)
- State management (state.py)
- File operations (file_ops.py)
- Reusable components (components.py)
- Configuration UI (config_ui.py)
- OAuth UI (oauth_ui.py)
- Business logic (logic.py)
- Panel rendering (panels.py)
"""

from .state import initialize_session_state, reset_editor_state, reset_sync_state, reset_triage_state
from .panels import render_left_panel, render_right_panel, HELP_TEXT
from .styles import CUSTOM_CSS
from .logic import run_triage_pipeline, sync_files_across_directories
from .oauth_ui import handle_oauth_callback, check_existing_authentication
from .file_ops import get_notes_directory

__all__ = [
    # State management
    "initialize_session_state",
    "reset_editor_state",
    "reset_sync_state",
    "reset_triage_state",
    # Panel rendering
    "render_left_panel",
    "render_right_panel",
    # Business logic
    "run_triage_pipeline",
    "sync_files_across_directories",
    # OAuth
    "handle_oauth_callback",
    "check_existing_authentication",
    # File operations
    "get_notes_directory",
    # Constants
    "CUSTOM_CSS",
    "HELP_TEXT",
]
