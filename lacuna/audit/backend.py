"""Audit storage backend for PostgreSQL."""

from datetime import datetime
from typing import Any, Optional

import structlog
from sqlalchemy import desc
from sqlalchemy.orm import Session

from lacuna.db.base import session_scope
from lacuna.db.models import AuditLogModel
from lacuna.models.audit import AuditQuery, AuditRecord, EventType, Severity

logger = structlog.get_logger()


class AuditBackend:
    """
    PostgreSQL backend for ISO 27001-compliant audit logging.

    Features:
    - Append-only storage (no updates/deletes)
    - Hash chain for tamper detection
    - Indexed for efficient querying
    """

    def __init__(self, verify_on_write: bool = True):
        """Initialize audit backend.

        Args:
            verify_on_write: Verify hash chain integrity on each write
        """
        self.verify_on_write = verify_on_write
        self._last_hash: Optional[str] = None

    def _get_last_hash(self, session: Session) -> Optional[str]:
        """Get the hash of the most recent audit record."""
        if self._last_hash is not None:
            return self._last_hash

        result = (
            session.query(AuditLogModel.record_hash)
            .order_by(desc(AuditLogModel.timestamp))
            .first()
        )

        if result:
            self._last_hash = result[0]
            return self._last_hash
        return None

    def write(self, record: AuditRecord) -> None:
        """Write a single audit record.

        Args:
            record: Audit record to write
        """
        with session_scope() as session:
            # Get previous hash for chain
            previous_hash = self._get_last_hash(session)
            record.previous_record_hash = previous_hash

            # Compute hash for this record
            record.record_hash = record.compute_hash()

            # Create database model
            model = AuditLogModel(
                event_id=record.event_id,
                timestamp=record.timestamp,
                event_type=record.event_type.value,
                severity=record.severity.value,
                user_id=record.user_id,
                user_session_id=record.user_session_id,
                user_ip_address=record.user_ip_address,
                user_role=record.user_role,
                user_department=record.user_department,
                resource_type=record.resource_type,
                resource_id=record.resource_id,
                resource_classification=record.resource_classification,
                resource_tags=record.resource_tags,
                action=record.action,
                action_result=record.action_result,
                action_metadata=record.action_metadata,
                policy_id=record.policy_id,
                policy_version=record.policy_version,
                classification_tier=record.classification_tier,
                classification_confidence=record.classification_confidence,
                classification_reasoning=record.classification_reasoning,
                parent_event_id=record.parent_event_id,
                lineage_chain=record.lineage_chain,
                compliance_flags=record.compliance_flags,
                retention_period_days=record.retention_period_days,
                previous_record_hash=record.previous_record_hash,
                record_hash=record.record_hash,
                signature=record.signature,
                system_id=record.system_id,
                system_version=record.system_version,
            )

            session.add(model)
            self._last_hash = record.record_hash

            logger.debug(
                "audit_record_written",
                event_id=str(record.event_id),
                event_type=record.event_type.value,
                record_hash=record.record_hash[:16] + "...",
            )

    def write_batch(self, records: list[AuditRecord]) -> None:
        """Write multiple audit records in a batch.

        Args:
            records: List of audit records to write
        """
        if not records:
            return

        with session_scope() as session:
            previous_hash = self._get_last_hash(session)

            for record in records:
                record.previous_record_hash = previous_hash
                record.record_hash = record.compute_hash()
                previous_hash = record.record_hash

                model = AuditLogModel(
                    event_id=record.event_id,
                    timestamp=record.timestamp,
                    event_type=record.event_type.value,
                    severity=record.severity.value,
                    user_id=record.user_id,
                    user_session_id=record.user_session_id,
                    user_ip_address=record.user_ip_address,
                    user_role=record.user_role,
                    user_department=record.user_department,
                    resource_type=record.resource_type,
                    resource_id=record.resource_id,
                    resource_classification=record.resource_classification,
                    resource_tags=record.resource_tags,
                    action=record.action,
                    action_result=record.action_result,
                    action_metadata=record.action_metadata,
                    policy_id=record.policy_id,
                    policy_version=record.policy_version,
                    classification_tier=record.classification_tier,
                    classification_confidence=record.classification_confidence,
                    classification_reasoning=record.classification_reasoning,
                    parent_event_id=record.parent_event_id,
                    lineage_chain=record.lineage_chain,
                    compliance_flags=record.compliance_flags,
                    retention_period_days=record.retention_period_days,
                    previous_record_hash=record.previous_record_hash,
                    record_hash=record.record_hash,
                    signature=record.signature,
                    system_id=record.system_id,
                    system_version=record.system_version,
                )
                session.add(model)

            self._last_hash = previous_hash

            logger.info(
                "audit_batch_written",
                count=len(records),
            )

    def query(self, query: AuditQuery) -> list[AuditRecord]:
        """Query audit records.

        Args:
            query: Query parameters

        Returns:
            List of matching audit records
        """
        with session_scope() as session:
            q = session.query(AuditLogModel)

            # Apply filters
            if query.start_time:
                q = q.filter(AuditLogModel.timestamp >= query.start_time)
            if query.end_time:
                q = q.filter(AuditLogModel.timestamp <= query.end_time)
            if query.user_id:
                q = q.filter(AuditLogModel.user_id == query.user_id)
            if query.resource_id:
                q = q.filter(AuditLogModel.resource_id == query.resource_id)
            if query.event_types:
                event_type_values = [et.value for et in query.event_types]
                q = q.filter(AuditLogModel.event_type.in_(event_type_values))
            if query.severities:
                severity_values = [s.value for s in query.severities]
                q = q.filter(AuditLogModel.severity.in_(severity_values))
            if query.action_result:
                q = q.filter(AuditLogModel.action_result == query.action_result)
            if query.resource_classification:
                q = q.filter(
                    AuditLogModel.resource_classification
                    == query.resource_classification
                )

            # Sorting
            if query.order_desc:
                q = q.order_by(desc(getattr(AuditLogModel, query.order_by)))
            else:
                q = q.order_by(getattr(AuditLogModel, query.order_by))

            # Pagination
            q = q.offset(query.offset).limit(query.limit)

            results = q.all()

            return [self._model_to_record(model) for model in results]

    def verify_chain(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> dict[str, Any]:
        """Verify the integrity of the hash chain.

        Args:
            start_time: Start of verification period
            end_time: End of verification period

        Returns:
            Verification result with details
        """
        with session_scope() as session:
            q = session.query(AuditLogModel).order_by(AuditLogModel.timestamp)

            if start_time:
                q = q.filter(AuditLogModel.timestamp >= start_time)
            if end_time:
                q = q.filter(AuditLogModel.timestamp <= end_time)

            records = q.all()

            if not records:
                return {
                    "verified": True,
                    "records_checked": 0,
                    "errors": [],
                    "message": "No records to verify",
                }

            errors = []
            previous_hash = None

            for i, model in enumerate(records):
                # Check previous hash linkage
                if i > 0 and model.previous_record_hash != previous_hash:
                    errors.append(
                        {
                            "event_id": str(model.event_id),
                            "timestamp": model.timestamp.isoformat(),
                            "error": "Hash chain broken - previous hash mismatch",
                            "expected": previous_hash,
                            "actual": model.previous_record_hash,
                        }
                    )

                # Verify record hash
                record = self._model_to_record(model)
                expected_hash = record.compute_hash()
                if expected_hash != model.record_hash:
                    errors.append(
                        {
                            "event_id": str(model.event_id),
                            "timestamp": model.timestamp.isoformat(),
                            "error": "Record hash mismatch - possible tampering",
                            "expected": expected_hash,
                            "actual": model.record_hash,
                        }
                    )

                previous_hash = model.record_hash

            return {
                "verified": len(errors) == 0,
                "records_checked": len(records),
                "errors": errors,
                "message": (
                    "Audit log integrity verified"
                    if not errors
                    else f"Found {len(errors)} integrity errors"
                ),
                "first_record": records[0].timestamp.isoformat() if records else None,
                "last_record": records[-1].timestamp.isoformat() if records else None,
            }

    def get_record_count(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> int:
        """Get count of audit records."""
        with session_scope() as session:
            q = session.query(AuditLogModel)

            if start_time:
                q = q.filter(AuditLogModel.timestamp >= start_time)
            if end_time:
                q = q.filter(AuditLogModel.timestamp <= end_time)

            return q.count()

    def _model_to_record(self, model: AuditLogModel) -> AuditRecord:
        """Convert database model to AuditRecord."""
        return AuditRecord(
            event_id=model.event_id,
            timestamp=model.timestamp,
            event_type=EventType(model.event_type),
            severity=Severity(model.severity),
            user_id=model.user_id,
            user_session_id=model.user_session_id,
            user_ip_address=model.user_ip_address,
            user_role=model.user_role,
            user_department=model.user_department,
            resource_type=model.resource_type,
            resource_id=model.resource_id,
            resource_classification=model.resource_classification,
            resource_tags=model.resource_tags or [],
            action=model.action,
            action_result=model.action_result,
            action_metadata=model.action_metadata or {},
            policy_id=model.policy_id,
            policy_version=model.policy_version,
            classification_tier=model.classification_tier,
            classification_confidence=model.classification_confidence,
            classification_reasoning=model.classification_reasoning,
            parent_event_id=model.parent_event_id,
            lineage_chain=model.lineage_chain or [],
            compliance_flags=model.compliance_flags or [],
            retention_period_days=model.retention_period_days,
            previous_record_hash=model.previous_record_hash,
            record_hash=model.record_hash,
            signature=model.signature,
            system_id=model.system_id,
            system_version=model.system_version,
        )
