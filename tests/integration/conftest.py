"""Pytest fixtures for integration tests."""

import os
from collections.abc import Generator

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

# Check if we're running in integration test mode
INTEGRATION_TEST = os.environ.get("LACUNA_DATABASE_URL") is not None


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test requiring external services",
    )


@pytest.fixture(scope="session")
def database_url() -> str:
    """Get database URL from environment."""
    url = os.environ.get(
        "LACUNA_DATABASE_URL",
        "postgresql://lacuna_test:lacuna_test@localhost:5433/lacuna_test",
    )
    return url


@pytest.fixture(scope="session")
def redis_url() -> str:
    """Get Redis URL from environment."""
    return os.environ.get("LACUNA_REDIS_URL", "redis://localhost:6380/0")


@pytest.fixture(scope="session")
def opa_endpoint() -> str:
    """Get OPA endpoint from environment."""
    return os.environ.get("LACUNA_POLICY_OPA_ENDPOINT", "http://localhost:8182")


@pytest.fixture(scope="session")
def db_engine(database_url: str):
    """Create database engine for tests."""
    engine = create_engine(database_url, echo=False)
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine) -> Generator[Session, None, None]:
    """Create a database session for tests.

    Each test gets a fresh session that is rolled back after the test.
    """
    connection = db_engine.connect()
    transaction = connection.begin()

    SessionLocal = sessionmaker(bind=connection)
    session = SessionLocal()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="session")
def setup_database(db_engine):
    """Set up database schema for tests."""
    from lacuna.db import models  # Import models to register them
    from lacuna.db.base import Base

    # Create all tables
    Base.metadata.create_all(bind=db_engine)

    yield

    # Drop all tables after tests
    Base.metadata.drop_all(bind=db_engine)


@pytest.fixture
def redis_client(redis_url: str):
    """Create Redis client for tests."""
    import redis

    client = redis.from_url(redis_url)
    yield client

    # Clean up test keys
    client.flushdb()
    client.close()


@pytest.fixture
def opa_client(opa_endpoint: str):
    """Create OPA client for tests."""
    from lacuna.policy.client import OPAClient

    client = OPAClient(endpoint=opa_endpoint)
    return client
