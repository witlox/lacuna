"""Tests for OPA policy client."""

from unittest.mock import MagicMock, Mock, patch

import pytest
import requests

from lacuna.policy.client import OPAClient


class TestOPAClientInit:
    """Tests for OPAClient initialization."""

    def test_client_default_init(self) -> None:
        """Test default initialization."""
        with patch("lacuna.policy.client.get_settings") as mock_settings:
            mock_settings.return_value.policy.opa_endpoint = "http://localhost:8181"
            mock_settings.return_value.policy.opa_policy_path = "lacuna/classification"
            mock_settings.return_value.policy.opa_timeout = 1.0

            client = OPAClient()

            assert client.endpoint == "http://localhost:8181"
            assert client.policy_path == "lacuna/classification"
            assert client.timeout == 1.0

    def test_client_custom_endpoint(self) -> None:
        """Test initialization with custom endpoint."""
        with patch("lacuna.policy.client.get_settings") as mock_settings:
            mock_settings.return_value.policy.opa_endpoint = None
            mock_settings.return_value.policy.opa_policy_path = "default"
            mock_settings.return_value.policy.opa_timeout = 1.0

            client = OPAClient(endpoint="http://custom:8181")

            assert client.endpoint == "http://custom:8181"

    def test_client_no_endpoint(self) -> None:
        """Test client without endpoint configured."""
        with patch("lacuna.policy.client.get_settings") as mock_settings:
            mock_settings.return_value.policy.opa_endpoint = None
            mock_settings.return_value.policy.opa_policy_path = "lacuna"
            mock_settings.return_value.policy.opa_timeout = 1.0

            client = OPAClient()

            assert client.endpoint is None
            assert client.is_available() is False


class TestOPAClientAvailability:
    """Tests for OPAClient availability checks."""

    def test_is_available_success(self) -> None:
        """Test successful availability check."""
        with patch("lacuna.policy.client.get_settings") as mock_settings:
            mock_settings.return_value.policy.opa_endpoint = "http://localhost:8181"
            mock_settings.return_value.policy.opa_policy_path = "lacuna"
            mock_settings.return_value.policy.opa_timeout = 1.0

            client = OPAClient()

            with patch.object(client._session, "get") as mock_get:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_get.return_value = mock_response

                assert client.is_available() is True

    def test_is_available_failure(self) -> None:
        """Test failed availability check."""
        with patch("lacuna.policy.client.get_settings") as mock_settings:
            mock_settings.return_value.policy.opa_endpoint = "http://localhost:8181"
            mock_settings.return_value.policy.opa_policy_path = "lacuna"
            mock_settings.return_value.policy.opa_timeout = 1.0

            client = OPAClient()

            with patch.object(client._session, "get") as mock_get:
                mock_get.side_effect = requests.RequestException("Connection failed")

                assert client.is_available() is False

    def test_is_available_no_endpoint(self) -> None:
        """Test availability with no endpoint."""
        with patch("lacuna.policy.client.get_settings") as mock_settings:
            mock_settings.return_value.policy.opa_endpoint = None
            mock_settings.return_value.policy.opa_policy_path = "lacuna"
            mock_settings.return_value.policy.opa_timeout = 1.0

            client = OPAClient()

            assert client.is_available() is False


class TestOPAClientEvaluate:
    """Tests for OPAClient policy evaluation."""

    @pytest.fixture
    def client(self):
        """Create a client with mocked settings."""
        with patch("lacuna.policy.client.get_settings") as mock_settings:
            mock_settings.return_value.policy.opa_endpoint = "http://localhost:8181"
            mock_settings.return_value.policy.opa_policy_path = "lacuna/classification"
            mock_settings.return_value.policy.opa_timeout = 1.0
            yield OPAClient()

    def test_evaluate_success(self, client) -> None:
        """Test successful policy evaluation."""
        with patch.object(client._session, "post") as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "result": {
                    "tier": "PROPRIETARY",
                    "confidence": 0.95,
                }
            }
            mock_post.return_value = mock_response

            result = client.evaluate({"query": "customer data"})

            assert result is not None
            assert result["tier"] == "PROPRIETARY"

    def test_evaluate_timeout(self, client) -> None:
        """Test evaluation timeout handling."""
        with patch.object(client._session, "post") as mock_post:
            mock_post.side_effect = requests.Timeout("Request timed out")

            result = client.evaluate({"query": "test"})

            assert result is None

    def test_evaluate_request_error(self, client) -> None:
        """Test evaluation request error handling."""
        with patch.object(client._session, "post") as mock_post:
            mock_post.side_effect = requests.RequestException("Connection error")

            result = client.evaluate({"query": "test"})

            assert result is None

    def test_evaluate_bad_status(self, client) -> None:
        """Test evaluation with non-200 status."""
        with patch.object(client._session, "post") as mock_post:
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            mock_post.return_value = mock_response

            result = client.evaluate({"query": "test"})

            assert result is None

    def test_evaluate_json_decode_error(self, client) -> None:
        """Test evaluation with invalid JSON response."""
        import json

        with patch.object(client._session, "post") as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.side_effect = json.JSONDecodeError("Invalid", "", 0)
            mock_post.return_value = mock_response

            result = client.evaluate({"query": "test"})

            assert result is None

    def test_evaluate_no_endpoint(self) -> None:
        """Test evaluation with no endpoint configured."""
        with patch("lacuna.policy.client.get_settings") as mock_settings:
            mock_settings.return_value.policy.opa_endpoint = None
            mock_settings.return_value.policy.opa_policy_path = "lacuna"
            mock_settings.return_value.policy.opa_timeout = 1.0

            client = OPAClient()
            result = client.evaluate({"query": "test"})

            assert result is None

    def test_evaluate_custom_policy_path(self, client) -> None:
        """Test evaluation with custom policy path."""
        with patch.object(client._session, "post") as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"result": {"allowed": True}}
            mock_post.return_value = mock_response

            _result = client.evaluate({"action": "export"}, policy_path="lacuna/export")

            # Verify URL was constructed correctly
            mock_post.assert_called_once()
            call_url = mock_post.call_args[0][0]
            assert "lacuna/export" in call_url


