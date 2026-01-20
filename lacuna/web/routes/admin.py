"""Admin web routes for system management."""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import yaml
from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from lacuna.audit.logger import AuditLogger
from lacuna.auth import AuthenticatedUser, require_admin
from lacuna.config import get_settings
from lacuna.models.audit import AuditQuery

router = APIRouter(prefix="/admin", tags=["Admin Web"])

templates = Jinja2Templates(directory="lacuna/web/templates")


def get_config_path() -> Path:
    """Get the configuration directory path."""
    return get_settings().config_path


@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    admin: AuthenticatedUser = Depends(require_admin),
):
    """Admin dashboard with system overview."""
    settings = get_settings()
    logger = AuditLogger()

    try:
        # Get recent activity stats
        query = AuditQuery(limit=1000)
        records = logger._backend.query(query)

        # Calculate stats
        total_events = len(records)
        unique_users = len({r.user_id for r in records})
        violations = sum(1 for r in records if r.action_result in ("denied", "blocked"))

        # Events in last hour
        one_hour_ago = datetime.now() - timedelta(hours=1)
        recent_events = sum(1 for r in records if r.timestamp > one_hour_ago)

        # By event type
        by_type: dict = {}
        for r in records:
            by_type[r.event_type.value] = by_type.get(r.event_type.value, 0) + 1

        # Recent violations
        recent_violations = [
            r for r in records if r.action_result in ("denied", "blocked")
        ][:10]

        return templates.TemplateResponse(
            "admin/dashboard.html",
            {
                "request": request,
                "active_page": "admin_dashboard",
                "is_admin": True,
                "current_user": admin,
                "settings": settings,
                "total_events": total_events,
                "unique_users": unique_users,
                "violations": violations,
                "recent_events": recent_events,
                "by_type": by_type,
                "recent_violations": recent_violations,
            },
        )
    finally:
        logger.stop()


@router.get("/users", response_class=HTMLResponse)
async def admin_users(
    request: Request,
    admin: AuthenticatedUser = Depends(require_admin),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
):
    """User management and activity monitoring."""
    logger = AuditLogger()

    try:
        query = AuditQuery(limit=5000)
        records = logger._backend.query(query)

        # Aggregate user data
        users_data: dict = {}
        for record in records:
            uid = record.user_id
            if uid not in users_data:
                users_data[uid] = {
                    "user_id": uid,
                    "first_seen": record.timestamp,
                    "last_seen": record.timestamp,
                    "event_count": 0,
                    "violations": 0,
                }
            users_data[uid]["event_count"] += 1
            if record.timestamp > users_data[uid]["last_seen"]:
                users_data[uid]["last_seen"] = record.timestamp
            if record.timestamp < users_data[uid]["first_seen"]:
                users_data[uid]["first_seen"] = record.timestamp
            if record.action_result in ("denied", "blocked"):
                users_data[uid]["violations"] += 1

        # Sort by event count
        users_list = sorted(
            users_data.values(),
            key=lambda x: x["event_count"],
            reverse=True,
        )

        # Paginate
        start_idx = (page - 1) * limit
        paginated = users_list[start_idx : start_idx + limit]

        return templates.TemplateResponse(
            "admin/users.html",
            {
                "request": request,
                "active_page": "admin_users",
                "is_admin": True,
                "users": paginated,
                "total_users": len(users_list),
                "page": page,
                "limit": limit,
                "has_prev": page > 1,
                "has_next": len(users_list) > page * limit,
            },
        )
    finally:
        logger.stop()


@router.get("/audit", response_class=HTMLResponse)
async def admin_audit(
    request: Request,
    admin: AuthenticatedUser = Depends(require_admin),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    user_id: Optional[str] = None,
    event_type: Optional[str] = None,
):
    """Audit log viewer."""
    logger = AuditLogger()

    try:
        query = AuditQuery(user_id=user_id, limit=limit * 10)
        records = logger._backend.query(query)

        # Filter by event type if specified
        if event_type:
            records = [r for r in records if r.event_type.value == event_type]

        # Get unique values for filters
        all_users = sorted({r.user_id for r in records})
        all_types = sorted({r.event_type.value for r in records})

        # Paginate
        start_idx = (page - 1) * limit
        paginated = records[start_idx : start_idx + limit]

        return templates.TemplateResponse(
            "admin/audit.html",
            {
                "request": request,
                "active_page": "admin_audit",
                "is_admin": True,
                "records": paginated,
                "total": len(records),
                "page": page,
                "limit": limit,
                "all_users": all_users,
                "all_types": all_types,
                "selected_user": user_id,
                "selected_type": event_type,
                "has_prev": page > 1,
                "has_next": len(records) > page * limit,
            },
        )
    finally:
        logger.stop()


