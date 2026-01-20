"""In-memory audit storage backend for development."""

from datetime import datetime
from typing import Optional

import structlog

from lacuna.models.audit import AuditQuery, AuditRecord

logger = structlog.get_logger()


class InMemoryAuditBackend:
    """
    In-memory backend for audit logging during development.

    Stores audit records in memory - data is lost on restart.
    This is suitable for local development and testing only.
    """

    def __init__(self, verify_on_write: bool = False):
        """Initialize in-memory audit backend.

        Args:
            verify_on_write: Ignored for in-memory backend
        """
        self._records: list[AuditRecord] = []
        self._last_hash: Optional[str] = None

    def write(self, record: AuditRecord) -> None:
        """Write a single audit record.

        Args:
            record: Audit record to write
        """
        self._records.append(record)
        self._last_hash = record.record_hash

        logger.debug(
            "audit_record_written_memory",
            event_id=record.event_id,
            event_type=record.event_type.value,
            user_id=record.user_id,
        )

    def write_batch(self, records: list[AuditRecord]) -> None:
        """Write multiple audit records.

        Args:
            records: List of audit records to write
        """
        for record in records:
            self.write(record)

    def query(self, query: AuditQuery) -> list[AuditRecord]:
        """Query audit records.

        Args:
            query: Query parameters

        Returns:
            List of matching audit records
        """
        results = self._records.copy()

        # Apply filters
        if query.user_id:
            results = [r for r in results if r.user_id == query.user_id]

        if query.resource_id:
            results = [r for r in results if r.resource_id == query.resource_id]

        if query.event_types:
            results = [r for r in results if r.event_type in query.event_types]

        if query.start_time:
            results = [r for r in results if r.timestamp >= query.start_time]

        if query.end_time:
            results = [r for r in results if r.timestamp <= query.end_time]

        # Sort by timestamp descending (most recent first)
        results.sort(key=lambda r: r.timestamp, reverse=True)

        # Apply limit
        if query.limit:
            results = results[: query.limit]

        return results

    def get_by_event_id(self, event_id: str) -> Optional[AuditRecord]:
        """Get a specific audit record by event ID.

        Args:
            event_id: Event ID to look up

        Returns:
            Audit record if found, None otherwise
        """
        for record in self._records:
            if record.event_id == event_id:
                return record
        return None

    def count(
        self,
        user_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> int:
        """Count audit records matching criteria.

        Args:
            user_id: Filter by user ID
            start_time: Start time filter
            end_time: End time filter

        Returns:
            Count of matching records
        """
        results = self._records

        if user_id:
            results = [r for r in results if r.user_id == user_id]

        if start_time:
            results = [r for r in results if r.timestamp >= start_time]

        if end_time:
            results = [r for r in results if r.timestamp <= end_time]

        return len(results)

    def clear(self) -> None:
        """Clear all records (for testing)."""
        self._records.clear()
        self._last_hash = None
