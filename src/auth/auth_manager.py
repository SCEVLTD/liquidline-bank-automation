"""
Authentication Manager for Enterprise SaaS Deployment
Supports: Streamlit Cloud Auth, Custom Auth, API Keys
"""

import streamlit as st
from functools import wraps
from typing import Optional, Dict, Any
import hashlib
import hmac
import os


class AuthManager:
    """
    Manages authentication for the Bank Reconciliation SaaS platform.

    Supports multiple authentication modes:
    1. Streamlit Cloud built-in auth (Teams/Enterprise)
    2. Simple password protection (for quick deployment)
    3. API key authentication (for programmatic access)
    4. Custom OAuth (future: Auth0, Clerk, etc.)
    """

    def __init__(self):
        self.auth_mode = self._detect_auth_mode()

    def _detect_auth_mode(self) -> str:
        """Detect which authentication mode to use based on environment"""
        # Check if running on Streamlit Cloud with auth enabled
        if hasattr(st, 'experimental_user') and st.experimental_user.email:
            return "streamlit_cloud"

        # Check for password protection
        if self._get_secret("APP_PASSWORD"):
            return "password"

        # Check for API key mode
        if self._get_secret("API_KEYS"):
            return "api_key"

        # Default: no auth (development mode)
        return "none"

    def _get_secret(self, key: str) -> Optional[str]:
        """Get secret from Streamlit secrets or environment"""
        try:
            if hasattr(st, 'secrets') and key in st.secrets:
                return st.secrets[key]
        except:
            pass
        return os.getenv(key)

    def check_authentication(self) -> bool:
        """
        Check if user is authenticated.
        Returns True if authenticated, False otherwise.
        """
        if self.auth_mode == "none":
            return True

        if self.auth_mode == "streamlit_cloud":
            return self._check_streamlit_cloud_auth()

        if self.auth_mode == "password":
            return self._check_password_auth()

        if self.auth_mode == "api_key":
            return self._check_api_key_auth()

        return False

    def _check_streamlit_cloud_auth(self) -> bool:
        """Check Streamlit Cloud authentication"""
        try:
            user_email = st.experimental_user.email
            allowed_domains = self._get_secret("ALLOWED_DOMAINS")
            allowed_emails = self._get_secret("ALLOWED_EMAILS")

            if allowed_emails:
                allowed_list = [e.strip() for e in allowed_emails.split(",")]
                return user_email in allowed_list

            if allowed_domains:
                domain_list = [d.strip() for d in allowed_domains.split(",")]
                user_domain = user_email.split("@")[1] if "@" in user_email else ""
                return user_domain in domain_list

            # If no restrictions, allow any authenticated user
            return bool(user_email)
        except:
            return False

    def _check_password_auth(self) -> bool:
        """Simple password protection"""
        if 'authenticated' not in st.session_state:
            st.session_state.authenticated = False

        if st.session_state.authenticated:
            return True

        # Show login form
        st.markdown("### Login Required")
        password = st.text_input("Password", type="password", key="login_password")

        if st.button("Login"):
            correct_password = self._get_secret("APP_PASSWORD")
            if password == correct_password:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Incorrect password")

        return False

    def _check_api_key_auth(self) -> bool:
        """API key authentication (for programmatic access)"""
        # Check query params for API key
        api_key = st.query_params.get("api_key", "")

        if not api_key:
            st.error("API key required. Add ?api_key=YOUR_KEY to URL")
            return False

        valid_keys = self._get_secret("API_KEYS")
        if valid_keys:
            key_list = [k.strip() for k in valid_keys.split(",")]
            return api_key in key_list

        return False

    def get_current_user(self) -> Dict[str, Any]:
        """Get information about the current authenticated user"""
        if self.auth_mode == "streamlit_cloud":
            try:
                return {
                    "email": st.experimental_user.email,
                    "auth_mode": "streamlit_cloud"
                }
            except:
                pass

        return {
            "email": "anonymous",
            "auth_mode": self.auth_mode
        }

    def get_client_config(self) -> Dict[str, Any]:
        """
        Get client-specific configuration.
        For multi-tenant SaaS, this returns settings for the current client.
        """
        # Default client config (Liquidline)
        config = {
            "client_name": self._get_secret("CLIENT_NAME") or "Liquidline",
            "client_logo": self._get_secret("CLIENT_LOGO") or None,
            "primary_color": self._get_secret("PRIMARY_COLOR") or "#1E88E5",
            "data_retention_days": int(self._get_secret("DATA_RETENTION_DAYS") or "90"),
            "features": {
                "ai_matching": self._get_secret("FEATURE_AI_MATCHING") != "false",
                "remittance_parsing": self._get_secret("FEATURE_REMITTANCE") != "false",
                "eagle_export": True,
                "excel_export": True,
            }
        }
        return config


def require_auth(func):
    """Decorator to require authentication for a function"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        auth = AuthManager()
        if not auth.check_authentication():
            st.stop()
            return None
        return func(*args, **kwargs)
    return wrapper


# Convenience function for use in Streamlit apps
def check_auth() -> bool:
    """Check if user is authenticated. Call at start of app."""
    auth = AuthManager()
    return auth.check_authentication()


def get_client_config() -> Dict[str, Any]:
    """Get client configuration for current tenant"""
    auth = AuthManager()
    return auth.get_client_config()
