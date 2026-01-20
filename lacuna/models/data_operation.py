"""Data operation models for tracking data access and transformations."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4


def _utc_now() -> datetime:
    """Get current UTC time in a timezone-aware manner."""
    return datetime.now(timezone.utc)


class OperationType(str, Enum):
    """Types of data operations that can be performed."""

    # Basic operations
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    EXPORT = "export"

    # Query operations
    QUERY = "query"
    SELECT = "select"
    INSERT = "insert"
    UPDATE = "update"

    # Transformation operations
    TRANSFORM = "transform"
    JOIN = "join"
    AGGREGATE = "aggregate"
    FILTER = "filter"
    ANONYMIZE = "anonymize"

    # Classification operations
    CLASSIFY = "classify"
    RECLASSIFY = "reclassify"

    # Administrative operations
    GRANT = "grant"
    REVOKE = "revoke"

    # System operations
    BACKUP = "backup"
    RESTORE = "restore"
    ARCHIVE = "archive"


@dataclass
class UserContext:
    """User context for data operations."""

    user_id: str
    user_role: Optional[str] = None
    user_department: Optional[str] = None
    user_clearance: Optional[str] = None
    session_id: Optional[str] = None
    ip_address: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "user_id": self.user_id,
            "user_role": self.user_role,
            "user_department": self.user_department,
            "user_clearance": self.user_clearance,
            "session_id": self.session_id,
            "ip_address": self.ip_address,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UserContext":
        """Create from dictionary representation."""
        return cls(
            user_id=data["user_id"],
            user_role=data.get("user_role"),
            user_department=data.get("user_department"),
            user_clearance=data.get("user_clearance"),
            session_id=data.get("session_id"),
            ip_address=data.get("ip_address"),
        )


@dataclass
class DataOperation:
    """
    Represents a data operation for governance tracking.

    This model captures all relevant information about a data operation
    including the action being performed, the resources involved, the user
    context, and any transformation details.
    """

    # Operation identification
    operation_id: UUID = field(default_factory=uuid4)
    operation_type: OperationType = OperationType.READ
    timestamp: datetime = field(default_factory=_utc_now)

    # Resource information
    resource_type: str = "unknown"  # file, table, dataset, query
    resource_id: str = ""  # Path, table name, dataset ID
    resource_path: Optional[str] = None

    # Source and destination (for transformations)
    sources: list[str] = field(default_factory=list)
    destination: Optional[str] = None
    destination_type: Optional[str] = None
    destination_encrypted: bool = False

    # User context
    user: Optional[UserContext] = None

    # Operation context
    purpose: Optional[str] = None  # Business justification
    environment: Optional[str] = None  # production, staging, dev
    project: Optional[str] = None

    # Transformation details
    code: Optional[str] = None  # SQL, Python, etc.
    transformation_type: Optional[str] = None  # join, aggregate, filter

    # Lineage
    lineage_chain: list[str] = field(default_factory=list)
    parent_operation_id: Optional[UUID] = None

    # Additional metadata
    metadata: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)

    # Result information (populated after operation)
    success: Optional[bool] = None
    error_message: Optional[str] = None
    records_affected: Optional[int] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "operation_id": str(self.operation_id),
            "operation_type": self.operation_type.value,
            "timestamp": self.timestamp.isoformat(),
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "resource_path": self.resource_path,
            "sources": self.sources,
            "destination": self.destination,
            "destination_type": self.destination_type,
            "destination_encrypted": self.destination_encrypted,
            "user": self.user.to_dict() if self.user else None,
            "purpose": self.purpose,
            "environment": self.environment,
            "project": self.project,
            "code": self.code,
            "transformation_type": self.transformation_type,
            "lineage_chain": self.lineage_chain,
            "parent_operation_id": (
                str(self.parent_operation_id) if self.parent_operation_id else None
            ),
            "metadata": self.metadata,
            "tags": self.tags,
            "success": self.success,
            "error_message": self.error_message,
            "records_affected": self.records_affected,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DataOperation":
        """Create from dictionary representation."""
        user_data = data.get("user")
        return cls(
            operation_id=(
                UUID(data["operation_id"]) if "operation_id" in data else uuid4()
            ),
            operation_type=OperationType(data.get("operation_type", "read")),
            timestamp=(
                datetime.fromisoformat(data["timestamp"])
                if "timestamp" in data
                else _utc_now()
            ),
            resource_type=data.get("resource_type", "unknown"),
            resource_id=data.get("resource_id", ""),
            resource_path=data.get("resource_path"),
            sources=data.get("sources", []),
            destination=data.get("destination"),
            destination_type=data.get("destination_type"),
            destination_encrypted=data.get("destination_encrypted", False),
            user=UserContext.from_dict(user_data) if user_data else None,
            purpose=data.get("purpose"),
            environment=data.get("environment"),
            project=data.get("project"),
            code=data.get("code"),
            transformation_type=data.get("transformation_type"),
            lineage_chain=data.get("lineage_chain", []),
            parent_operation_id=(
                UUID(data["parent_operation_id"])
                if data.get("parent_operation_id")
                else None
            ),
            metadata=data.get("metadata", {}),
            tags=data.get("tags", []),
            success=data.get("success"),
            error_message=data.get("error_message"),
            records_affected=data.get("records_affected"),
        )

    def is_transformation(self) -> bool:
        """Check if this operation is a data transformation."""
        transformation_ops = {
            OperationType.TRANSFORM,
            OperationType.JOIN,
            OperationType.AGGREGATE,
            OperationType.FILTER,
            OperationType.ANONYMIZE,
        }
        return self.operation_type in transformation_ops

    def is_export(self) -> bool:
        """Check if this operation exports data outside the system."""
        return self.operation_type == OperationType.EXPORT

    def is_write_operation(self) -> bool:
        """Check if this operation writes or modifies data."""
        write_ops = {
            OperationType.WRITE,
            OperationType.INSERT,
            OperationType.UPDATE,
            OperationType.DELETE,
        }
        return self.operation_type in write_ops
