"""FastAPI authentication dependencies."""

from typing import Optional

from fastapi import Depends, HTTPException, Request, status

from lacuna.auth.models import AuthenticatedUser
from lacuna.config import get_settings


def _extract_user_from_headers(request: Request) -> Optional[AuthenticatedUser]:
    """Extract user information from reverse proxy headers."""
    settings = get_settings()
    auth_settings = settings.auth

    # Get user ID from header
    user_id = request.headers.get(auth_settings.user_header)
    if not user_id:
        return None

    # Extract other headers
    email = request.headers.get(auth_settings.email_header)
    display_name = request.headers.get(auth_settings.name_header)

    # Parse groups (comma-separated)
    groups_header = request.headers.get(auth_settings.groups_header, "")
    groups = [g.strip() for g in groups_header.split(",") if g.strip()]

    # Get client IP
    ip_address = request.client.host if request.client else None
    # Check for forwarded IP
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        ip_address = forwarded.split(",")[0].strip()

    return AuthenticatedUser(
        user_id=user_id,
        email=email,
        display_name=display_name,
        groups=groups,
        auth_method="proxy",
        ip_address=ip_address,
    )


def _extract_user_from_api_key(request: Request) -> Optional[AuthenticatedUser]:
    """Extract user information from API key."""
    from lacuna.auth.api_keys import get_api_key_store

    settings = get_settings()
    auth_settings = settings.auth

    # Get authorization header
    auth_header = request.headers.get(auth_settings.api_key_header)
    if not auth_header:
        return None

    # Parse Bearer token
    prefix = auth_settings.api_key_prefix
    if not auth_header.startswith(f"{prefix} "):
        return None

    raw_key = auth_header[len(prefix) + 1 :]
    if not raw_key.startswith("lac_"):
        return None

    # Look up the API key
    store = get_api_key_store()
    api_key = store.get_by_raw_key(raw_key)

    if api_key is None:
        return None

    if not api_key.is_valid:
        return None

    # Update last used timestamp
    store.update_last_used(api_key.id)

    # Get client IP
    ip_address = request.client.host if request.client else None

    return AuthenticatedUser(
        user_id=api_key.service_account_id,
        groups=api_key.groups,
        auth_method="api_key",
        api_key_id=api_key.id,
        ip_address=ip_address,
    )


def _get_dev_user() -> AuthenticatedUser:
    """Get a default user for dev mode."""
    settings = get_settings()
    return AuthenticatedUser(
        user_id="dev-user",
        email="dev@localhost",
        display_name="Development User",
        groups=[settings.auth.admin_group],  # Admin in dev mode
        auth_method="dev",
    )


async def get_optional_user(request: Request) -> Optional[AuthenticatedUser]:
    """Get current user if authenticated, None otherwise.

    This dependency does not require authentication.
    """
    settings = get_settings()

    # Dev mode bypass
    if not settings.auth.enabled or settings.environment == "development":
        return _get_dev_user()

    # Try API key first (for service accounts)
    user = _extract_user_from_api_key(request)
    if user:
        return user

    # Try proxy headers
    user = _extract_user_from_headers(request)
    if user:
        return user

    return None


async def get_current_user(
    user: Optional[AuthenticatedUser] = Depends(get_optional_user),
) -> AuthenticatedUser:
    """Get current authenticated user.

    Raises 401 if not authenticated.
    """
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def require_authenticated(
    user: AuthenticatedUser = Depends(get_current_user),
) -> AuthenticatedUser:
    """Require authenticated user (alias for get_current_user)."""
    return user


async def require_admin(
    user: AuthenticatedUser = Depends(get_current_user),
) -> AuthenticatedUser:
    """Require admin user.

    Raises 403 if user is not an admin.
    """
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


class AuthContext:
    """Context manager for authentication in request handlers."""

    def __init__(self, request: Request):
        """Initialize auth context with request."""
        self.request = request
        self._user: Optional[AuthenticatedUser] = None

    async def get_user(self) -> Optional[AuthenticatedUser]:
        """Get the current user."""
        if self._user is None:
            self._user = await get_optional_user(self.request)
        return self._user

    async def require_user(self) -> AuthenticatedUser:
        """Require an authenticated user."""
        user = await self.get_user()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )
        return user

    async def require_admin(self) -> AuthenticatedUser:
        """Require an admin user."""
        user = await self.require_user()
        if not user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required",
            )
        return user
