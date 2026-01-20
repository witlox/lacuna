#!/usr/bin/env python3
"""Complete governance workflow example.

Demonstrates a full data governance workflow including:
- Classification
- Policy evaluation
- Lineage tracking
- Audit logging
"""

from lacuna.engine.governance import GovernanceEngine
from lacuna.models.data_operation import DataOperation, OperationType, UserContext


def print_section(title: str) -> None:
    """Print a section header."""
    print(f"\n{'='*60}")
    print(f" {title}")
    print("=" * 60)


def main() -> None:
    """Run a complete governance workflow."""
    print("╔════════════════════════════════════════════════════════════╗")
    print("║           Lacuna Data Governance Workflow                  ║")
    print("╚════════════════════════════════════════════════════════════╝")

    # Initialize
    engine = GovernanceEngine()

    # Define our user
    user = UserContext(
        user_id="data_analyst_01",
        user_role="analyst",
        user_department="business_intelligence",
        session_id="session_abc123",
    )

    print(f"\nUser: {user.user_id}")
    print(f"Role: {user.user_role}")
    print(f"Department: {user.user_department}")

    # ==========================================================
    # Step 1: Classify the source data
    # ==========================================================
    print_section("Step 1: Data Classification")

    queries = {
        "sales_data": "SELECT date, product, quantity, revenue FROM sales",
        "customer_data": "SELECT customer_id, name, email, phone FROM customers",
        "payment_data": "SELECT transaction_id, credit_card, amount FROM payments",
    }

    classifications = {}
    for name, query in queries.items():
        result = engine.classify(query)
        classifications[name] = result
        print(f"\n{name}:")
        print(f"  Query: {query[:50]}...")
        print(f"  Tier: {result.tier.value}")
        print(f"  Confidence: {result.confidence:.2%}")

    # ==========================================================
    # Step 2: Request access to data
    # ==========================================================
    print_section("Step 2: Access Request Evaluation")

    access_requests = [
        ("sales_data", OperationType.READ),
        ("customer_data", OperationType.READ),
        ("payment_data", OperationType.READ),
        ("payment_data", OperationType.EXPORT),
    ]

    approved = []
    denied = []

    for resource, op_type in access_requests:
        operation = DataOperation(
            operation_type=op_type,
            resource_id=f"{resource}.csv",
            user_context=user,
        )
        result = engine.evaluate_operation(operation)

        status = "✓ APPROVED" if result.allowed else "✗ DENIED"
        print(f"\n{op_type.value.upper()} {resource}: {status}")

        if result.allowed:
            approved.append((resource, op_type))
        else:
            denied.append((resource, op_type, result.to_user_message()))
            print(f"  Reason: {result.to_user_message()}")

    # ==========================================================
    # Step 3: Perform approved operations with lineage tracking
    # ==========================================================
    print_section("Step 3: Data Transformation with Lineage")

    if approved:
        # Join sales and customer data
        print("\nTransformation: Join sales with customers")
        transform_op = DataOperation(
            operation_type=OperationType.JOIN,
            resource_id="sales_with_customers.parquet",
            source_resources=["sales_data.csv", "customer_data.csv"],
            user_context=user,
            metadata={
                "join_type": "left",
                "join_key": "customer_id",
            },
        )
        result = engine.evaluate_operation(transform_op)
        print(f"  Sources: {transform_op.source_resources}")
        print(f"  Output: {transform_op.resource_id}")
        print(f"  Status: {'✓ Recorded' if result.allowed else '✗ Denied'}")

        # Aggregate the joined data
        print("\nTransformation: Aggregate by month")
        agg_op = DataOperation(
            operation_type=OperationType.AGGREGATE,
            resource_id="monthly_sales_report.parquet",
            source_resources=["sales_with_customers.parquet"],
            user_context=user,
            metadata={
                "group_by": ["year", "month"],
                "aggregations": ["sum(revenue)", "count(customer_id)"],
            },
        )
        result = engine.evaluate_operation(agg_op)
        print(f"  Source: {agg_op.source_resources}")
        print(f"  Output: {agg_op.resource_id}")
        print(f"  Status: {'✓ Recorded' if result.allowed else '✗ Denied'}")

    # ==========================================================
    # Step 4: Review audit trail
    # ==========================================================
    print_section("Step 4: Audit Trail Review")

    print(f"\nQuerying audit logs for user: {user.user_id}")
    try:
        logs = engine.query_audit_logs(user_id=user.user_id, limit=5)
        print(f"Found {len(logs)} audit entries")
        for i, log in enumerate(logs[:3], 1):
            print(f"\n  Entry {i}:")
            print(f"    Event: {log.get('event_type', 'N/A')}")
            print(f"    Resource: {log.get('resource_id', 'N/A')}")
            print(f"    Time: {log.get('timestamp', 'N/A')}")
    except Exception as e:
        print(f"  (Audit query requires running backend: {e})")

    # ==========================================================
    # Step 5: Check lineage
    # ==========================================================
    print_section("Step 5: Lineage Verification")

    try:
        print("\nLineage for: monthly_sales_report.parquet")
        lineage = engine.get_lineage("monthly_sales_report.parquet")
        nodes = list(lineage.get("nodes", {}).keys())
        edges = lineage.get("edges", [])
        print(f"  Nodes in graph: {len(nodes)}")
        print(f"  Connections: {len(edges)}")

        if nodes:
            print("  Data flow:")
            for node in nodes:
                print(f"    - {node}")
    except Exception as e:
        print(f"  (Lineage query requires running backend: {e})")

    # ==========================================================
    # Summary
    # ==========================================================
    print_section("Workflow Summary")

    print(f"\nClassifications performed: {len(classifications)}")
    print(f"Access requests approved: {len(approved)}")
    print(f"Access requests denied: {len(denied)}")

    if denied:
        print("\nDenied requests:")
        for resource, op_type, reason in denied:
            print(f"  - {op_type.value} {resource}: {reason}")

    print("\n✓ Governance workflow complete")
    print("  All operations have been classified, evaluated, and audited.")


if __name__ == "__main__":
    main()
