"""Evaluation API endpoints for policy decisions."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from lacuna.api.app import get_engine
from lacuna.auth.dependencies import get_current_user
from lacuna.auth.models import AuthenticatedUser
from lacuna.engine.governance import GovernanceEngine
from lacuna.models.data_operation import DataOperation, OperationType, UserContext

router = APIRouter()


class EvaluateRequest(BaseModel):
    """Request model for governance evaluation."""

    operation_type: str = Field(
        ..., description="Operation type (read, write, export, query, etc.)"
    )
    resource_type: str = Field(..., description="Resource type (file, table, dataset)")
    resource_id: str = Field(..., description="Resource identifier")
    user_id: Optional[str] = Field(
        None, description="User ID override (defaults to auth)"
    )
    user_role: Optional[str] = Field(None, description="User role")
    destination: Optional[str] = Field(
        None, description="Destination for exports/writes"
    )
    destination_type: Optional[str] = Field(None, description="Destination type")
    destination_encrypted: bool = Field(False, description="Is destination encrypted")
    sources: Optional[list[str]] = Field(
        None, description="Source artifacts for transformations"
    )
    purpose: Optional[str] = Field(None, description="Business justification")
    project: Optional[str] = Field(None, description="Project context")
    environment: Optional[str] = Field(None, description="Environment")


class EvaluateResponse(BaseModel):
    """Response model for governance evaluation."""

    allowed: bool = Field(..., description="Whether the operation is allowed")
    classification_tier: Optional[str] = Field(
        None, description="Data classification tier"
    )
    confidence: Optional[float] = Field(None, description="Classification confidence")
    reasoning: str = Field(..., description="Explanation for decision")
    alternatives: list[str] = Field(
        default_factory=list, description="Alternative actions if denied"
    )
    tags: list[str] = Field(default_factory=list, description="Data tags")
    policy_rules: list[str] = Field(
        default_factory=list, description="Matched policy rules"
    )
    evaluation_id: str = Field(..., description="Unique evaluation ID")
    latency_ms: Optional[float] = Field(None, description="Total evaluation latency")


@router.post("/evaluate", response_model=EvaluateResponse)
async def evaluate_operation(
    request: EvaluateRequest,
    engine: GovernanceEngine = Depends(get_engine),
    user: AuthenticatedUser = Depends(get_current_user),
) -> EvaluateResponse:
    """Evaluate a data operation against governance policies.

    Returns whether the operation is allowed, along with reasoning
    and alternatives if denied.
    """
    try:
        # Map string operation type to enum
        try:
            op_type = OperationType(request.operation_type)
        except ValueError:
            op_type = OperationType.READ

        # Use request user_id if provided, otherwise use authenticated user
        effective_user_id = request.user_id or user.user_id

        # Build operation
        operation = DataOperation(
            operation_type=op_type,
            resource_type=request.resource_type,
            resource_id=request.resource_id,
            destination=request.destination,
            destination_type=request.destination_type,
            destination_encrypted=request.destination_encrypted,
            sources=request.sources or [],
            user=UserContext(
                user_id=effective_user_id,
                user_role=request.user_role,
            ),
            purpose=request.purpose,
            project=request.project,
            environment=request.environment,
        )

        # Evaluate
        result = engine.evaluate_operation(operation)

        return EvaluateResponse(
            allowed=result.allowed,
            classification_tier=result.tier,
            confidence=result.confidence,
            reasoning=result.reasoning,
            alternatives=result.alternatives,
            tags=result.tags,
            policy_rules=result.matched_rules,
            evaluation_id=str(result.evaluation_id),
            latency_ms=result.total_latency_ms,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


class ExportEvaluateRequest(BaseModel):
    """Request model for export evaluation."""

    source: str = Field(..., description="Source resource ID")
    destination: str = Field(..., description="Destination path or URL")
    user_id: Optional[str] = Field(
        None, description="User ID override (defaults to auth)"
    )
    purpose: Optional[str] = Field(None, description="Business justification")


@router.post("/evaluate/export", response_model=EvaluateResponse)
async def evaluate_export(
    request: ExportEvaluateRequest,
    engine: GovernanceEngine = Depends(get_engine),
    user: AuthenticatedUser = Depends(get_current_user),
) -> EvaluateResponse:
    """Evaluate an export operation.

    Simplified endpoint specifically for export operations.
    """
    # Use request user_id if provided, otherwise use authenticated user
    effective_user_id = request.user_id or user.user_id

    result = engine.evaluate_export(
        source=request.source,
        destination=request.destination,
        user_id=effective_user_id,
        purpose=request.purpose,
    )

    return EvaluateResponse(
        allowed=result.allowed,
        classification_tier=result.tier,
        confidence=result.confidence,
        reasoning=result.reasoning,
        alternatives=result.alternatives,
        tags=result.tags,
        policy_rules=result.matched_rules,
        evaluation_id=str(result.evaluation_id),
        latency_ms=result.total_latency_ms,
    )
