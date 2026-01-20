"""Authentication module for Lacuna."""

from lacuna.auth.dependencies import (
    get_current_user,
    get_optional_user,
    require_admin,
    require_authenticated,
)
from lacuna.auth.models import APIKey, AuthenticatedUser

__all__ = [
    "AuthenticatedUser",
    "APIKey",
    "get_current_user",
    "get_optional_user",
    "require_admin",
    "require_authenticated",
]
