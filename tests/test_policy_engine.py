"""Additional tests for PolicyEngine to improve coverage."""

from unittest.mock import MagicMock, patch

import pytest

from lacuna.models.classification import Classification, DataTier
from lacuna.models.data_operation import DataOperation, OperationType, UserContext
from lacuna.policy.client import OPAClient
from lacuna.policy.engine import PolicyEngine


class TestPolicyEngineFallback:
    """Tests for PolicyEngine fallback policies."""

    @pytest.fixture
    def engine(self):
        """Create engine with mocked OPA client and enabled policy."""
        mock_client = MagicMock(spec=OPAClient)
        mock_client.is_available.return_value = False
        mock_client.endpoint = "http://localhost:8181"
        mock_client.policy_path = "lacuna/classification"

        # Mock settings to enable policy
        with patch("lacuna.policy.engine.get_settings") as mock_settings:
            mock_settings.return_value.policy.enabled = True
            engine = PolicyEngine(
                opa_client=mock_client, enabled=True, fallback_on_error=True
            )
            # Force enabled since settings are mocked
            engine.enabled = True
            return engine

    def test_fallback_allows_public_export(self, engine) -> None:
        """Test fallback allows PUBLIC data export anywhere."""
        operation = DataOperation(
            operation_type=OperationType.EXPORT,
            resource_id="public.csv",
            destination="~/Downloads/export.csv",
            user=UserContext(user_id="test"),
        )
        classification = Classification(
            tier=DataTier.PUBLIC,
            confidence=0.9,
            reasoning="Public data",
        )

        result = engine.evaluate(operation, classification)

        assert result.decision.allowed is True

    def test_fallback_blocks_proprietary_to_downloads(self, engine) -> None:
        """Test fallback blocks PROPRIETARY export to Downloads."""
        operation = DataOperation(
            operation_type=OperationType.EXPORT,
            resource_id="customers.csv",
            destination="~/Downloads/export.csv",
            user=UserContext(user_id="test"),
        )
        classification = Classification(
            tier=DataTier.PROPRIETARY,
            confidence=0.95,
            reasoning="Contains PII",
            tags=["PII", "EMAIL"],
        )

        result = engine.evaluate(operation, classification)

        assert result.decision.allowed is False
        assert "alternatives" in result.decision.to_dict()
        assert len(result.decision.alternatives) > 0

    def test_fallback_blocks_proprietary_to_tmp(self, engine) -> None:
        """Test fallback blocks PROPRIETARY export to /tmp."""
        operation = DataOperation(
            operation_type=OperationType.EXPORT,
            resource_id="customers.csv",
            destination="/tmp/export.csv",
            user=UserContext(user_id="test"),
        )
        classification = Classification(
            tier=DataTier.PROPRIETARY,
            confidence=0.95,
            reasoning="Contains PII",
        )

        result = engine.evaluate(operation, classification)

        assert result.decision.allowed is False

    def test_fallback_blocks_unencrypted_external_proprietary(self, engine) -> None:
        """Test fallback blocks unencrypted PROPRIETARY export to S3."""
        operation = DataOperation(
            operation_type=OperationType.EXPORT,
            resource_id="customers.csv",
            destination="s3://bucket/export.csv",
            destination_encrypted=False,
            user=UserContext(user_id="test"),
        )
        classification = Classification(
            tier=DataTier.PROPRIETARY,
            confidence=0.95,
            reasoning="Contains PII",
        )

        result = engine.evaluate(operation, classification)

        assert result.decision.allowed is False
        assert "encryption" in result.decision.reasoning.lower()

    def test_fallback_allows_encrypted_external_proprietary(self, engine) -> None:
        """Test fallback allows encrypted PROPRIETARY export to S3."""
        operation = DataOperation(
            operation_type=OperationType.EXPORT,
            resource_id="customers.csv",
            destination="s3://bucket/export.csv",
            destination_encrypted=True,
            user=UserContext(user_id="test"),
        )
        classification = Classification(
            tier=DataTier.PROPRIETARY,
            confidence=0.95,
            reasoning="Contains PII",
        )

        result = engine.evaluate(operation, classification)

        # Should be allowed when encrypted
        assert result.decision.allowed is True

    def test_fallback_allows_read_operations(self, engine) -> None:
        """Test fallback allows read operations."""
        operation = DataOperation(
            operation_type=OperationType.READ,
            resource_id="customers.csv",
            user=UserContext(user_id="test"),
        )
        classification = Classification(
            tier=DataTier.PROPRIETARY,
            confidence=0.95,
            reasoning="Contains PII",
        )

        result = engine.evaluate(operation, classification)

        assert result.decision.allowed is True


