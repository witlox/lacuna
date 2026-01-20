"""LLM-based classifier for complex reasoning."""

import json
from typing import Optional

from lacuna.classifier.base import Classifier
from lacuna.config import get_settings
from lacuna.models.classification import Classification, ClassificationContext, DataTier


class LLMClassifier(Classifier):
    """
    LLM-based classifier for complex queries requiring reasoning.

    This is the third (fallback) layer in the classification pipeline,
    designed to handle 2% of queries with ~200ms latency using LLM reasoning.
    """

    def __init__(
        self,
        endpoint: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 500,
        priority: int = 80,
    ):
        """Initialize LLM classifier.

        Args:
            endpoint: LLM API endpoint (vLLM, Ollama, etc.)
            model: Model name
            temperature: Sampling temperature (lower = more deterministic)
            max_tokens: Maximum tokens in response
            priority: Priority in pipeline (default: 80)
        """
        super().__init__(priority)
        settings = get_settings()

        self.endpoint = endpoint or settings.classification.llm_endpoint
        self.model = model or settings.classification.llm_model
        self.temperature = temperature
        self.max_tokens = max_tokens

        self.system_prompt = """You are a data classification assistant for a data governance system.

Your task is to classify queries into one of three sensitivity tiers:

1. **PROPRIETARY**: Highly sensitive, company-specific information
   - Customer data, proprietary algorithms, trade secrets
   - Internal projects, confidential business strategies
   - Any information that could harm the company if leaked

2. **INTERNAL**: Internal processes and infrastructure
   - Deployment procedures, monitoring setup
   - Internal APIs, infrastructure architecture
   - Information useful only to employees

3. **PUBLIC**: General knowledge, public information
   - Programming language syntax, public APIs
   - General concepts, tutorials, documentation
   - Information freely available online

Respond with JSON in this exact format:
{
  "tier": "PROPRIETARY" | "INTERNAL" | "PUBLIC",
  "confidence": 0.0-1.0,
  "reasoning": "Brief explanation of classification decision",
  "tags": ["optional", "tags"]
}
"""

    @property
    def name(self) -> str:
        """Get classifier name."""
        return "LLMClassifier"

    def classify(
        self, query: str, context: Optional[ClassificationContext] = None
    ) -> Optional[Classification]:
        """Classify query using LLM reasoning.

        Args:
            query: Query text to classify
            context: Optional context information

        Returns:
            Classification from LLM, None if LLM unavailable or errors
        """
        if not self.endpoint:
            return None

        try:
            # Build prompt with context
            user_prompt = f"Classify this query:\n\n{query}"

            if context:
                context_info = []
                if context.project:
                    context_info.append(f"Project: {context.project}")
                if context.user_role:
                    context_info.append(f"User role: {context.user_role}")
                if context.environment:
                    context_info.append(f"Environment: {context.environment}")
                if context.conversation:
                    recent_messages = context.conversation[-3:]  # Last 3 messages
                    context_info.append(
                        f"Recent conversation: {json.dumps(recent_messages)}"
                    )

                if context_info:
                    user_prompt += "\n\nContext:\n" + "\n".join(context_info)

            # Call LLM
            response = self._call_llm(user_prompt)

            if not response:
                return None

            # Parse response
            result = self._parse_response(response)

            if not result:
                return None

            return Classification(
                tier=DataTier(result["tier"]),
                confidence=min(0.95, float(result["confidence"])),  # Cap at 0.95
                reasoning=result["reasoning"],
                matched_rules=["llm_reasoning"],
                tags=result.get("tags", []),
                classifier_name=self.name,
                classifier_version="1.0.0",
                metadata={"model": self.model, "endpoint": self.endpoint},
            )

        except Exception as e:
            # Log error but don't fail - return None to fallback
            import structlog

            logger = structlog.get_logger()
            logger.warning("llm_classification_failed", error=str(e))
            return None

    def _call_llm(self, user_prompt: str) -> Optional[str]:
        """Call LLM API.

        Args:
            user_prompt: User prompt

        Returns:
            LLM response text
        """
        try:
            import openai

            # Support OpenAI-compatible APIs (vLLM, Ollama, etc.)
            client = openai.OpenAI(
                base_url=self.endpoint,
                api_key="not-needed",  # Many local servers don't need API key
            )

            response = client.chat.completions.create(
                model=self.model or "default",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

            return response.choices[0].message.content

        except ImportError as err:
            raise ImportError(
                "openai not installed. Install with: pip install openai"
            ) from err
        except Exception as e:
            import structlog

            logger = structlog.get_logger()
            logger.error("llm_api_call_failed", error=str(e), endpoint=self.endpoint)
            return None

    def _parse_response(self, response: str) -> Optional[dict]:
        """Parse LLM JSON response.

        Args:
            response: Raw LLM response

        Returns:
            Parsed dict or None if invalid
        """
        try:
            # Try to extract JSON from response (may have markdown formatting)
            if "```json" in response:
                # Extract JSON from markdown code block
                start = response.find("```json") + 7
                end = response.find("```", start)
                json_str = response[start:end].strip()
            elif "```" in response:
                # Extract from generic code block
                start = response.find("```") + 3
                end = response.find("```", start)
                json_str = response[start:end].strip()
            else:
                json_str = response.strip()

            result = json.loads(json_str)

            # Validate required fields
            if "tier" not in result or "confidence" not in result:
                return None

            # Validate tier value
            if result["tier"] not in ["PROPRIETARY", "INTERNAL", "PUBLIC"]:
                return None

            # Ensure reasoning exists
            if "reasoning" not in result:
                result["reasoning"] = "LLM classification"

            return result

        except (json.JSONDecodeError, ValueError, KeyError):
            return None
