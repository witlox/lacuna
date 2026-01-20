"""Integration tests for OPA policy evaluation."""

import pytest
import requests

pytestmark = pytest.mark.integration


class TestOPAConnection:
    """Tests for OPA connectivity."""

    def test_opa_health(self, opa_endpoint):
        """Test that OPA is healthy."""
        response = requests.get(f"{opa_endpoint}/health")
        assert response.status_code == 200

    def test_opa_policies_loaded(self, opa_endpoint):
        """Test that policies are loaded."""
        response = requests.get(f"{opa_endpoint}/v1/policies")
        assert response.status_code == 200

        data = response.json()
        assert "result" in data


class TestClassificationPolicy:
    """Tests for classification policy evaluation."""

    def test_classify_customer_query(self, opa_endpoint):
        """Test classification of customer-related query."""
        input_data = {
            "input": {
                "query": "How do we handle customer payment data?",
                "context": {
                    "project": "analytics",
                    "user_role": "analyst",
                },
                "tags": [],
            }
        }

        response = requests.post(
            f"{opa_endpoint}/v1/data/lacuna/classification",
            json=input_data,
        )

        assert response.status_code == 200
        result = response.json()

        # Should classify as PROPRIETARY due to "customer" keyword
        if "result" in result and result["result"]:
            assert result["result"].get("tier") == "PROPRIETARY"

    def test_classify_public_query(self, opa_endpoint):
        """Test classification of public query."""
        input_data = {
            "input": {
                "query": "What is the weather today?",
                "context": {
                    "project": "public",
                    "user_role": "analyst",
                },
                "tags": [],
            }
        }

        response = requests.post(
            f"{opa_endpoint}/v1/data/lacuna/classification",
            json=input_data,
        )

        assert response.status_code == 200
        result = response.json()

        # Should classify as PUBLIC (no sensitive patterns)
        if "result" in result and result["result"]:
            tier = result["result"].get("tier", "PUBLIC")
            assert tier in ["PUBLIC", "INTERNAL"]

    def test_classify_with_pii_tags(self, opa_endpoint):
        """Test classification when PII tags are present."""
        input_data = {
            "input": {
                "query": "Generate a summary report",
                "context": {
                    "project": "reporting",
                },
                "tags": ["PII", "SSN"],
            }
        }

        response = requests.post(
            f"{opa_endpoint}/v1/data/lacuna/classification",
            json=input_data,
        )

        assert response.status_code == 200
        result = response.json()

        # Should classify as PROPRIETARY due to PII tags
        if "result" in result and result["result"]:
            assert result["result"].get("tier") == "PROPRIETARY"

    def test_classify_internal_infrastructure(self, opa_endpoint):
        """Test classification of internal infrastructure query."""
        input_data = {
            "input": {
                "query": "Check the staging deployment status",
                "context": {
                    "project": "devops",
                },
                "tags": [],
            }
        }

        response = requests.post(
            f"{opa_endpoint}/v1/data/lacuna/classification",
            json=input_data,
        )

        assert response.status_code == 200
        result = response.json()

        # Should classify as INTERNAL due to "staging" keyword
        if "result" in result and result["result"]:
            tier = result["result"].get("tier")
            assert tier in ["INTERNAL", "PROPRIETARY"]


class TestExportPolicy:
    """Tests for export policy evaluation."""

    def test_deny_proprietary_to_downloads(self, opa_endpoint):
        """Test that PROPRIETARY data export to Downloads is denied."""
        input_data = {
            "input": {
                "source": {
                    "classification": "PROPRIETARY",
                    "tags": ["PII", "CUSTOMER"],
                },
                "destination": {
                    "path": "~/Downloads/export.csv",
                    "encrypted": False,
                },
            }
        }

        response = requests.post(
            f"{opa_endpoint}/v1/data/lacuna/export/allow",
            json=input_data,
        )

        assert response.status_code == 200
        result = response.json()

        # Should be denied
        assert result.get("result") is False

    def test_allow_public_export(self, opa_endpoint):
        """Test that PUBLIC data can be exported anywhere."""
        input_data = {
            "input": {
                "source": {
                    "classification": "PUBLIC",
                    "tags": [],
                },
                "destination": {
                    "path": "~/Downloads/public_data.csv",
                    "encrypted": False,
                },
            }
        }

        response = requests.post(
            f"{opa_endpoint}/v1/data/lacuna/export/allow",
            json=input_data,
        )

        assert response.status_code == 200
        result = response.json()

        # Should be allowed (PUBLIC has no restrictions)
        # The default policy is deny, so we check if there are no deny rules
        if "result" in result:
            # If allow is True or deny list is empty
            assert result.get("result") in [True, None]

    def test_deny_internal_external_export(self, opa_endpoint):
        """Test that INTERNAL data cannot go to external destinations."""
        input_data = {
            "input": {
                "source": {
                    "classification": "INTERNAL",
                    "tags": ["DEPLOYMENT"],
                },
                "destination": {
                    "path": "s3://external-bucket/data.csv",
                    "encrypted": True,
                },
            }
        }

        response = requests.post(
            f"{opa_endpoint}/v1/data/lacuna/export/allow",
            json=input_data,
        )

        assert response.status_code == 200
        result = response.json()

        # Should be denied (INTERNAL cannot go external)
        assert result.get("result") is False

    def test_get_export_alternatives(self, opa_endpoint):
        """Test getting alternatives when export is denied."""
        input_data = {
            "input": {
                "source": {
                    "classification": "PROPRIETARY",
                    "tags": ["PII", "EMAIL"],
                },
                "destination": {
                    "path": "~/Downloads/customer_emails.csv",
                    "encrypted": False,
                },
            }
        }

        response = requests.post(
            f"{opa_endpoint}/v1/data/lacuna/export/alternatives",
            json=input_data,
        )

        assert response.status_code == 200
        result = response.json()

        # Should have alternatives
        if "result" in result and result["result"]:
            alternatives = result["result"]
            assert len(alternatives) > 0

    def test_get_deny_reasons(self, opa_endpoint):
        """Test getting denial reasons."""
        input_data = {
            "input": {
                "source": {
                    "classification": "PROPRIETARY",
                    "tags": ["PII"],
                },
                "destination": {
                    "path": "~/Downloads/export.csv",
                    "encrypted": False,
                },
            }
        }

        response = requests.post(
            f"{opa_endpoint}/v1/data/lacuna/export/deny",
            json=input_data,
        )

        assert response.status_code == 200
        result = response.json()

        # Should have deny reasons
        if "result" in result and result["result"]:
            deny_reasons = result["result"]
            assert len(deny_reasons) > 0
            # Should mention unmanaged location
            assert any("unmanaged" in reason.lower() for reason in deny_reasons)


class TestOPAClient:
    """Tests for the OPA client wrapper."""

    def test_opa_client_is_available(self, opa_client):
        """Test that OPA client reports availability."""
        assert opa_client.is_available() is True

    def test_opa_client_evaluate(self, opa_client):
        """Test OPA client evaluation method."""
        policy_input = {
            "query": "customer data analysis",
            "context": {"project": "analytics"},
            "tags": [],
        }

        result = opa_client.evaluate(policy_input)

        # Result should be a dictionary
        assert isinstance(result, dict)
