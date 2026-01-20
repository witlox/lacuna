"""Database connection and session management."""

from collections.abc import Generator
from contextlib import contextmanager
from typing import Any, Optional

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from lacuna.config import get_settings

# Base class for all database models
Base: Any = declarative_base()

# Global engine and session factory
_engine: Optional[Engine] = None
_SessionLocal: Optional[sessionmaker] = None


def get_engine() -> Engine:
    """Get or create database engine."""
    global _engine
    if _engine is None:
        settings = get_settings()
        db_url = settings.database.url

        # SQLite doesn't support connection pooling the same way
        if db_url.startswith("sqlite"):
            _engine = create_engine(
                db_url,
                echo=settings.database.echo,
                connect_args={"check_same_thread": False},  # Allow multi-thread access
            )
        else:
            # PostgreSQL and other databases
            _engine = create_engine(
                db_url,
                pool_size=settings.database.pool_size,
                max_overflow=settings.database.max_overflow,
                echo=settings.database.echo,
                pool_pre_ping=True,  # Verify connections before using
            )
    return _engine


def get_session_factory() -> sessionmaker:
    """Get or create session factory."""
    global _SessionLocal
    if _SessionLocal is None:
        engine = get_engine()
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return _SessionLocal


def get_session() -> Session:
    """Get a new database session."""
    SessionLocal = get_session_factory()
    session: Session = SessionLocal()
    return session


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Provide a transactional scope for database operations."""
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    """Initialize database schema."""
    from lacuna.db.models import (  # noqa: F401
        AuditLogModel,
        ClassificationModel,
        LineageEdgeModel,
        PolicyEvaluationModel,
    )

    engine = get_engine()
    Base.metadata.create_all(bind=engine)
