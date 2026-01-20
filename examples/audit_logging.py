#!/usr/bin/env python3
"""Audit logging example.

Demonstrates how to query and inspect audit logs
for compliance and investigation purposes.
"""

from datetime import datetime, timedelta, timezone

from lacuna.engine.governance import GovernanceEngine
from lacuna.models.data_operation import DataOperation, OperationType, UserContext


def main() -> None:
    """Run audit logging examples."""
    # Initialize the governance engine
    engine = GovernanceEngine()

    print("=== Audit Logging Examples ===\n")

    # First, generate some audit events
    print("1. Generating audit events:")
    users = [
        UserContext(user_id="alice", user_role="analyst"),
        UserContext(user_id="bob", user_role="engineer"),
        UserContext(user_id="charlie", user_role="admin"),
    ]
    operations = [
        (OperationType.READ, "sales_data.csv"),
        (OperationType.EXPORT, "customer_list.csv"),
        (OperationType.DELETE, "temp_file.txt"),
    ]

    for user, (op_type, resource) in zip(users, operations):
        op = DataOperation(
            operation_type=op_type,
            resource_id=resource,
            user_context=user,
        )
        engine.evaluate_operation(op)
        print(f"   {user.user_id}: {op_type.value} on {resource}")
    print()

    # Example 2: Query all recent audit logs
    print("2. Querying recent audit logs:")
    try:
        logs = engine.query_audit_logs(limit=10)
        print(f"   Found {len(logs)} audit entries")
        for log in logs[:3]:
            print(f"   - {log.get('timestamp', 'N/A')}: {log.get('event_type', 'N/A')}")
    except Exception as e:
        print(f"   (Audit query requires running backend: {e})")
    print()

    # Example 3: Query by user
    print("3. Querying audit logs for specific user:")
    try:
        logs = engine.query_audit_logs(user_id="alice", limit=5)
        print("   User: alice")
        print(f"   Events: {len(logs)}")
    except Exception as e:
        print(f"   (Audit query requires running backend: {e})")
    print()

    # Example 4: Query by time range
    print("4. Querying audit logs by time range:")
    try:
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=1)
        logs = engine.query_audit_logs(
            start_time=start_time,
            end_time=end_time,
            limit=10,
        )
        print("   Time range: last 1 hour")
        print(f"   Events: {len(logs)}")
    except Exception as e:
        print(f"   (Audit query requires running backend: {e})")
    print()

    # Example 5: Query by resource
    print("5. Querying audit logs for specific resource:")
    try:
        logs = engine.query_audit_logs(resource_id="sales_data.csv", limit=5)
        print("   Resource: sales_data.csv")
        print(f"   Access events: {len(logs)}")
    except Exception as e:
        print(f"   (Audit query requires running backend: {e})")
    print()

    # Example 6: Count audit events
    print("6. Counting audit events:")
    try:
        count = engine.count_audit_logs()
        print(f"   Total audit events: {count}")
    except Exception as e:
        print(f"   (Audit query requires running backend: {e})")


if __name__ == "__main__":
    main()
