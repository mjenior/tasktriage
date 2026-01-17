"""
OAuth UI integration for Google Drive.

Handles OAuth flow UI, authentication state, and user interactions
for Google Drive integration.
"""

import os
import secrets

import streamlit as st

from tasktriage.config import is_gdrive_available
from tasktriage.oauth import OAuthManager


def get_oauth_manager() -> OAuthManager:
    """Get or create OAuth manager instance.

    Returns:
        OAuthManager instance

    Raises:
        ValueError: If OAuth credentials not configured
    """
    client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")
    redirect_uri = "http://localhost:8501"

    if not client_id or not client_secret:
        raise ValueError("OAuth credentials not configured in .env")

    return OAuthManager(client_id, client_secret, redirect_uri)


def initiate_oauth_flow() -> None:
    """Start OAuth authorization flow.

    Generates authorization URL and displays it to the user.
    """
    try:
        oauth_mgr = get_oauth_manager()
        state = secrets.token_urlsafe(32)
        st.session_state.oauth_state = state

        auth_url = oauth_mgr.get_authorization_url(state)
        st.info(f"Please visit this URL to authorize TaskTriage:\n\n{auth_url}")
        st.markdown(f"[Click here to authorize]({auth_url})")
    except ValueError as e:
        st.error(f"OAuth not configured: {e}")


def handle_oauth_callback() -> None:
    """Handle OAuth callback and exchange code for tokens.

    Checks for OAuth callback parameters in URL query params,
    exchanges authorization code for tokens, and updates session state.
    """
    try:
        query_params = st.query_params

        if "code" in query_params and "state" in query_params:
            code = query_params["code"]

            # Exchange code for tokens
            oauth_mgr = get_oauth_manager()

            try:
                credentials = oauth_mgr.exchange_code_for_tokens(code)
                st.session_state.oauth_authenticated = True
                st.session_state.oauth_credentials = credentials

                st.query_params.clear()
                st.success("✓ Successfully authenticated with Google Drive!")
                st.rerun()

            except Exception as e:
                st.error(f"Authentication failed: {e}")
                st.session_state.oauth_authenticated = False
    except Exception:
        # Silently handle errors in callback handling
        pass


def check_existing_authentication() -> None:
    """Check if already authenticated from saved tokens.

    Updates session state if valid saved credentials are found.
    """
    if not st.session_state.oauth_authenticated and is_gdrive_available():
        try:
            oauth_mgr = get_oauth_manager()
            if oauth_mgr.is_authenticated():
                st.session_state.oauth_authenticated = True
                st.session_state.oauth_credentials = oauth_mgr.load_credentials()
        except Exception:
            pass  # OAuth not configured yet


def render_oauth_section(env_config: dict) -> None:
    """Render OAuth authentication section in config panel.

    Args:
        env_config: Dictionary of environment configuration
    """
    st.markdown("**Google Drive (OAuth 2.0)**")

    if st.session_state.oauth_authenticated:
        st.success("✓ Authenticated with Google Drive")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Refresh Token", use_container_width=True):
                try:
                    oauth_mgr = get_oauth_manager()
                    creds = oauth_mgr.load_credentials()
                    if creds:
                        from google.auth.transport.requests import Request
                        creds.refresh(Request())
                        oauth_mgr.save_credentials(creds)
                        st.success("Token refreshed!")
                except Exception as e:
                    st.error(f"Token refresh failed: {e}")

        with col2:
            if st.button("🚪 Sign Out", use_container_width=True):
                try:
                    oauth_mgr = get_oauth_manager()
                    oauth_mgr.clear_credentials()
                    st.session_state.oauth_authenticated = False
                    st.session_state.oauth_credentials = None
                    st.success("Signed out!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Sign out failed: {e}")
    else:
        st.warning("⚠ Not authenticated with Google Drive")

        client_id = st.text_input(
            "GOOGLE_OAUTH_CLIENT_ID",
            value=env_config.get("GOOGLE_OAUTH_CLIENT_ID", ""),
            help="OAuth 2.0 Client ID from Google Cloud Console"
        )

        client_secret = st.text_input(
            "GOOGLE_OAUTH_CLIENT_SECRET",
            value=env_config.get("GOOGLE_OAUTH_CLIENT_SECRET", ""),
            type="password",
            help="OAuth 2.0 Client Secret from Google Cloud Console"
        )

        if st.button("🔐 Sign in with Google", type="primary", use_container_width=True):
            if not client_id or not client_secret:
                st.error("Please configure OAuth client ID and secret first")
            else:
                env_config["GOOGLE_OAUTH_CLIENT_ID"] = client_id
                env_config["GOOGLE_OAUTH_CLIENT_SECRET"] = client_secret
                # Note: config save happens in config_ui.py
                initiate_oauth_flow()
