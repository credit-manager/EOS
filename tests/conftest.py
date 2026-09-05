"""
EOS Platform - Pytest Fixtures and Configuration

Shared fixtures for database sessions, HTTP clients, authentication,
tenant isolation, and test data.
"""
import asyncio
import os
from typing import AsyncGenerator, Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Set safe local defaults without overriding CI-provided configuration.
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql://eos_test:test_password@localhost:5432/eos_test",
)
os.environ.setdefault(
    "SECRET_KEY",
    "test_secret_key_for_testing_only_12345678901234567890",
)
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_engine():
    """Create a test database engine."""
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql://eos_test:test_password@localhost:5432/eos_test",
    )
    engine = create_engine(
        database_url,
        echo=False,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(test_engine) -> Generator[Session, None, None]:
    """Create a fresh database session for each test."""
    from models import Base

    Base.metadata.create_all(bind=test_engine)
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine,
    )
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.rollback()
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
async def async_db_session(test_engine) -> AsyncGenerator[Session, None]:
    """Provide a synchronous SQLAlchemy session to async tests."""
    from models import Base

    Base.metadata.create_all(bind=test_engine)
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine,
    )
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.rollback()
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="session")
def test_client():
    """Create a FastAPI test client."""
    from fastapi.testclient import TestClient
    from main import app

    with TestClient(app, base_url="http://testserver") as client:
        yield client


@pytest.fixture(scope="function")
def auth_token(test_client, request) -> str:
    """Create/authenticate a test user and return its access token."""
    node_id = request.node.nodeid[:50].replace("/", "_")
    login_data = {
        "email": f"test_{node_id}@test.com",
        "password": "TestPassword123!",
    }

    response = test_client.post("/api/v1/auth/login", json=login_data)

    if response.status_code == 401:
        register_data = {
            "email": login_data["email"],
            "password": login_data["password"],
            "full_name": "Test User",
            "company_name": "Test Company",
        }
        register_response = test_client.post(
            "/api/v1/auth/register",
            json=register_data,
        )
        assert register_response.status_code in [200, 201], (
            f"Registration failed: {register_response.text}"
        )
        response = test_client.post("/api/v1/auth/login", json=login_data)

    assert response.status_code == 200, f"Login failed: {response.text}"
    data = response.json()
    return data.get("data", {}).get("access_token", data.get("access_token"))


@pytest.fixture(scope="function")
def tenant_context(db_session, request) -> dict:
    """Create a test tenant and company and return their IDs."""
    from models import Company, Tenant

    node_id = request.node.nodeid[:30].replace("/", "_")
    tenant = Tenant(
        name=f"Test Tenant {node_id}",
        slug=f"test-tenant-{node_id}",
        is_active=True,
    )
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)

    company = Company(
        tenant_id=tenant.id,
        name="Test Company",
        tax_id="TEST123456",
    )
    db_session.add(company)
    db_session.commit()
    db_session.refresh(company)

    yield {
        "tenant_id": tenant.id,
        "tenant_slug": tenant.slug,
        "company_id": company.id,
    }

    db_session.delete(company)
    db_session.delete(tenant)
    db_session.commit()


@pytest.fixture(scope="function")
def mock_ai_service():
    """Mock AI service for tests without external API calls."""
    from unittest.mock import AsyncMock, MagicMock

    mock = MagicMock()
    mock.analyze_business = AsyncMock(
        return_value={
            "industry": "trading",
            "modules": ["accounting", "inventory", "sales"],
            "entities": [],
        }
    )
    return mock


@pytest.fixture(scope="function")
def mock_email_service():
    """Mock email service for tests without sending real emails."""
    from unittest.mock import AsyncMock, MagicMock

    mock = MagicMock()
    mock.send_email = AsyncMock(return_value=True)
    mock.send_verification_email = AsyncMock(return_value=True)
    mock.send_password_reset = AsyncMock(return_value=True)
    return mock


@pytest.fixture(params=["tourism", "construction", "manufacturing", "trading"])
def industry_type(request):
    """Parametrized fixture for supported industry types."""
    return request.param


@pytest.fixture
def sample_user_data():
    """Sample user data."""
    return {
        "email": "user@example.com",
        "password": "SecurePassword123!",
        "full_name": "John Doe",
        "company_name": "Acme Corp",
        "phone": "+1234567890",
    }


@pytest.fixture
def sample_company_data():
    """Sample company data."""
    return {
        "name": "Test Company LLC",
        "tax_id": "TAX123456789",
        "address": "123 Test Street",
        "city": "Test City",
        "country": "EG",
        "phone": "+201234567890",
    }


def create_test_user(db_session, email=None, password="TestPassword123!"):
    """Helper to create a test user."""
    from models import User
    import uuid

    if email is None:
        email = f"user_{uuid.uuid4().hex[:8]}@test.com"

    user = User(
        email=email,
        full_name="Test User",
        is_active=True,
    )
    user.set_password(password)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def cleanup_all_data(db_session):
    """Drop and recreate all test tables."""
    from models import Base

    Base.metadata.drop_all(bind=db_session.get_bind())
    Base.metadata.create_all(bind=db_session.get_bind())
