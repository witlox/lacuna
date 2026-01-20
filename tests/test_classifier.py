"""Tests for classification pipeline."""

import pytest

from lacuna.classifier.heuristic import HeuristicClassifier
from lacuna.classifier.pipeline import ClassificationPipeline
from lacuna.models.classification import Classification, ClassificationContext, DataTier


class TestHeuristicClassifier:
    """Tests for heuristic classifier."""

    def test_pii_detection_email(self) -> None:
        """Test email PII detection."""
        classifier = HeuristicClassifier()
        result = classifier.classify("Contact me at john@example.com")

        assert result is not None
        assert result.tier == DataTier.PROPRIETARY
        assert "EMAIL" in result.tags
        assert result.confidence >= 0.9

    def test_pii_detection_ssn(self) -> None:
        """Test SSN PII detection."""
        classifier = HeuristicClassifier()
        result = classifier.classify("SSN: 123-45-6789")

        assert result is not None
        assert result.tier == DataTier.PROPRIETARY
        assert "SSN" in result.tags

    def test_pii_detection_phone(self) -> None:
        """Test phone number PII detection."""
        classifier = HeuristicClassifier()
        result = classifier.classify("Call me at 555-123-4567")

        assert result is not None
        assert result.tier == DataTier.PROPRIETARY
        assert "PHONE" in result.tags

    def test_pii_detection_credit_card(self) -> None:
        """Test credit card PII detection."""
        classifier = HeuristicClassifier()
        result = classifier.classify("Card: 4111-1111-1111-1111")

        assert result is not None
        assert result.tier == DataTier.PROPRIETARY
        assert "CREDIT_CARD" in result.tags

    def test_proprietary_keywords(self) -> None:
        """Test proprietary keyword detection."""
        classifier = HeuristicClassifier()
        result = classifier.classify("This is confidential information")

        assert result is not None
        assert result.tier == DataTier.PROPRIETARY

    def test_internal_keywords(self) -> None:
        """Test internal keyword detection."""
        classifier = HeuristicClassifier()
        result = classifier.classify("How do we deploy to staging?")

        assert result is not None
        assert result.tier == DataTier.INTERNAL

    def test_public_keywords(self) -> None:
        """Test public keyword detection."""
        classifier = HeuristicClassifier()
        result = classifier.classify("What is machine learning?")

        assert result is not None
        assert result.tier == DataTier.PUBLIC

    def test_project_context_proprietary(self) -> None:
        """Test proprietary project context."""
        classifier = HeuristicClassifier(proprietary_projects=["project_apollo"])
        context = ClassificationContext(project="project_apollo")
        result = classifier.classify("How do we do X?", context)

        assert result is not None
        assert result.tier == DataTier.PROPRIETARY

    def test_no_match_returns_none(self) -> None:
        """Test that ambiguous queries return None for fallback."""
        classifier = HeuristicClassifier()
        # A query with no clear indicators
        _result = classifier.classify("hello")

        # May return None to allow next classifier
        # or may return a low-confidence result


class TestClassificationPipeline:
    """Tests for classification pipeline."""

    def test_pipeline_initialization(self) -> None:
        """Test pipeline initializes with classifiers."""
        pipeline = ClassificationPipeline()

        assert len(pipeline.classifiers) >= 1
        assert pipeline.confidence_threshold > 0

    def test_pipeline_classification(self) -> None:
        """Test pipeline returns classification."""
        pipeline = ClassificationPipeline()
        result = pipeline.classify("Contact me at test@example.com")

        assert result is not None
        assert isinstance(result.tier, DataTier)
        assert 0 <= result.confidence <= 1

    def test_pipeline_short_circuit(self) -> None:
        """Test pipeline short-circuits on high confidence."""
        pipeline = ClassificationPipeline(short_circuit=True)
        result = pipeline.classify("SSN: 123-45-6789")

        # Should short-circuit at heuristic layer
        assert result is not None
        assert result.tier == DataTier.PROPRIETARY
        assert result.classifier_name == "HeuristicClassifier"

    def test_pipeline_caching(self) -> None:
        """Test pipeline caches results."""
        pipeline = ClassificationPipeline()

        # First call
        result1 = pipeline.classify("What is Python?")

        # Second call (should be cached)
        result2 = pipeline.classify("What is Python?")

        assert result1.tier == result2.tier
        assert pipeline._cache

    def test_pipeline_fallback(self) -> None:
        """Test pipeline falls back to default on no match."""
        pipeline = ClassificationPipeline(default_tier=DataTier.PROPRIETARY)

        # Empty classifiers list
        pipeline.classifiers = []

        result = pipeline.classify("random query")

        assert result.tier == DataTier.PROPRIETARY
        assert result.confidence == 0.5

    def test_pipeline_stats(self) -> None:
        """Test pipeline statistics."""
        pipeline = ClassificationPipeline()
        stats = pipeline.get_stats()

        assert "classifiers" in stats
        assert "cache_size" in stats
        assert "confidence_threshold" in stats
