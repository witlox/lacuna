#!/usr/bin/env python3
"""Lineage tracking example.

Demonstrates how to track data lineage and provenance
as data flows through transformations.
"""

from lacuna.engine.governance import GovernanceEngine
from lacuna.models.data_operation import DataOperation, OperationType, UserContext


def main() -> None:
    """Run lineage tracking examples."""
    # Initialize the governance engine
    engine = GovernanceEngine()

    print("=== Lineage Tracking Examples ===\n")

    user = UserContext(
        user_id="data_engineer",
        user_role="engineer",
        user_department="data_platform",
    )

    # Example 1: Track a simple transformation
    print("1. Recording a simple transformation:")
    operation = DataOperation(
        operation_type=OperationType.TRANSFORM,
        resource_id="cleaned_sales.parquet",
        source_resources=["raw_sales.csv"],
        user_context=user,
        metadata={"transformation": "clean_nulls"},
    )
    result = engine.evaluate_operation(operation)
    print("   Source: raw_sales.csv")
    print("   Target: cleaned_sales.parquet")
    print(f"   Recorded: {result.allowed}")
    print()

    # Example 2: Track a join operation
    print("2. Recording a join operation:")
    operation = DataOperation(
        operation_type=OperationType.JOIN,
        resource_id="sales_with_customers.parquet",
        source_resources=["cleaned_sales.parquet", "customers.csv"],
        user_context=user,
        metadata={"join_key": "customer_id"},
    )
    result = engine.evaluate_operation(operation)
    print(f"   Sources: {operation.source_resources}")
    print(f"   Target: {operation.resource_id}")
    print("   Join key: customer_id")
    print()

    # Example 3: Track an aggregation
    print("3. Recording an aggregation:")
    operation = DataOperation(
        operation_type=OperationType.AGGREGATE,
        resource_id="monthly_revenue.parquet",
        source_resources=["sales_with_customers.parquet"],
        user_context=user,
        metadata={"group_by": "month", "aggregation": "sum(revenue)"},
    )
    result = engine.evaluate_operation(operation)
    print(f"   Source: {operation.source_resources[0]}")
    print(f"   Target: {operation.resource_id}")
    print("   Aggregation: sum(revenue) by month")
    print()

    # Example 4: Query upstream lineage
    print("4. Querying upstream lineage:")
    try:
        upstream = engine.get_upstream("monthly_revenue.parquet")
        print("   Artifact: monthly_revenue.parquet")
        print(f"   Upstream sources: {upstream}")
    except Exception as e:
        print(f"   (Lineage query requires running backend: {e})")
    print()

    # Example 5: Query downstream lineage
    print("5. Querying downstream lineage:")
    try:
        downstream = engine.get_downstream("raw_sales.csv")
        print("   Artifact: raw_sales.csv")
        print(f"   Downstream artifacts: {downstream}")
    except Exception as e:
        print(f"   (Lineage query requires running backend: {e})")
    print()

    # Example 6: Get full lineage graph
    print("6. Getting lineage graph:")
    try:
        graph = engine.get_lineage("monthly_revenue.parquet")
        print("   Artifact: monthly_revenue.parquet")
        print(f"   Nodes: {list(graph.get('nodes', {}).keys())}")
        print(f"   Edges: {len(graph.get('edges', []))} connections")
    except Exception as e:
        print(f"   (Lineage query requires running backend: {e})")


if __name__ == "__main__":
    main()
