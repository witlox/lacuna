"""Embedding-based classifier using semantic similarity."""

from typing import TYPE_CHECKING, Optional

import numpy as np

from lacuna.classifier.base import Classifier
from lacuna.config import get_settings
from lacuna.models.classification import Classification, ClassificationContext, DataTier

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer


class EmbeddingClassifier(Classifier):
    """
    Semantic similarity-based classifier using embeddings.

    This is the second layer in the classification pipeline, designed to handle
    8% of queries with ~10ms latency using semantic similarity matching.
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        examples_by_tier: Optional[dict[DataTier, list[str]]] = None,
        threshold: float = 0.75,
        priority: int = 70,
    ):
        """Initialize embedding classifier.

        Args:
            model_name: Name of the embedding model
            examples_by_tier: Example queries for each tier
            threshold: Minimum similarity threshold (0.0 to 1.0)
            priority: Priority in pipeline (default: 70)
        """
        super().__init__(priority)
        settings = get_settings()

        self.model_name = model_name or settings.classification.embedding_model
        self.threshold = threshold
        self.model: Optional[SentenceTransformer] = None
        self.examples_by_tier = examples_by_tier or self._default_examples()
        self.example_embeddings: dict[DataTier, np.ndarray] = {}

    @property
    def name(self) -> str:
        """Get classifier name."""
        return "EmbeddingClassifier"

    def _default_examples(self) -> dict[DataTier, list[str]]:
        """Get default example queries for each tier."""
        return {
            DataTier.PROPRIETARY: [
                "How do we handle customer data in production?",
                "What's our deployment strategy for client_acme?",
                "Debug the authentication issue in project_apollo",
                "Optimize our internal ML pipeline",
                "Customer retention metrics for Q4",
            ],
            DataTier.INTERNAL: [
                "How do we deploy to staging?",
                "What's our monitoring setup?",
                "Explain our CI/CD pipeline",
                "Infrastructure architecture overview",
                "Internal API documentation",
            ],
            DataTier.PUBLIC: [
                "What's the latest Python version?",
                "How does PostgreSQL handle MVCC?",
                "Explain React hooks",
                "Docker best practices",
                "What is machine learning?",
            ],
        }

    def _load_model(self) -> None:
        """Load the embedding model."""
        if self.model is not None:
            return

        try:
            from sentence_transformers import SentenceTransformer

            settings = get_settings()
            self.model = SentenceTransformer(
                self.model_name, device=settings.classification.embedding_device
            )

            # Precompute example embeddings
            for tier, examples in self.examples_by_tier.items():
                embeddings = self.model.encode(examples, convert_to_numpy=True)  # type: ignore[attr-defined]
                # Average embeddings for this tier
                self.example_embeddings[tier] = np.mean(embeddings, axis=0)

        except ImportError as err:
            raise ImportError(
                "sentence-transformers not installed. "
                "Install with: pip install sentence-transformers"
            ) from err

    def classify(
        self, query: str, context: Optional[ClassificationContext] = None
    ) -> Optional[Classification]:
        """Classify query using semantic similarity.

        Args:
            query: Query text to classify
            context: Optional context information

        Returns:
            Classification if similarity threshold met, None otherwise
        """
        # Load model lazily
        self._load_model()

        if self.model is None:
            return None

        # Encode query
        query_embedding = self.model.encode([query], convert_to_numpy=True)[0]

        # Compute similarity to each tier
        similarities = {}
        for tier, tier_embedding in self.example_embeddings.items():
            # Cosine similarity
            similarity = self._cosine_similarity(query_embedding, tier_embedding)
            similarities[tier] = similarity

        # Find best match
        best_tier = max(similarities, key=lambda t: similarities[t])
        best_similarity = similarities[best_tier]

        # Check if above threshold
        if best_similarity < self.threshold:
            return None

        # Calculate confidence based on similarity and margin
        sorted_sims = sorted(similarities.values(), reverse=True)
        margin = sorted_sims[0] - sorted_sims[1] if len(sorted_sims) > 1 else 0.1
        confidence = min(0.95, best_similarity + margin * 0.5)

        return Classification(
            tier=best_tier,
            confidence=confidence,
            reasoning=(
                f"Semantic similarity to {best_tier.value} examples: "
                f"{best_similarity:.2f}"
            ),
            matched_rules=["embedding_similarity"],
            tags=[],
            classifier_name=self.name,
            classifier_version="1.0.0",
            metadata={
                "similarities": {
                    tier.value: float(sim) for tier, sim in similarities.items()
                },
                "model": self.model_name,
            },
        )

    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Compute cosine similarity between two vectors.

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Cosine similarity (0.0 to 1.0)
        """
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(dot_product / (norm1 * norm2))

    def add_examples(self, tier: DataTier, examples: list[str]) -> None:
        """Add training examples for a tier.

        Args:
            tier: Data tier
            examples: List of example queries
        """
        if tier not in self.examples_by_tier:
            self.examples_by_tier[tier] = []

        self.examples_by_tier[tier].extend(examples)

        # Recompute embeddings if model is loaded
        if self.model is not None:
            embeddings = self.model.encode(
                self.examples_by_tier[tier], convert_to_numpy=True
            )
            self.example_embeddings[tier] = np.mean(embeddings, axis=0)
