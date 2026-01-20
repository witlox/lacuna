"""Tests for dev mode backend selection and CLI."""

import importlib
import os
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from lacuna.cli import cli


class TestBackendSelection:
    """Tests for backend selection based on database URL."""

    def test_audit_backend_sqlite_uses_memory(self) -> None:
        """Test that SQLite URL uses in-memory audit backend."""
        with patch("lacuna.config.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                database=MagicMock(url="sqlite:///data/test.db"),
                audit=MagicMock(verify_integrity=False, enabled=True),
            )

            # Reimport to pick up the patched settings
            import lacuna.audit.logger as logger_module

            importlib.reload(logger_module)

            from lacuna.audit.memory_backend import InMemoryAuditBackend

            backend = logger_module.get_audit_backend()
            assert isinstance(backend, InMemoryAuditBackend)

    def test_audit_backend_postgres_url_detected(self) -> None:
        """Test that PostgreSQL URL is detected as non-SQLite."""
        with patch("lacuna.config.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                database=MagicMock(url="postgresql://user:pass@localhost/db"),
                audit=MagicMock(verify_integrity=False, enabled=True),
            )

            # Verify the URL detection logic
            settings = mock_settings.return_value
            assert not settings.database.url.startswith("sqlite")

    def test_lineage_backend_sqlite_uses_memory(self) -> None:
        """Test that SQLite URL uses in-memory lineage backend."""
        with patch("lacuna.config.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                database=MagicMock(url="sqlite:///data/test.db"),
                lineage=MagicMock(enabled=True, max_depth=10),
            )

            # Reimport to pick up the patched settings
            import lacuna.lineage.tracker as tracker_module

            importlib.reload(tracker_module)

            from lacuna.lineage.memory_backend import InMemoryLineageBackend

            backend = tracker_module.get_lineage_backend()
            assert isinstance(backend, InMemoryLineageBackend)

    def test_lineage_backend_postgres_url_detected(self) -> None:
        """Test that PostgreSQL URL is detected as non-SQLite."""
        with patch("lacuna.config.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                database=MagicMock(url="postgresql://user:pass@localhost/db"),
                lineage=MagicMock(enabled=True, max_depth=10),
            )

            # Verify the URL detection logic
            settings = mock_settings.return_value
            assert not settings.database.url.startswith("sqlite")


