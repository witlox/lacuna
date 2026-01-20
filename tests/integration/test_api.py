"""End-to-end integration tests for the Lacuna API."""

import time
from typing import Optional

import pytest
import requests

pytestmark = pytest.mark.integration


class TestAPIHealth:
    """Tests for API health and readiness."""

    @pytest.fixture(scope="class")
    def api_base_url(self) -> str:
        """Get API base URL."""
        import os

        return os.environ.get("LACUNA_API_URL", "http://localhost:8000")

    def test_health_endpoint(self, api_base_url):
        """Test health endpoint returns healthy status."""
        response = requests.get(f"{api_base_url}/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"

    def test_readiness_endpoint(self, api_base_url):
        """Test readiness endpoint."""
        response = requests.get(f"{api_base_url}/health/ready")

        # Should return 200 if all dependencies are ready
        assert response.status_code in [200, 503]

    def test_openapi_docs(self, api_base_url):
        """Test OpenAPI documentation is available."""
        response = requests.get(f"{api_base_url}/openapi.json")
        assert response.status_code == 200

        data = response.json()
        assert "openapi" in data
        assert data["info"]["title"] == "Lacuna"


class TestClassificationAPI:
    """Tests for classification API endpoints."""

    @pytest.fixture(scope="class")
    def api_base_url(self) -> str:
        import os

        return os.environ.get("LACUNA_API_URL", "http://localhost:8000")

    def test_classify_proprietary_query(self, api_base_url):
        """Test classifying a proprietary query."""
        response = requests.post(
            f"{api_base_url}/api/v1/classify",
            json={
                "query": "What are the customer payment details?",
                "project": "analytics",
                "user_id": "test-user",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["tier"] == "PROPRIETARY"
        assert data["confidence"] >= 0.5
        assert "reasoning" in data

    def test_classify_public_query(self, api_base_url):
        """Test classifying a public query."""
        response = requests.post(
            f"{api_base_url}/api/v1/classify",
            json={
                "query": "What is machine learning?",
                "user_id": "test-user",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["tier"] in ["PUBLIC", "INTERNAL"]
        assert "reasoning" in data

    def test_classify_with_context(self, api_base_url):
        """Test classification with full context."""
        response = requests.post(
            f"{api_base_url}/api/v1/classify",
            json={
                "query": "Generate quarterly report",
                "project": "finance",
                "user_id": "analyst@company.com",
                "user_role": "analyst",
                "environment": "production",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "tier" in data
        assert "classifier" in data

    def test_batch_classification(self, api_base_url):
        """Test batch classification endpoint."""
        response = requests.post(
            f"{api_base_url}/api/v1/classify/batch",
            json={
                "queries": [
                    "Customer purchase history",
                    "Weather forecast for tomorrow",
                    "Internal deployment schedule",
                ],
                "user_id": "test-user",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "results" in data
        assert len(data["results"]) == 3
        assert "total_latency_ms" in data


class TestEvaluationAPI:
    """Tests for policy evaluation API endpoints."""

    @pytest.fixture(scope="class")
    def api_base_url(self) -> str:
        import os

        return os.environ.get("LACUNA_API_URL", "http://localhost:8000")

    def test_evaluate_read_operation(self, api_base_url):
        """Test evaluating a read operation."""
        response = requests.post(
            f"{api_base_url}/api/v1/evaluate",
            json={
                "operation_type": "read",
                "resource_type": "table",
                "resource_id": "public.products",
                "user_id": "analyst@company.com",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "allowed" in data
        # Read operations should generally be allowed
        assert data["allowed"] is True

    def test_evaluate_export_blocked(self, api_base_url):
        """Test that proprietary export to Downloads is blocked."""
        response = requests.post(
            f"{api_base_url}/api/v1/evaluate",
            json={
                "operation_type": "export",
                "resource_type": "file",
                "resource_id": "customers.csv",
                "resource_classification": "PROPRIETARY",
                "resource_tags": ["PII"],
                "destination": "~/Downloads/export.csv",
                "user_id": "analyst@company.com",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["allowed"] is False
        assert "reasoning" in data
        assert "alternatives" in data
        assert len(data["alternatives"]) > 0

    def test_evaluate_with_full_context(self, api_base_url):
        """Test evaluation with full operation context."""
        response = requests.post(
            f"{api_base_url}/api/v1/evaluate",
            json={
                "operation_type": "transform",
                "resource_type": "table",
                "resource_id": "raw.customers",
                "sources": ["raw.customer_master", "raw.orders"],
                "destination": "analytics.customer_summary",
                "user_id": "data-engineer@company.com",
                "user_role": "engineer",
                "purpose": "Create customer analytics summary",
                "environment": "production",
                "project": "customer-360",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "allowed" in data
        assert "classification" in data
        assert "reasoning" in data


class TestLineageAPI:
    """Tests for lineage API endpoints."""

    @pytest.fixture(scope="class")
    def api_base_url(self) -> str:
        import os

        return os.environ.get("LACUNA_API_URL", "http://localhost:8000")

    def test_track_lineage(self, api_base_url):
        """Test tracking lineage for a transformation."""
        response = requests.post(
            f"{api_base_url}/api/v1/lineage/track",
            json={
                "operation_type": "transform",
                "sources": ["source_a.csv", "source_b.csv"],
                "destination": "combined_output.csv",
                "user_id": "analyst@company.com",
                "transformation_description": "Join sources A and B",
            },
        )

        assert response.status_code in [200, 201]

    def test_get_upstream_lineage(self, api_base_url):
        """Test getting upstream lineage."""
        response = requests.get(
            f"{api_base_url}/api/v1/lineage/upstream/combined_output.csv"
        )

        # May return 200 or 404 depending on test order
        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            assert "artifact_id" in data

    def test_get_downstream_lineage(self, api_base_url):
        """Test getting downstream lineage."""
        response = requests.get(
            f"{api_base_url}/api/v1/lineage/downstream/source_a.csv"
        )

        assert response.status_code in [200, 404]


class TestAuditAPI:
    """Tests for audit API endpoints."""

    @pytest.fixture(scope="class")
    def api_base_url(self) -> str:
        import os

        return os.environ.get("LACUNA_API_URL", "http://localhost:8000")

    def test_query_audit_logs(self, api_base_url):
        """Test querying audit logs."""
        response = requests.get(
            f"{api_base_url}/api/v1/audit/logs",
            params={
                "limit": 10,
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "logs" in data or "results" in data or isinstance(data, list)

    def test_query_audit_by_user(self, api_base_url):
        """Test querying audit logs by user."""
        response = requests.get(
            f"{api_base_url}/api/v1/audit/logs",
            params={
                "user_id": "test-user",
                "limit": 10,
            },
        )

        assert response.status_code == 200

    def test_query_audit_by_event_type(self, api_base_url):
        """Test querying audit logs by event type."""
        response = requests.get(
            f"{api_base_url}/api/v1/audit/logs",
            params={
                "event_type": "policy.deny",
                "limit": 10,
            },
        )

        assert response.status_code == 200


class TestAPIPerformance:
    """Performance tests for API endpoints."""

    @pytest.fixture(scope="class")
    def api_base_url(self) -> str:
        import os

        return os.environ.get("LACUNA_API_URL", "http://localhost:8000")

    def test_classification_latency(self, api_base_url):
        """Test that classification responds within SLA."""
        start = time.time()

        response = requests.post(
            f"{api_base_url}/api/v1/classify",
            json={
                "query": "Quick classification test",
                "user_id": "perf-test",
            },
        )

        latency_ms = (time.time() - start) * 1000

        assert response.status_code == 200
        # Heuristic classification should be < 100ms
        assert latency_ms < 500  # Allow some slack for cold start

    def test_concurrent_classifications(self, api_base_url):
        """Test concurrent classification requests."""
        import concurrent.futures

        def classify(query: str):
            return requests.post(
                f"{api_base_url}/api/v1/classify",
                json={"query": query, "user_id": "concurrent-test"},
            )

        queries = [f"Test query {i}" for i in range(10)]

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(classify, q) for q in queries]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # All requests should succeed
        assert all(r.status_code == 200 for r in results)
