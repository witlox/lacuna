#!/usr/bin/env python3
"""Custom classifier example.

Demonstrates how to create custom classification rules
for domain-specific data sensitivity detection.
"""

import re
from typing import Any

from lacuna.classifier.base import BaseClassifier
from lacuna.classifier.pipeline import ClassificationPipeline
from lacuna.engine.governance import GovernanceEngine
from lacuna.models.classification import Classification, ClassificationContext, DataTier


class HealthcareClassifier(BaseClassifier):
    """Custom classifier for healthcare data.

    Detects PHI (Protected Health Information) and other
    healthcare-specific sensitive data patterns.
    """

    name = "healthcare"
    priority = 100  # High priority - check early

    # PHI patterns
    PHI_PATTERNS = [
        r"\bpatient[_\s]?id\b",
        r"\bmedical[_\s]?record[_\s]?number\b",
        r"\bmrn\b",
        r"\bdiagnosis\b",
        r"\btreatment\b",
        r"\bprescription\b",
        r"\blab[_\s]?results?\b",
        r"\bhealth[_\s]?insurance\b",
        r"\bhipaa\b",
    ]

    # Sensitive field names
    SENSITIVE_FIELDS = {
        "patient_name",
        "date_of_birth",
        "social_security",
        "insurance_id",
        "diagnosis_code",
        "icd_code",
        "medication",
        "dosage",
        "physician",
        "medical_history",
    }

    def classify(
        self,
        query: str,
        context: ClassificationContext | None = None,
        **kwargs: Any,
    ) -> Classification | None:
        """Classify healthcare-related queries.

        Returns PROPRIETARY for any PHI or healthcare data.
        """
        query_lower = query.lower()

        # Check for PHI patterns
        for pattern in self.PHI_PATTERNS:
            if re.search(pattern, query_lower, re.IGNORECASE):
                return Classification(
                    tier=DataTier.PROPRIETARY,
                    confidence=0.95,
                    reasoning=f"Contains PHI pattern: {pattern}",
                    classifier_name=self.name,
                )

        # Check for sensitive field names
        for field in self.SENSITIVE_FIELDS:
            if field in query_lower:
                return Classification(
                    tier=DataTier.PROPRIETARY,
                    confidence=0.90,
                    reasoning=f"Contains sensitive healthcare field: {field}",
                    classifier_name=self.name,
                )

        # Not healthcare data - let other classifiers handle it
        return None


class FinancialClassifier(BaseClassifier):
    """Custom classifier for financial data.

    Detects PCI-DSS relevant data and other financial
    sensitive information.
    """

    name = "financial"
    priority = 90

    SENSITIVE_PATTERNS = [
        r"\bcredit[_\s]?card\b",
        r"\bcard[_\s]?number\b",
        r"\bcvv\b",
        r"\bexpiry[_\s]?date\b",
        r"\bbank[_\s]?account\b",
        r"\brouting[_\s]?number\b",
        r"\biban\b",
        r"\bswift\b",
        r"\btax[_\s]?id\b",
        r"\bein\b",  # Employer Identification Number
    ]

    INTERNAL_PATTERNS = [
        r"\brevenue\b",
        r"\bprofit\b",
        r"\bforecast\b",
        r"\bbudget\b",
        r"\bexpenses?\b",
    ]

    def classify(
        self,
        query: str,
        context: ClassificationContext | None = None,
        **kwargs: Any,
    ) -> Classification | None:
        """Classify financial data queries."""
        query_lower = query.lower()

        # Check for PCI-DSS relevant patterns
        for pattern in self.SENSITIVE_PATTERNS:
            if re.search(pattern, query_lower, re.IGNORECASE):
                return Classification(
                    tier=DataTier.PROPRIETARY,
                    confidence=0.95,
                    reasoning=f"Contains PCI-DSS relevant pattern: {pattern}",
                    classifier_name=self.name,
                )

        # Check for internal financial data
        for pattern in self.INTERNAL_PATTERNS:
            if re.search(pattern, query_lower, re.IGNORECASE):
                return Classification(
                    tier=DataTier.INTERNAL,
                    confidence=0.80,
                    reasoning=f"Contains internal financial data: {pattern}",
                    classifier_name=self.name,
                )

        return None


def main() -> None:
    """Run custom classifier examples."""
    print("=== Custom Classifier Examples ===\n")

    # Create a custom pipeline with our classifiers
    pipeline = ClassificationPipeline()

    # Register custom classifiers
    healthcare_classifier = HealthcareClassifier()
    financial_classifier = FinancialClassifier()

    pipeline.register_classifier(healthcare_classifier)
    pipeline.register_classifier(financial_classifier)

    print("1. Registered custom classifiers:")
    print(f"   - {healthcare_classifier.name} (priority: {healthcare_classifier.priority})")
    print(f"   - {financial_classifier.name} (priority: {financial_classifier.priority})")
    print()

    # Test healthcare classifications
    print("2. Healthcare data classification:")
    healthcare_queries = [
        "SELECT patient_id, diagnosis FROM medical_records",
        "SELECT mrn, lab_results FROM patient_tests",
        "SELECT name, email FROM newsletter_subscribers",  # Not healthcare
    ]

    for query in healthcare_queries:
        result = pipeline.classify(query)
        print(f"   Query: {query[:50]}...")
        print(f"   Tier: {result.tier.value}, Classifier: {result.classifier_name}")
        print()

    # Test financial classifications
    print("3. Financial data classification:")
    financial_queries = [
        "SELECT credit_card, cvv FROM payments",
        "SELECT revenue, profit FROM quarterly_financials",
        "SELECT product_name FROM catalog",  # Not financial
    ]

    for query in financial_queries:
        result = pipeline.classify(query)
        print(f"   Query: {query[:50]}...")
        print(f"   Tier: {result.tier.value}, Classifier: {result.classifier_name}")
        print()

    # Example 4: Use with GovernanceEngine
    print("4. Using custom classifiers with GovernanceEngine:")
    engine = GovernanceEngine(classifier=pipeline)

    query = "SELECT patient_name, diagnosis_code FROM hospital_records"
    result = engine.classify(query)
    print(f"   Query: {query}")
    print(f"   Tier: {result.tier.value}")
    print(f"   Confidence: {result.confidence:.2%}")
    print(f"   Reasoning: {result.reasoning}")


if __name__ == "__main__":
    main()
