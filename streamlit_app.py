"""
TaskTriage Streamlit UI

A professional, Canvas-style interface for the TaskTriage GTD-based task analysis tool.
"""

import streamlit as st

from tasktriage import __version__
from tasktriage.streamlit_ui import (
    initialize_session_state,
    render_left_panel,
    render_right_panel,
    handle_oauth_callback,
    check_existing_authentication,
    get_notes_directory,
    CUSTOM_CSS,
    HELP_TEXT,
)

# Page configuration
st.set_page_config(
    page_title="TaskTriage",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Apply custom CSS
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# Initialize session state
initialize_session_state()


def main():
    """Main application entry point."""
    # Handle OAuth callback
    handle_oauth_callback()

    # Check for existing authentication
    check_existing_authentication()

    # Header
    st.markdown(f"# 📋 TaskTriage v{__version__}", help=HELP_TEXT)

    # Get notes directory
    notes_dir = get_notes_directory()

    if notes_dir is None or not notes_dir.exists():
        st.warning("No notes directory configured. Please set up your configuration.")
        notes_dir = None

    # Two-panel layout
    left_col, right_col = st.columns([3, 7], gap="medium")

    with left_col:
        render_left_panel(notes_dir)

    with right_col:
        render_right_panel(notes_dir)


if __name__ == "__main__":
    main()
