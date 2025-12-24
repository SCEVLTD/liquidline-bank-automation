"""
Authentication module for enterprise deployment.
Supports multiple auth providers for SaaS licensing model.
"""

from .auth_manager import AuthManager, require_auth

__all__ = ['AuthManager', 'require_auth']
