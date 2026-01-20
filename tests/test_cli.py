"""Tests for Lacuna CLI."""

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from lacuna.cli import cli
from lacuna.models.classification import Classification, DataTier


class TestCLIHelp:
    """Tests for CLI help and version commands."""

    def test_cli_help(self) -> None:
        """Test CLI help output."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "Lacuna" in result.output
        assert "classify" in result.output
        assert "evaluate" in result.output
        assert "audit" in result.output
        assert "lineage" in result.output

    def test_cli_version(self) -> None:
        """Test CLI version output."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])

        assert result.exit_code == 0
        assert "lacuna" in result.output.lower()

    def test_cli_debug_flag(self) -> None:
        """Test CLI debug flag."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--debug", "--help"])

        assert result.exit_code == 0


class TestClassifyCommand:
    """Tests for classify command."""

    @patch("lacuna.engine.governance.GovernanceEngine")
    def test_classify_basic(self, mock_engine_class) -> None:
        """Test basic classify command."""
        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine

        mock_classification = Classification(
            tier=DataTier.PROPRIETARY,
            confidence=0.95,
            reasoning="Contains customer data",
            tags=["PII"],
            classifier_name="heuristic",
        )
        mock_engine.classify.return_value = mock_classification

        runner = CliRunner()
        result = runner.invoke(cli, ["classify", "customer data query"])

        assert result.exit_code == 0
        assert "PROPRIETARY" in result.output
        mock_engine.stop.assert_called_once()

    @patch("lacuna.engine.governance.GovernanceEngine")
    def test_classify_json_output(self, mock_engine_class) -> None:
        """Test classify command with JSON output."""
        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine

        mock_classification = Classification(
            tier=DataTier.PUBLIC,
            confidence=0.8,
            reasoning="No sensitive data",
            tags=[],
            classifier_name="heuristic",
        )
        mock_engine.classify.return_value = mock_classification

        runner = CliRunner()
        result = runner.invoke(cli, ["classify", "-j", "public query"])

        assert result.exit_code == 0
        # Verify JSON output
        output = json.loads(result.output)
        assert output["tier"] == "PUBLIC"

    @patch("lacuna.engine.governance.GovernanceEngine")
    def test_classify_with_project(self, mock_engine_class) -> None:
        """Test classify command with project context."""
        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine

        mock_classification = Classification(
            tier=DataTier.INTERNAL,
            confidence=0.9,
            reasoning="Project data",
            tags=[],
            classifier_name="heuristic",
        )
        mock_engine.classify.return_value = mock_classification

        runner = CliRunner()
        result = runner.invoke(
            cli, ["classify", "--project", "analytics", "--user", "test-user", "query"]
        )

        assert result.exit_code == 0
        # Verify classify was called
        mock_engine.classify.assert_called_once()

    @patch("lacuna.engine.governance.GovernanceEngine")
    def test_classify_error_handling(self, mock_engine_class) -> None:
        """Test classify command error handling."""
        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine
        mock_engine.classify.side_effect = Exception("Classification failed")

        runner = CliRunner()
        result = runner.invoke(cli, ["classify", "test query"])

        assert result.exit_code == 1
        assert "Error" in result.output


class TestEvaluateCommand:
    """Tests for evaluate command."""

    @patch("lacuna.engine.governance.GovernanceEngine")
    def test_evaluate_allowed(self, mock_engine_class) -> None:
        """Test evaluate command when operation is allowed."""
        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine

        mock_result = MagicMock()
        mock_result.allowed = True
        mock_result.tier = "PUBLIC"
        mock_result.reasoning = "Operation allowed"
        mock_result.tags = []
        mock_result.alternatives = []
        mock_result.matched_rules = []
        mock_result.total_latency_ms = 10.5
        mock_result.to_dict.return_value = {"allowed": True}

        mock_engine.evaluate_export.return_value = mock_result

        runner = CliRunner()
        result = runner.invoke(cli, ["evaluate", "source.csv", "dest.csv"])

        assert result.exit_code == 0
        assert "Allowed" in result.output

    @patch("lacuna.engine.governance.GovernanceEngine")
    def test_evaluate_denied(self, mock_engine_class) -> None:
        """Test evaluate command when operation is denied."""
        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine

        mock_result = MagicMock()
        mock_result.allowed = False
        mock_result.tier = "PROPRIETARY"
        mock_result.reasoning = "Cannot export to unmanaged location"
        mock_result.tags = ["PII"]
        mock_result.alternatives = ["Use anonymized version"]
        mock_result.matched_rules = ["export-policy"]
        mock_result.total_latency_ms = 15.0

        mock_engine.evaluate_export.return_value = mock_result

        runner = CliRunner()
        result = runner.invoke(
            cli, ["evaluate", "sensitive.csv", "~/Downloads/export.csv"]
        )

        assert result.exit_code == 0
        assert "Denied" in result.output

    @patch("lacuna.engine.governance.GovernanceEngine")
    def test_evaluate_json_output(self, mock_engine_class) -> None:
        """Test evaluate command with JSON output."""
        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine

        mock_result = MagicMock()
        mock_result.allowed = True
        mock_result.to_dict.return_value = {"allowed": True, "tier": "PUBLIC"}

        mock_engine.evaluate_export.return_value = mock_result

        runner = CliRunner()
        result = runner.invoke(cli, ["evaluate", "-j", "source.csv", "dest.csv"])

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["allowed"] is True


class TestAuditCommands:
    """Tests for audit subcommands."""

    @patch("lacuna.audit.logger.AuditLogger")
    def test_audit_verify_success(self, mock_logger_class) -> None:
        """Test audit verify command success case."""
        mock_logger = MagicMock()
        mock_logger_class.return_value = mock_logger

        mock_logger.verify_integrity.return_value = {
            "verified": True,
            "records_checked": 100,
            "message": "All records verified",
        }

        runner = CliRunner()
        result = runner.invoke(cli, ["audit", "verify"])

        assert result.exit_code == 0
        assert "Verified" in result.output

    @patch("lacuna.audit.logger.AuditLogger")
    def test_audit_verify_failure(self, mock_logger_class) -> None:
        """Test audit verify command failure case."""
        mock_logger = MagicMock()
        mock_logger_class.return_value = mock_logger

        mock_logger.verify_integrity.return_value = {
            "verified": False,
            "records_checked": 50,
            "message": "Hash mismatch detected",
            "errors": [{"event_id": "123", "error": "Hash mismatch"}],
        }

        runner = CliRunner()
        result = runner.invoke(cli, ["audit", "verify"])

        assert result.exit_code == 0
        assert "Failed" in result.output

    @patch("lacuna.audit.logger.AuditLogger")
    def test_audit_verify_with_time_range(self, mock_logger_class) -> None:
        """Test audit verify with time range."""
        mock_logger = MagicMock()
        mock_logger_class.return_value = mock_logger

        mock_logger.verify_integrity.return_value = {
            "verified": True,
            "records_checked": 10,
            "message": "OK",
        }

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "audit",
                "verify",
                "--start",
                "2025-01-01T00:00:00",
                "--end",
                "2025-01-19T00:00:00",
            ],
        )

        assert result.exit_code == 0

    @patch("lacuna.audit.logger.AuditLogger")
    def test_audit_query(self, mock_logger_class) -> None:
        """Test audit query command."""
        mock_logger = MagicMock()
        mock_backend = MagicMock()
        mock_logger._backend = mock_backend
        mock_logger_class.return_value = mock_logger

        # Create mock records
        mock_record = MagicMock()
        mock_record.timestamp.strftime.return_value = "2025-01-19 12:00:00"
        mock_record.user_id = "test-user"
        mock_record.event_type.value = "data.access"
        mock_record.action_result = "success"
        mock_record.to_dict.return_value = {}

        mock_backend.query.return_value = [mock_record]

        runner = CliRunner()
        result = runner.invoke(cli, ["audit", "query", "--user", "test-user"])

        assert result.exit_code == 0


class TestLineageCommands:
    """Tests for lineage subcommands."""

    @patch("lacuna.lineage.tracker.LineageTracker")
    def test_lineage_show(self, mock_tracker_class) -> None:
        """Test lineage show command."""
        mock_tracker = MagicMock()
        mock_tracker_class.return_value = mock_tracker

        mock_graph = MagicMock()
        mock_graph.to_dict.return_value = {"nodes": [], "edges": []}
        mock_tracker.get_lineage.return_value = mock_graph
        mock_tracker.to_graph.return_value = "Lineage Graph:\n  customers.csv"
        mock_tracker.get_upstream.return_value = ["source.csv"]
        mock_tracker.get_downstream.return_value = ["analysis.csv"]

        runner = CliRunner()
        result = runner.invoke(cli, ["lineage", "show", "customers.csv"])

        assert result.exit_code == 0
        assert "customers.csv" in result.output

    @patch("lacuna.lineage.tracker.LineageTracker")
    def test_lineage_impact(self, mock_tracker_class) -> None:
        """Test lineage impact command."""
        mock_tracker = MagicMock()
        mock_tracker_class.return_value = mock_tracker

        mock_tracker.get_impact_analysis.return_value = {
            "downstream_count": 5,
            "downstream_artifacts": ["a.csv", "b.csv", "c.csv"],
            "by_depth": {1: ["a.csv"], 2: ["b.csv", "c.csv"]},
        }

        runner = CliRunner()
        result = runner.invoke(cli, ["lineage", "impact", "source.csv"])

        assert result.exit_code == 0
        assert "5" in result.output or "Impact" in result.output


class TestConfigCommand:
    """Tests for config command."""

    @patch("lacuna.config.get_settings")
    def test_config_display(self, mock_get_settings) -> None:
        """Test config display command."""
        mock_settings = MagicMock()
        mock_settings.environment = "test"
        mock_settings.debug = True
        mock_settings.database.url = "postgresql://test@localhost/test"
        mock_settings.redis.url = "redis://localhost:6379"
        mock_settings.classification.strategy = "hybrid"
        mock_settings.classification.heuristic_enabled = True
        mock_settings.classification.embedding_enabled = False
        mock_settings.classification.llm_enabled = False
        mock_settings.policy.enabled = True
        mock_settings.audit.enabled = True
        mock_settings.lineage.enabled = True

        mock_get_settings.return_value = mock_settings

        runner = CliRunner()
        result = runner.invoke(cli, ["config"])

        assert result.exit_code == 0
        assert "test" in result.output


class TestStatsCommand:
    """Tests for stats command."""

    @patch("lacuna.engine.governance.GovernanceEngine")
    def test_stats_display(self, mock_engine_class) -> None:
        """Test stats display command."""
        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine

        mock_engine.get_stats.return_value = {
            "classifier": {"classifications_count": 100},
            "policy_engine": {"evaluations_count": 50},
            "lineage_tracker": {"edges_count": 200},
        }

        runner = CliRunner()
        result = runner.invoke(cli, ["stats"])

        assert result.exit_code == 0
        assert "Statistics" in result.output


class TestMigrateCommand:
    """Tests for migrate command."""

    def test_migrate_command(self) -> None:
        """Test migrate command."""
        runner = CliRunner()
        result = runner.invoke(cli, ["migrate"])

        assert result.exit_code == 0
        # Currently just shows a message
        assert "alembic" in result.output.lower()


class TestServeCommand:
    """Tests for serve command."""

    @patch("uvicorn.run")
    def test_serve_command(self, mock_uvicorn_run) -> None:
        """Test serve command."""
        runner = CliRunner()
        _result = runner.invoke(
            cli, ["serve", "--port", "8001"], catch_exceptions=False
        )

        # The command should try to start the server
        mock_uvicorn_run.assert_called_once()
        call_kwargs = mock_uvicorn_run.call_args[1]
        assert call_kwargs["port"] == 8001
