"""Policy models for OPA integration and policy evaluation."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID, uuid4


def _utc_now() -> datetime:
    """Get current UTC time in a timezone-aware manner."""
    return datetime.now(timezone.utc)


@dataclass
class PolicyDecision:
    """
    Result of a policy evaluation by OPA.

    Represents whether an operation is allowed or denied,
    along with detailed reasoning and suggested alternatives.
    """

    # Decision
    allowed: bool = False
    decision_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=_utc_now)

    # Policy information
    policy_id: Optional[str] = None
    policy_version: Optional[str] = None
    policy_name: Optional[str] = None

    # Reasoning
    reasoning: str = ""
    matched_rules: list[str] = field(default_factory=list)

    # Alternatives (when denied)
    alternatives: list[str] = field(default_factory=list)

    # Additional context
    evaluated_conditions: dict[str, bool] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    # Performance metrics
    evaluation_time_ms: Optional[float] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "allowed": self.allowed,
            "decision_id": str(self.decision_id),
            "timestamp": self.timestamp.isoformat(),
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "policy_name": self.policy_name,
            "reasoning": self.reasoning,
            "matched_rules": self.matched_rules,
            "alternatives": self.alternatives,
            "evaluated_conditions": self.evaluated_conditions,
            "metadata": self.metadata,
            "evaluation_time_ms": self.evaluation_time_ms,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PolicyDecision":
        """Create from dictionary representation."""
        return cls(
            allowed=data.get("allowed", False),
            decision_id=UUID(data["decision_id"]) if "decision_id" in data else uuid4(),
            timestamp=(
                datetime.fromisoformat(data["timestamp"])
                if "timestamp" in data
                else _utc_now()
            ),
            policy_id=data.get("policy_id"),
            policy_version=data.get("policy_version"),
            policy_name=data.get("policy_name"),
            reasoning=data.get("reasoning", ""),
            matched_rules=data.get("matched_rules", []),
            alternatives=data.get("alternatives", []),
            evaluated_conditions=data.get("evaluated_conditions", {}),
            metadata=data.get("metadata", {}),
            evaluation_time_ms=data.get("evaluation_time_ms"),
        )

    def is_deny(self) -> bool:
        """Check if this decision denies the operation."""
        return not self.allowed

    def has_alternatives(self) -> bool:
        """Check if alternatives are available for denied operations."""
        return len(self.alternatives) > 0


@dataclass
class PolicyInput:
    """
    Input data for policy evaluation.

    This represents the complete context that OPA needs to make
    a policy decision about a data operation.
    """

    # Operation details
    action: str  # read, write, export, etc.
    resource_type: str  # file, table, dataset
    resource_id: str

    # Data classification
    classification_tier: Optional[str] = None  # PROPRIETARY/INTERNAL/PUBLIC
    classification_confidence: Optional[float] = None
    tags: list[str] = field(default_factory=list)  # PII, PHI, FINANCIAL

    # User context
    user_id: Optional[str] = None
    user_role: Optional[str] = None
    user_clearance: Optional[str] = None
    user_department: Optional[str] = None

    # Destination (for exports/writes)
    destination: Optional[str] = None
    destination_type: Optional[str] = None
    destination_encrypted: bool = False

    # Lineage
    lineage_chain: list[str] = field(default_factory=list)

    # Additional context
    environment: Optional[str] = None  # production, staging, dev
    project: Optional[str] = None
    purpose: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation for OPA."""
        return {
            "action": self.action,
            "source": {
                "type": self.resource_type,
                "id": self.resource_id,
                "classification": self.classification_tier,
                "confidence": self.classification_confidence,
                "tags": self.tags,
                "lineage": self.lineage_chain,
            },
            "destination": (
                {
                    "path": self.destination,
                    "type": self.destination_type,
                    "encrypted": self.destination_encrypted,
                }
                if self.destination
                else None
            ),
            "user": {
                "id": self.user_id,
                "role": self.user_role,
                "clearance": self.user_clearance,
                "department": self.user_department,
            },
            "context": {
                "environment": self.environment,
                "project": self.project,
                "purpose": self.purpose,
                "metadata": self.metadata,
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PolicyInput":
        """Create from dictionary representation."""
        source = data.get("source", {})
        destination = data.get("destination", {})
        user = data.get("user", {})
        context = data.get("context", {})

        return cls(
            action=data.get("action", ""),
            resource_type=source.get("type", ""),
            resource_id=source.get("id", ""),
            classification_tier=source.get("classification"),
            classification_confidence=source.get("confidence"),
            tags=source.get("tags", []),
            user_id=user.get("id"),
            user_role=user.get("role"),
            user_clearance=user.get("clearance"),
            user_department=user.get("department"),
            destination=destination.get("path") if destination else None,
            destination_type=destination.get("type") if destination else None,
            destination_encrypted=(
                destination.get("encrypted", False) if destination else False
            ),
            lineage_chain=source.get("lineage", []),
            environment=context.get("environment"),
            project=context.get("project"),
            purpose=context.get("purpose"),
            metadata=context.get("metadata", {}),
        )


@dataclass
class PolicyEvaluation:
    """
    Complete policy evaluation result including decision and audit information.

    This combines the policy decision with additional metadata for
    audit logging and tracking.
    """

    # The decision
    decision: PolicyDecision

    # Evaluation metadata
    evaluation_id: UUID = field(default_factory=uuid4)
    evaluated_at: datetime = field(default_factory=_utc_now)

    # Input that was evaluated
    policy_input: Optional[PolicyInput] = None

    # OPA server information
    opa_endpoint: Optional[str] = None
    opa_policy_path: Optional[str] = None

    # Error information (if evaluation failed)
    error: Optional[str] = None
    error_details: Optional[dict[str, Any]] = None

    # Fallback information
    is_fallback: bool = False
    fallback_reason: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "decision": self.decision.to_dict(),
            "evaluation_id": str(self.evaluation_id),
            "evaluated_at": self.evaluated_at.isoformat(),
            "policy_input": self.policy_input.to_dict() if self.policy_input else None,
            "opa_endpoint": self.opa_endpoint,
            "opa_policy_path": self.opa_policy_path,
            "error": self.error,
            "error_details": self.error_details,
            "is_fallback": self.is_fallback,
            "fallback_reason": self.fallback_reason,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PolicyEvaluation":
        """Create from dictionary representation."""
        decision_data = data.get("decision", {})
        policy_input_data = data.get("policy_input")

        return cls(
            decision=PolicyDecision.from_dict(decision_data),
            evaluation_id=(
                UUID(data["evaluation_id"]) if "evaluation_id" in data else uuid4()
            ),
            evaluated_at=(
                datetime.fromisoformat(data["evaluated_at"])
                if "evaluated_at" in data
                else _utc_now()
            ),
            policy_input=(
                PolicyInput.from_dict(policy_input_data) if policy_input_data else None
            ),
            opa_endpoint=data.get("opa_endpoint"),
            opa_policy_path=data.get("opa_policy_path"),
            error=data.get("error"),
            error_details=data.get("error_details"),
            is_fallback=data.get("is_fallback", False),
            fallback_reason=data.get("fallback_reason"),
        )

    def is_success(self) -> bool:
        """Check if the evaluation completed successfully."""
        return self.error is None

    def is_allowed(self) -> bool:
        """Check if the operation is allowed."""
        return self.decision.allowed

    def is_denied(self) -> bool:
        """Check if the operation is denied."""
        return not self.decision.allowed


@dataclass
class PolicyRule:
    """
    Represents a single policy rule.

    Used for policy management and documentation.
    """

    # Rule identification
    rule_id: str
    name: str
    description: str

    # Rule definition
    conditions: list[str] = field(default_factory=list)
    action: str = "deny"  # allow or deny

    # Priority (higher number = higher priority)
    priority: int = 0

    # Metadata
    version: str = "1.0.0"
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)
    created_by: Optional[str] = None
    tags: list[str] = field(default_factory=list)

    # Status
    enabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "description": self.description,
            "conditions": self.conditions,
            "action": self.action,
            "priority": self.priority,
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "created_by": self.created_by,
            "tags": self.tags,
            "enabled": self.enabled,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PolicyRule":
        """Create from dictionary representation."""
        return cls(
            rule_id=data["rule_id"],
            name=data["name"],
            description=data["description"],
            conditions=data.get("conditions", []),
            action=data.get("action", "deny"),
            priority=data.get("priority", 0),
            version=data.get("version", "1.0.0"),
            created_at=(
                datetime.fromisoformat(data["created_at"])
                if "created_at" in data
                else _utc_now()
            ),
            updated_at=(
                datetime.fromisoformat(data["updated_at"])
                if "updated_at" in data
                else _utc_now()
            ),
            created_by=data.get("created_by"),
            tags=data.get("tags", []),
            enabled=data.get("enabled", True),
        )
