"""Policy engine for evaluating data governance policies."""

import time
from typing import Any, Optional

import structlog

from lacuna.config import get_settings
from lacuna.models.classification import Classification, DataTier
from lacuna.models.data_operation import DataOperation, OperationType
from lacuna.models.policy import PolicyDecision, PolicyEvaluation, PolicyInput
from lacuna.policy.client import OPAClient

logger = structlog.get_logger()


class PolicyEngine:
    """
    Policy evaluation engine with OPA integration.

    Features:
    - OPA-based policy evaluation
    - Built-in fallback policies
    - Caching for performance
    - Detailed decision reasoning
    """

    def __init__(
        self,
        opa_client: Optional[OPAClient] = None,
        enabled: bool = True,
        fallback_on_error: bool = True,
    ):
        """Initialize policy engine.

        Args:
            opa_client: OPA client for policy evaluation
            enabled: Enable/disable policy evaluation
            fallback_on_error: Use fallback policies on OPA errors
        """
        settings = get_settings()
        self.enabled = enabled and settings.policy.enabled
        self.fallback_on_error = fallback_on_error

        self._opa_client = opa_client or OPAClient()
        self._cache: dict[str, PolicyDecision] = {}
        self._cache_ttl = 300  # 5 minutes

    def evaluate(
        self,
        operation: DataOperation,
        classification: Optional[Classification] = None,
    ) -> PolicyEvaluation:
        """Evaluate a data operation against policies.

        Args:
            operation: Data operation to evaluate
            classification: Classification of the data

        Returns:
            Complete policy evaluation result
        """
        start_time = time.time()

        if not self.enabled:
            # Policy engine disabled - allow all
            return PolicyEvaluation(
                decision=PolicyDecision(
                    allowed=True,
                    reasoning="Policy engine disabled - operation allowed",
                ),
                is_fallback=True,
                fallback_reason="Policy engine disabled",
            )

        # Build policy input
        policy_input = self._build_policy_input(operation, classification)

        # Check cache
        cache_key = self._make_cache_key(policy_input)
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            logger.debug("policy_cache_hit", action=operation.operation_type.value)
            return PolicyEvaluation(
                decision=cached,
                policy_input=policy_input,
            )

        # Try OPA evaluation
        decision = None
        opa_error = None

        if self._opa_client.is_available():
            try:
                opa_result = self._opa_client.evaluate(policy_input.to_dict())
                if opa_result:
                    decision = self._parse_opa_result(opa_result)
            except Exception as e:
                opa_error = str(e)
                logger.warning("opa_evaluation_error", error=opa_error)

        # Fallback to built-in policies
        is_fallback = False
        if decision is None:
            if self.fallback_on_error:
                decision = self._evaluate_fallback(operation, classification)
                is_fallback = True
            else:
                decision = PolicyDecision(
                    allowed=False,
                    reasoning="Policy evaluation failed and fallback disabled",
                )

        # Record evaluation time
        elapsed_ms = (time.time() - start_time) * 1000
        decision.evaluation_time_ms = elapsed_ms

        # Cache result
        self._cache[cache_key] = decision

        logger.info(
            "policy_evaluated",
            action=operation.operation_type.value,
            allowed=decision.allowed,
            is_fallback=is_fallback,
            latency_ms=round(elapsed_ms, 2),
        )

        return PolicyEvaluation(
            decision=decision,
            policy_input=policy_input,
            opa_endpoint=self._opa_client.endpoint,
            opa_policy_path=self._opa_client.policy_path,
            error=opa_error,
            is_fallback=is_fallback,
            fallback_reason="OPA unavailable" if is_fallback and opa_error else None,
        )

    def _build_policy_input(
        self,
        operation: DataOperation,
        classification: Optional[Classification],
    ) -> PolicyInput:
        """Build policy input from operation and classification."""
        return PolicyInput(
            action=operation.operation_type.value,
            resource_type=operation.resource_type,
            resource_id=operation.resource_id,
            classification_tier=classification.tier.value if classification else None,
            classification_confidence=(
                classification.confidence if classification else None
            ),
            tags=classification.tags if classification else [],
            user_id=operation.user.user_id if operation.user else None,
            user_role=operation.user.user_role if operation.user else None,
            user_clearance=operation.user.user_clearance if operation.user else None,
            user_department=operation.user.user_department if operation.user else None,
            destination=operation.destination,
            destination_type=operation.destination_type,
            destination_encrypted=operation.destination_encrypted,
            lineage_chain=operation.lineage_chain,
            environment=operation.environment,
            project=operation.project,
            purpose=operation.purpose,
        )

    def _parse_opa_result(self, result: dict[str, Any]) -> PolicyDecision:
        """Parse OPA evaluation result into PolicyDecision."""
        # Handle different OPA response formats

        # Format 1: Direct allow/deny
        if "allow" in result:
            allowed = result["allow"]
            reasoning = result.get(
                "reason", result.get("reasoning", "Policy evaluated")
            )
            alternatives = result.get("alternatives", [])

            return PolicyDecision(
                allowed=allowed,
                reasoning=reasoning,
                alternatives=alternatives,
                matched_rules=result.get("matched_rules", []),
                policy_id=result.get("policy_id"),
                policy_version=result.get("policy_version"),
            )

        # Format 2: Deny rules (deny is a set of reasons)
        if "deny" in result:
            deny_reasons = result["deny"]
            if deny_reasons:
                return PolicyDecision(
                    allowed=False,
                    reasoning="; ".join(str(r) for r in deny_reasons),
                    alternatives=result.get("alternatives", []),
                    matched_rules=list(deny_reasons),
                )
            return PolicyDecision(
                allowed=True,
                reasoning="No deny rules matched",
            )

        # Format 3: Classification result
        if "classification" in result:
            classifications = result["classification"]
            if classifications:
                # Take highest confidence classification
                best = max(classifications, key=lambda c: c.get("confidence", 0))
                return PolicyDecision(
                    allowed=True,
                    reasoning=best.get("reasoning", "Classification policy matched"),
                    metadata={"classification": best},
                )

        # Default: allow if no explicit deny
        return PolicyDecision(
            allowed=True,
            reasoning="No explicit policy decision - allowing by default",
        )

    def _evaluate_fallback(
        self,
        operation: DataOperation,
        classification: Optional[Classification],
    ) -> PolicyDecision:
        """Evaluate using built-in fallback policies.

        Fallback rules:
        1. PROPRIETARY data cannot be exported to unmanaged locations
        2. PROPRIETARY data requires encryption for external destinations
        3. Internal operations on INTERNAL data are allowed
        4. PUBLIC data has no restrictions
        """
        tier = classification.tier if classification else DataTier.PUBLIC
        tags = classification.tags if classification else []

        # Check export restrictions
        if operation.operation_type == OperationType.EXPORT:
            return self._evaluate_export_policy(operation, tier, tags)

        # Check write restrictions
        if operation.is_write_operation():
            return self._evaluate_write_policy(operation, tier, tags)

        # Default: allow reads and other operations
        return PolicyDecision(
            allowed=True,
            reasoning=f"Fallback policy: {operation.operation_type.value} allowed for {tier.value} data",
            matched_rules=["fallback_default_allow"],
        )

    def _evaluate_export_policy(
        self,
        operation: DataOperation,
        tier: DataTier,
        tags: list[str],
    ) -> PolicyDecision:
        """Evaluate export-specific policies."""
        destination = operation.destination or ""

        # PROPRIETARY data restrictions
        if tier == DataTier.PROPRIETARY:
            # Check for unmanaged locations
            unmanaged_patterns = [
                "~/Downloads",
                "/tmp",  # nosec B108 - pattern matching, not file access
                "Downloads",
                "Desktop",
            ]

            for pattern in unmanaged_patterns:
                if pattern.lower() in destination.lower():
                    pii_columns = [
                        t for t in tags if t in ("PII", "PHI", "SSN", "EMAIL")
                    ]

                    return PolicyDecision(
                        allowed=False,
                        reasoning=(
                            f"Cannot export {tier.value} data to unmanaged location: {destination}"
                        ),
                        matched_rules=["proprietary_export_restriction"],
                        alternatives=[
                            f"Use anonymized version: lacuna.anonymize(data, {pii_columns})",
                            "Save to governed location: /governed/workspace/",
                            "Request exception: lacuna.request_exception()",
                        ],
                    )

            # Check encryption for external destinations
            if not operation.destination_encrypted:
                external_patterns = [
                    "s3://",
                    "gs://",
                    "azure://",
                    "http://",
                    "https://",
                ]
                for pattern in external_patterns:
                    if destination.startswith(pattern):
                        return PolicyDecision(
                            allowed=False,
                            reasoning="PROPRIETARY data requires encryption for external destinations",
                            matched_rules=["proprietary_encryption_required"],
                            alternatives=[
                                "Enable encryption for the destination",
                                "Use lacuna.encrypt() before export",
                            ],
                        )

        # INTERNAL data - allow internal destinations only
        if tier == DataTier.INTERNAL:
            external_patterns = ["s3://", "gs://", "azure://", "http://", "https://"]
            for pattern in external_patterns:
                if destination.startswith(pattern):
                    return PolicyDecision(
                        allowed=False,
                        reasoning="INTERNAL data cannot be exported to external destinations",
                        matched_rules=["internal_export_restriction"],
                        alternatives=["Use an internal storage location"],
                    )

        # PUBLIC data - allow all exports
        return PolicyDecision(
            allowed=True,
            reasoning=f"Export allowed for {tier.value} data",
            matched_rules=["export_allowed"],
        )

    def _evaluate_write_policy(
        self,
        operation: DataOperation,
        tier: DataTier,
        tags: list[str],
    ) -> PolicyDecision:
        """Evaluate write-specific policies."""
        # For now, allow writes with logging
        return PolicyDecision(
            allowed=True,
            reasoning=f"Write operation allowed for {tier.value} data with audit logging",
            matched_rules=["write_allowed_with_audit"],
        )

    def _make_cache_key(self, policy_input: PolicyInput) -> str:
        """Generate cache key for policy input."""
        key_parts = [
            policy_input.action,
            policy_input.resource_type,
            policy_input.resource_id,
            policy_input.classification_tier or "",
            policy_input.destination or "",
            policy_input.user_role or "",
        ]
        return "|".join(key_parts)

    def clear_cache(self) -> None:
        """Clear policy evaluation cache."""
        self._cache.clear()
        logger.info("policy_cache_cleared")

    def get_stats(self) -> dict[str, Any]:
        """Get policy engine statistics."""
        return {
            "enabled": self.enabled,
            "opa_available": self._opa_client.is_available(),
            "cache_size": len(self._cache),
            "fallback_on_error": self.fallback_on_error,
        }
