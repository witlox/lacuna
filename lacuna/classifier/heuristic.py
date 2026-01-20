"""Heuristic classifier using regex and keyword matching."""

import re
from typing import Optional

from lacuna.classifier.base import Classifier
from lacuna.config import get_settings
from lacuna.models.classification import Classification, ClassificationContext, DataTier


class HeuristicClassifier(Classifier):
    """
    Fast heuristic-based classifier using regex and keyword matching.

    This is the first layer in the classification pipeline, designed to handle
    90% of queries with <1ms latency using simple pattern matching.
    """

    def __init__(
        self,
        proprietary_terms: Optional[list[str]] = None,
        proprietary_projects: Optional[list[str]] = None,
        proprietary_customers: Optional[list[str]] = None,
        priority: int = 60,
    ):
        """Initialize heuristic classifier.

        Args:
            proprietary_terms: List of proprietary terms
            proprietary_projects: List of proprietary project names
            proprietary_customers: List of proprietary customer names
            priority: Priority in pipeline (default: 60)
        """
        super().__init__(priority)
        settings = get_settings()

        # Load proprietary terms from config
        self.proprietary_terms = set(
            proprietary_terms or settings.proprietary_terms or []
        )
        self.proprietary_projects = set(
            proprietary_projects or settings.proprietary_projects or []
        )
        self.proprietary_customers = set(
            proprietary_customers or settings.proprietary_customers or []
        )

        # PII patterns
        self.pii_patterns = {
            "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
            "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
            "phone": re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b"),
            "credit_card": re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"),
            "ip_address": re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"),
        }

        # Proprietary indicators
        self.proprietary_keywords = {
            "confidential",
            "proprietary",
            "internal only",
            "do not distribute",
            "trade secret",
            "classified",
        }

        # Internal indicators
        self.internal_keywords = {
            "internal",
            "deployment",
            "infrastructure",
            "monitoring",
            "staging",
            "production environment",
        }

        # Public indicators
        self.public_keywords = {
            "public",
            "open source",
            "documentation",
            "tutorial",
            "how to",
            "what is",
        }

    @property
    def name(self) -> str:
        """Get classifier name."""
        return "HeuristicClassifier"

    def classify(
        self, query: str, context: Optional[ClassificationContext] = None
    ) -> Optional[Classification]:
        """Classify query using heuristic rules.

        Args:
            query: Query text to classify
            context: Optional context information

        Returns:
            Classification if patterns match, None otherwise
        """
        query_lower = query.lower()
        matched_rules = []
        tags = []

        # Check for PII patterns (always PROPRIETARY)
        pii_detected = self._detect_pii(query)
        if pii_detected:
            tags.extend(pii_detected)
            matched_rules.append("pii_pattern_match")
            return Classification(
                tier=DataTier.PROPRIETARY,
                confidence=0.99,
                reasoning=f"PII detected: {', '.join(pii_detected)}",
                matched_rules=matched_rules,
                tags=tags,
                classifier_name=self.name,
                classifier_version="1.0.0",
            )

        # Check project context
        if context and context.project:
            if context.project in self.proprietary_projects:
                matched_rules.append("proprietary_project_context")
                return Classification(
                    tier=DataTier.PROPRIETARY,
                    confidence=0.95,
                    reasoning=f"Project '{context.project}' is proprietary",
                    matched_rules=matched_rules,
                    tags=tags,
                    classifier_name=self.name,
                    classifier_version="1.0.0",
                )
            elif context.project == "learning" or context.project == "public":
                matched_rules.append("public_project_context")
                return Classification(
                    tier=DataTier.PUBLIC,
                    confidence=0.90,
                    reasoning=f"Project '{context.project}' is public",
                    matched_rules=matched_rules,
                    tags=tags,
                    classifier_name=self.name,
                    classifier_version="1.0.0",
                )

        # Check for proprietary customers
        for customer in self.proprietary_customers:
            if customer.lower() in query_lower:
                matched_rules.append("proprietary_customer_reference")
                tags.append("CUSTOMER_DATA")
                return Classification(
                    tier=DataTier.PROPRIETARY,
                    confidence=0.98,
                    reasoning=f"References proprietary customer: {customer}",
                    matched_rules=matched_rules,
                    tags=tags,
                    classifier_name=self.name,
                    classifier_version="1.0.0",
                )

        # Check for proprietary terms
        for term in self.proprietary_terms:
            if term.lower() in query_lower:
                matched_rules.append("proprietary_term_match")
                return Classification(
                    tier=DataTier.PROPRIETARY,
                    confidence=0.95,
                    reasoning=f"Matches proprietary term: {term}",
                    matched_rules=matched_rules,
                    tags=tags,
                    classifier_name=self.name,
                    classifier_version="1.0.0",
                )

        # Check for proprietary keywords
        for keyword in self.proprietary_keywords:
            if keyword in query_lower:
                matched_rules.append("proprietary_keyword_match")
                return Classification(
                    tier=DataTier.PROPRIETARY,
                    confidence=0.92,
                    reasoning=f"Contains proprietary keyword: {keyword}",
                    matched_rules=matched_rules,
                    tags=tags,
                    classifier_name=self.name,
                    classifier_version="1.0.0",
                )

        # Check for internal keywords
        internal_matches = [kw for kw in self.internal_keywords if kw in query_lower]
        if internal_matches:
            matched_rules.append("internal_keyword_match")
            return Classification(
                tier=DataTier.INTERNAL,
                confidence=0.85,
                reasoning=f"Contains internal keywords: {', '.join(internal_matches)}",
                matched_rules=matched_rules,
                tags=tags,
                classifier_name=self.name,
                classifier_version="1.0.0",
            )

        # Check for public indicators
        public_matches = [kw for kw in self.public_keywords if kw in query_lower]
        if public_matches:
            matched_rules.append("public_keyword_match")
            return Classification(
                tier=DataTier.PUBLIC,
                confidence=0.80,
                reasoning=f"Contains public indicators: {', '.join(public_matches)}",
                matched_rules=matched_rules,
                tags=tags,
                classifier_name=self.name,
                classifier_version="1.0.0",
            )

        # No clear match - return None to pass to next classifier
        return None

    def _detect_pii(self, text: str) -> list[str]:
        """Detect PII patterns in text.

        Args:
            text: Text to scan for PII

        Returns:
            List of detected PII types
        """
        detected = []

        for pii_type, pattern in self.pii_patterns.items():
            if pattern.search(text):
                detected.append(pii_type.upper())

        return detected
