"""
Configuration UI panel.

Handles loading, saving, and rendering of configuration settings
for environment variables and model configuration.
"""

from pathlib import Path

import streamlit as st
import yaml
from dotenv import dotenv_values, set_key

from tasktriage.config import CONFIG_PATH


def load_env_config() -> dict:
    """Load configuration from .env file.

    Returns:
        Dictionary of environment variables
    """
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        return dict(dotenv_values(env_path))
    return {}


def save_env_config(config: dict) -> bool:
    """Save configuration to .env file.

    Args:
        config: Dictionary of environment variables to save

    Returns:
        True if successful, False otherwise
    """
    env_path = Path(__file__).parent.parent.parent / ".env"
    try:
        for key, value in config.items():
            set_key(str(env_path), key, value)
        return True
    except Exception as e:
        st.error(f"Error saving configuration: {e}")
        return False


def load_yaml_config() -> dict:
    """Load model configuration from config.yaml.

    Returns:
        Dictionary of model configuration settings
    """
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH) as f:
                return yaml.safe_load(f) or {}
        except Exception:
            pass
    return {"model": "claude-haiku-4-5-20251001", "temperature": 0.7, "max_tokens": 4096}


def save_yaml_config(config: dict) -> bool:
    """Save model configuration to config.yaml.

    Args:
        config: Dictionary of model configuration to save

    Returns:
        True if successful, False otherwise
    """
    try:
        with open(CONFIG_PATH, "w") as f:
            yaml.dump(config, f, default_flow_style=False)
        return True
    except Exception as e:
        st.error(f"Error saving config.yaml: {e}")
        return False


def render_config_panel(oauth_section_renderer) -> None:
    """Render the complete configuration panel.

    Args:
        oauth_section_renderer: Function to render the OAuth section
    """
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
        index=["auto", "usb", "gdrive"].index(yaml_config.get("notes_source", "auto"))
    )

    st.markdown("**Input Directories**")

    external_input_dir = st.text_input(
        "EXTERNAL_INPUT_DIR",
        value=env_config.get("EXTERNAL_INPUT_DIR", ""),
        help="Path to USB/mounted device notes directory"
    )

    local_input_dir = st.text_input(
        "LOCAL_INPUT_DIR",
        value=env_config.get("LOCAL_INPUT_DIR", ""),
        help="Path to local hard drive notes directory (optional)"
    )

    # Render OAuth section
    oauth_section_renderer(env_config)

    # Google Drive folder ID (always show this)
    gdrive_folder = st.text_input(
        "GOOGLE_DRIVE_FOLDER_ID",
        value=env_config.get("GOOGLE_DRIVE_FOLDER_ID", ""),
        help="Google Drive folder ID for your notes"
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
                "EXTERNAL_INPUT_DIR": external_input_dir,
                "LOCAL_INPUT_DIR": local_input_dir,
                "GOOGLE_OAUTH_CLIENT_ID": env_config.get("GOOGLE_OAUTH_CLIENT_ID", ""),
                "GOOGLE_OAUTH_CLIENT_SECRET": env_config.get("GOOGLE_OAUTH_CLIENT_SECRET", ""),
                "GOOGLE_DRIVE_FOLDER_ID": gdrive_folder,
                "LOCAL_OUTPUT_DIR": local_output,
            }
            save_env_config(new_env)

            # Save yaml config
            new_yaml = {
                "model": model,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "notes_source": notes_source,
            }
            save_yaml_config(new_yaml)

            st.success("Configuration saved!")
            st.rerun()

    with col2:
        if st.button("Cancel", key="btn_cancel_config"):
            st.session_state.show_config = False
            st.rerun()
