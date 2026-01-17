"""
Reusable UI components for the Streamlit interface.

Contains small, focused UI components that can be reused across the application.
"""

from pathlib import Path

import streamlit as st


def render_image_preview(file_path: Path) -> None:
    """Render an image preview if the selected file is an image.

    Args:
        file_path: Path to the image file
    """
    if file_path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp"}:
        try:
            with open(file_path, "rb") as f:
                image_data = f.read()
            st.image(image_data, caption=file_path.name, use_container_width=True)
        except Exception as e:
            st.error(f"Error loading image: {e}")


def render_quick_markup_tools() -> None:
    """Render the quick markup tools section.

    Displays copyable task markers for completed, removed, and urgent tasks.
    """
    st.markdown('<p class="section-header">Quick Markup</p>', unsafe_allow_html=True)
    st.caption("Copyable task markers ( ✓ Completed, ✗ Removed, ☆ Urgent )")

    # Show markup text
    col1, col2, col3 = st.columns(3, width=200)

    with col1:
        st.code(" ✓", language=None)

    with col2:
        st.code(" ✗", language=None)

    with col3:
        st.code(" ☆", language=None)


def render_progress_display(progress_messages: list[str]) -> None:
    """Render progress messages in a container.

    Args:
        progress_messages: List of progress message strings to display
    """
    if not progress_messages:
        return

    progress_container = st.container()
    with progress_container:
        for msg in progress_messages:
            st.text(msg)
