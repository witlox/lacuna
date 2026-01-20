"""Audit logger with async batch writing for performance."""

import threading
from datetime import datetime
from queue import Empty, Queue
from typing import Any, Optional

import structlog

from lacuna.config import get_settings
from lacuna.models.audit import AuditRecord, EventType, Severity
from lacuna.models.classification import Classification
from lacuna.models.data_operation import DataOperation
from lacuna.models.policy import PolicyDecision

logger = structlog.get_logger()


def get_audit_backend() -> Any:
    """Get the appropriate audit backend based on configuration."""
    settings = get_settings()

    # Use in-memory backend for development with SQLite
    if settings.database.url.startswith("sqlite"):
        from lacuna.audit.memory_backend import InMemoryAuditBackend

        return InMemoryAuditBackend(verify_on_write=settings.audit.verify_integrity)
    else:
        from lacuna.audit.backend import AuditBackend

        return AuditBackend(verify_on_write=settings.audit.verify_integrity)


class AuditLogger:
    """
    High-performance audit logger with async batch writing.

    Features:
    - Non-blocking audit log writes
    - Batch writes for performance
    - Automatic flush on threshold or timeout
    - ISO 27001-compliant record structure
    """

    def __init__(
        self,
        backend: Optional[Any] = None,
        batch_size: int = 100,
        flush_interval: float = 5.0,
        enabled: bool = True,
    ):
        """Initialize audit logger.

        Args:
            backend: Audit storage backend
            batch_size: Maximum records before auto-flush
            flush_interval: Seconds between automatic flushes
            enabled: Enable/disable audit logging
        """
        settings = get_settings()
        self.enabled = enabled and settings.audit.enabled
        self.batch_size = batch_size
        self.flush_interval = flush_interval

        self._backend = backend or get_audit_backend()
        self._queue: Queue[AuditRecord] = Queue()
        self._buffer: list[AuditRecord] = []
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._worker_thread: Optional[threading.Thread] = None

        if self.enabled:
            self._start_worker()

    def _start_worker(self) -> None:
        """Start background worker thread for batch writes."""
        self._worker_thread = threading.Thread(
            target=self._worker_loop, daemon=True, name="audit-logger"
        )
        self._worker_thread.start()
        logger.info("audit_logger_started", batch_size=self.batch_size)

    def _worker_loop(self) -> None:
        """Background worker that processes the audit queue."""
        while not self._stop_event.is_set():
            try:
                # Wait for items with timeout
                try:
                    record = self._queue.get(timeout=self.flush_interval)
                    with self._lock:
                        self._buffer.append(record)
                except Empty:
                    pass

                # Flush if buffer is full or timeout
                with self._lock:
                    if len(self._buffer) >= self.batch_size or (
                        self._buffer and self._queue.empty()
                    ):
                        self._flush_buffer()

            except Exception as e:
                logger.error("audit_worker_error", error=str(e))

    def _flush_buffer(self) -> None:
        """Flush the buffer to storage (must hold lock)."""
        if not self._buffer:
            return

        try:
            self._backend.write_batch(self._buffer)
            logger.debug("audit_buffer_flushed", count=len(self._buffer))
            self._buffer = []
        except Exception as e:
            logger.error("audit_flush_error", error=str(e), count=len(self._buffer))

    def log(self, record: AuditRecord) -> None:
        """Log an audit record asynchronously.

        Args:
            record: Audit record to log
        """
        if not self.enabled:
            return

        self._queue.put(record)

    def log_classification(
        self,
        classification: Classification,
        query: str,
        user_id: str,
        context: Optional[dict[str, Any]] = None,
    ) -> AuditRecord:
        """Log a classification event.

        Args:
            classification: Classification result
            query: Query that was classified
            user_id: User who made the query
            context: Additional context

        Returns:
            Created audit record
        """
        record = AuditRecord(
            event_type=EventType.CLASSIFICATION_AUTO,
            severity=Severity.INFO,
            user_id=user_id,
            resource_type="query",
            resource_id=self._hash_query(query),
            resource_classification=classification.tier.value,
            resource_tags=classification.tags,
            action="classify",
            action_result="success",
            action_metadata={
                "query_length": len(query),
                "classifier": classification.classifier_name,
                **(context or {}),
            },
            classification_tier=classification.tier.value,
            classification_confidence=classification.confidence,
            classification_reasoning=classification.reasoning,
        )

        self.log(record)
        return record

    def log_data_access(
        self,
        operation: DataOperation,
        classification: Optional[Classification] = None,
        allowed: bool = True,
        reason: Optional[str] = None,
    ) -> AuditRecord:
        """Log a data access event.

        Args:
            operation: Data operation being performed
            classification: Classification of the data
            allowed: Whether the operation was allowed
            reason: Reason for allow/deny

        Returns:
            Created audit record
        """
        event_type = EventType.POLICY_ALLOW if allowed else EventType.POLICY_DENY
        severity = Severity.INFO if allowed else Severity.WARNING

        record = AuditRecord(
            event_type=event_type,
            severity=severity,
            user_id=operation.user.user_id if operation.user else "unknown",
            user_session_id=operation.user.session_id if operation.user else None,
            user_ip_address=operation.user.ip_address if operation.user else None,
            user_role=operation.user.user_role if operation.user else None,
            resource_type=operation.resource_type,
            resource_id=operation.resource_id,
            resource_classification=(
                classification.tier.value if classification else None
            ),
            resource_tags=classification.tags if classification else [],
            action=operation.operation_type.value,
            action_result="success" if allowed else "denied",
            action_metadata={
                "destination": operation.destination,
                "sources": operation.sources,
                "purpose": operation.purpose,
            },
            classification_tier=classification.tier.value if classification else None,
            classification_confidence=(
                classification.confidence if classification else None
            ),
            classification_reasoning=reason,
            lineage_chain=operation.lineage_chain,
        )

        self.log(record)
        return record

    def log_policy_evaluation(
        self,
        operation: DataOperation,
        decision: PolicyDecision,
        classification: Optional[Classification] = None,
    ) -> AuditRecord:
        """Log a policy evaluation event.

        Args:
            operation: Data operation being evaluated
            decision: Policy decision result
            classification: Classification of the data

        Returns:
            Created audit record
        """
        event_type = (
            EventType.POLICY_ALLOW if decision.allowed else EventType.POLICY_DENY
        )
        severity = Severity.INFO if decision.allowed else Severity.WARNING

        record = AuditRecord(
            event_type=event_type,
            severity=severity,
            user_id=operation.user.user_id if operation.user else "unknown",
            user_session_id=operation.user.session_id if operation.user else None,
            user_ip_address=operation.user.ip_address if operation.user else None,
            user_role=operation.user.user_role if operation.user else None,
            resource_type=operation.resource_type,
            resource_id=operation.resource_id,
            resource_classification=(
                classification.tier.value if classification else None
            ),
            resource_tags=classification.tags if classification else [],
            action=operation.operation_type.value,
            action_result="success" if decision.allowed else "denied",
            action_metadata={
                "destination": operation.destination,
                "alternatives": decision.alternatives,
            },
            policy_id=decision.policy_id,
            policy_version=decision.policy_version,
            classification_tier=classification.tier.value if classification else None,
            classification_confidence=(
                classification.confidence if classification else None
            ),
            classification_reasoning=decision.reasoning,
        )

        self.log(record)
        return record

    def log_admin_action(
        self,
        action: str,
        user_id: str,
        resource_type: str,
        resource_id: str,
        details: Optional[dict[str, Any]] = None,
    ) -> AuditRecord:
        """Log an administrative action.

        Args:
            action: Action being performed
            user_id: User performing the action
            resource_type: Type of resource affected
            resource_id: ID of resource affected
            details: Additional details

        Returns:
            Created audit record
        """
        event_type_map = {
            "policy.create": EventType.ADMIN_POLICY_CREATE,
            "policy.update": EventType.ADMIN_POLICY_UPDATE,
            "policy.delete": EventType.ADMIN_POLICY_DELETE,
            "user.grant": EventType.ADMIN_USER_GRANT,
            "user.revoke": EventType.ADMIN_USER_REVOKE,
        }

        record = AuditRecord(
            event_type=event_type_map.get(action, EventType.SYSTEM_CONFIG_CHANGE),
            severity=Severity.INFO,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            action_result="success",
            action_metadata=details or {},
        )

        self.log(record)
        return record

    def flush(self) -> None:
        """Force flush all pending audit records."""
        if not self.enabled:
            return

        # Wait for queue to drain
        while not self._queue.empty():
            try:
                record = self._queue.get_nowait()
                with self._lock:
                    self._buffer.append(record)
            except Empty:
                break

        # Flush buffer
        with self._lock:
            self._flush_buffer()

    def stop(self) -> None:
        """Stop the audit logger and flush remaining records."""
        if self._worker_thread:
            self._stop_event.set()
            self.flush()
            self._worker_thread.join(timeout=5.0)
            logger.info("audit_logger_stopped")

    def verify_integrity(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> dict[str, Any]:
        """Verify audit log integrity.

        Args:
            start_time: Start of verification period
            end_time: End of verification period

        Returns:
            Verification result
        """
        return self._backend.verify_chain(start_time, end_time)

    def query(self, **kwargs: Any) -> list[AuditRecord]:
        """Query audit records.

        Args:
            **kwargs: Query parameters (see AuditQuery)

        Returns:
            List of matching records
        """
        from lacuna.models.audit import AuditQuery

        query = AuditQuery(**kwargs)
        return self._backend.query(query)

    def _hash_query(self, query: str) -> str:
        """Hash query for privacy-preserving storage."""
        import hashlib

        return hashlib.sha256(query.encode()).hexdigest()

    def __enter__(self) -> "AuditLogger":
        """Context manager entry."""
        return self

    def __exit__(self, _exc_type: Any, _exc_val: Any, _exc_tb: Any) -> None:
        """Context manager exit."""
        self.stop()