@router.get("/config", response_class=HTMLResponse)
async def admin_config(
    request: Request,
    admin: AuthenticatedUser = Depends(require_admin),
):
    """Manage system configuration settings."""
    settings = get_settings()

    # Load config files
    config_file = get_config_path() / "default.yaml"
    terms_file = get_config_path() / "proprietary_terms.yaml"

    config_data: dict[str, Any] = {}
    if config_file.exists():
        with open(config_file) as f:
            config_data = yaml.safe_load(f) or {}

    terms_data: dict[str, list[str]] = {"projects": [], "customers": [], "terms": []}
    if terms_file.exists():
        with open(terms_file) as f:
            terms_data = yaml.safe_load(f) or terms_data

    return templates.TemplateResponse(
        "admin/config.html",
        {
            "request": request,
            "active_page": "admin_config",
            "is_admin": True,
            "settings": settings,
            "config_data": config_data,
            "terms_data": terms_data,
        },
    )


@router.post("/config/update", response_class=HTMLResponse)
async def admin_config_update(
    request: Request,
    admin: AuthenticatedUser = Depends(require_admin),
    key: str = Form(...),
    value: str = Form(...),
):
    """Update a configuration value."""
    config_file = get_config_path() / "default.yaml"

    # Load existing config
    config_data: dict[str, Any] = {}
    if config_file.exists():
        with open(config_file) as f:
            config_data = yaml.safe_load(f) or {}

    # Parse value
    parsed_value: Any = value
    if value.lower() in ("true", "yes"):
        parsed_value = True
    elif value.lower() in ("false", "no"):
        parsed_value = False
    else:
        try:
            parsed_value = int(value)
        except ValueError:
            try:
                parsed_value = float(value)
            except ValueError:
                pass

    # Set nested key
    parts = key.split(".")
    current = config_data
    for part in parts[:-1]:
        if part not in current:
            current[part] = {}
        current = current[part]
    current[parts[-1]] = parsed_value

    # Save
    with open(config_file, "w") as f:
        yaml.dump(config_data, f, default_flow_style=False)

    return RedirectResponse(url="/admin/config?updated=1", status_code=303)


@router.post("/terms/add", response_class=HTMLResponse)
async def admin_terms_add(
    request: Request,
    admin: AuthenticatedUser = Depends(require_admin),
    category: str = Form(...),
    value: str = Form(...),
):
    """Add a proprietary term/project/customer."""
    terms_file = get_config_path() / "proprietary_terms.yaml"

    terms_data: dict[str, list[str]] = {"projects": [], "customers": [], "terms": []}
    if terms_file.exists():
        with open(terms_file) as f:
            terms_data = yaml.safe_load(f) or terms_data

    if category in terms_data and value not in terms_data[category]:
        terms_data[category].append(value)

        with open(terms_file, "w") as f:
            yaml.dump(terms_data, f, default_flow_style=False)

    return RedirectResponse(url="/admin/config?added=1", status_code=303)


@router.post("/terms/remove", response_class=HTMLResponse)
async def admin_terms_remove(
    request: Request,
    admin: AuthenticatedUser = Depends(require_admin),
    category: str = Form(...),
    value: str = Form(...),
):
    """Remove a proprietary term/project/customer."""
    terms_file = get_config_path() / "proprietary_terms.yaml"

    terms_data: dict[str, list[str]] = {"projects": [], "customers": [], "terms": []}
    if terms_file.exists():
        with open(terms_file) as f:
            terms_data = yaml.safe_load(f) or terms_data

    if category in terms_data and value in terms_data[category]:
        terms_data[category].remove(value)

        with open(terms_file, "w") as f:
            yaml.dump(terms_data, f, default_flow_style=False)

    return RedirectResponse(url="/admin/config?removed=1", status_code=303)


