"""Health check endpoints."""

from typing import Any

from fastapi import APIRouter

from lacuna.__version__ import __version__
from lacuna.config import get_settings

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, Any]:
    """Check service health status."""
    return {
        "status": "healthy",
        "version": __version__,
    }


@router.get("/health/ready")
async def readiness_check() -> dict[str, Any]:
    """Readiness check for Kubernetes."""
    settings = get_settings()
    return {
        "status": "ready",
        "version": __version__,
        "environment": settings.environment,
    }


@router.get("/health/live")
async def liveness_check() -> dict[str, str]:
    """Liveness check for Kubernetes."""
    return {"status": "alive"}
