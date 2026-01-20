"""Authentication models."""

import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4


def _utc_now() -> datetime:
    """Get current UTC time."""
    return datetime.now(timezone.utc)


@dataclass
class AuthenticatedUser:
    """Authenticated user context.

    This represents a user authenticated via either:
    - Reverse proxy headers (OIDC/SSO)
    - API key (service accounts)
    """

    user_id: str
    email: Optional[str] = None
    display_name: Optional[str] = None
    groups: list[str] = field(default_factory=list)

    # Authentication metadata
    auth_method: str = "proxy"  # "proxy" or "api_key"
    api_key_id: Optional[UUID] = None

    # Session info
    session_id: Optional[str] = None
    ip_address: Optional[str] = None

    @property
    def is_admin(self) -> bool:
        """Check if user is an admin."""
        from lacuna.config import get_settings

        settings = get_settings()
        return settings.auth.admin_group in self.groups

    @property
    def is_service_account(self) -> bool:
        """Check if this is a service account (API key auth)."""
        return self.auth_method == "api_key"

    def to_dict(self) -> dict:
        """Convert to dictionary for logging/serialization."""
        return {
            "user_id": self.user_id,
            "email": self.email,
            "display_name": self.display_name,
            "groups": self.groups,
            "auth_method": self.auth_method,
            "api_key_id": str(self.api_key_id) if self.api_key_id else None,
            "is_admin": self.is_admin,
            "is_service_account": self.is_service_account,
        }


@dataclass
class APIKey:
    """API key for service account authentication."""

    id: UUID = field(default_factory=uuid4)
    name: str = ""  # Human-readable name (e.g., "dbt-production")
    description: Optional[str] = None

    # The actual key (only shown once on creation)
    key_hash: str = ""  # SHA-256 hash of the key
    key_prefix: str = ""  # First 12 chars for identification (e.g., "lac_abc12345")

    # Associated identity
    service_account_id: str = ""  # Username for this service account
    groups: list[str] = field(default_factory=list)  # Groups/roles

    # Metadata
    created_at: datetime = field(default_factory=_utc_now)
    created_by: str = ""  # Admin who created it
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None

    # Status
    is_active: bool = True
    revoked_at: Optional[datetime] = None
    revoked_by: Optional[str] = None

    @property
    def is_expired(self) -> bool:
        """Check if the key has expired."""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at

    @property
    def is_valid(self) -> bool:
        """Check if the key is valid (active and not expired)."""
        return self.is_active and not self.is_expired

    @classmethod
    def generate_key(cls) -> tuple[str, str, str]:
        """Generate a new API key.

        Returns:
            Tuple of (full_key, key_hash, key_prefix)
        """
        import hashlib

        # Generate a secure random key
        raw_key = secrets.token_urlsafe(32)
        full_key = f"lac_{raw_key}"

        # Hash with SHA-256 for storage
        key_hash = hashlib.sha256(full_key.encode()).hexdigest()

        # Prefix for identification
        key_prefix = full_key[:12]

        return full_key, key_hash, key_prefix

    @classmethod
    def verify_key(cls, provided_key: str, stored_hash: str) -> bool:
        """Verify an API key against stored hash."""
        import hashlib

        provided_hash = hashlib.sha256(provided_key.encode()).hexdigest()
        return secrets.compare_digest(provided_hash, stored_hash)

    def to_dict(self, include_sensitive: bool = False) -> dict:
        """Convert to dictionary."""
        result = {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "key_prefix": self.key_prefix,
            "service_account_id": self.service_account_id,
            "groups": self.groups,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "last_used_at": (
                self.last_used_at.isoformat() if self.last_used_at else None
            ),
            "is_active": self.is_active,
            "is_expired": self.is_expired,
            "is_valid": self.is_valid,
        }
        if include_sensitive:
            result["key_hash"] = self.key_hash
        return result
