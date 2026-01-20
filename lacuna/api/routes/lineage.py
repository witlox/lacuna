"""Lineage API endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from lacuna.api.app import get_engine
from lacuna.auth.dependencies import get_current_user
from lacuna.auth.models import AuthenticatedUser
from lacuna.engine.governance import GovernanceEngine

router = APIRouter()


class LineageNode(BaseModel):
    """Lineage node model."""

    node_id: str
    resource_type: Optional[str] = None
    classification_tier: Optional[str] = None
    tags: list[str] = Field(default_factory=list)


class LineageEdge(BaseModel):
    """Lineage edge model."""

    source_id: str
    destination_id: str
    operation_type: str
    timestamp: Optional[str] = None


class LineageGraphResponse(BaseModel):
    """Response model for lineage graph."""

    artifact_id: str
    nodes: list[LineageNode]
    edges: list[LineageEdge]
    upstream_count: int
    downstream_count: int


@router.get("/lineage/{artifact_id}", response_model=LineageGraphResponse)
async def get_lineage(
    artifact_id: str,
    max_depth: int = Query(10, description="Maximum traversal depth"),
    engine: GovernanceEngine = Depends(get_engine),
    _user: AuthenticatedUser = Depends(get_current_user),
) -> LineageGraphResponse:
    """Get lineage information for an artifact.

    Returns the complete lineage graph including upstream and downstream
    dependencies.
    """
    try:
        graph_data = engine.get_lineage(artifact_id)

        nodes = [
            LineageNode(
                node_id=nid,
                resource_type=node.get("resource_type"),
                classification_tier=node.get("classification_tier"),
                tags=node.get("tags", []),
            )
            for nid, node in graph_data.get("nodes", {}).items()
        ]

        edges = [
            LineageEdge(
                source_id=edge.get("source_id"),
                destination_id=edge.get("destination_id"),
                operation_type=edge.get("operation_type"),
                timestamp=edge.get("timestamp"),
            )
            for edge in graph_data.get("edges", [])
        ]

        upstream = engine.get_upstream(artifact_id)
        downstream = engine.get_downstream(artifact_id)

        return LineageGraphResponse(
            artifact_id=artifact_id,
            nodes=nodes,
            edges=edges,
            upstream_count=len(upstream),
            downstream_count=len(downstream),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


class UpstreamResponse(BaseModel):
    """Response model for upstream dependencies."""

    artifact_id: str
    upstream: list[str]
    count: int


@router.get("/lineage/{artifact_id}/upstream", response_model=UpstreamResponse)
async def get_upstream(
    artifact_id: str,
    max_depth: int = Query(10, description="Maximum traversal depth"),
    engine: GovernanceEngine = Depends(get_engine),
    _user: AuthenticatedUser = Depends(get_current_user),
) -> UpstreamResponse:
    """Get upstream dependencies of an artifact."""
    upstream = engine.get_upstream(artifact_id)
    return UpstreamResponse(
        artifact_id=artifact_id,
        upstream=upstream,
        count=len(upstream),
    )


class DownstreamResponse(BaseModel):
    """Response model for downstream dependencies."""

    artifact_id: str
    downstream: list[str]
    count: int


@router.get("/lineage/{artifact_id}/downstream", response_model=DownstreamResponse)
async def get_downstream(
    artifact_id: str,
    max_depth: int = Query(10, description="Maximum traversal depth"),
    engine: GovernanceEngine = Depends(get_engine),
    _user: AuthenticatedUser = Depends(get_current_user),
) -> DownstreamResponse:
    """Get downstream dependents of an artifact."""
    downstream = engine.get_downstream(artifact_id)
    return DownstreamResponse(
        artifact_id=artifact_id,
        downstream=downstream,
        count=len(downstream),
    )


class ImpactAnalysisResponse(BaseModel):
    """Response model for impact analysis."""

    artifact_id: str
    downstream_count: int
    downstream_artifacts: list[str]
    by_depth: dict[str, list[str]]


@router.get("/lineage/{artifact_id}/impact", response_model=ImpactAnalysisResponse)
async def get_impact_analysis(
    artifact_id: str,
    engine: GovernanceEngine = Depends(get_engine),
    _user: AuthenticatedUser = Depends(get_current_user),
) -> ImpactAnalysisResponse:
    """Analyze impact of changes to an artifact.

    Shows all downstream dependencies that would be affected
    by changes to this artifact.
    """
    tracker = engine._lineage_tracker
    analysis = tracker.get_impact_analysis(artifact_id)

    # Convert int keys to strings for JSON
    by_depth = {str(k): v for k, v in analysis.get("by_depth", {}).items()}

    return ImpactAnalysisResponse(
        artifact_id=artifact_id,
        downstream_count=analysis.get("downstream_count", 0),
        downstream_artifacts=analysis.get("downstream_artifacts", []),
        by_depth=by_depth,
    )
