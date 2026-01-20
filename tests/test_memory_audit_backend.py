"""Tests for in-memory audit backend (dev mode)."""

from datetime import datetime, timedelta, timezone

import pytest

from lacuna.audit.memory_backend import InMemoryAuditBackend
from lacuna.models.audit import AuditQuery, AuditRecord, EventType, Severity


class TestInMemoryAuditBackendInit:
    """Tests for InMemoryAuditBackend initialization."""

    def test_init_default(self) -> None:
        """Test default initialization."""
        backend = InMemoryAuditBackend()
        assert backend._records == []
        assert backend._last_hash is None

    def test_init_with_verify(self) -> None:
        """Test initialization with verify_on_write (should be ignored)."""
        backend = InMemoryAuditBackend(verify_on_write=True)
        assert backend._records == []


class TestInMemoryAuditBackendWrite:
    """Tests for InMemoryAuditBackend write operations."""

    @pytest.fixture
    def backend(self) -> InMemoryAuditBackend:
        """Create a fresh backend for each test."""
        return InMemoryAuditBackend()

    @pytest.fixture
    def sample_record(self) -> AuditRecord:
        """Create a sample audit record."""
        return AuditRecord(
            event_type=EventType.DATA_ACCESS,
            severity=Severity.INFO,
            user_id="test-user",
            resource_type="file",
            resource_id="test.csv",
            action="read",
            action_result="success",
        )

    def test_write_single_record(
        self, backend: InMemoryAuditBackend, sample_record: AuditRecord
    ) -> None:
        """Test writing a single record."""
        backend.write(sample_record)

        assert len(backend._records) == 1
        assert backend._records[0] == sample_record
        assert backend._last_hash == sample_record.record_hash

    def test_write_multiple_records(self, backend: InMemoryAuditBackend) -> None:
        """Test writing multiple records sequentially."""
        records = [
            AuditRecord(
                event_type=EventType.DATA_ACCESS,
                user_id=f"user-{i}",
                action="read",
            )
            for i in range(5)
        ]

        for record in records:
            backend.write(record)

        assert len(backend._records) == 5
        assert backend._last_hash == records[-1].record_hash

    def test_write_batch(self, backend: InMemoryAuditBackend) -> None:
        """Test batch writing records."""
        records = [
            AuditRecord(
                event_type=EventType.DATA_ACCESS,
                user_id=f"user-{i}",
                action="read",
            )
            for i in range(3)
        ]

        backend.write_batch(records)

        assert len(backend._records) == 3


class TestInMemoryAuditBackendQuery:
    """Tests for InMemoryAuditBackend query operations."""

    @pytest.fixture
    def backend_with_data(self) -> InMemoryAuditBackend:
        """Create a backend with sample data."""
        backend = InMemoryAuditBackend()

        # Add test records with varying attributes
        now = datetime.now(timezone.utc)
        records = [
            AuditRecord(
                event_type=EventType.DATA_ACCESS,
                user_id="user-a",
                resource_id="file1.csv",
                action="read",
                timestamp=now - timedelta(hours=2),
            ),
            AuditRecord(
                event_type=EventType.DATA_EXPORT,
                user_id="user-a",
                resource_id="file2.csv",
                action="export",
                timestamp=now - timedelta(hours=1),
            ),
            AuditRecord(
                event_type=EventType.POLICY_DENY,
                user_id="user-b",
                resource_id="file3.csv",
                action="export",
                timestamp=now,
            ),
        ]

        for record in records:
            backend.write(record)

        return backend

    def test_query_all(self, backend_with_data: InMemoryAuditBackend) -> None:
        """Test querying all records."""
        query = AuditQuery()
        results = backend_with_data.query(query)

        assert len(results) == 3

    def test_query_by_user_id(self, backend_with_data: InMemoryAuditBackend) -> None:
        """Test querying by user ID."""
        query = AuditQuery(user_id="user-a")
        results = backend_with_data.query(query)

        assert len(results) == 2
        assert all(r.user_id == "user-a" for r in results)

    def test_query_by_resource_id(
        self, backend_with_data: InMemoryAuditBackend
    ) -> None:
        """Test querying by resource ID."""
        query = AuditQuery(resource_id="file1.csv")
        results = backend_with_data.query(query)

        assert len(results) == 1
        assert results[0].resource_id == "file1.csv"

    def test_query_by_event_type(self, backend_with_data: InMemoryAuditBackend) -> None:
        """Test querying by event type."""
        query = AuditQuery(event_types=[EventType.POLICY_DENY])
        results = backend_with_data.query(query)

        assert len(results) == 1
        assert results[0].event_type == EventType.POLICY_DENY

    def test_query_by_time_range(self, backend_with_data: InMemoryAuditBackend) -> None:
        """Test querying by time range."""
        now = datetime.now(timezone.utc)
        query = AuditQuery(
            start_time=now - timedelta(minutes=90),
            end_time=now + timedelta(minutes=1),
        )
        results = backend_with_data.query(query)

        # Should get records from last 90 minutes
        assert len(results) >= 1

    def test_query_with_limit(self, backend_with_data: InMemoryAuditBackend) -> None:
        """Test querying with limit."""
        query = AuditQuery(limit=2)
        results = backend_with_data.query(query)

        assert len(results) == 2

    def test_query_sorted_by_timestamp(
        self, backend_with_data: InMemoryAuditBackend
    ) -> None:
        """Test that results are sorted by timestamp descending."""
        query = AuditQuery()
        results = backend_with_data.query(query)

        # Most recent should be first
        for i in range(len(results) - 1):
            assert results[i].timestamp >= results[i + 1].timestamp


class TestInMemoryAuditBackendLookup:
    """Tests for InMemoryAuditBackend lookup operations."""

    @pytest.fixture
    def backend(self) -> InMemoryAuditBackend:
        """Create a fresh backend."""
        return InMemoryAuditBackend()

    def test_get_by_event_id_found(self, backend: InMemoryAuditBackend) -> None:
        """Test getting record by event ID when it exists."""
        record = AuditRecord(
            event_type=EventType.DATA_ACCESS,
            user_id="test-user",
            action="read",
        )
        backend.write(record)

        result = backend.get_by_event_id(record.event_id)

        assert result is not None
        assert result.event_id == record.event_id

    def test_get_by_event_id_not_found(self, backend: InMemoryAuditBackend) -> None:
        """Test getting record by event ID when it doesn't exist."""
        result = backend.get_by_event_id("nonexistent-id")
        assert result is None

    def test_count_all(self, backend: InMemoryAuditBackend) -> None:
        """Test counting all records."""
        for i in range(5):
            backend.write(
                AuditRecord(event_type=EventType.DATA_ACCESS, user_id=f"user-{i}")
            )

        count = backend.count()
        assert count == 5

    def test_count_by_user(self, backend: InMemoryAuditBackend) -> None:
        """Test counting by user ID."""
        backend.write(AuditRecord(event_type=EventType.DATA_ACCESS, user_id="user-a"))
        backend.write(AuditRecord(event_type=EventType.DATA_ACCESS, user_id="user-a"))
        backend.write(AuditRecord(event_type=EventType.DATA_ACCESS, user_id="user-b"))

        count = backend.count(user_id="user-a")
        assert count == 2

    def test_clear(self, backend: InMemoryAuditBackend) -> None:
        """Test clearing all records."""
        backend.write(AuditRecord(event_type=EventType.DATA_ACCESS, user_id="test"))

        assert len(backend._records) == 1

        backend.clear()

        assert len(backend._records) == 0
        assert backend._last_hash is None
