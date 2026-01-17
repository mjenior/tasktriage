"""
Streamlit session state management.

Centralizes all session state initialization and management functions.
"""

import streamlit as st


def initialize_session_state() -> None:
    """Initialize all Streamlit session state variables.

    This function should be called once at the start of the app to ensure
    all session state variables are properly initialized.
    """
    # File selection state
    if "selected_file" not in st.session_state:
        st.session_state.selected_file = None

    # Editor content state
    if "file_content" not in st.session_state:
        st.session_state.file_content = ""
    if "original_content" not in st.session_state:
        st.session_state.original_content = ""
    if "content_editor" not in st.session_state:
        st.session_state.content_editor = ""

    # Sync operation state
    if "sync_running" not in st.session_state:
        st.session_state.sync_running = False
    if "sync_disabled" not in st.session_state:
        st.session_state.sync_disabled = False

    # Triage operation state
    if "triage_progress" not in st.session_state:
        st.session_state.triage_progress = []
    if "triage_running" not in st.session_state:
        st.session_state.triage_running = False
    if "triage_disabled" not in st.session_state:
        st.session_state.triage_disabled = False

    # Configuration UI state
    if "show_config" not in st.session_state:
        st.session_state.show_config = False

    # File list selection state
    if "raw_notes_selection" not in st.session_state:
        st.session_state.raw_notes_selection = None
    if "analysis_files_selection" not in st.session_state:
        st.session_state.analysis_files_selection = None

    # OAuth authentication state
    if "oauth_authenticated" not in st.session_state:
        st.session_state.oauth_authenticated = False
    if "oauth_state" not in st.session_state:
        st.session_state.oauth_state = None
    if "oauth_credentials" not in st.session_state:
        st.session_state.oauth_credentials = None


def reset_editor_state() -> None:
    """Reset editor-related state variables.

    Useful when switching to a different file or after saving.
    """
    st.session_state.file_content = ""
    st.session_state.original_content = ""
    st.session_state.content_editor = ""


def reset_sync_state() -> None:
    """Reset sync operation state variables.

    Should be called after sync operation completes or is cancelled.
    """
    st.session_state.sync_running = False
    st.session_state.sync_disabled = False


def reset_triage_state() -> None:
    """Reset triage operation state variables.

    Should be called after triage operation completes or is cancelled.
    """
    st.session_state.triage_running = False
    st.session_state.triage_disabled = False
    st.session_state.triage_progress = []
