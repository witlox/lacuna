#!/usr/bin/env python3
"""Batch classification example.

Demonstrates efficient classification of multiple data items
using both the SDK and the API.
"""

import time

from lacuna.engine.governance import GovernanceEngine
from lacuna.models.classification import ClassificationContext


def main() -> None:
    """Run batch classification examples."""
    # Initialize the governance engine
    engine = GovernanceEngine()

    print("=== Batch Classification Examples ===\n")

    # Example dataset of queries to classify
    queries = [
        # Public data
        "SELECT product_name, description FROM catalog",
        "SELECT category, price FROM products",
        "SELECT title, author FROM blog_posts",
        # Internal data
        "SELECT employee_name, department FROM staff",
        "SELECT project_name, budget FROM projects",
        "SELECT vendor_name, contract_value FROM vendors",
        # Proprietary/sensitive data
        "SELECT ssn, date_of_birth FROM customers",
        "SELECT credit_card, cvv FROM payment_methods",
        "SELECT api_key, secret FROM credentials",
        "SELECT salary, bonus FROM compensation",
    ]

    # Example 1: Classify all queries
    print("1. Classifying dataset:")
    start = time.time()
    results = []
    for query in queries:
        result = engine.classify(query)
        results.append((query, result))
    elapsed = time.time() - start

    print(f"   Classified {len(queries)} queries in {elapsed:.3f}s")
    print(f"   Average: {elapsed/len(queries)*1000:.1f}ms per query")
    print()

    # Example 2: Group by tier
    print("2. Results by sensitivity tier:")
    by_tier: dict[str, list[str]] = {}
    for query, result in results:
        tier = result.tier.value
        if tier not in by_tier:
            by_tier[tier] = []
        by_tier[tier].append(query[:50])

    for tier in ["PUBLIC", "INTERNAL", "PROPRIETARY"]:
        if tier in by_tier:
            print(f"\n   {tier} ({len(by_tier[tier])} items):")
            for q in by_tier[tier]:
                print(f"     - {q}")
    print()

    # Example 3: Filter high-sensitivity items
    print("3. High-sensitivity queries (PROPRIETARY):")
    proprietary = [
        (q, r) for q, r in results if r.tier.value == "PROPRIETARY"
    ]
    for query, result in proprietary:
        print(f"   - {query[:60]}")
        print(f"     Confidence: {result.confidence:.2%}")
        print(f"     Reason: {result.reasoning}")
    print()

    # Example 4: Classify with shared context
    print("4. Batch classification with context:")
    context = ClassificationContext(
        user_id="batch_processor",
        user_role="system",
        environment="production",
        project="data_audit",
    )

    sensitive_count = 0
    for query in queries:
        result = engine.classify(query, context=context)
        if result.tier.value == "PROPRIETARY":
            sensitive_count += 1

    print(f"   Context: {context.project} ({context.environment})")
    print(f"   Total queries: {len(queries)}")
    print(f"   Sensitive items: {sensitive_count}")
    print(f"   Sensitivity rate: {sensitive_count/len(queries):.1%}")
    print()

    # Example 5: Classification statistics
    print("5. Classification statistics:")
    confidence_sum = sum(r.confidence for _, r in results)
    avg_confidence = confidence_sum / len(results)

    tier_counts = {}
    for _, result in results:
        tier = result.tier.value
        tier_counts[tier] = tier_counts.get(tier, 0) + 1

    print(f"   Average confidence: {avg_confidence:.2%}")
    print("   Distribution:")
    for tier, count in sorted(tier_counts.items()):
        pct = count / len(results) * 100
        bar = "█" * int(pct / 5)
        print(f"     {tier:12} {count:3} ({pct:5.1f}%) {bar}")


if __name__ == "__main__":
    main()
