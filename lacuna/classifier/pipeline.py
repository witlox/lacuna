"""Classification pipeline orchestrating multiple classifiers."""

import time
from typing import Optional

import structlog

from lacuna.classifier.base import Classifier
from lacuna.classifier.embedding import EmbeddingClassifier
from lacuna.classifier.heuristic import HeuristicClassifier
from lacuna.classifier.llm import LLMClassifier
from lacuna.config import get_settings
from lacuna.models.classification import Classification, ClassificationContext, DataTier

logger = structlog.get_logger()


class ClassificationPipeline:
    """
    Multi-layer classification pipeline with short-circuiting.

    Executes classifiers in priority order, stopping at first high-confidence
    result. Designed for 90%+ throughput with <10ms P95 latency.

    Architecture:
    - Layer 1 (Priority 60): Heuristic - <1ms, handles 90% of queries
    - Layer 2 (Priority 70): Embedding - ~10ms, handles 8% of queries
    - Layer 3 (Priority 80): LLM - ~200ms, handles 2% of queries
    """

    def __init__(
        self,
        classifiers: Optional[list[Classifier]] = None,
        confidence_threshold: float = 0.9,
        short_circuit: bool = True,
        default_tier: DataTier = DataTier.PROPRIETARY,
    ):
        """Initialize classification pipeline.

        Args:
            classifiers: List of classifiers (auto-initialized if None)
            confidence_threshold: Minimum confidence for short-circuit
            short_circuit: Stop at first high-confidence result
            default_tier: Default tier when all classifiers fail
        """
        self.settings = get_settings()
        self.confidence_threshold = (
            confidence_threshold or self.settings.classification.confidence_threshold
        )
        self.short_circuit = (
            short_circuit
            if short_circuit is not None
            else self.settings.classification.short_circuit
        )
        self.default_tier = default_tier

        # Initialize classifiers
        if classifiers is None:
            self.classifiers = self._init_default_classifiers()
        else:
            self.classifiers = classifiers

        # Sort by priority (lower = earlier)
        self.classifiers.sort(key=lambda c: c.priority)

        # Cache for query classifications (in-memory)
        self._cache: dict = {}
        self._cache_enabled = True

    def _init_default_classifiers(self) -> list[Classifier]:
        """Initialize default classifier stack.

        Returns:
            List of classifiers in priority order
        """
        classifiers: list[Classifier] = []

        # Layer 1: Heuristic (always enabled, fastest)
        if self.settings.classification.heuristic_enabled:
            classifiers.append(
                HeuristicClassifier(
                    priority=self.settings.classification.heuristic_priority
                )
            )

        # Layer 2: Embedding (if enabled, requires sentence-transformers)
        if self.settings.classification.embedding_enabled:
            try:
                classifiers.append(
                    EmbeddingClassifier(
                        priority=self.settings.classification.embedding_priority
                    )
                )
            except ImportError:
                logger.warning(
                    "embedding_classifier_disabled",
                    reason="sentence-transformers not installed",
                )

        # Layer 3: LLM (if endpoint configured)
        if (
            self.settings.classification.llm_enabled
            and self.settings.classification.llm_endpoint
        ):
            classifiers.append(
                LLMClassifier(priority=self.settings.classification.llm_priority)
            )

        return classifiers

    def classify(
        self, query: str, context: Optional[ClassificationContext] = None
    ) -> Classification:
        """Classify a query using the pipeline.

        Args:
            query: Query text to classify
            context: Optional context information

        Returns:
            Classification result (never None, falls back to default tier)
        """
        start_time = time.time()

        # Check cache
        cache_key = self._make_cache_key(query, context)
        if self._cache_enabled and cache_key in self._cache:
            cached = self._cache[cache_key]
            logger.debug(
                "classification_cache_hit",
                query=query[:100],
                tier=cached.tier.value,
                cached=True,
            )
            return cached

        results = []
        classifier_used = None

        # Run classifiers in priority order
        for classifier in self.classifiers:
            try:
                result = classifier.classify(query, context)

                if result is not None:
                    results.append(result)
                    classifier_used = classifier.name

                    logger.debug(
                        "classifier_result",
                        classifier=classifier.name,
                        tier=result.tier.value,
                        confidence=result.confidence,
                    )

                    # Short-circuit on high confidence
                    if (
                        self.short_circuit
                        and result.confidence >= self.confidence_threshold
                    ):
                        elapsed_ms = (time.time() - start_time) * 1000
                        logger.info(
                            "classification_complete",
                            query=query[:100],
                            tier=result.tier.value,
                            confidence=result.confidence,
                            classifier=classifier.name,
                            latency_ms=round(elapsed_ms, 2),
                        )

                        # Cache result
                        if self._cache_enabled:
                            self._cache[cache_key] = result

                        return result

            except Exception as e:
                logger.error(
                    "classifier_error",
                    classifier=classifier.name,
                    error=str(e),
                    query=query[:100],
                )
                continue

        # No high-confidence result, use best available or default
        if results:
            # Sort by confidence
            results.sort(key=lambda r: r.confidence, reverse=True)
            best_result = results[0]

            elapsed_ms = (time.time() - start_time) * 1000
            logger.info(
                "classification_complete_low_confidence",
                query=query[:100],
                tier=best_result.tier.value,
                confidence=best_result.confidence,
                classifier=classifier_used,
                latency_ms=round(elapsed_ms, 2),
            )

            # Cache result
            if self._cache_enabled:
                self._cache[cache_key] = best_result

            return best_result
        else:
            # All classifiers failed - use conservative default
            default_result = Classification(
                tier=self.default_tier,
                confidence=0.5,
                reasoning="No classifiers matched - using conservative default",
                matched_rules=["default_fallback"],
                tags=[],
                classifier_name="DefaultFallback",
                classifier_version="1.0.0",
            )

            elapsed_ms = (time.time() - start_time) * 1000
            logger.warning(
                "classification_fallback",
                query=query[:100],
                tier=self.default_tier.value,
                latency_ms=round(elapsed_ms, 2),
            )

            # Don't cache fallback results
            return default_result

    def _make_cache_key(
        self, query: str, context: Optional[ClassificationContext]
    ) -> str:
        """Make cache key from query and context.

        Args:
            query: Query text
            context: Optional context

        Returns:
            Cache key string
        """
        key_parts = [query]

        if context:
            if context.project:
                key_parts.append(f"project:{context.project}")
            if context.user_role:
                key_parts.append(f"role:{context.user_role}")
            if context.environment:
                key_parts.append(f"env:{context.environment}")

        return "|".join(key_parts)

    def add_classifier(self, classifier: Classifier) -> None:
        """Add a classifier to the pipeline.

        Args:
            classifier: Classifier to add
        """
        self.classifiers.append(classifier)
        self.classifiers.sort(key=lambda c: c.priority)

    def remove_classifier(self, classifier_name: str) -> bool:
        """Remove a classifier from the pipeline.

        Args:
            classifier_name: Name of classifier to remove

        Returns:
            True if removed, False if not found
        """
        initial_len = len(self.classifiers)
        self.classifiers = [c for c in self.classifiers if c.name != classifier_name]
        return len(self.classifiers) < initial_len

    def clear_cache(self) -> None:
        """Clear the classification cache."""
        self._cache.clear()
        logger.info("classification_cache_cleared")

    def get_stats(self) -> dict:
        """Get pipeline statistics.

        Returns:
            Dictionary with statistics
        """
        return {
            "classifiers": [
                {"name": c.name, "priority": c.priority} for c in self.classifiers
            ],
            "cache_size": len(self._cache),
            "cache_enabled": self._cache_enabled,
            "confidence_threshold": self.confidence_threshold,
            "short_circuit": self.short_circuit,
            "default_tier": self.default_tier.value,
        }
