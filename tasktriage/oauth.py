"""
OAuth 2.0 authentication for Google Drive.

Handles OAuth flow, token storage, and automatic token refresh.
"""

import json
import os
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

# OAuth configuration
SCOPES = ["https://www.googleapis.com/auth/drive"]
TOKEN_FILE = Path.home() / ".tasktriage" / "oauth_tokens.json"
KEY_FILE = Path.home() / ".tasktriage" / "encryption.key"


class OAuthManager:
    """Manages OAuth 2.0 authentication and token persistence."""

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        """Initialize OAuth manager.

        Args:
            client_id: Google OAuth client ID
            client_secret: Google OAuth client secret
            redirect_uri: OAuth redirect URI (must match Google Console config)

        Raises:
            ValueError: If credentials are missing
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self._ensure_directories()
        self._ensure_encryption_key()

    def _ensure_directories(self):
        """Create ~/.tasktriage directory if it doesn't exist."""
        TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)

    def _ensure_encryption_key(self):
        """Generate or load encryption key for token storage."""
        if not KEY_FILE.exists():
            key = Fernet.generate_key()
            KEY_FILE.write_bytes(key)
            # Set restrictive permissions (owner read/write only)
            KEY_FILE.chmod(0o600)

        self._cipher = Fernet(KEY_FILE.read_bytes())

    def get_authorization_url(self, state: str) -> str:
        """Generate OAuth authorization URL.

        Args:
            state: Random state string for CSRF protection

        Returns:
            Authorization URL to redirect user to
        """
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            },
            scopes=SCOPES,
            redirect_uri=self.redirect_uri,
        )

        auth_url, _ = flow.authorization_url(
            access_type="offline",  # Request refresh token
            include_granted_scopes="true",
            state=state,
            prompt="consent",  # Force consent screen to ensure refresh token
        )

        return auth_url

    def exchange_code_for_tokens(self, code: str) -> Credentials:
        """Exchange authorization code for access/refresh tokens.

        Args:
            code: Authorization code from OAuth callback

        Returns:
            OAuth credentials object
        """
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            },
            scopes=SCOPES,
            redirect_uri=self.redirect_uri,
        )

        flow.fetch_token(code=code)
        credentials = flow.credentials

        # Save tokens immediately after exchange
        self.save_credentials(credentials)

        return credentials

    def save_credentials(self, credentials: Credentials):
        """Save OAuth credentials to encrypted file.

        Args:
            credentials: Google OAuth credentials to save
        """
        token_data = {
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": credentials.scopes,
            "expiry": credentials.expiry.isoformat() if credentials.expiry else None,
        }

        # Encrypt token data
        encrypted_data = self._cipher.encrypt(json.dumps(token_data).encode())

        # Write to file with restrictive permissions
        TOKEN_FILE.write_bytes(encrypted_data)
        TOKEN_FILE.chmod(0o600)

    def load_credentials(self) -> Optional[Credentials]:
        """Load OAuth credentials from encrypted file.

        Returns:
            Credentials object or None if no saved credentials exist
        """
        if not TOKEN_FILE.exists():
            return None

        try:
            # Decrypt token data
            encrypted_data = TOKEN_FILE.read_bytes()
            token_json = self._cipher.decrypt(encrypted_data).decode()
            token_data = json.loads(token_json)

            # Reconstruct credentials
            credentials = Credentials(
                token=token_data["token"],
                refresh_token=token_data["refresh_token"],
                token_uri=token_data["token_uri"],
                client_id=token_data["client_id"],
                client_secret=token_data["client_secret"],
                scopes=token_data["scopes"],
            )

            # Handle token refresh if expired
            if credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
                self.save_credentials(credentials)

            return credentials

        except Exception as e:
            # If decryption fails or token is invalid, return None
            # This forces re-authentication
            print(f"Error loading credentials: {e}")
            return None

    def is_authenticated(self) -> bool:
        """Check if user has valid OAuth credentials.

        Returns:
            True if authenticated with valid tokens
        """
        credentials = self.load_credentials()
        return credentials is not None and credentials.valid

    def clear_credentials(self):
        """Remove saved OAuth credentials (logout)."""
        if TOKEN_FILE.exists():
            TOKEN_FILE.unlink()
