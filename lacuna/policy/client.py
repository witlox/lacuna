"""OPA (Open Policy Agent) client for policy evaluation."""

import json
from typing import Any, Optional

import requests
import structlog

from lacuna.config import get_settings

logger = structlog.get_logger()


class OPAClient:
    """
    Client for communicating with Open Policy Agent server.

    Supports:
    - Policy evaluation via REST API
    - Connection pooling for performance
    - Timeout and retry handling
    """

    def __init__(
        self,
        endpoint: Optional[str] = None,
        policy_path: Optional[str] = None,
        timeout: float = 1.0,
    ):
        """Initialize OPA client.

        Args:
            endpoint: OPA server endpoint (e.g., http://localhost:8181)
            policy_path: Policy path for queries
            timeout: Request timeout in seconds
        """
        settings = get_settings()
        self.endpoint = endpoint or settings.policy.opa_endpoint
        self.policy_path = policy_path or settings.policy.opa_policy_path
        self.timeout = timeout or settings.policy.opa_timeout

        # Create session for connection pooling
        self._session = requests.Session()
        self._session.headers.update({"Content-Type": "application/json"})

    def is_available(self) -> bool:
        """Check if OPA server is available.

        Returns:
            True if OPA is reachable
        """
        if not self.endpoint:
            return False

        try:
            response = self._session.get(
                f"{self.endpoint}/health",
                timeout=self.timeout,
            )
            return response.status_code == 200
        except requests.RequestException:
            return False

    def evaluate(
        self,
        input_data: dict[str, Any],
        policy_path: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        """Evaluate a policy against input data.

        Args:
            input_data: Input data for policy evaluation
            policy_path: Override policy path

        Returns:
            Policy evaluation result, or None on error
        """
        if not self.endpoint:
            logger.warning("opa_not_configured")
            return None

        path = policy_path or self.policy_path
        url = f"{self.endpoint}/v1/data/{path.replace('.', '/')}"

        try:
            response = self._session.post(
                url,
                json={"input": input_data},
                timeout=self.timeout,
            )

            if response.status_code != 200:
                logger.warning(
                    "opa_evaluation_failed",
                    status_code=response.status_code,
                    response=response.text[:200],
                )
                return None

            result = response.json()
            return dict(result.get("result")) if result.get("result") else None

        except requests.Timeout:
            logger.warning("opa_timeout", url=url, timeout=self.timeout)
            return None
        except requests.RequestException as e:
            logger.error("opa_request_error", error=str(e), url=url)
            return None
        except json.JSONDecodeError as e:
            logger.error("opa_json_error", error=str(e))
            return None

    def evaluate_classification(
        self, input_data: dict[str, Any]
    ) -> Optional[dict[str, Any]]:
        """Evaluate classification policy.

        Args:
            input_data: Classification input data

        Returns:
            Classification result from OPA
        """
        return self.evaluate(input_data, f"{self.policy_path}/classification")

    def evaluate_export(self, input_data: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Evaluate export policy.

        Args:
            input_data: Export operation data

        Returns:
            Policy decision for export
        """
        return self.evaluate(input_data, f"{self.policy_path}/export")

    def get_policies(self) -> Optional[dict[str, Any]]:
        """Get all loaded policies.

        Returns:
            Dictionary of loaded policies
        """
        if not self.endpoint:
            return None

        try:
            response = self._session.get(
                f"{self.endpoint}/v1/policies",
                timeout=self.timeout,
            )

            if response.status_code == 200:
                return dict(response.json())
            return None

        except requests.RequestException:
            return None

    def load_policy(self, policy_id: str, policy_rego: str) -> bool:
        """Load a policy into OPA.

        Args:
            policy_id: Unique policy identifier
            policy_rego: Rego policy content

        Returns:
            True if policy was loaded successfully
        """
        if not self.endpoint:
            return False

        try:
            response = self._session.put(
                f"{self.endpoint}/v1/policies/{policy_id}",
                data=policy_rego,
                headers={"Content-Type": "text/plain"},
                timeout=self.timeout,
            )

            success = response.status_code in (200, 201)
            if success:
                logger.info("opa_policy_loaded", policy_id=policy_id)
            else:
                logger.warning(
                    "opa_policy_load_failed",
                    policy_id=policy_id,
                    status_code=response.status_code,
                )
            return success

        except requests.RequestException as e:
            logger.error("opa_policy_load_error", error=str(e), policy_id=policy_id)
            return False

    def delete_policy(self, policy_id: str) -> bool:
        """Delete a policy from OPA.

        Args:
            policy_id: Policy identifier to delete

        Returns:
            True if policy was deleted
        """
        if not self.endpoint:
            return False

        try:
            response = self._session.delete(
                f"{self.endpoint}/v1/policies/{policy_id}",
                timeout=self.timeout,
            )
            return response.status_code in (200, 204)

        except requests.RequestException:
            return False

    def close(self) -> None:
        """Close the client session."""
        self._session.close()

    def __enter__(self) -> "OPAClient":
        """Context manager entry."""
        return self

    def __exit__(self, _exc_type: Any, _exc_val: Any, _exc_tb: Any) -> None:
        """Context manager exit."""
        self.close()
