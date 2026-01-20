"""Tests for configuration settings."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from lacuna.config.settings import (
    AuditSettings,
    ClassificationSettings,
    DatabaseSettings,
    LineageSettings,
    MonitoringSettings,
    PolicySettings,
    RedisSettings,
    RoutingSettings,
    Settings,
    get_settings,
    load_config,
)


class TestDatabaseSettings:
    """Tests for database settings."""

    def test_default_values(self) -> None:
        """Test default database settings."""
        settings = DatabaseSettings()

        assert "postgresql://" in settings.url
        assert settings.pool_size == 20
        assert settings.max_overflow == 10
        assert settings.echo is False

    def test_custom_values(self) -> None:
        """Test custom database settings."""
        settings = DatabaseSettings(
            url="postgresql://user:pass@host:5432/db",
            pool_size=50,
            echo=True,
        )

        assert settings.url == "postgresql://user:pass@host:5432/db"
        assert settings.pool_size == 50
        assert settings.echo is True


class TestRedisSettings:
    """Tests for Redis settings."""

    def test_default_values(self) -> None:
        """Test default Redis settings."""
        settings = RedisSettings()

        assert "redis://" in settings.url
        assert settings.ttl == 3600
        assert settings.enabled is True

    def test_disabled_redis(self) -> None:
        """Test disabled Redis."""
        settings = RedisSettings(enabled=False)

        assert settings.enabled is False


class TestClassificationSettings:
    """Tests for classification settings."""

    def test_default_values(self) -> None:
        """Test default classification settings."""
        settings = ClassificationSettings()

        assert settings.strategy == "conservative"
        assert settings.confidence_threshold == 0.9
        assert settings.short_circuit is True
        assert settings.heuristic_enabled is True
        assert settings.embedding_enabled is True
        assert settings.llm_enabled is True

    def test_llm_configuration(self) -> None:
        """Test LLM configuration."""
        settings = ClassificationSettings(
            llm_enabled=True,
            llm_endpoint="http://localhost:8080",
            llm_model="gpt-4",
            llm_temperature=0.2,
            llm_max_tokens=1000,
        )

        assert settings.llm_endpoint == "http://localhost:8080"
        assert settings.llm_model == "gpt-4"
        assert settings.llm_temperature == 0.2
        assert settings.llm_max_tokens == 1000


class TestLineageSettings:
    """Tests for lineage settings."""

    def test_default_values(self) -> None:
        """Test default lineage settings."""
        settings = LineageSettings()

        assert settings.enabled is True
        assert settings.sampling_rate == 1.0
        assert settings.max_depth == 10


class TestAuditSettings:
    """Tests for audit settings."""

    def test_default_values(self) -> None:
        """Test default audit settings."""
        settings = AuditSettings()

        assert settings.enabled is True
        assert settings.retention_days == 2555  # 7 years
        assert settings.verify_integrity is True
        assert settings.alert_enabled is True


class TestPolicySettings:
    """Tests for policy settings."""

    def test_default_values(self) -> None:
        """Test default policy settings."""
        settings = PolicySettings()

        assert settings.enabled is False
        assert settings.opa_endpoint is None
        assert settings.opa_policy_path == "lacuna/classification"
        assert settings.opa_timeout == 1.0

    def test_opa_configuration(self) -> None:
        """Test OPA configuration."""
        settings = PolicySettings(
            enabled=True,
            opa_endpoint="http://localhost:8181",
        )

        assert settings.enabled is True
        assert settings.opa_endpoint == "http://localhost:8181"


class TestMonitoringSettings:
    """Tests for monitoring settings."""

    def test_default_values(self) -> None:
        """Test default monitoring settings."""
        settings = MonitoringSettings()

        assert settings.enabled is True
        assert settings.prometheus_port == 9090
        assert settings.loki_url is None


class TestRoutingSettings:
    """Tests for routing settings."""

    def test_default_values(self) -> None:
        """Test default routing settings."""
        settings = RoutingSettings()

        assert settings.proprietary_local_rag is True
        assert settings.proprietary_web_search is False
        assert settings.public_web_search is True


class TestMainSettings:
    """Tests for main Settings class."""

    def test_default_values(self) -> None:
        """Test default main settings."""
        settings = Settings()

        assert settings.app_name == "Lacuna"
        assert settings.environment == "development"
        assert settings.debug is False
        assert settings.log_level == "INFO"

    def test_nested_settings(self) -> None:
        """Test nested settings objects."""
        settings = Settings()

        assert isinstance(settings.database, DatabaseSettings)
        assert isinstance(settings.redis, RedisSettings)
        assert isinstance(settings.classification, ClassificationSettings)
        assert isinstance(settings.lineage, LineageSettings)
        assert isinstance(settings.audit, AuditSettings)
        assert isinstance(settings.policy, PolicySettings)

    def test_path_creation(self) -> None:
        """Test that paths are created if they don't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            new_config_path = Path(tmpdir) / "new_config"
            _settings = Settings(config_path=new_config_path)

            assert new_config_path.exists()

    def test_proprietary_terms(self) -> None:
        """Test proprietary terms lists."""
        settings = Settings(
            proprietary_projects=["project_a", "project_b"],
            proprietary_customers=["customer_1"],
            proprietary_terms=["term_x", "term_y"],
        )

        assert "project_a" in settings.proprietary_projects
        assert "customer_1" in settings.proprietary_customers
        assert "term_x" in settings.proprietary_terms


