#!/usr/bin/env python3
"""Policy evaluation example.

Demonstrates how to evaluate data operations against
governance policies to determine if they are allowed.
"""

from lacuna.engine.governance import GovernanceEngine
from lacuna.models.data_operation import DataOperation, OperationType, UserContext


def main() -> None:
    """Run policy evaluation examples."""
    # Initialize the governance engine
    engine = GovernanceEngine()

    print("=== Policy Evaluation Examples ===\n")

    # Example 1: Basic read operation
    print("1. Evaluating a read operation:")
    user = UserContext(
        user_id="alice",
        user_role="analyst",
        user_department="marketing",
    )
    operation = DataOperation(
        operation_type=OperationType.READ,
        resource_id="marketing_data.csv",
        user_context=user,
    )
    result = engine.evaluate_operation(operation)
    print(f"   Operation: {operation.operation_type.value} on {operation.resource_id}")
    print(f"   User: {user.user_id} ({user.user_role})")
    print(f"   Allowed: {result.allowed}")
    if not result.allowed:
        print(f"   Reason: {result.to_user_message()}")
    print()

    # Example 2: Export operation (higher risk)
    print("2. Evaluating an export operation:")
    user = UserContext(
        user_id="bob",
        user_role="intern",
        user_department="engineering",
    )
    operation = DataOperation(
        operation_type=OperationType.EXPORT,
        resource_id="customer_pii.csv",
        user_context=user,
    )
    result = engine.evaluate_operation(operation)
    print(f"   Operation: {operation.operation_type.value} on {operation.resource_id}")
    print(f"   User: {user.user_id} ({user.user_role})")
    print(f"   Allowed: {result.allowed}")
    if not result.allowed:
        print(f"   Message: {result.to_user_message()}")
    print()

    # Example 3: Transform operation with lineage
    print("3. Evaluating a transform operation:")
    user = UserContext(
        user_id="charlie",
        user_role="data_engineer",
        user_department="data_platform",
    )
    operation = DataOperation(
        operation_type=OperationType.TRANSFORM,
        resource_id="aggregated_metrics.parquet",
        source_resources=["raw_events.csv", "user_sessions.csv"],
        user_context=user,
        metadata={"transformation": "aggregate_by_day"},
    )
    result = engine.evaluate_operation(operation)
    print(f"   Operation: {operation.operation_type.value}")
    print(f"   Sources: {operation.source_resources}")
    print(f"   Target: {operation.resource_id}")
    print(f"   Allowed: {result.allowed}")
    print()

    # Example 4: Delete operation (administrative)
    print("4. Evaluating a delete operation:")
    user = UserContext(
        user_id="admin",
        user_role="admin",
        user_department="it",
        user_clearance="high",
    )
    operation = DataOperation(
        operation_type=OperationType.DELETE,
        resource_id="old_logs.csv",
        user_context=user,
    )
    result = engine.evaluate_operation(operation)
    print(f"   Operation: {operation.operation_type.value} on {operation.resource_id}")
    print(f"   User: {user.user_id} (clearance: {user.user_clearance})")
    print(f"   Allowed: {result.allowed}")
    print()

    # Example 5: Check multiple operations
    print("5. Batch policy checks:")
    operations = [
        (OperationType.READ, "public_docs.md"),
        (OperationType.WRITE, "internal_config.yaml"),
        (OperationType.EXPORT, "proprietary_model.pkl"),
    ]
    user = UserContext(user_id="eve", user_role="developer")
    for op_type, resource in operations:
        op = DataOperation(
            operation_type=op_type,
            resource_id=resource,
            user_context=user,
        )
        r = engine.evaluate_operation(op)
        status = "✓ Allowed" if r.allowed else "✗ Denied"
        print(f"   {status} | {op_type.value:10} | {resource}")


if __name__ == "__main__":
    main()
