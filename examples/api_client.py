#!/usr/bin/env python3
"""API client example.

Demonstrates how to interact with the Lacuna REST API
using HTTP requests.

Prerequisites:
    Start the dev server: lacuna dev
"""

import sys

import requests

BASE_URL = "http://localhost:8000"


def check_health() -> bool:
    """Check if the API is healthy."""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        return False


def classify_query(query: str, context: dict | None = None) -> dict:
    """Classify a query via the API."""
    payload = {"query": query}
    if context:
        payload["context"] = context

    response = requests.post(
        f"{BASE_URL}/api/v1/classify",
        json=payload,
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def classify_batch(queries: list[str]) -> dict:
    """Classify multiple queries in a single request."""
    response = requests.post(
        f"{BASE_URL}/api/v1/classify/batch",
        json={"queries": queries},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def evaluate_operation(
    operation_type: str,
    resource_id: str,
    user_id: str,
    user_role: str | None = None,
) -> dict:
    """Evaluate a data operation against policies."""
    payload = {
        "operation_type": operation_type,
        "resource_id": resource_id,
        "user_context": {
            "user_id": user_id,
            "user_role": user_role,
        },
    }
    response = requests.post(
        f"{BASE_URL}/api/v1/evaluate",
        json=payload,
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def get_lineage(artifact_id: str, max_depth: int = 10) -> dict:
    """Get lineage for an artifact."""
    response = requests.get(
        f"{BASE_URL}/api/v1/lineage/{artifact_id}",
        params={"max_depth": max_depth},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def query_audit_logs(
    user_id: str | None = None,
    resource_id: str | None = None,
    limit: int = 10,
) -> dict:
    """Query audit logs."""
    params = {"limit": limit}
    if user_id:
        params["user_id"] = user_id
    if resource_id:
        params["resource_id"] = resource_id

    response = requests.get(
        f"{BASE_URL}/api/v1/audit",
        params=params,
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def get_openapi_spec() -> dict:
    """Get the OpenAPI specification."""
    response = requests.get(f"{BASE_URL}/openapi.json", timeout=10)
    response.raise_for_status()
    return response.json()


def main() -> None:
    """Run API client examples."""
    print("=== Lacuna API Client Examples ===\n")

    # Check if server is running
    print("1. Checking API health:")
    if not check_health():
        print("   ✗ API is not reachable at", BASE_URL)
        print("   Please start the dev server: lacuna dev")
        sys.exit(1)
    print("   ✓ API is healthy")
    print()

    # Classify a query
    print("2. Classifying a query:")
    result = classify_query("SELECT email, phone FROM customers")
    print(f"   Tier: {result.get('tier')}")
    print(f"   Confidence: {result.get('confidence', 0):.2%}")
    print()

    # Classify with context
    print("3. Classifying with user context:")
    context = {"user_id": "analyst", "project": "quarterly_report"}
    result = classify_query("SELECT revenue FROM sales", context)
    print(f"   Tier: {result.get('tier')}")
    print()

    # Batch classification
    print("4. Batch classification:")
    queries = [
        "SELECT name FROM users",
        "SELECT ssn FROM employees",
        "SELECT id FROM products",
    ]
    results = classify_batch(queries)
    for item in results.get("classifications", []):
        print(f"   {item.get('tier', 'N/A'):12} | {item.get('query', 'N/A')[:40]}")
    print()

    # Evaluate operation
    print("5. Evaluating an operation:")
    result = evaluate_operation(
        operation_type="read",
        resource_id="customer_data.csv",
        user_id="alice",
        user_role="analyst",
    )
    allowed = result.get("allowed", False)
    status = "✓ Allowed" if allowed else "✗ Denied"
    print(f"   {status}")
    print()

    # Get OpenAPI spec info
    print("6. OpenAPI specification:")
    spec = get_openapi_spec()
    print(f"   Title: {spec.get('info', {}).get('title')}")
    print(f"   Version: {spec.get('info', {}).get('version')}")
    print(f"   Endpoints: {len(spec.get('paths', {}))}")
    print()

    # Query audit logs
    print("7. Querying audit logs:")
    try:
        logs = query_audit_logs(limit=5)
        print(f"   Retrieved {len(logs.get('logs', []))} log entries")
    except requests.exceptions.HTTPError as e:
        print(f"   Error: {e}")


if __name__ == "__main__":
    main()
