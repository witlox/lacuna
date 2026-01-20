"""Audit API endpoints."""

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from lacuna.api.app import get_engine
from lacuna.auth.dependencies import get_current_user
from lacuna.auth.models import AuthenticatedUser
from lacuna.engine.governance import GovernanceEngine
from lacuna.models.audit import EventType

router = APIRouter()


class AuditRecordResponse(BaseModel):
    """Response model for audit records."""

    event_id: str
    timestamp: str
    event_type: str
    severity: str
    user_id: str
    resource_type: str
    resource_id: str
    resource_classification: Optional[str] = None
    action: str
    action_result: str
    reasoning: Optional[str] = None


class AuditQueryResponse(BaseModel):
    """Response model for audit queries."""

    records: list[AuditRecordResponse]
    total: int
    offset: int
    limit: int


@router.get("/audit", response_model=AuditQueryResponse)
async def query_audit_logs(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    resource_id: Optional[str] = Query(None, description="Filter by resource ID"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    action_result: Optional[str] = Query(None, description="Filter by action result"),
    start_time: Optional[str] = Query(None, description="Start time (ISO format)"),
    end_time: Optional[str] = Query(None, description="End time (ISO format)"),
    limit: int = Query(100, le=1000, description="Maximum records to return"),
    offset: int = Query(0, description="Offset for pagination"),
    engine: GovernanceEngine = Depends(get_engine),
    _user: AuthenticatedUser = Depends(get_current_user),
) -> AuditQueryResponse:
    """Query audit logs with filters.

    Supports filtering by user, resource, event type, and time range.
    """
    try:
        # Build query parameters
        query_params: dict[str, Any] = {
            "limit": limit,
            "offset": offset,
        }

        if user_id:
            query_params["user_id"] = user_id
        if resource_id:
            query_params["resource_id"] = resource_id
        if action_result:
            query_params["action_result"] = action_result
        if start_time:
            query_params["start_time"] = datetime.fromisoformat(start_time)
        if end_time:
            query_params["end_time"] = datetime.fromisoformat(end_time)
        if event_type:
            try:
                query_params["event_types"] = [EventType(event_type)]
            except ValueError:
                pass

        # Query audit logs
        records = engine._audit_logger.query(**query_params)

        return AuditQueryResponse(
            records=[
                AuditRecordResponse(
                    event_id=str(r.event_id),
                    timestamp=r.timestamp.isoformat(),
                    event_type=r.event_type.value,
                    severity=r.severity.value,
                    user_id=r.user_id,
                    resource_type=r.resource_type,
                    resource_id=r.resource_id,
                    resource_classification=r.resource_classification,
                    action=r.action,
                    action_result=r.action_result,
                    reasoning=r.classification_reasoning,
                )
                for r in records
            ],
            total=len(records),
            offset=offset,
            limit=limit,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


class IntegrityVerificationResponse(BaseModel):
    """Response model for integrity verification."""

    verified: bool
    records_checked: int
    errors: list[dict[str, Any]]
    message: str
    first_record: Optional[str] = None
    last_record: Optional[str] = None


@router.get("/audit/verify", response_model=IntegrityVerificationResponse)
async def verify_audit_integrity(
    start_time: Optional[str] = Query(None, description="Start time (ISO format)"),
    end_time: Optional[str] = Query(None, description="End time (ISO format)"),
    engine: GovernanceEngine = Depends(get_engine),
    _user: AuthenticatedUser = Depends(get_current_user),
) -> IntegrityVerificationResponse:
    """Verify audit log integrity using hash chain.

    Checks that no audit records have been tampered with.
    """
    try:
        start = datetime.fromisoformat(start_time) if start_time else None
        end = datetime.fromisoformat(end_time) if end_time else None

        result = engine._audit_logger.verify_integrity(start, end)

        return IntegrityVerificationResponse(
            verified=result["verified"],
            records_checked=result["records_checked"],
            errors=result["errors"],
            message=result["message"],
            first_record=result.get("first_record"),
            last_record=result.get("last_record"),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


class AuditStatsResponse(BaseModel):
    """Response model for audit statistics."""

    total_records: int
    by_event_type: dict[str, int]
    by_action_result: dict[str, int]
    by_classification: dict[str, int]


@router.get("/audit/stats", response_model=AuditStatsResponse)
async def get_audit_stats(
    start_time: Optional[str] = Query(None, description="Start time (ISO format)"),
    end_time: Optional[str] = Query(None, description="End time (ISO format)"),
    engine: GovernanceEngine = Depends(get_engine),
    _user: AuthenticatedUser = Depends(get_current_user),
) -> AuditStatsResponse:
    """Get audit log statistics.

    Returns aggregated statistics about audit events.
    """
    try:
        # For now, return basic stats
        # In production, this would query aggregated data from the database
        return AuditStatsResponse(
            total_records=0,
            by_event_type={},
            by_action_result={},
            by_classification={},
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
