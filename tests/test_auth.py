"""Tests for authentication module."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi import Request

from lacuna.auth.api_keys import APIKeyStore
from lacuna.auth.models import APIKey, AuthenticatedUser


class TestAuthenticatedUser:
    """Tests for AuthenticatedUser model."""

    def test_create_user(self):
        """Test basic user creation."""
        user = AuthenticatedUser(
            user_id="test-user",
            email="test@example.com",
            groups=["group1", "group2"],
            display_name="Test User",
        )

        assert user.user_id == "test-user"
        assert user.email == "test@example.com"
        assert user.groups == ["group1", "group2"]
        assert user.display_name == "Test User"
        assert user.auth_method == "proxy"
        assert user.api_key_id is None

    def test_is_admin_with_admin_group(self):
        """Test admin detection with default group."""
        user = AuthenticatedUser(
            user_id="admin-user",
            groups=["lacuna-admins", "other-group"],
        )

        assert user.is_admin is True

    def test_is_admin_without_admin_group(self):
        """Test non-admin user."""
        user = AuthenticatedUser(
            user_id="regular-user",
            groups=["users", "developers"],
        )

        assert user.is_admin is False

    def test_is_service_account_proxy(self):
        """Test service account detection for proxy auth."""
        user = AuthenticatedUser(
            user_id="human-user",
            auth_method="proxy",
        )

        assert user.is_service_account is False

    def test_is_service_account_api_key(self):
        """Test service account detection for API key auth."""
        user = AuthenticatedUser(
            user_id="svc-dbt",
            auth_method="api_key",
            api_key_id=uuid4(),
        )

        assert user.is_service_account is True

    def test_to_dict(self):
        """Test conversion to dictionary."""
        user = AuthenticatedUser(
            user_id="test-user",
            email="test@example.com",
            groups=["group1"],
        )

        data = user.to_dict()

        assert data["user_id"] == "test-user"
        assert data["email"] == "test@example.com"
        assert data["groups"] == ["group1"]
        assert "is_admin" in data


class TestAPIKey:
    """Tests for APIKey model."""

    def test_generate_key(self):
        """Test API key generation."""
        full_key, key_hash, key_prefix = APIKey.generate_key()

        assert full_key.startswith("lac_")
        assert len(full_key) > 40
        assert len(key_hash) == 64  # SHA-256 hex
        assert key_prefix.startswith("lac_")
        assert len(key_prefix) == 12

    def test_verify_key_success(self):
        """Test successful key verification."""
        full_key, key_hash, _ = APIKey.generate_key()

        assert APIKey.verify_key(full_key, key_hash) is True

    def test_verify_key_failure(self):
        """Test failed key verification."""
        _, key_hash, _ = APIKey.generate_key()

        assert APIKey.verify_key("lac_wrongkey", key_hash) is False

    def test_is_valid_active_key(self):
        """Test is_valid for active key without expiry."""
        api_key = APIKey(
            name="test-key",
            service_account_id="svc-test",
            is_active=True,
        )

        assert api_key.is_active is True
        assert api_key.is_expired is False
        assert api_key.is_valid is True

    def test_is_valid_revoked_key(self):
        """Test is_valid for revoked key."""
        api_key = APIKey(
            name="test-key",
            service_account_id="svc-test",
            is_active=False,
        )

        assert api_key.is_active is False
        assert api_key.is_valid is False

    def test_is_valid_expired_key(self):
        """Test is_valid for expired key."""
        api_key = APIKey(
            name="test-key",
            service_account_id="svc-test",
            is_active=True,
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )

        assert api_key.is_expired is True
        assert api_key.is_valid is False

    def test_to_dict(self):
        """Test conversion to dictionary."""
        api_key = APIKey(
            name="test-key",
            service_account_id="svc-test",
            groups=["group1"],
        )

        data = api_key.to_dict()

        assert data["name"] == "test-key"
        assert data["service_account_id"] == "svc-test"
        assert data["groups"] == ["group1"]
        assert "key_hash" not in data  # Sensitive data excluded by default


class TestAPIKeyStore:
    """Tests for API key store."""

    def setup_method(self):
        """Clear store before each test."""
        store = APIKeyStore()
        store.clear()

    def test_create_and_get_key(self):
        """Test creating and retrieving an API key."""
        store = APIKeyStore()

        api_key, raw_key = store.create(
            name="test-key",
            service_account_id="svc-test",
            created_by="admin",
        )

        assert raw_key.startswith("lac_")
        assert api_key.name == "test-key"

        retrieved = store.get(api_key.id)

        assert retrieved is not None
        assert retrieved.id == api_key.id
        assert retrieved.name == "test-key"

    def test_get_by_raw_key(self):
        """Test retrieving key by raw key value."""
        store = APIKeyStore()

        api_key, raw_key = store.create(
            name="test-key",
            service_account_id="svc-test",
            created_by="admin",
        )

        retrieved = store.get_by_raw_key(raw_key)

        assert retrieved is not None
        assert retrieved.id == api_key.id
        assert retrieved.service_account_id == "svc-test"

    def test_get_by_raw_key_not_found(self):
        """Test retrieving non-existent key."""
        store = APIKeyStore()

        result = store.get_by_raw_key("lac_nonexistent")

        assert result is None

    def test_revoke_key(self):
        """Test revoking an API key."""
        store = APIKeyStore()

        api_key, _ = store.create(
            name="test-key",
            service_account_id="svc-test",
            created_by="admin",
        )

        assert store.revoke(api_key.id, revoked_by="admin") is True

        retrieved = store.get(api_key.id)
        assert retrieved is not None
        assert retrieved.is_active is False
        assert retrieved.is_valid is False

    def test_delete_key(self):
        """Test deleting an API key."""
        store = APIKeyStore()

        api_key, _ = store.create(
            name="test-key",
            service_account_id="svc-test",
            created_by="admin",
        )

        assert store.delete(api_key.id) is True
        assert store.get(api_key.id) is None

    def test_list_all_keys(self):
        """Test listing all keys."""
        store = APIKeyStore()
        store.clear()

        store.create(name="key1", service_account_id="svc1", created_by="admin")
        store.create(name="key2", service_account_id="svc2", created_by="admin")

        keys = store.list_all()

        assert len(keys) == 2

    def test_update_last_used(self):
        """Test updating last used timestamp."""
        store = APIKeyStore()

        api_key, _ = store.create(
            name="test-key",
            service_account_id="svc-test",
            created_by="admin",
        )

        assert api_key.last_used_at is None

        store.update_last_used(api_key.id)

        updated = store.get(api_key.id)
        assert updated is not None
        assert updated.last_used_at is not None


class TestDevModeAuth:
    """Tests for authentication in dev mode."""

    def test_dev_user_creation(self):
        """Test that dev mode user has admin privileges."""
        from lacuna.auth.dependencies import _get_dev_user

        user = _get_dev_user()

        assert user.user_id == "dev-user"
        assert user.email == "dev@localhost"
        assert "lacuna-admins" in user.groups
        assert user.is_admin is True
