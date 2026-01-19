"""Test configuration and fixtures."""

import pytest
from typing import Generator

from lacuna.config.settings import Settings
from lacuna.models.classification import Classification, ClassificationContext, DataTier
from lacuna.models.data_operation import DataOperation, OperationType, UserContext


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