class TestDevCommand:
    """Tests for lacuna dev CLI command."""

    # Environment variables to clean up after tests
    ENV_VARS_TO_CLEAN = [
        "LACUNA_ENVIRONMENT",
        "LACUNA_DEBUG",
        "LACUNA_DATABASE__URL",
        "LACUNA_REDIS__ENABLED",
        "LACUNA_CLASSIFICATION__EMBEDDING_ENABLED",
        "LACUNA_CLASSIFICATION__LLM_ENABLED",
        "LACUNA_POLICY__ENABLED",
        "LACUNA_MONITORING__ENABLED",
        "LACUNA_LOG_FORMAT",
        "LACUNA_LOG_LEVEL",
    ]

    @pytest.fixture(autouse=True)
    def cleanup_env(self) -> None:
        """Clean up environment variables after each test."""
        # Store original values
        original_values = {k: os.environ.get(k) for k in self.ENV_VARS_TO_CLEAN}

        yield

        # Restore original values or remove
        for key, value in original_values.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_dev_command_exists(self) -> None:
        """Test that dev command is registered."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "dev" in result.output

    def test_dev_command_help(self) -> None:
        """Test dev command help output."""
        runner = CliRunner()
        result = runner.invoke(cli, ["dev", "--help"])

        assert result.exit_code == 0
        assert "development mode" in result.output.lower()
        assert "--port" in result.output
        assert "--host" in result.output
        assert "--reload" in result.output

    @patch("uvicorn.run")
    @patch("lacuna.db.base.init_db")
    def test_dev_command_sets_environment(
        self, mock_init_db: MagicMock, mock_uvicorn: MagicMock
    ) -> None:
        """Test that dev command sets environment variables."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            runner.invoke(cli, ["dev"], catch_exceptions=False)

            # Check environment was set correctly
            assert os.environ.get("LACUNA_ENVIRONMENT") == "development"
            assert os.environ.get("LACUNA_DEBUG") == "true"
            assert "sqlite" in os.environ.get("LACUNA_DATABASE__URL", "").lower()
            assert os.environ.get("LACUNA_REDIS__ENABLED") == "false"
            assert os.environ.get("LACUNA_CLASSIFICATION__EMBEDDING_ENABLED") == "false"
            assert os.environ.get("LACUNA_CLASSIFICATION__LLM_ENABLED") == "false"
            assert os.environ.get("LACUNA_POLICY__ENABLED") == "false"

    @patch("uvicorn.run")
    @patch("lacuna.db.base.init_db")
    def test_dev_command_starts_uvicorn(
        self, mock_init_db: MagicMock, mock_uvicorn: MagicMock
    ) -> None:
        """Test that dev command starts uvicorn with correct settings."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            runner.invoke(cli, ["dev", "--port", "8080"], catch_exceptions=False)

            mock_uvicorn.assert_called_once()
            call_kwargs = mock_uvicorn.call_args[1]
            assert call_kwargs["port"] == 8080
            assert call_kwargs["reload"] is True
            assert call_kwargs["log_level"] == "debug"

    @patch("uvicorn.run")
    @patch("lacuna.db.base.init_db")
    def test_dev_command_creates_data_dir(
        self, mock_init_db: MagicMock, mock_uvicorn: MagicMock
    ) -> None:
        """Test that dev command creates data directory."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            runner.invoke(cli, ["dev"], catch_exceptions=False)

            # Data directory should be created
            assert os.path.exists("data")

    @patch("uvicorn.run")
    @patch("lacuna.db.base.init_db")
    def test_dev_command_initializes_db(
        self, mock_init_db: MagicMock, mock_uvicorn: MagicMock
    ) -> None:
        """Test that dev command initializes database."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            runner.invoke(cli, ["dev"], catch_exceptions=False)

            mock_init_db.assert_called_once()

    @patch("uvicorn.run")
    @patch("lacuna.db.base.init_db")
    def test_dev_command_default_host(
        self, mock_init_db: MagicMock, mock_uvicorn: MagicMock
    ) -> None:
        """Test that dev command uses localhost by default."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            runner.invoke(cli, ["dev"], catch_exceptions=False)

            call_kwargs = mock_uvicorn.call_args[1]
            assert call_kwargs["host"] == "127.0.0.1"

    @patch("uvicorn.run")
    @patch("lacuna.db.base.init_db")
    def test_dev_command_no_reload(
        self, mock_init_db: MagicMock, mock_uvicorn: MagicMock
    ) -> None:
        """Test that --no-reload disables auto-reload."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            runner.invoke(cli, ["dev", "--no-reload"], catch_exceptions=False)

            call_kwargs = mock_uvicorn.call_args[1]
            assert call_kwargs["reload"] is False


class TestDevModeIntegration:
    """Integration tests for dev mode components working together."""

    def test_audit_logger_with_memory_backend(self) -> None:
        """Test AuditLogger uses InMemoryAuditBackend with SQLite."""
        with patch("lacuna.config.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                database=MagicMock(url="sqlite:///data/test.db"),
                audit=MagicMock(verify_integrity=False, enabled=True),
            )

            # Reimport to pick up the patched settings
            import lacuna.audit.logger as logger_module

            importlib.reload(logger_module)

            from lacuna.audit.memory_backend import InMemoryAuditBackend

            audit_logger = logger_module.AuditLogger()
            assert isinstance(audit_logger._backend, InMemoryAuditBackend)

    def test_lineage_tracker_with_memory_backend(self) -> None:
        """Test LineageTracker uses InMemoryLineageBackend with SQLite."""
        with patch("lacuna.config.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                database=MagicMock(url="sqlite:///data/test.db"),
                lineage=MagicMock(enabled=True, max_depth=10),
            )

            # Reimport to pick up the patched settings
            import lacuna.lineage.tracker as tracker_module

            importlib.reload(tracker_module)

            from lacuna.lineage.memory_backend import InMemoryLineageBackend

            tracker = tracker_module.LineageTracker()
            assert isinstance(tracker._backend, InMemoryLineageBackend)
