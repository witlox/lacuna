"""Tests for audit logging."""

from datetime import datetime, timezone

import pytest

from lacuna.models.audit import AuditQuery, AuditRecord, EventType, Severity


class TestAuditRecord:
    """Tests for AuditRecord model."""

    def test_audit_record_creation(self) -> None:
        """Test creating an audit record."""
        record = AuditRecord(
            event_type=EventType.DATA_ACCESS,
            severity=Severity.INFO,
            user_id="test-user",
            resource_type="file",
            resource_id="customers.csv",
            action="read",
            action_result="success",
        )

        assert record.event_id is not None
        assert record.timestamp is not None
        assert record.user_id == "test-user"
        assert record.event_type == EventType.DATA_ACCESS

    def test_audit_record_hash_computation(self) -> None:
        """Test hash chain computation."""
        record = AuditRecord(
            event_type=EventType.DATA_ACCESS,
            severity=Severity.INFO,
            user_id="test-user",
            resource_type="file",
            resource_id="test.csv",
            action="read",
            action_result="success",
        )

        hash1 = record.compute_hash()
        hash2 = record.compute_hash()

        # Hash should be deterministic
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex length

    def test_audit_record_hash_changes_with_content(self) -> None:
        """Test that hash changes when content changes."""
        record1 = AuditRecord(
            event_type=EventType.DATA_ACCESS,
            user_id="user1",
            resource_id="file1",
            action="read",
            action_result="success",
        )

        record2 = AuditRecord(
            event_type=EventType.DATA_ACCESS,
            user_id="user2",  # Different user
            resource_id="file1",
            action="read",
            action_result="success",
        )

        assert record1.compute_hash() != record2.compute_hash()

    def test_audit_record_to_dict(self) -> None:
        """Test serialization to dictionary."""
        record = AuditRecord(
            event_type=EventType.POLICY_DENY,
            severity=Severity.WARNING,
            user_id="test-user",
            resource_type="file",
            resource_id="sensitive.csv",
            action="export",
            action_result="denied",
        )

        data = record.to_dict()

        assert data["event_type"] == "policy.deny"
        assert data["severity"] == "WARNING"
        assert data["user_id"] == "test-user"
        assert data["action_result"] == "denied"

    def test_audit_record_from_dict(self) -> None:
        """Test deserialization from dictionary."""
        data = {
            "event_type": "data.access",
            "severity": "INFO",
            "user_id": "test-user",
            "resource_type": "table",
            "resource_id": "customers",
            "action": "select",
            "action_result": "success",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        record = AuditRecord.from_dict(data)

        assert record.event_type == EventType.DATA_ACCESS
        assert record.severity == Severity.INFO
        assert record.user_id == "test-user"

    def test_is_sensitive_event(self) -> None:
        """Test sensitive event detection."""
        record = AuditRecord(
            resource_classification="PROPRIETARY",
            resource_tags=["PII"],
        )

        assert record.is_sensitive_event()

    def test_is_policy_violation(self) -> None:
        """Test policy violation detection."""
        record = AuditRecord(
            event_type=EventType.POLICY_DENY,
            action_result="denied",
        )

        assert record.is_policy_violation()

    def test_is_administrative_action(self) -> None:
        """Test administrative action detection."""
        record = AuditRecord(
            event_type=EventType.ADMIN_POLICY_CREATE,
        )

        assert record.is_administrative_action()


class TestAuditQuery:
    """Tests for AuditQuery model."""

    def test_audit_query_creation(self) -> None:
        """Test creating an audit query."""
        query = AuditQuery(
            user_id="test-user",
            limit=50,
            offset=0,
        )

        assert query.user_id == "test-user"
        assert query.limit == 50

    def test_audit_query_with_filters(self) -> None:
        """Test query with multiple filters."""
        query = AuditQuery(
            user_id="analyst@example.com",
            event_types=[EventType.DATA_ACCESS, EventType.DATA_EXPORT],
            severities=[Severity.WARNING, Severity.ERROR],
            resource_classification="PROPRIETARY",
            limit=100,
        )

        assert len(query.event_types) == 2
        assert len(query.severities) == 2
        assert query.resource_classification == "PROPRIETARY"

    def test_audit_query_to_dict(self) -> None:
        """Test query serialization."""
        query = AuditQuery(
            user_id="test-user",
            event_types=[EventType.DATA_ACCESS],
            limit=25,
        )

        data = query.to_dict()

        assert data["user_id"] == "test-user"
        assert data["limit"] == 25
        assert "data.access" in data["event_types"]
