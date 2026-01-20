"""Audit models for ISO 27001-compliant logging."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4


def _utc_now() -> datetime:
    """Get current UTC time in a timezone-aware manner."""
    return datetime.now(timezone.utc)


class EventType(str, Enum):
    """Types of auditable events (ISO 27001 A.12.4.1)."""

    # Access Events (A.9.4.1)
    DATA_ACCESS = "data.access"
    DATA_READ = "data.read"
    DATA_WRITE = "data.write"
    DATA_DELETE = "data.delete"
    DATA_EXPORT = "data.export"

    # Classification Events
    CLASSIFICATION_AUTO = "classification.automatic"
    CLASSIFICATION_MANUAL = "classification.manual_override"
    CLASSIFICATION_POLICY_CHANGE = "classification.policy_change"

    # Policy Events
    POLICY_EVALUATION = "policy.evaluation"
    POLICY_ALLOW = "policy.allow"
    POLICY_DENY = "policy.deny"
    POLICY_EXCEPTION = "policy.exception_granted"

    # Administrative Events (A.12.4.3)
    ADMIN_POLICY_CREATE = "admin.policy.create"
    ADMIN_POLICY_UPDATE = "admin.policy.update"
    ADMIN_POLICY_DELETE = "admin.policy.delete"
    ADMIN_USER_GRANT = "admin.user.grant_access"
    ADMIN_USER_REVOKE = "admin.user.revoke_access"

    # Authentication Events
    AUTH_SUCCESS = "auth.success"
    AUTH_FAILURE = "auth.failure"
    AUTH_LOGOUT = "auth.logout"

    # System Events
    SYSTEM_CONFIG_CHANGE = "system.config.change"
    SYSTEM_ERROR = "system.error"
    AUDIT_LOG_ACCESS = "audit.log.access"
    INTEGRITY_CHECK = "audit.integrity_check"


class Severity(str, Enum):
    """Severity levels for audit events."""

    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class AuditRecord:
    """
    ISO 27001-compliant audit record.

    This comprehensive record captures all information required for
    compliance with ISO 27001/27002 controls, particularly:
    - A.9.4: System and Application Access Control
    - A.12.4: Logging and Monitoring
    - A.18.1: Compliance with Legal and Contractual Requirements
    """

    # Core Identity (A.12.4.1)
    event_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=_utc_now)
    event_type: EventType = EventType.DATA_ACCESS
    severity: Severity = Severity.INFO

    # Actor Identification (A.9.4.1)
    user_id: str = ""
    user_session_id: Optional[str] = None
    user_ip_address: Optional[str] = None
    user_role: Optional[str] = None
    user_department: Optional[str] = None
    user_clearance: Optional[str] = None

    # Target Resource (A.9.4.1)
    resource_type: str = "unknown"  # dataset, table, file, query
    resource_id: str = ""
    resource_classification: Optional[str] = None  # PROPRIETARY/INTERNAL/PUBLIC
    resource_tags: list[str] = field(default_factory=list)  # PII, PHI, FINANCIAL

    # Action Details (A.12.4.1)
    action: str = ""  # read, write, classify, export
    action_result: str = ""  # success, denied, error
    action_metadata: dict[str, Any] = field(default_factory=dict)

    # Policy/Governance
    policy_id: Optional[str] = None
    policy_version: Optional[str] = None
    classification_tier: Optional[str] = None
    classification_confidence: Optional[float] = None
    classification_reasoning: Optional[str] = None

    # Lineage/Provenance
    parent_event_id: Optional[UUID] = None
    lineage_chain: list[str] = field(default_factory=list)

    # Compliance Metadata (A.18.1)
    compliance_flags: list[str] = field(default_factory=list)  # GDPR, HIPAA, SOX
    retention_period_days: int = 2555  # 7 years default

    # Tamper Detection (A.12.4.2)
    previous_record_hash: Optional[str] = None
    record_hash: str = ""
    signature: Optional[str] = None

    # System Context
    system_id: str = "lacuna"
    system_version: str = "0.1.0"
    environment: Optional[str] = None  # production, staging, dev

    # Additional metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "event_id": str(self.event_id),
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type.value,
            "severity": self.severity.value,
            "user_id": self.user_id,
            "user_session_id": self.user_session_id,
            "user_ip_address": self.user_ip_address,
            "user_role": self.user_role,
            "user_department": self.user_department,
            "user_clearance": self.user_clearance,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "resource_classification": self.resource_classification,
            "resource_tags": self.resource_tags,
            "action": self.action,
            "action_result": self.action_result,
            "action_metadata": self.action_metadata,
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "classification_tier": self.classification_tier,
            "classification_confidence": self.classification_confidence,
            "classification_reasoning": self.classification_reasoning,
            "parent_event_id": (
                str(self.parent_event_id) if self.parent_event_id else None
            ),
            "lineage_chain": self.lineage_chain,
            "compliance_flags": self.compliance_flags,
            "retention_period_days": self.retention_period_days,
            "previous_record_hash": self.previous_record_hash,
            "record_hash": self.record_hash,
            "signature": self.signature,
            "system_id": self.system_id,
            "system_version": self.system_version,
            "environment": self.environment,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AuditRecord":
        """Create from dictionary representation."""
        return cls(
            event_id=UUID(data["event_id"]) if "event_id" in data else uuid4(),
            timestamp=(
                datetime.fromisoformat(data["timestamp"])
                if "timestamp" in data
                else _utc_now()
            ),
            event_type=EventType(data.get("event_type", "data.access")),
            severity=Severity(data.get("severity", "INFO")),
            user_id=data.get("user_id", ""),
            user_session_id=data.get("user_session_id"),
            user_ip_address=data.get("user_ip_address"),
            user_role=data.get("user_role"),
            user_department=data.get("user_department"),
            user_clearance=data.get("user_clearance"),
            resource_type=data.get("resource_type", "unknown"),
            resource_id=data.get("resource_id", ""),
            resource_classification=data.get("resource_classification"),
            resource_tags=data.get("resource_tags", []),
            action=data.get("action", ""),
            action_result=data.get("action_result", ""),
            action_metadata=data.get("action_metadata", {}),
            policy_id=data.get("policy_id"),
            policy_version=data.get("policy_version"),
            classification_tier=data.get("classification_tier"),
            classification_confidence=data.get("classification_confidence"),
            classification_reasoning=data.get("classification_reasoning"),
            parent_event_id=(
                UUID(data["parent_event_id"]) if data.get("parent_event_id") else None
            ),
            lineage_chain=data.get("lineage_chain", []),
            compliance_flags=data.get("compliance_flags", []),
            retention_period_days=data.get("retention_period_days", 2555),
            previous_record_hash=data.get("previous_record_hash"),
            record_hash=data.get("record_hash", ""),
            signature=data.get("signature"),
            system_id=data.get("system_id", "lacuna"),
            system_version=data.get("system_version", "0.1.0"),
            environment=data.get("environment"),
            metadata=data.get("metadata", {}),
        )

    def compute_hash(self) -> str:
        """
        Compute SHA-256 hash of the record for tamper detection.

        This creates a hash chain by including the previous record's hash,
        enabling verification of audit log integrity per ISO 27001 A.12.4.2.

        Returns:
            Hexadecimal string representation of the hash
        """
        import hashlib
        import json

        # Create deterministic serialization
        hash_data = {
            "event_id": str(self.event_id),
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type.value,
            "user_id": self.user_id,
            "resource_id": self.resource_id,
            "action": self.action,
            "action_result": self.action_result,
            "previous_record_hash": self.previous_record_hash,
        }

        serialized = json.dumps(hash_data, sort_keys=True)
        return hashlib.sha256(serialized.encode()).hexdigest()

    def is_sensitive_event(self) -> bool:
        """Check if this event involves sensitive data access."""
        sensitive_classifications = {"PROPRIETARY"}
        sensitive_tags = {"PII", "PHI", "FINANCIAL", "CONFIDENTIAL"}

        return self.resource_classification in sensitive_classifications or bool(
            sensitive_tags.intersection(set(self.resource_tags))
        )

    def is_policy_violation(self) -> bool:
        """Check if this event represents a policy violation."""
        return (
            self.action_result == "denied" or self.event_type == EventType.POLICY_DENY
        )

    def is_administrative_action(self) -> bool:
        """Check if this is an administrative event (A.12.4.3)."""
        admin_events = {
            EventType.ADMIN_POLICY_CREATE,
            EventType.ADMIN_POLICY_UPDATE,
            EventType.ADMIN_POLICY_DELETE,
            EventType.ADMIN_USER_GRANT,
            EventType.ADMIN_USER_REVOKE,
        }
        return self.event_type in admin_events


@dataclass
class AuditQuery:
    """
    Query parameters for searching audit records.

    Used for compliance reporting and investigation.
    """

    # Time range
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    # Filters
    user_id: Optional[str] = None
    resource_id: Optional[str] = None
    event_types: list[EventType] = field(default_factory=list)
    severities: list[Severity] = field(default_factory=list)
    action_result: Optional[str] = None  # success, denied, error

    # Classification filters
    resource_classification: Optional[str] = None
    resource_tags: list[str] = field(default_factory=list)

    # Compliance filters
    compliance_flags: list[str] = field(default_factory=list)

    # Pagination
    limit: int = 100
    offset: int = 0

    # Sorting
    order_by: str = "timestamp"
    order_desc: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "user_id": self.user_id,
            "resource_id": self.resource_id,
            "event_types": [et.value for et in self.event_types],
            "severities": [s.value for s in self.severities],
            "action_result": self.action_result,
            "resource_classification": self.resource_classification,
            "resource_tags": self.resource_tags,
            "compliance_flags": self.compliance_flags,
            "limit": self.limit,
            "offset": self.offset,
            "order_by": self.order_by,
            "order_desc": self.order_desc,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AuditQuery":
        """Create from dictionary representation."""
        return cls(
            start_time=(
                datetime.fromisoformat(data["start_time"])
                if data.get("start_time")
                else None
            ),
            end_time=(
                datetime.fromisoformat(data["end_time"])
                if data.get("end_time")
                else None
            ),
            user_id=data.get("user_id"),
            resource_id=data.get("resource_id"),
            event_types=[EventType(et) for et in data.get("event_types", [])],
            severities=[Severity(s) for s in data.get("severities", [])],
            action_result=data.get("action_result"),
            resource_classification=data.get("resource_classification"),
            resource_tags=data.get("resource_tags", []),
            compliance_flags=data.get("compliance_flags", []),
            limit=data.get("limit", 100),
            offset=data.get("offset", 0),
            order_by=data.get("order_by", "timestamp"),
            order_desc=data.get("order_desc", True),
        )
