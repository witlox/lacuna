"""Main governance engine orchestrating all components."""

import time
from typing import Any, Optional

import structlog

from lacuna.audit.logger import AuditLogger
from lacuna.classifier.pipeline import ClassificationPipeline
from lacuna.config import get_settings
from lacuna.engine.result import GovernanceResult
from lacuna.lineage.tracker import LineageTracker
from lacuna.models.classification import Classification, ClassificationContext
from lacuna.models.data_operation import DataOperation, OperationType, UserContext
from lacuna.policy.engine import PolicyEngine

logger = structlog.get_logger()


class GovernanceEngine:
    """
    Main orchestrator for data governance operations.

    Combines:
    - Classification pipeline for data sensitivity analysis
    - Policy engine for access control decisions
    - Audit logger for ISO 27001-compliant logging
    - Lineage tracker for data provenance

    Usage:
        engine = GovernanceEngine()
        result = engine.evaluate_operation(operation)
        if result.allowed:
            # Proceed with operation
        else:
            print(result.to_user_message())
    """

    def __init__(
        self,
        classifier: Optional[ClassificationPipeline] = None,
        policy_engine: Optional[PolicyEngine] = None,
        audit_logger: Optional[AuditLogger] = None,
        lineage_tracker: Optional[LineageTracker] = None,
    ):
        """Initialize governance engine.

        Args:
            classifier: Classification pipeline
            policy_engine: Policy evaluation engine
            audit_logger: Audit logging service
            lineage_tracker: Lineage tracking service
        """
        self.settings = get_settings()

        # Initialize components
        self._classifier = classifier or ClassificationPipeline()
        self._policy_engine = policy_engine or PolicyEngine()
        self._audit_logger = audit_logger or AuditLogger()
        self._lineage_tracker = lineage_tracker or LineageTracker()

        logger.info(
            "governance_engine_initialized",
            classifier=self._classifier.__class__.__name__,
            policy_enabled=self._policy_engine.enabled,
            audit_enabled=self._audit_logger.enabled,
            lineage_enabled=self._lineage_tracker.enabled,
        )

    def evaluate_operation(
        self,
        operation: DataOperation,
        context: Optional[ClassificationContext] = None,
    ) -> GovernanceResult:
        """Evaluate a data operation through the full governance pipeline.

        This is the main entry point for governance evaluation:
        1. Classify the data involved
        2. Apply lineage-based classification inheritance
        3. Evaluate policies
        4. Log audit record
        5. Track lineage (if allowed)

        Args:
            operation: Data operation to evaluate
            context: Classification context

        Returns:
            Complete governance result with decision and reasoning
        """
        start_time = time.time()
        result = GovernanceResult(operation=operation)

        try:
            # Step 1: Classify the data
            classification_start = time.time()
            classification = self._classify_operation(operation, context)
            result.classification = classification
            result.classification_latency_ms = (
                time.time() - classification_start
            ) * 1000

            # Step 2: Apply lineage-based inheritance
            if operation.lineage_chain or operation.sources:
                inherited = self._lineage_tracker.compute_inherited_classification(
                    operation.resource_id, classification
                )
                if inherited.tier > classification.tier:
                    classification = inherited
                    result.classification = classification

            # Step 3: Evaluate policies
            policy_start = time.time()
            policy_result = self._policy_engine.evaluate(operation, classification)
            result.policy_latency_ms = (time.time() - policy_start) * 1000

            result.allowed = policy_result.decision.allowed
            result.policy_decision = policy_result.decision
            result.reasoning = policy_result.decision.reasoning
            result.alternatives = policy_result.decision.alternatives
            result.matched_rules = policy_result.decision.matched_rules

            # Step 4: Log audit record
            audit_record = self._audit_logger.log_policy_evaluation(
                operation, policy_result.decision, classification
            )
            result.audit_event_id = audit_record.event_id

            # Step 5: Track lineage (only if allowed)
            if result.allowed:
                self._lineage_tracker.track_operation(operation, classification)

            # Record total latency
            result.total_latency_ms = (time.time() - start_time) * 1000

            logger.info(
                "governance_evaluation_complete",
                operation=operation.operation_type.value,
                resource=operation.resource_id[:50] if operation.resource_id else None,
                tier=classification.tier.value,
                allowed=result.allowed,
                latency_ms=round(result.total_latency_ms, 2),
            )

            return result

        except Exception as e:
            result.error = str(e)
            result.allowed = False
            result.reasoning = f"Governance evaluation failed: {e}"
            result.total_latency_ms = (time.time() - start_time) * 1000

            logger.error(
                "governance_evaluation_error",
                operation=operation.operation_type.value,
                error=str(e),
            )

            return result

    def classify(
        self,
        query: str,
        context: Optional[ClassificationContext] = None,
    ) -> Classification:
        """Classify a query or text.

        Args:
            query: Text to classify
            context: Classification context

        Returns:
            Classification result
        """
        classification = self._classifier.classify(query, context)

        # Log classification
        user_id = context.user_id if context and context.user_id else "anonymous"
        self._audit_logger.log_classification(classification, query, user_id)

        return classification

    def evaluate_query(
        self,
        query: str,
        user_id: str = "anonymous",
        project: Optional[str] = None,
        environment: Optional[str] = None,
    ) -> GovernanceResult:
        """Evaluate a query for classification and routing.

        Simplified interface for query classification without full operation tracking.

        Args:
            query: Query text to evaluate
            user_id: User making the query
            project: Project context
            environment: Environment (production, staging, dev)

        Returns:
            Governance result with classification
        """
        context = ClassificationContext(
            user_id=user_id,
            project=project,
            environment=environment,
        )

        # Create a read operation for the query
        operation = DataOperation(
            operation_type=OperationType.QUERY,
            resource_type="query",
            resource_id=query[:100],  # Use query prefix as ID
            user=UserContext(user_id=user_id),
            project=project,
            environment=environment,
        )

        return self.evaluate_operation(operation, context)

    def evaluate_export(
        self,
        source: str,
        destination: str,
        user_id: str,
        purpose: Optional[str] = None,
    ) -> GovernanceResult:
        """Evaluate a data export operation.

        Args:
            source: Source resource ID (file, table, etc.)
            destination: Destination path or URL
            user_id: User performing the export
            purpose: Business justification

        Returns:
            Governance result with policy decision
        """
        operation = DataOperation(
            operation_type=OperationType.EXPORT,
            resource_type="file",
            resource_id=source,
            destination=destination,
            user=UserContext(user_id=user_id),
            purpose=purpose,
            destination_encrypted=self._is_encrypted_destination(destination),
        )

        # Classify the source data
        context = ClassificationContext(user_id=user_id)

        return self.evaluate_operation(operation, context)

    def _classify_operation(
        self,
        operation: DataOperation,
        context: Optional[ClassificationContext] = None,
    ) -> Classification:
        """Classify data involved in an operation."""
        # Build classification context from operation
        if context is None:
            context = ClassificationContext()

        if operation.user:
            context.user_id = context.user_id or operation.user.user_id
            context.user_role = context.user_role or operation.user.user_role

        context.project = context.project or operation.project
        context.environment = context.environment or operation.environment

        # Classify the resource
        return self._classifier.classify(operation.resource_id, context)

    def _is_encrypted_destination(self, destination: str) -> bool:
        """Check if destination supports encryption."""
        encrypted_patterns = [
            "s3://",  # S3 with server-side encryption
            "gs://",  # GCS with encryption
            "/governed/",  # Governed storage
            "/secure/",  # Secure locations
        ]
        return any(destination.startswith(p) for p in encrypted_patterns)

    def get_lineage(self, artifact_id: str) -> dict[str, Any]:
        """Get lineage information for an artifact.

        Args:
            artifact_id: Artifact to get lineage for

        Returns:
            Lineage information
        """
        graph = self._lineage_tracker.get_lineage(artifact_id)
        return graph.to_dict()

    def get_upstream(self, artifact_id: str) -> list:
        """Get upstream dependencies of an artifact."""
        return self._lineage_tracker.get_upstream(artifact_id)

    def get_downstream(self, artifact_id: str) -> list:
        """Get downstream dependents of an artifact."""
        return self._lineage_tracker.get_downstream(artifact_id)

    def verify_audit_integrity(self) -> dict[str, Any]:
        """Verify audit log integrity.

        Returns:
            Verification result
        """
        return self._audit_logger.verify_integrity()

    def get_stats(self) -> dict[str, Any]:
        """Get governance engine statistics.

        Returns:
            Dictionary with component statistics
        """
        return {
            "classifier": self._classifier.get_stats(),
            "policy_engine": self._policy_engine.get_stats(),
            "lineage_tracker": self._lineage_tracker.get_stats(),
        }

    def flush(self) -> None:
        """Flush all pending operations."""
        self._audit_logger.flush()

    def stop(self) -> None:
        """Stop all background processes."""
        self._audit_logger.stop()
        logger.info("governance_engine_stopped")

    def __enter__(self) -> "GovernanceEngine":
        """Context manager entry."""
        return self

    def __exit__(self, _exc_type: Any, _exc_val: Any, _exc_tb: Any) -> None:
        """Context manager exit."""
        self.stop()
