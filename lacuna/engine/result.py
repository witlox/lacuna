"""Result model for governance engine evaluations."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID, uuid4

from lacuna.models.classification import Classification
from lacuna.models.data_operation import DataOperation
from lacuna.models.policy import PolicyDecision


def _utc_now() -> datetime:
    """Get current UTC time in a timezone-aware manner."""
    return datetime.now(timezone.utc)


@dataclass
class GovernanceResult:
    """
    Complete result of a governance evaluation.

    Combines classification, policy decision, and audit information
    into a single result object.
    """

    # Identification
    evaluation_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=_utc_now)

    # The operation that was evaluated
    operation: Optional[DataOperation] = None

    # Classification result
    classification: Optional[Classification] = None

    # Policy decision
    allowed: bool = True
    policy_decision: Optional[PolicyDecision] = None

    # Reasoning and feedback
    reasoning: str = ""
    alternatives: list[str] = field(default_factory=list)
    matched_rules: list[str] = field(default_factory=list)

    # Lineage
    lineage_chain: list[str] = field(default_factory=list)

    # Performance metrics
    classification_latency_ms: Optional[float] = None
    policy_latency_ms: Optional[float] = None
    total_latency_ms: Optional[float] = None

    # Audit
    audit_event_id: Optional[UUID] = None

    # Error information
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "evaluation_id": str(self.evaluation_id),
            "timestamp": self.timestamp.isoformat(),
            "allowed": self.allowed,
            "classification": (
                self.classification.to_dict() if self.classification else None
            ),
            "classification_tier": (
                self.classification.tier.value if self.classification else None
            ),
            "confidence": (
                self.classification.confidence if self.classification else None
            ),
            "reasoning": self.reasoning,
            "alternatives": self.alternatives,
            "matched_rules": self.matched_rules,
            "tags": self.classification.tags if self.classification else [],
            "lineage_chain": self.lineage_chain,
            "latency_ms": self.total_latency_ms,
            "audit_event_id": str(self.audit_event_id) if self.audit_event_id else None,
            "error": self.error,
        }

    def to_user_message(self) -> str:
        """Generate user-friendly message about the evaluation result."""
        if self.allowed:
            tier = self.classification.tier.value if self.classification else "UNKNOWN"
            confidence = self.classification.confidence if self.classification else 0
            return (
                f"✓ Operation allowed\n"
                f"Classification: {tier} ({confidence:.0%} confidence)\n"
                f"Reasoning: {self.reasoning}"
            )
        else:
            lines = [
                "❌ Governance Policy Violation\n",
                f"Action: {self.operation.operation_type.value if self.operation else 'unknown'}",
            ]

            if self.operation and self.operation.destination:
                lines.append(f"Destination: {self.operation.destination}")

            lines.append(f"Reason: {self.reasoning}")

            if self.classification:
                lines.append(f"Classification: {self.classification.tier.value}")
                if self.classification.tags:
                    lines.append(f"Tags: {', '.join(self.classification.tags)}")

            if self.alternatives:
                lines.append("\nAlternatives:")
                for i, alt in enumerate(self.alternatives, 1):
                    lines.append(f"  {i}. {alt}")

            if self.matched_rules:
                lines.append(f"\nPolicy: {', '.join(self.matched_rules)}")

            return "\n".join(lines)

    @property
    def is_denied(self) -> bool:
        """Check if the operation was denied."""
        return not self.allowed

    @property
    def tier(self) -> Optional[str]:
        """Get classification tier value."""
        return self.classification.tier.value if self.classification else None

    @property
    def confidence(self) -> Optional[float]:
        """Get classification confidence."""
        return self.classification.confidence if self.classification else None

    @property
    def tags(self) -> list[str]:
        """Get classification tags."""
        return self.classification.tags if self.classification else []
