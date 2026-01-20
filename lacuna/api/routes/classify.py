"""Classification API endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from lacuna.api.app import get_engine
from lacuna.auth.dependencies import get_current_user
from lacuna.auth.models import AuthenticatedUser
from lacuna.engine.governance import GovernanceEngine
from lacuna.models.classification import ClassificationContext

router = APIRouter()


class ClassifyRequest(BaseModel):
    """Request model for classification."""

    query: str = Field(..., description="Query or text to classify")
    project: Optional[str] = Field(None, description="Project context")
    user_id: Optional[str] = Field(None, description="User identifier (overrides auth)")
    user_role: Optional[str] = Field(None, description="User role")
    environment: Optional[str] = Field(
        None, description="Environment (dev/staging/prod)"
    )
    conversation: Optional[list[dict[str, str]]] = Field(
        None, description="Previous conversation messages"
    )


class ClassifyResponse(BaseModel):
    """Response model for classification."""

    tier: str = Field(
        ..., description="Classification tier (PROPRIETARY/INTERNAL/PUBLIC)"
    )
    confidence: float = Field(..., description="Classification confidence (0.0-1.0)")
    reasoning: str = Field(..., description="Explanation for classification")
    tags: list[str] = Field(
        default_factory=list, description="Data tags (PII, PHI, etc.)"
    )
    classifier: str = Field(..., description="Classifier that made the decision")
    latency_ms: float = Field(default=0.0, description="Classification latency")


@router.post("/classify", response_model=ClassifyResponse)
async def classify(
    request: ClassifyRequest,
    engine: GovernanceEngine = Depends(get_engine),
    user: AuthenticatedUser = Depends(get_current_user),
) -> ClassifyResponse:
    """Classify a query or text for data sensitivity.

    Returns the classification tier, confidence, and reasoning.
    """
    # Use request user_id if provided, otherwise use authenticated user
    effective_user_id = request.user_id or user.user_id

    context = ClassificationContext(
        user_id=effective_user_id,
        user_role=request.user_role,
        project=request.project,
        environment=request.environment,
        conversation=request.conversation or [],
    )

    try:
        import time

        start = time.time()

        classification = engine.classify(request.query, context)

        latency = (time.time() - start) * 1000

        return ClassifyResponse(
            tier=classification.tier.value,
            confidence=classification.confidence,
            reasoning=classification.reasoning,
            tags=classification.tags,
            classifier=classification.classifier_name,
            latency_ms=round(latency, 2),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


class BatchClassifyRequest(BaseModel):
    """Request model for batch classification."""

    queries: list[str] = Field(..., description="List of queries to classify")
    project: Optional[str] = Field(None, description="Project context")
    user_id: Optional[str] = Field(None, description="User identifier (overrides auth)")


class BatchClassifyResponse(BaseModel):
    """Response model for batch classification."""

    results: list[ClassifyResponse]
    total_latency_ms: float


@router.post("/classify/batch", response_model=BatchClassifyResponse)
async def classify_batch(
    request: BatchClassifyRequest,
    engine: GovernanceEngine = Depends(get_engine),
    user: AuthenticatedUser = Depends(get_current_user),
) -> BatchClassifyResponse:
    """Classify multiple queries in a batch."""
    import time

    start = time.time()

    # Use request user_id if provided, otherwise use authenticated user
    effective_user_id = request.user_id or user.user_id

    results = []
    context = ClassificationContext(
        user_id=effective_user_id,
        project=request.project,
    )

    for query in request.queries:
        classification = engine.classify(query, context)
        results.append(
            ClassifyResponse(
                tier=classification.tier.value,
                confidence=classification.confidence,
                reasoning=classification.reasoning,
                tags=classification.tags,
                classifier=classification.classifier_name,
            )
        )

    return BatchClassifyResponse(
        results=results,
        total_latency_ms=round((time.time() - start) * 1000, 2),
    )