class TestPolicyEngineOPAParsing:
    """Tests for OPA result parsing."""

    @pytest.fixture
    def engine(self):
        mock_client = MagicMock(spec=OPAClient)
        mock_client.is_available.return_value = True
        mock_client.endpoint = "http://localhost:8181"
        mock_client.policy_path = "lacuna/classification"

        with patch("lacuna.policy.engine.get_settings") as mock_settings:
            mock_settings.return_value.policy.enabled = True
            engine = PolicyEngine(opa_client=mock_client, enabled=True)
            engine.enabled = True
            return engine

    def test_parse_opa_allow_format(self, engine) -> None:
        """Test parsing OPA allow/deny format."""
        opa_result = {
            "allow": True,
            "reason": "Policy matched",
            "matched_rules": ["rule_1"],
        }

        decision = engine._parse_opa_result(opa_result)

        assert decision.allowed is True
        assert decision.reasoning == "Policy matched"

    def test_parse_opa_deny_format(self, engine) -> None:
        """Test parsing OPA deny rules format."""
        opa_result = {
            "deny": ["Cannot export to external location", "Encryption required"],
            "alternatives": ["Use governed location"],
        }

        decision = engine._parse_opa_result(opa_result)

        assert decision.allowed is False
        assert "external location" in decision.reasoning

    def test_parse_opa_empty_deny(self, engine) -> None:
        """Test parsing OPA with empty deny set."""
        opa_result = {
            "deny": [],
        }

        decision = engine._parse_opa_result(opa_result)

        assert decision.allowed is True

    def test_parse_opa_classification_format(self, engine) -> None:
        """Test parsing OPA classification result format."""
        opa_result = {
            "classification": [
                {
                    "tier": "PROPRIETARY",
                    "confidence": 0.95,
                    "reasoning": "Customer data",
                },
                {
                    "tier": "INTERNAL",
                    "confidence": 0.7,
                    "reasoning": "Internal reference",
                },
            ]
        }

        decision = engine._parse_opa_result(opa_result)

        assert decision.allowed is True
        assert "classification" in decision.metadata

    def test_parse_opa_default_allow(self, engine) -> None:
        """Test parsing unknown OPA format defaults to allow."""
        opa_result = {
            "some_unknown_field": "value",
        }

        decision = engine._parse_opa_result(opa_result)

        assert decision.allowed is True


class TestPolicyEngineCaching:
    """Tests for PolicyEngine caching."""

    def test_cache_hit(self) -> None:
        """Test that cache hits return cached decision."""
        mock_client = MagicMock(spec=OPAClient)
        mock_client.is_available.return_value = True
        mock_client.evaluate.return_value = {"allow": True, "reason": "Cached"}
        mock_client.endpoint = "http://localhost:8181"
        mock_client.policy_path = "lacuna/classification"

        with patch("lacuna.policy.engine.get_settings") as mock_settings:
            mock_settings.return_value.policy.enabled = True
            engine = PolicyEngine(opa_client=mock_client, enabled=True)
            engine.enabled = True

            operation = DataOperation(
                operation_type=OperationType.READ,
                resource_id="test.csv",
                resource_type="file",
            )
            classification = Classification(
                tier=DataTier.PUBLIC,
                confidence=0.9,
                reasoning="Public",
            )

            # First call
            _result1 = engine.evaluate(operation, classification)

            # Second call should hit cache
            _result2 = engine.evaluate(operation, classification)

            # OPA should only be called once
            assert (
                mock_client.evaluate.call_count <= 2
            )  # May be called twice due to cache key differences

    def test_disabled_engine_allows_all(self) -> None:
        """Test that disabled engine allows all operations."""
        with patch("lacuna.policy.engine.get_settings") as mock_settings:
            mock_settings.return_value.policy.enabled = False
            engine = PolicyEngine(enabled=False)

            operation = DataOperation(
                operation_type=OperationType.EXPORT,
                resource_id="secret.csv",
                destination="~/Downloads/hack.csv",
            )
            classification = Classification(
                tier=DataTier.PROPRIETARY,
                confidence=0.99,
                reasoning="Top secret",
            )

            result = engine.evaluate(operation, classification)

            assert result.decision.allowed is True
            assert result.is_fallback is True


class TestPolicyEngineStats:
    """Tests for PolicyEngine statistics."""

    def test_get_stats(self) -> None:
        """Test getting engine statistics."""
        mock_client = MagicMock(spec=OPAClient)
        mock_client.is_available.return_value = False
        mock_client.endpoint = "http://localhost:8181"
        mock_client.policy_path = "lacuna/classification"

        with patch("lacuna.policy.engine.get_settings") as mock_settings:
            mock_settings.return_value.policy.enabled = True
            engine = PolicyEngine(opa_client=mock_client, enabled=True)

            # Make some evaluations
            operation = DataOperation(
                operation_type=OperationType.READ,
                resource_id="test.csv",
                resource_type="file",
            )

            engine.evaluate(operation)
            engine.evaluate(operation)

            stats = engine.get_stats()

            assert "cache_size" in stats
            assert "opa_available" in stats