class TestOPAClientSpecializedMethods:
    """Tests for specialized evaluation methods."""

    @pytest.fixture
    def client(self):
        with patch("lacuna.policy.client.get_settings") as mock_settings:
            mock_settings.return_value.policy.opa_endpoint = "http://localhost:8181"
            mock_settings.return_value.policy.opa_policy_path = "lacuna"
            mock_settings.return_value.policy.opa_timeout = 1.0
            yield OPAClient()

    def test_evaluate_classification(self, client) -> None:
        """Test classification-specific evaluation."""
        with patch.object(client, "evaluate") as mock_eval:
            mock_eval.return_value = {"tier": "PUBLIC"}

            _result = client.evaluate_classification({"query": "weather"})

            mock_eval.assert_called_once()
            assert "classification" in mock_eval.call_args[0][1]

    def test_evaluate_export(self, client) -> None:
        """Test export-specific evaluation."""
        with patch.object(client, "evaluate") as mock_eval:
            mock_eval.return_value = {"allowed": False}

            _result = client.evaluate_export({"destination": "~/Downloads"})

            mock_eval.assert_called_once()
            assert "export" in mock_eval.call_args[0][1]


class TestOPAClientPolicyManagement:
    """Tests for policy management methods."""

    @pytest.fixture
    def client(self):
        with patch("lacuna.policy.client.get_settings") as mock_settings:
            mock_settings.return_value.policy.opa_endpoint = "http://localhost:8181"
            mock_settings.return_value.policy.opa_policy_path = "lacuna"
            mock_settings.return_value.policy.opa_timeout = 1.0
            yield OPAClient()

    def test_get_policies_success(self, client) -> None:
        """Test getting loaded policies."""
        with patch.object(client._session, "get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"result": [{"id": "test-policy"}]}
            mock_get.return_value = mock_response

            result = client.get_policies()

            assert result is not None

    def test_get_policies_failure(self, client) -> None:
        """Test handling policy fetch failure."""
        with patch.object(client._session, "get") as mock_get:
            mock_get.side_effect = requests.RequestException("Failed")

            result = client.get_policies()

            assert result is None

    def test_load_policy_success(self, client) -> None:
        """Test loading a policy."""
        with patch.object(client._session, "put") as mock_put:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_put.return_value = mock_response

            result = client.load_policy("test-policy", "package test")

            assert result is True

    def test_load_policy_failure(self, client) -> None:
        """Test handling policy load failure."""
        with patch.object(client._session, "put") as mock_put:
            mock_response = Mock()
            mock_response.status_code = 400
            mock_put.return_value = mock_response

            result = client.load_policy("test-policy", "invalid rego")

            assert result is False

    def test_delete_policy_success(self, client) -> None:
        """Test deleting a policy."""
        with patch.object(client._session, "delete") as mock_delete:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_delete.return_value = mock_response

            result = client.delete_policy("test-policy")

            assert result is True

    def test_delete_policy_not_found(self, client) -> None:
        """Test deleting non-existent policy."""
        with patch.object(client._session, "delete") as mock_delete:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_delete.return_value = mock_response

            result = client.delete_policy("nonexistent")

            assert result is False


class TestOPAClientContextManager:
    """Tests for context manager functionality."""

    def test_context_manager(self) -> None:
        """Test using client as context manager."""
        with patch("lacuna.policy.client.get_settings") as mock_settings:
            mock_settings.return_value.policy.opa_endpoint = "http://localhost:8181"
            mock_settings.return_value.policy.opa_policy_path = "lacuna"
            mock_settings.return_value.policy.opa_timeout = 1.0

            with OPAClient() as client:
                assert client.endpoint == "http://localhost:8181"

            # Session should be closed after context exit

    def test_close_method(self) -> None:
        """Test explicit close method."""
        with patch("lacuna.policy.client.get_settings") as mock_settings:
            mock_settings.return_value.policy.opa_endpoint = "http://localhost:8181"
            mock_settings.return_value.policy.opa_policy_path = "lacuna"
            mock_settings.return_value.policy.opa_timeout = 1.0

            client = OPAClient()

            with patch.object(client._session, "close") as mock_close:
                client.close()
                mock_close.assert_called_once()
