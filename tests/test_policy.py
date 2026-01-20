"""Tests for policy engine."""

import pytest

from lacuna.models.classification import Classification, DataTier
from lacuna.models.data_operation import DataOperation, OperationType, UserContext
from lacuna.models.policy import PolicyDecision, PolicyInput
from lacuna.policy.engine import PolicyEngine


class TestPolicyDecision:
    """Tests for PolicyDecision model."""

    def test_decision_allow(self) -> None:
        """Test creating an allow decision."""
        decision = PolicyDecision(
            allowed=True,
            reasoning="Operation allowed by policy",
        )

        assert decision.allowed
        assert not decision.is_deny()

    def test_decision_deny_with_alternatives(self) -> None:
        """Test creating a deny decision with alternatives."""
        decision = PolicyDecision(
            allowed=False,
            reasoning="PROPRIETARY data cannot be exported",
            alternatives=[
                "Use anonymized version",
                "Save to governed location",
            ],
        )

        assert not decision.allowed
        assert decision.is_deny()
        assert decision.has_alternatives()
        assert len(decision.alternatives) == 2


class TestPolicyInput:
    """Tests for PolicyInput model."""

    def test_policy_input_creation(self) -> None:
        """Test creating policy input."""
        policy_input = PolicyInput(
            action="export",
            resource_type="file",
            resource_id="customers.csv",
            classification_tier="PROPRIETARY",
            tags=["PII"],
            user_id="analyst@example.com",
            destination="/tmp/export.csv",
        )

        assert policy_input.action == "export"
        assert policy_input.classification_tier == "PROPRIETARY"

    def test_policy_input_to_dict(self) -> None:
        """Test OPA-format serialization."""
        policy_input = PolicyInput(
            action="read",
            resource_type="table",
            resource_id="customers",
            user_id="test-user",
        )

        data = policy_input.to_dict()

        assert data["action"] == "read"
        assert data["source"]["type"] == "table"
        assert data["user"]["id"] == "test-user"


class TestPolicyEngine:
    """Tests for PolicyEngine."""

    @pytest.fixture
    def engine(self) -> PolicyEngine:
        """Create policy engine for testing with fallback enabled."""
        # Create engine and force enable it for testing (bypassing settings)
        engine = PolicyEngine(enabled=True, fallback_on_error=True)
        engine.enabled = True  # Force enable for testing
        return engine

    @pytest.fixture
    def proprietary_export_operation(self) -> DataOperation:
        """Create a proprietary export operation."""
        return DataOperation(
            operation_type=OperationType.EXPORT,
            resource_type="file",
            resource_id="customers.csv",
            destination="~/Downloads/export.csv",
            user=UserContext(user_id="analyst"),
        )

    @pytest.fixture
    def proprietary_classification(self) -> Classification:
        """Create proprietary classification."""
        return Classification(
            tier=DataTier.PROPRIETARY,
            confidence=0.95,
            reasoning="Contains PII",
            tags=["PII", "CUSTOMER_DATA"],
        )

    def test_fallback_blocks_proprietary_export_to_downloads(
        self,
        engine: PolicyEngine,
        proprietary_export_operation: DataOperation,
        proprietary_classification: Classification,
    ) -> None:
        """Test that fallback policy blocks PROPRIETARY exports to Downloads."""
        result = engine.evaluate(
            proprietary_export_operation,
            proprietary_classification,
        )

        assert not result.decision.allowed
        assert "PROPRIETARY" in result.decision.reasoning
        assert result.decision.alternatives  # Should have alternatives

    def test_allows_public_data_export(self, engine: PolicyEngine) -> None:
        """Test that PUBLIC data can be exported anywhere."""
        operation = DataOperation(
            operation_type=OperationType.EXPORT,
            resource_type="file",
            resource_id="public_data.csv",
            destination="~/Downloads/data.csv",
            user=UserContext(user_id="analyst"),
        )

        classification = Classification(
            tier=DataTier.PUBLIC,
            confidence=0.9,
            reasoning="Public data",
        )

        result = engine.evaluate(operation, classification)

        assert result.decision.allowed

    def test_allows_read_operations(self, engine: PolicyEngine) -> None:
        """Test that read operations are generally allowed."""
        operation = DataOperation(
            operation_type=OperationType.READ,
            resource_type="file",
            resource_id="data.csv",
            user=UserContext(user_id="analyst"),
        )

        classification = Classification(
            tier=DataTier.PROPRIETARY,
            confidence=0.9,
            reasoning="Proprietary data",
        )

        result = engine.evaluate(operation, classification)

        # Reads should be allowed (with logging)
        assert result.decision.allowed

    def test_caches_policy_decisions(self, engine: PolicyEngine) -> None:
        """Test that policy decisions are cached."""
        operation = DataOperation(
            operation_type=OperationType.READ,
            resource_type="file",
            resource_id="test.csv",
            user=UserContext(user_id="user"),
        )

        classification = Classification(
            tier=DataTier.PUBLIC,
            confidence=0.9,
            reasoning="Test",
        )

        # First evaluation
        result1 = engine.evaluate(operation, classification)

        # Second evaluation (should hit cache)
        result2 = engine.evaluate(operation, classification)

        assert result1.decision.allowed == result2.decision.allowed
        assert len(engine._cache) > 0

    def test_disabled_engine_allows_all(self) -> None:
        """Test that disabled engine allows all operations."""
        engine = PolicyEngine(enabled=False)

        operation = DataOperation(
            operation_type=OperationType.EXPORT,
            resource_type="file",
            resource_id="sensitive.csv",
            destination="/tmp/leak.csv",
            user=UserContext(user_id="hacker"),
        )

        classification = Classification(
            tier=DataTier.PROPRIETARY,
            confidence=1.0,
            reasoning="Top secret",
        )

        result = engine.evaluate(operation, classification)

        assert result.decision.allowed
        assert result.is_fallback

    def test_get_stats(self, engine: PolicyEngine) -> None:
        """Test getting engine statistics."""
        stats = engine.get_stats()

        assert "enabled" in stats
        assert "opa_available" in stats
        assert "cache_size" in stats
