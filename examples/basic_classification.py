#!/usr/bin/env python3
"""Basic classification example.

Demonstrates how to classify data queries and content
to determine their sensitivity tier.
"""

from lacuna.engine.governance import GovernanceEngine
from lacuna.models.classification import ClassificationContext, DataTier


def main() -> None:
    """Run basic classification examples."""
    # Initialize the governance engine
    engine = GovernanceEngine()

    print("=== Basic Classification Examples ===\n")

    # Example 1: Simple query classification
    print("1. Classifying a simple query:")
    query = "SELECT name, email FROM users"
    result = engine.classify(query)
    print(f"   Query: {query}")
    print(f"   Tier: {result.tier}")
    print(f"   Confidence: {result.confidence:.2%}")
    print(f"   Reasoning: {result.reasoning}")
    print()

    # Example 2: Query with sensitive data
    print("2. Classifying a query with sensitive fields:")
    query = "SELECT ssn, credit_card FROM customers"
    result = engine.classify(query)
    print(f"   Query: {query}")
    print(f"   Tier: {result.tier}")
    print(f"   Reasoning: {result.reasoning}")
    print()

    # Example 3: Classification with context
    print("3. Classification with user context:")
    context = ClassificationContext(
        user_id="analyst_01",
        user_role="data_analyst",
        user_department="finance",
        project="quarterly_report",
        environment="production",
    )
    query = "SELECT revenue, costs FROM financials"
    result = engine.classify(query, context=context)
    print(f"   Query: {query}")
    print(f"   User: {context.user_id} ({context.user_role})")
    print(f"   Tier: {result.tier}")
    print()

    # Example 4: Compare classification tiers
    print("4. Comparing data sensitivity tiers:")
    print(f"   PUBLIC < INTERNAL: {DataTier.PUBLIC < DataTier.INTERNAL}")
    print(f"   INTERNAL < PROPRIETARY: {DataTier.INTERNAL < DataTier.PROPRIETARY}")
    print(f"   PROPRIETARY is most sensitive: {DataTier.PROPRIETARY.value_int}")
    print()

    # Example 5: Batch classification
    print("5. Batch classification:")
    queries = [
        "SELECT id, name FROM products",
        "SELECT salary FROM employees",
        "SELECT api_key FROM credentials",
    ]
    for q in queries:
        r = engine.classify(q)
        print(f"   {r.tier.value:12} | {q}")


if __name__ == "__main__":
    main()