@router.get("/policies", response_class=HTMLResponse)
async def admin_policies(
    request: Request,
    admin: AuthenticatedUser = Depends(require_admin),
):
    """Policy management page."""
    settings = get_settings()

    # Load policy files
    policies_dir = Path("policies")
    policy_files = []
    if policies_dir.exists():
        for f in policies_dir.glob("*.rego"):
            with open(f) as pf:
                content = pf.read()
            policy_files.append(
                {
                    "name": f.name,
                    "path": str(f),
                    "size": f.stat().st_size,
                    "modified": datetime.fromtimestamp(f.stat().st_mtime),
                    "content": content[:500] + "..." if len(content) > 500 else content,
                }
            )

    return templates.TemplateResponse(
        "admin/policies.html",
        {
            "request": request,
            "active_page": "admin_policies",
            "is_admin": True,
            "settings": settings,
            "policy_files": policy_files,
        },
    )


@router.get("/alerts", response_class=HTMLResponse)
async def admin_alerts(
    request: Request,
    admin: AuthenticatedUser = Depends(require_admin),
):
    """Real-time alerts page."""
    logger = AuditLogger()

    try:
        # Get recent high-severity events
        query = AuditQuery(limit=100)
        records = logger._backend.query(query)

        # Filter for alert-worthy events
        alerts = [
            r for r in records if r.action_result in ("denied", "blocked", "failed")
        ][:20]

        return templates.TemplateResponse(
            "admin/alerts.html",
            {
                "request": request,
                "active_page": "admin_alerts",
                "is_admin": True,
                "alerts": alerts,
            },
        )
    finally:
        logger.stop()


# =============================================================================
# API Key Management Routes
# =============================================================================


@router.get("/api-keys", response_class=HTMLResponse)
async def admin_api_keys(
    request: Request,
    admin: AuthenticatedUser = Depends(require_admin),
):
    """Display API key management page."""
    from lacuna.auth.api_keys import get_api_key_store

    store = get_api_key_store()
    api_keys = store.list_all()

    # Sort by creation date (newest first)
    api_keys.sort(key=lambda k: k.created_at, reverse=True)

    return templates.TemplateResponse(
        "admin/api_keys.html",
        {
            "request": request,
            "active_page": "admin_api_keys",
            "is_admin": True,
            "api_keys": api_keys,
            "new_key": request.query_params.get("new_key"),
        },
    )


@router.post("/api-keys/create", response_class=HTMLResponse)
async def admin_api_keys_create(
    request: Request,
    admin: AuthenticatedUser = Depends(require_admin),
    name: str = Form(...),
    service_account_id: str = Form(...),
    description: str = Form(""),
    groups: str = Form(""),
    expires_days: Optional[int] = Form(None),
):
    """Create a new API key."""
    from datetime import timezone

    from lacuna.auth.api_keys import get_api_key_store

    store = get_api_key_store()

    # Parse groups
    groups_list = [g.strip() for g in groups.split(",") if g.strip()]

    # Calculate expiry
    expires_at = None
    if expires_days and expires_days > 0:
        expires_at = datetime.now(timezone.utc) + timedelta(days=expires_days)

    # Create the key
    api_key, raw_key = store.create(
        name=name,
        service_account_id=service_account_id,
        description=description or None,
        groups=groups_list,
        expires_at=expires_at,
        created_by=admin.user_id,
    )

    # Redirect with the raw key (shown once)
    return RedirectResponse(
        url=f"/admin/api-keys?new_key={raw_key}",
        status_code=303,
    )


@router.post("/api-keys/{key_id}/revoke", response_class=HTMLResponse)
async def admin_api_keys_revoke(
    request: Request,
    key_id: str,
    admin: AuthenticatedUser = Depends(require_admin),
):
    """Revoke an API key."""
    from uuid import UUID

    from lacuna.auth.api_keys import get_api_key_store

    store = get_api_key_store()
    store.revoke(UUID(key_id), revoked_by=admin.user_id)

    return RedirectResponse(url="/admin/api-keys?revoked=1", status_code=303)


@router.post("/api-keys/{key_id}/delete", response_class=HTMLResponse)
async def admin_api_keys_delete(
    request: Request,
    key_id: str,
    admin: AuthenticatedUser = Depends(require_admin),
):
    """Delete an API key."""
    from uuid import UUID

    from lacuna.auth.api_keys import get_api_key_store

    store = get_api_key_store()
    store.delete(UUID(key_id))

    return RedirectResponse(url="/admin/api-keys?deleted=1", status_code=303)
