"""Test configuration and fixtures."""

import os
from collections.abc import Generator

import pytest

from lacuna.config.settings import Settings
from lacuna.models.classification import Classification, ClassificationContext, DataTier
from lacuna.models.data_operation import DataOperation, OperationType, UserContext


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test (requires external services)",
    )


def pytest_collection_modifyitems(config, items):
    """Skip integration tests unless explicitly requested."""
    # Check if we're running integration tests
    run_integration = (
        os.environ.get("LACUNA_RUN_INTEGRATION_TESTS", "").lower() == "true"
    )

    if not run_integration:
        skip_integration = pytest.mark.skip(
            reason="Integration tests skipped (set LACUNA_RUN_INTEGRATION_TESTS=true to run)"
        )
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_integration)


@pytest.fixture
def settings() -> Settings:
    """Create test settings."""
    return Settings(
        environment="test",
        debug=True,
    )


@pytest.fixture
def sample_classification() -> Classification:
    """Create sample classification."""
    return Classification(
        tier=DataTier.PROPRIETARY,
        confidence=0.95,
        reasoning="Test classification",
        tags=["PII", "CUSTOMER_DATA"],
        classifier_name="TestClassifier",
    )


@pytest.fixture
def sample_context() -> ClassificationContext:
    """Create sample classification context."""
    return ClassificationContext(
        user_id="test-user",
        user_role="analyst",
        project="test-project",
        environment="test",
    )


@pytest.fixture
def sample_operation() -> DataOperation:
    """Create sample data operation."""
    return DataOperation(
        operation_type=OperationType.EXPORT,
        resource_type="file",
        resource_id="customers.csv",
        destination="~/Downloads/export.csv",
        user=UserContext(user_id="test-user", user_role="analyst"),
        purpose="Test export",
    )
