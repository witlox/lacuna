"""FastAPI application factory."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

from lacuna.__version__ import __version__
from lacuna.config import get_settings
from lacuna.engine.governance import GovernanceEngine

logger = structlog.get_logger()

# Global governance engine instance
_engine: GovernanceEngine | None = None


def get_engine() -> GovernanceEngine:
    """Get the governance engine instance."""
    global _engine
    if _engine is None:
        _engine = GovernanceEngine()
    return _engine


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler."""
    global _engine

    # Startup
    logger.info("lacuna_api_starting", version=__version__)
    _engine = GovernanceEngine()

    yield

    # Shutdown
    if _engine:
        _engine.stop()
    logger.info("lacuna_api_stopped")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Lacuna",
        description="Privacy-aware data governance and lineage tracking API",
        version=__version__,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routes
    from lacuna.api.routes import classify, evaluate, lineage, audit, health

    app.include_router(health.router, tags=["Health"])
    app.include_router(classify.router, prefix="/api/v1", tags=["Classification"])
    app.include_router(evaluate.router, prefix="/api/v1", tags=["Evaluation"])
    app.include_router(lineage.router, prefix="/api/v1", tags=["Lineage"])
    app.include_router(audit.router, prefix="/api/v1", tags=["Audit"])

    return app


# Create the default app instance
app = create_app()

