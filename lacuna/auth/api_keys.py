"""API key storage and management."""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

import structlog

from lacuna.auth.models import APIKey

logger = structlog.get_logger()


class APIKeyStore:
    """In-memory API key store.

    In production, this would be backed by the database.
    For dev mode, uses in-memory storage.
    """

    _instance: Optional["APIKeyStore"] = None
    _keys: dict[UUID, APIKey]  # id -> APIKey
    _hash_index: dict[str, UUID]  # key_hash -> id

    def __new__(cls) -> "APIKeyStore":
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._keys = {}
            cls._instance._hash_index = {}
        return cls._instance

    def create(
        self,
        name: str,
        service_account_id: str,
        created_by: str,
        description: Optional[str] = None,
        groups: Optional[list[str]] = None,
        expires_at: Optional[datetime] = None,
    ) -> tuple[APIKey, str]:
        """Create a new API key.

        Returns:
            Tuple of (APIKey, raw_key). The raw_key is only returned once!
        """
        # Generate the key
        raw_key, key_hash, key_prefix = APIKey.generate_key()

        # Create the API key object
        api_key = APIKey(
            name=name,
            description=description,
            key_hash=key_hash,
            key_prefix=key_prefix,
            service_account_id=service_account_id,
            groups=groups or [],
            created_by=created_by,
            expires_at=expires_at,
        )

        # Store it
        self._keys[api_key.id] = api_key
        self._hash_index[key_hash] = api_key.id

        logger.info(
            "api_key_created",
            key_id=str(api_key.id),
            name=name,
            service_account_id=service_account_id,
            created_by=created_by,
        )

        return api_key, raw_key

    def get(self, key_id: UUID) -> Optional[APIKey]:
        """Get an API key by ID."""
        return self._keys.get(key_id)

    def get_by_raw_key(self, raw_key: str) -> Optional[APIKey]:
        """Get an API key by the raw key value."""
        import hashlib

        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        key_id = self._hash_index.get(key_hash)
        if key_id is None:
            return None
        return self._keys.get(key_id)

    def list_all(self) -> list[APIKey]:
        """List all API keys (without sensitive data)."""
        return list(self._keys.values())

    def list_active(self) -> list[APIKey]:
        """List only active, non-expired API keys."""
        return [k for k in self._keys.values() if k.is_valid]

    def revoke(self, key_id: UUID, revoked_by: str) -> bool:
        """Revoke an API key."""
        api_key = self._keys.get(key_id)
        if api_key is None:
            return False

        api_key.is_active = False
        api_key.revoked_at = datetime.now(timezone.utc)
        api_key.revoked_by = revoked_by

        logger.info(
            "api_key_revoked",
            key_id=str(key_id),
            revoked_by=revoked_by,
        )

        return True

    def delete(self, key_id: UUID) -> bool:
        """Permanently delete an API key."""
        api_key = self._keys.pop(key_id, None)
        if api_key is None:
            return False

        # Remove from hash index
        self._hash_index.pop(api_key.key_hash, None)

        logger.info("api_key_deleted", key_id=str(key_id))
        return True

    def update_last_used(self, key_id: UUID) -> None:
        """Update the last_used_at timestamp."""
        api_key = self._keys.get(key_id)
        if api_key:
            api_key.last_used_at = datetime.now(timezone.utc)

    def clear(self) -> None:
        """Clear all API keys (for testing)."""
        self._keys.clear()
        self._hash_index.clear()


def get_api_key_store() -> APIKeyStore:
    """Get the API key store instance."""
    return APIKeyStore()