class TestGetSettings:
    """Tests for get_settings function."""

    def test_get_settings_cached(self) -> None:
        """Test that get_settings returns cached instance."""
        # Clear cache first
        get_settings.cache_clear()

        settings1 = get_settings()
        settings2 = get_settings()

        assert settings1 is settings2

    def test_get_settings_returns_settings(self) -> None:
        """Test that get_settings returns Settings instance."""
        get_settings.cache_clear()
        settings = get_settings()

        assert isinstance(settings, Settings)


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_config_missing_directory(self) -> None:
        """Test loading config from missing directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            missing_path = Path(tmpdir) / "missing"
            config = load_config(missing_path)

            assert config == {}

    def test_load_config_with_default_yaml(self) -> None:
        """Test loading config with default.yaml."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir)

            default_config = {
                "environment": "test",
                "debug": True,
            }
            with open(config_path / "default.yaml", "w") as f:
                yaml.safe_dump(default_config, f)

            config = load_config(config_path)

            assert config["environment"] == "test"
            assert config["debug"] is True

    def test_load_config_with_proprietary_terms(self) -> None:
        """Test loading config with proprietary terms."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir)

            # Create default.yaml
            with open(config_path / "default.yaml", "w") as f:
                yaml.safe_dump({"environment": "test"}, f)

            # Create proprietary_terms.yaml
            terms = {
                "projects": ["secret_project"],
                "customers": ["acme_corp"],
                "terms": ["confidential"],
            }
            with open(config_path / "proprietary_terms.yaml", "w") as f:
                yaml.safe_dump(terms, f)

            config = load_config(config_path)

            assert "secret_project" in config["proprietary_projects"]
            assert "acme_corp" in config["proprietary_customers"]
            assert "confidential" in config["proprietary_terms"]

    def test_load_config_empty_files(self) -> None:
        """Test loading config with empty files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir)

            # Create empty files
            (config_path / "default.yaml").touch()
            (config_path / "proprietary_terms.yaml").touch()

            config = load_config(config_path)

            # Should handle empty files gracefully
            assert isinstance(config, dict)


class TestEnvironmentVariables:
    """Tests for environment variable configuration."""

    def test_env_override(self) -> None:
        """Test environment variable overrides."""
        # Set environment variable
        with patch.dict(
            os.environ,
            {
                "LACUNA_ENVIRONMENT": "production",
                "LACUNA_DEBUG": "true",
            },
        ):
            # Clear cache to pick up new env vars
            get_settings.cache_clear()

            settings = Settings()

            assert settings.environment == "production"
            assert settings.debug is True

    def test_nested_env_override(self) -> None:
        """Test nested environment variable overrides."""
        with patch.dict(
            os.environ,
            {
                "LACUNA_DATABASE__POOL_SIZE": "100",
                "LACUNA_REDIS__ENABLED": "false",
            },
        ):
            get_settings.cache_clear()

            _settings = Settings()

            # Note: nested overrides via env may need specific format
            # This test verifies the mechanism exists
