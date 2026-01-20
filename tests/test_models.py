"""Tests for data models."""

from datetime import datetime
from uuid import uuid4

import pytest

from lacuna.models.classification import (
    Classification,
    ClassificationContext,
    DataTier,
)
from lacuna.models.data_operation import DataOperation, OperationType, UserContext


class TestDataTier:
    """Tests for DataTier enum."""

    def test_tier_ordering(self) -> None:
        """Test tier comparison ordering."""
        assert DataTier.PUBLIC < DataTier.INTERNAL
        assert DataTier.INTERNAL < DataTier.PROPRIETARY
        assert DataTier.PUBLIC < DataTier.PROPRIETARY

    def test_tier_value_int(self) -> None:
        """Test tier numeric values."""
        assert DataTier.PUBLIC.value_int == 0
        assert DataTier.INTERNAL.value_int == 1
        assert DataTier.PROPRIETARY.value_int == 2


class TestClassification:
    """Tests for Classification model."""

    def test_classification_creation(self) -> None:
        """Test creating a classification."""
        classification = Classification(
            tier=DataTier.PROPRIETARY,
            confidence=0.95,
            reasoning="Contains PII",
            tags=["PII", "EMAIL"],
            classifier_name="HeuristicClassifier",
        )

        assert classification.tier == DataTier.PROPRIETARY
        assert classification.confidence == 0.95
        assert "PII" in classification.tags

    def test_classification_to_dict(self) -> None:
        """Test serialization to dictionary."""
        classification = Classification(
            tier=DataTier.INTERNAL,
            confidence=0.8,
            reasoning="Internal docs",
        )

        data = classification.to_dict()

        assert data["tier"] == "INTERNAL"
        assert data["confidence"] == 0.8

    def test_classification_from_dict(self) -> None:
        """Test deserialization from dictionary."""
        data = {
            "tier": "PUBLIC",
            "confidence": 0.9,
            "reasoning": "Public knowledge",
            "tags": [],
        }

        classification = Classification.from_dict(data)

        assert classification.tier == DataTier.PUBLIC
        assert classification.confidence == 0.9

    def test_classification_inheritance(self) -> None:
        """Test classification inheritance."""
        parent = Classification(
            tier=DataTier.PROPRIETARY,
            confidence=0.95,
            reasoning="Parent is proprietary",
            tags=["PII"],
        )

        child = Classification(
            tier=DataTier.INTERNAL,
            confidence=0.8,
            reasoning="Child is internal",
            tags=["INTERNAL_DOCS"],
        )

        inherited = child.inherit_from(parent)

        # Should inherit more restrictive tier
        assert inherited.tier == DataTier.PROPRIETARY
        # Should merge tags
        assert "PII" in inherited.tags
        assert "INTERNAL_DOCS" in inherited.tags


class TestDataOperation:
    """Tests for DataOperation model."""

    def test_operation_creation(self) -> None:
        """Test creating a data operation."""
        operation = DataOperation(
            operation_type=OperationType.READ,
            resource_type="file",
            resource_id="data.csv",
            user=UserContext(user_id="analyst"),
        )

        assert operation.operation_type == OperationType.READ
        assert operation.resource_id == "data.csv"

    def test_operation_is_transformation(self) -> None:
        """Test transformation detection."""
        join_op = DataOperation(operation_type=OperationType.JOIN)
        read_op = DataOperation(operation_type=OperationType.READ)

        assert join_op.is_transformation()
        assert not read_op.is_transformation()

    def test_operation_is_export(self) -> None:
        """Test export detection."""
        export_op = DataOperation(operation_type=OperationType.EXPORT)
        read_op = DataOperation(operation_type=OperationType.READ)

        assert export_op.is_export()
        assert not read_op.is_export()

    def test_operation_is_write(self) -> None:
        """Test write operation detection."""
        write_op = DataOperation(operation_type=OperationType.WRITE)
        insert_op = DataOperation(operation_type=OperationType.INSERT)
        read_op = DataOperation(operation_type=OperationType.READ)

        assert write_op.is_write_operation()
        assert insert_op.is_write_operation()
        assert not read_op.is_write_operation()

    def test_operation_to_dict(self) -> None:
        """Test serialization."""
        operation = DataOperation(
            operation_type=OperationType.EXPORT,
            resource_id="data.csv",
            destination="/tmp/export.csv",
            user=UserContext(user_id="user", user_role="analyst"),
        )

        data = operation.to_dict()

        assert data["operation_type"] == "export"
        assert data["destination"] == "/tmp/export.csv"
        assert data["user"]["user_id"] == "user"
