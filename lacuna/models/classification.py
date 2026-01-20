"""Classification models for data sensitivity tiers."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4


def _utc_now() -> datetime:
    """Get current UTC time in a timezone-aware manner."""
    return datetime.now(timezone.utc)


class DataTier(str, Enum):
    """Data sensitivity tiers for classification."""

    PROPRIETARY = "PROPRIETARY"
    INTERNAL = "INTERNAL"
    PUBLIC = "PUBLIC"

    def __lt__(self, other: object) -> bool:  # type: ignore[override]
        """Compare tiers by sensitivity level."""
        if not isinstance(other, DataTier):
            return NotImplemented
        order = {
            DataTier.PUBLIC: 0,
            DataTier.INTERNAL: 1,
            DataTier.PROPRIETARY: 2,
        }
        return order[self] < order[other]

    def __le__(self, other: object) -> bool:  # type: ignore[override]
        """Compare tiers by sensitivity level."""
        if not isinstance(other, DataTier):
            return NotImplemented
        return self == other or self < other

    @property
    def value_int(self) -> int:
        """Get numeric value for tier (higher = more sensitive)."""
        return {
            DataTier.PUBLIC: 0,
            DataTier.INTERNAL: 1,
            DataTier.PROPRIETARY: 2,
        }[self]


class Severity(str, Enum):
    """Severity levels for audit events."""

    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class ClassificationContext:
    """Context information for classification decisions."""

    # User information
    user_id: Optional[str] = None
    user_role: Optional[str] = None
    user_department: Optional[str] = None
    session_id: Optional[str] = None

    # Request context
    project: Optional[str] = None
    environment: Optional[str] = None
    ip_address: Optional[str] = None

    # Conversation history
    conversation: list[dict[str, str]] = field(default_factory=list)

    # File context
    files: list[str] = field(default_factory=list)

    # Additional metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    # Timestamp
    timestamp: datetime = field(default_factory=_utc_now)


@dataclass
class Classification:
    """Result of a classification operation."""

    # Core classification
    tier: DataTier
    confidence: float  # 0.0 to 1.0

    # Reasoning
    reasoning: str
    matched_rules: list[str] = field(default_factory=list)

    # Tags (PII, PHI, FINANCIAL, etc.)
    tags: list[str] = field(default_factory=list)

    # Classification metadata
    classifier_name: str = "unknown"
    classifier_version: Optional[str] = None
    classification_id: UUID = field(default_factory=uuid4)
    classified_at: datetime = field(default_factory=_utc_now)

    # Lineage
    parent_classification_id: Optional[UUID] = None

    # Additional metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "tier": self.tier.value,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "matched_rules": self.matched_rules,
            "tags": self.tags,
            "classifier_name": self.classifier_name,
            "classifier_version": self.classifier_version,
            "classification_id": str(self.classification_id),
            "classified_at": self.classified_at.isoformat(),
            "parent_classification_id": (
                str(self.parent_classification_id)
                if self.parent_classification_id
                else None
            ),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Classification":
        """Create from dictionary representation."""
        return cls(
            tier=DataTier(data["tier"]),
            confidence=data["confidence"],
            reasoning=data["reasoning"],
            matched_rules=data.get("matched_rules", []),
            tags=data.get("tags", []),
            classifier_name=data.get("classifier_name", "unknown"),
            classifier_version=data.get("classifier_version"),
            classification_id=(
                UUID(data["classification_id"])
                if "classification_id" in data
                else uuid4()
            ),
            classified_at=(
                datetime.fromisoformat(data["classified_at"])
                if "classified_at" in data
                else _utc_now()
            ),
            parent_classification_id=(
                UUID(data["parent_classification_id"])
                if data.get("parent_classification_id")
                else None
            ),
            metadata=data.get("metadata", {}),
        )

    def inherit_from(self, parent: "Classification") -> "Classification":
        """
        Create a new classification inheriting properties from parent.

        Uses the most restrictive tier between self and parent.
        """
        # Inherit the more restrictive tier
        inherited_tier = max(self.tier, parent.tier)

        # Merge tags
        inherited_tags = list(set(self.tags + parent.tags))

        # Combine reasoning
        inherited_reasoning = (
            f"{self.reasoning} (inherited from parent: {parent.reasoning})"
        )

        return Classification(
            tier=inherited_tier,
            confidence=min(self.confidence, parent.confidence),
            reasoning=inherited_reasoning,
            matched_rules=self.matched_rules + parent.matched_rules,
            tags=inherited_tags,
            classifier_name=self.classifier_name,
            classifier_version=self.classifier_version,
            parent_classification_id=parent.classification_id,
            metadata={**parent.metadata, **self.metadata},
        )
