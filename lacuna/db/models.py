"""SQLAlchemy database models for Lacuna."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    TypeDecorator,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import relationship

from lacuna.db.base import Base


def _utc_now() -> datetime:
    """Get current UTC time in a timezone-aware manner."""
    return datetime.now(timezone.utc)


class StringList(TypeDecorator):  # type: ignore[type-arg]
    """Type that works as ARRAY on PostgreSQL and JSON on SQLite."""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):  # type: ignore[no-untyped-def]
        """Load dialect-specific implementation."""
        if dialect.name == "postgresql":
            return dialect.type_descriptor(ARRAY(String))
        return dialect.type_descriptor(JSON())

    def process_bind_param(self, value, dialect):  # type: ignore[no-untyped-def]
        """Process value when binding to parameter."""
        if value is None:
            return []
        return list(value)

    def process_result_value(self, value, dialect):  # type: ignore[no-untyped-def]
        """Process value when reading from result."""
        if value is None:
            return []
        return list(value)


class ClassificationModel(Base):
    """Database model for classification records."""

    __tablename__ = "classifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    timestamp = Column(DateTime, nullable=False, default=_utc_now, index=True)

    # Classification result
    tier = Column(String(20), nullable=False, index=True)
    confidence = Column(Float, nullable=False)
    reasoning = Column(Text, nullable=False)
    matched_rules: Column[list[str]] = Column(StringList(), default=list)
    tags: Column[list[str]] = Column(StringList(), default=list, index=True)

    # Classifier information
    classifier_name = Column(String(100), nullable=False)
    classifier_version = Column(String(50))

    # Lineage
    parent_id = Column(UUID(as_uuid=True), ForeignKey("classifications.id"))

    # Extra data
    extra_data = Column(JSON, default=dict)

    # Relationships
    parent = relationship("ClassificationModel", remote_side=[id])

    __table_args__ = (Index("idx_classification_tier_timestamp", "tier", "timestamp"),)


class LineageEdgeModel(Base):
    """Database model for lineage edges."""

    __tablename__ = "lineage_edges"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    timestamp = Column(DateTime, nullable=False, default=_utc_now, index=True)

    # Source and target artifacts
    source_artifact_id = Column(String(500), nullable=False, index=True)
    target_artifact_id = Column(String(500), nullable=False, index=True)

    # Operation type
    operation_type = Column(String(50), nullable=False)

    # Classifications
    source_classification_id = Column(
        UUID(as_uuid=True), ForeignKey("classifications.id")
    )
    target_classification_id = Column(
        UUID(as_uuid=True), ForeignKey("classifications.id")
    )

    # Extra data
    extra_data = Column(JSON, default=dict)

    # Relationships
    source_classification = relationship(
        "ClassificationModel", foreign_keys=[source_classification_id]
    )
    target_classification = relationship(
        "ClassificationModel", foreign_keys=[target_classification_id]
    )

    __table_args__ = (
        Index("idx_lineage_source", "source_artifact_id", "timestamp"),
        Index("idx_lineage_target", "target_artifact_id", "timestamp"),
        Index(
            "idx_lineage_unique",
            "source_artifact_id",
            "target_artifact_id",
            "operation_type",
            unique=True,
        ),
    )


class AuditLogModel(Base):
    """ISO 27001-compliant audit log model."""

    __tablename__ = "audit_log"

    # Core identity
    event_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    timestamp = Column(DateTime, nullable=False, default=_utc_now, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    severity = Column(String(20), nullable=False, index=True)

    # Actor identification
    user_id = Column(String(255), nullable=False, index=True)
    user_session_id = Column(String(255))
    user_ip_address = Column(String(45))  # IPv4/IPv6 compatible
    user_role = Column(String(100))
    user_department = Column(String(100))

    # Target resource
    resource_type = Column(String(50), nullable=False)
    resource_id = Column(String(500), nullable=False, index=True)
    resource_classification = Column(String(20), index=True)
    resource_tags: Column[list[str]] = Column(StringList(), default=list)

    # Action details
    action = Column(String(100), nullable=False)
    action_result = Column(String(20), nullable=False, index=True)
    action_metadata = Column(JSON, default=dict)

    # Policy/Governance
    policy_id = Column(String(100))
    policy_version = Column(String(50))
    classification_tier = Column(String(20))
    classification_confidence = Column(Float)
    classification_reasoning = Column(Text)

    # Lineage/Provenance
    parent_event_id = Column(UUID(as_uuid=True), ForeignKey("audit_log.event_id"))
    lineage_chain: Column[list[str]] = Column(StringList(), default=list)

    # Compliance metadata
    compliance_flags: Column[list[str]] = Column(StringList(), default=list)
    retention_period_days = Column(Integer, default=2555)

    # Tamper detection (hash chain)
    previous_record_hash = Column(String(64))
    record_hash = Column(String(64), nullable=False)
    signature = Column(Text)

    # System context
    system_id = Column(String(100))
    system_version = Column(String(50))

    # Relationships
    parent_event = relationship("AuditLogModel", remote_side=[event_id])

    __table_args__ = (
        Index("idx_audit_timestamp", "timestamp"),
        Index("idx_audit_user_timestamp", "user_id", "timestamp"),
        Index("idx_audit_resource_timestamp", "resource_id", "timestamp"),
        Index(
            "idx_audit_classification_timestamp", "resource_classification", "timestamp"
        ),
        Index("idx_audit_event_type", "event_type", "timestamp"),
        Index("idx_audit_action_result", "action_result", "timestamp"),
    )


class PolicyEvaluationModel(Base):
    """Database model for policy evaluation records."""

    __tablename__ = "policy_evaluations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    timestamp = Column(DateTime, nullable=False, default=_utc_now, index=True)

    # Policy information
    policy_id = Column(String(100), nullable=False, index=True)
    policy_version = Column(String(50))
    policy_name = Column(String(255))

    # Evaluation result
    allowed = Column(String(20), nullable=False, index=True)  # "allow", "deny", "error"
    reason = Column(Text, nullable=False)
    confidence = Column(Float)

    # Context
    user_id = Column(String(255), nullable=False, index=True)
    resource_id = Column(String(500), nullable=False)
    operation_type = Column(String(50), nullable=False)

    # Classification at time of evaluation
    classification_id = Column(UUID(as_uuid=True), ForeignKey("classifications.id"))

    # Evaluation extra data
    evaluation_duration_ms = Column(Float)
    alternatives = Column(JSON, default=list)
    extra_data = Column(JSON, default=dict)

    # Relationships
    classification = relationship("ClassificationModel")

    __table_args__ = (
        Index("idx_policy_eval_timestamp", "timestamp"),
        Index("idx_policy_eval_user", "user_id", "timestamp"),
        Index("idx_policy_eval_resource", "resource_id", "timestamp"),
        Index("idx_policy_eval_result", "allowed", "timestamp"),
    )
