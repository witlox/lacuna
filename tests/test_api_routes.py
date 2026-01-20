"""Unit tests for Lacuna API routes."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from lacuna.models.classification import Classification, DataTier


class TestHealthRoutes:
    """Tests for health check endpoints."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create a test client."""
        from lacuna.api.app import create_app

        app = create_app()
        return TestClient(app)

    def test_health_endpoint(self, client: TestClient) -> None:
        """Test basic health check."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data

    def test_readiness_endpoint(self, client: TestClient) -> None:
        """Test readiness check."""
        response = client.get("/health/ready")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert "environment" in data

    def test_liveness_endpoint(self, client: TestClient) -> None:
        """Test liveness check."""
        response = client.get("/health/live")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"


class TestClassifyRoutes:
    """Tests for classification endpoints."""

    @pytest.fixture
    def mock_engine(self) -> MagicMock:
        """Create a mock governance engine."""
        mock = MagicMock()
        mock.classify.return_value = Classification(
            tier=DataTier.PROPRIETARY,
            confidence=0.95,
            reasoning="Contains customer data",
            tags=["PII"],
            classifier_name="heuristic",
        )
        return mock

    @pytest.fixture
    def client(self, mock_engine: MagicMock) -> TestClient:
        """Create a test client with mocked engine."""
        from lacuna.api.app import create_app

        app = create_app()

        # Override the engine dependency
        from lacuna.api import app as app_module

        app_module._engine = mock_engine

        return TestClient(app)

    def test_classify_basic(self, client: TestClient) -> None:
        """Test basic classification."""
        response = client.post(
            "/api/v1/classify",
            json={
                "query": "What are the customer payment details?",
                "user_id": "test-user",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["tier"] == "PROPRIETARY"
        assert data["confidence"] == 0.95
        assert "reasoning" in data
        assert "PII" in data["tags"]

    def test_classify_with_context(self, client: TestClient) -> None:
        """Test classification with full context."""
        response = client.post(
            "/api/v1/classify",
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

    def test_classify_batch(self, client: TestClient) -> None:
        """Test batch classification."""
        response = client.post(
            "/api/v1/classify/batch",
            json={
                "queries": ["Query 1", "Query 2", "Query 3"],
                "user_id": "test-user",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert len(data["results"]) == 3
        assert "total_latency_ms" in data

    def test_classify_missing_query(self, client: TestClient) -> None:
        """Test classification with missing query."""
        response = client.post(
            "/api/v1/classify",
            json={"user_id": "test-user"},
        )

        assert response.status_code == 422  # Validation error


class TestEvaluateRoutes:
    """Tests for policy evaluation endpoints."""

    @pytest.fixture
    def mock_engine(self) -> MagicMock:
        """Create a mock governance engine."""
        mock = MagicMock()

        # Mock for evaluation result
        mock_result = MagicMock()
        mock_result.allowed = True
        mock_result.tier = "PUBLIC"
        mock_result.confidence = 0.9
        mock_result.reasoning = "Operation allowed"
        mock_result.tags = []
        mock_result.alternatives = []
        mock_result.matched_rules = []
        mock_result.evaluation_id = "eval-123"
        mock_result.total_latency_ms = 10.5

        mock.evaluate_operation.return_value = mock_result
        return mock

    @pytest.fixture
    def client(self, mock_engine: MagicMock) -> TestClient:
        """Create a test client with mocked engine."""
        from lacuna.api.app import create_app

        app = create_app()

        from lacuna.api import app as app_module

        app_module._engine = mock_engine

        return TestClient(app)

    def test_evaluate_operation(self, client: TestClient) -> None:
        """Test evaluating an operation."""
        response = client.post(
            "/api/v1/evaluate",
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
        assert data["allowed"] is True

    def test_evaluate_export(self, client: TestClient) -> None:
        """Test evaluating an export operation."""
        response = client.post(
            "/api/v1/evaluate",
            json={
                "operation_type": "export",
                "resource_type": "file",
                "resource_id": "customers.csv",
                "destination": "~/Downloads/export.csv",
                "user_id": "analyst@company.com",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "allowed" in data

    def test_evaluate_missing_fields(self, client: TestClient) -> None:
        """Test evaluation with missing required fields."""
        response = client.post(
            "/api/v1/evaluate",
            json={
                "operation_type": "read",
                # Missing resource_type, resource_id, user_id
            },
        )

        assert response.status_code == 422  # Validation error


class TestLineageRoutes:
    """Tests for lineage endpoints."""

    @pytest.fixture
    def mock_engine(self) -> MagicMock:
        """Create a mock governance engine with lineage tracker."""
        mock = MagicMock()

        # Mock get_lineage to return proper structure
        mock.get_lineage.return_value = {
            "nodes": {"source.csv": {}, "output.csv": {}},
            "edges": [
                {
                    "source_id": "source.csv",
                    "destination_id": "output.csv",
                    "operation_type": "transform",
                }
            ],
        }

        # Mock upstream/downstream
        mock.get_upstream.return_value = ["source_a.csv", "source_b.csv"]
        mock.get_downstream.return_value = ["output.csv"]

        mock.lineage_tracker = MagicMock()
        mock.lineage_tracker.track_operation.return_value = MagicMock()

        mock.classify.return_value = Classification(
            tier=DataTier.INTERNAL,
            confidence=0.9,
            reasoning="Internal data",
            classifier_name="heuristic",
        )
        return mock

    @pytest.fixture
    def client(self, mock_engine: MagicMock) -> TestClient:
        """Create a test client with mocked engine."""
        from lacuna.api.app import create_app

        app = create_app()

        from lacuna.api import app as app_module

        app_module._engine = mock_engine

        return TestClient(app)

    def test_get_lineage(self, client: TestClient) -> None:
        """Test getting lineage for an artifact."""
        response = client.get("/api/v1/lineage/output.csv")

        assert response.status_code == 200
        data = response.json()
        assert "artifact_id" in data
        assert data["artifact_id"] == "output.csv"


class TestAuditRoutes:
    """Tests for audit endpoints."""

    @pytest.fixture
    def mock_engine(self) -> MagicMock:
        """Create a mock governance engine with audit logger."""
        mock = MagicMock()

        # Mock audit logger backend
        mock_logger = MagicMock()
        mock_backend = MagicMock()
        mock_backend.query.return_value = []
        mock_logger._backend = mock_backend

        mock.audit_logger = mock_logger

        # Mock query_audit_logs to return proper structure
        mock.query_audit_logs.return_value = {
            "records": [],
            "total": 0,
        }

        mock.classify.return_value = Classification(
            tier=DataTier.INTERNAL,
            confidence=0.9,
            reasoning="Internal",
            classifier_name="heuristic",
        )
        return mock

    @pytest.fixture
    def client(self, mock_engine: MagicMock) -> TestClient:
        """Create a test client with mocked engine."""
        from lacuna.api.app import create_app

        app = create_app()

        from lacuna.api import app as app_module

        app_module._engine = mock_engine

        return TestClient(app)

    def test_query_audit_logs(self, client: TestClient) -> None:
        """Test querying audit logs."""
        response = client.get("/api/v1/audit")

        assert response.status_code == 200

    def test_query_audit_with_filters(self, client: TestClient) -> None:
        """Test querying audit logs with filters."""
        response = client.get(
            "/api/v1/audit",
            params={
                "user_id": "test-user",
                "limit": 10,
            },
        )

        assert response.status_code == 200


class TestOpenAPI:
    """Tests for OpenAPI documentation."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create a test client."""
        from lacuna.api.app import create_app

        app = create_app()
        return TestClient(app)

    def test_openapi_json(self, client: TestClient) -> None:
        """Test OpenAPI JSON endpoint."""
        response = client.get("/openapi.json")

        assert response.status_code == 200
        data = response.json()
        assert data["openapi"].startswith("3.")
        assert data["info"]["title"] == "Lacuna"

    def test_docs_redirect(self, client: TestClient) -> None:
        """Test docs endpoint exists."""
        response = client.get("/docs", follow_redirects=False)

        # Should return 200 (Swagger UI) or redirect
        assert response.status_code in [200, 307]

    def test_redoc_redirect(self, client: TestClient) -> None:
        """Test redoc endpoint exists."""
        response = client.get("/redoc", follow_redirects=False)

        assert response.status_code in [200, 307]
