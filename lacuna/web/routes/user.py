"""User-facing web routes."""

from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from lacuna.audit.logger import AuditLogger
from lacuna.auth import AuthenticatedUser, get_current_user
from lacuna.models.audit import AuditQuery, EventType

router = APIRouter(prefix="/user", tags=["User Web"])

# Templates directory
templates = Jinja2Templates(directory="lacuna/web/templates")


@router.get("/dashboard", response_class=HTMLResponse)
async def user_dashboard(
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """User dashboard showing overview of activity."""
    logger = AuditLogger()

    try:
        # Get recent activity stats
        query = AuditQuery(user_id=user.user_id, limit=100)
        records = logger._backend.query(query)

        # Calculate stats
        total_requests = len(records)
        successful = sum(1 for r in records if r.action_result == "success")
        denied = sum(1 for r in records if r.action_result in ("denied", "blocked"))

        # Get violations (denied requests)
        violations = [r for r in records if r.action_result in ("denied", "blocked")][
            :5
        ]

        # Activity by type
        by_type: dict = {}
        for r in records:
            by_type[r.event_type.value] = by_type.get(r.event_type.value, 0) + 1

        return templates.TemplateResponse(
            "user/dashboard.html",
            {
                "request": request,
                "active_page": "user_dashboard",
                "current_user": user,
                "total_requests": total_requests,
                "successful": successful,
                "denied": denied,
                "success_rate": (
                    (successful / total_requests * 100) if total_requests > 0 else 100
                ),
                "violations": violations,
                "by_type": by_type,
                "recent_records": records[:10],
            },
        )
    finally:
        logger.stop()


@router.get("/history", response_class=HTMLResponse)
async def user_history(
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    event_type: Optional[str] = None,
):
    """User activity history with filtering."""
    logger = AuditLogger()

    try:
        query = AuditQuery(user_id=user.user_id, limit=limit * page)
        records = logger._backend.query(query)

        # Filter by event type if specified
        if event_type:
            records = [r for r in records if r.event_type.value == event_type]

        # Paginate
        start_idx = (page - 1) * limit
        paginated = records[start_idx : start_idx + limit]

        # Get available event types for filter
        event_types = sorted({r.event_type.value for r in records})

        return templates.TemplateResponse(
            "user/history.html",
            {
                "request": request,
                "active_page": "user_history",
                "current_user": user,
                "records": paginated,
                "page": page,
                "limit": limit,
                "total": len(records),
                "event_types": event_types,
                "selected_event_type": event_type,
                "has_prev": page > 1,
                "has_next": len(records) > page * limit,
            },
        )
    finally:
        logger.stop()


@router.get("/violations", response_class=HTMLResponse)
async def user_violations(
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Show policy violations with explanations and recommendations."""
    logger = AuditLogger()

    try:
        query = AuditQuery(user_id=user.user_id, limit=500)
        records = logger._backend.query(query)

        # Filter to violations only
        violations = [
            r for r in records if r.action_result in ("denied", "blocked", "failed")
        ]

        # Group by type
        by_type: dict = {}
        for v in violations:
            event_type = v.event_type.value
            if event_type not in by_type:
                by_type[event_type] = []
            by_type[event_type].append(v)

        # Generate recommendations based on violation patterns
        recommendations = _generate_recommendations(violations)

        return templates.TemplateResponse(
            "user/violations.html",
            {
                "request": request,
                "active_page": "user_violations",
                "current_user": user,
                "violations": violations[:50],
                "total_violations": len(violations),
                "by_type": by_type,
                "recommendations": recommendations,
            },
        )
    finally:
        logger.stop()


@router.get("/recommendations", response_class=HTMLResponse)
async def user_recommendations(
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Personalized recommendations for correct behavior."""
    logger = AuditLogger()

    try:
        query = AuditQuery(user_id=user.user_id, limit=500)
        records = logger._backend.query(query)

        violations = [
            r for r in records if r.action_result in ("denied", "blocked", "failed")
        ]

        recommendations = _generate_recommendations(violations)

        return templates.TemplateResponse(
            "user/recommendations.html",
            {
                "request": request,
                "active_page": "user_recommendations",
                "current_user": user,
                "recommendations": recommendations,
                "violation_count": len(violations),
            },
        )
    finally:
        logger.stop()


def _generate_recommendations(violations: list) -> list:
    """Generate recommendations based on violation patterns."""
    recommendations = []

    if not violations:
        recommendations.append(
            {
                "type": "success",
                "title": "Great job!",
                "message": "You have no policy violations. Keep up the good work!",
                "icon": "✅",
            }
        )
        return recommendations

    # Analyze patterns
    export_violations = sum(
        1 for v in violations if v.event_type == EventType.DATA_EXPORT
    )
    access_violations = sum(
        1 for v in violations if v.event_type == EventType.DATA_ACCESS
    )
    classification_issues = sum(
        1 for v in violations if v.event_type == EventType.CLASSIFICATION_AUTO
    )

    if export_violations > 0:
        recommendations.append(
            {
                "type": "warning",
                "title": "Data Export Issues",
                "message": f"You have {export_violations} blocked export attempts. "
                "Consider checking data classification before exporting. "
                "Use 'lacuna classify' to check sensitivity levels.",
                "icon": "📤",
            }
        )

    if access_violations > 0:
        recommendations.append(
            {
                "type": "info",
                "title": "Access Permission Issues",
                "message": f"You have {access_violations} access denials. "
                "Ensure you have proper authorization before accessing sensitive data. "
                "Contact your administrator if you need access.",
                "icon": "🔐",
            }
        )

    if classification_issues > 0:
        recommendations.append(
            {
                "type": "info",
                "title": "Classification Awareness",
                "message": f"You've encountered {classification_issues} classification issues. "
                "Review the data classification tiers: PROPRIETARY, INTERNAL, PUBLIC.",
                "icon": "📊",
            }
        )

    # General recommendations
    recommendations.append(
        {
            "type": "tip",
            "title": "Best Practice",
            "message": "Always check data sensitivity with 'lacuna evaluate' before "
            "sharing or exporting data.",
            "icon": "💡",
        }
    )

    return recommendations
